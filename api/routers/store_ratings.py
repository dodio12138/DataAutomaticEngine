"""
店铺评分 API 路由（临时容器执行）
提供 Deliveroo 店铺评分爬取接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from docker.errors import APIError
import os

from utils import client, LOG_DIR, ensure_image_exists, get_db_env_dict

router = APIRouter(prefix="/run", tags=["store-ratings"])


class StoreRatingsRequest(BaseModel):
    """评分爬取请求模型"""
    store_code: str | None = Field(None, description="英文店铺代码，或 'all'（默认 all）")
    stores: list[str] | None = Field(None, description="多个英文店铺代码数组，或包含 'all'")

    class Config:
        json_schema_extra = {
            "example": {
                "stores": ["battersea_maocai", "brent_maocai"]
            }
        }


@router.post("/store-ratings")
def run_store_ratings_crawler(req: StoreRatingsRequest):
    """
    创建临时容器运行 Deliveroo 店铺评分爬虫。
    
    - 默认跑所有店铺（--stores all）
    - 支持单店铺或多个店铺（英文代码）
    - 评分数据为实时，记录日期为前一天
    - 日志写入到 /app/logs
    """
    # 确保镜像存在
    ensure_image_exists("dataautomaticengine-crawler", "../crawler")
    
    # 组装 stores 参数
    stores_arg = "all"
    if req.stores:
        if any(s.strip().lower() == "all" for s in req.stores):
            stores_arg = "all"
        else:
            stores_arg = ",".join([s.strip() for s in req.stores if s.strip()])
    elif req.store_code:
        stores_arg = "all" if req.store_code.strip().lower() == "all" else req.store_code.strip()
    
    # 环境变量（数据库）
    env_dict = get_db_env_dict()
    
    # 日志与容器名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(LOG_DIR, f"ratings_{timestamp}.log")
    container_name = f"ratings_{timestamp}"
    
    # 覆盖命令：执行批量脚本
    command = [
        "python", "run_store_ratings.py",
        "--stores", stores_arg,
    ]
    
    try:
        container = client.containers.run(
            image="dataautomaticengine-crawler",
            name=container_name,
            environment=env_dict,
            network="dataautomaticengine_default",
            working_dir="/app",
            shm_size="1g",
            labels={
                "com.docker.compose.project": "dataautomaticengine",
                "com.docker.compose.service": "crawler-temp"
            },
            command=command,  # 覆盖默认 CMD
            remove=True,
            detach=True,
        )
        
        exit_code = container.wait()
        logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
        
        # 打印并写文件
        print(f"\n{'='*60}")
        print(f"[容器: {container_name}] 店铺评分爬虫执行日志")
        print(f"{'='*60}")
        print(logs)
        print(f"{'='*60}\n")
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Store Ratings Crawler Log ===\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Command: {' '.join(command)}\n")
            f.write(f"Exit Code: {exit_code}\n")
            f.write(f"Env: {env_dict}\n")
            f.write(f"===================================\n\n")
            f.write(logs)
        
        return {
            "status": "executed",
            "container_name": container_name,
            "container_id": container.id[:12],
            "exit_code": exit_code,
            "stores": stores_arg,
            "log_file": log_file,
            "output": logs,
        }
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"exec failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"error: {str(e)}")

@router.get("/store-ratings/history")
async def get_ratings_history(
    store_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """
    查询历史评分数据
    
    - **store_code**: 店铺代码（可选）
    - **start_date**: 开始日期（可选）
    - **end_date**: 结束日期（可选）
    - **limit**: 返回记录数（默认100）
    """
    import psycopg2
    from utils import get_db_connection
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询
        query = """
        SELECT 
            date, store_code, store_name, platform,
            average_rating, rating_count,
            five_star_count, four_star_count, three_star_count,
            two_star_count, one_star_count,
            created_at, updated_at
        FROM store_ratings
        WHERE 1=1
        """
        params = []
        
        if store_code:
            query += " AND store_code = %s"
            params.append(store_code)
        
        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)
        
        query += " ORDER BY date DESC, store_code LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 格式化结果
        results = []
        for row in rows:
            results.append({
                "date": row[0].strftime("%Y-%m-%d"),
                "store_code": row[1],
                "store_name": row[2],
                "platform": row[3],
                "average_rating": float(row[4]) if row[4] else None,
                "rating_count": row[5],
                "rating_breakdown": {
                    "five_star": row[6],
                    "four_star": row[7],
                    "three_star": row[8],
                    "two_star": row[9],
                    "one_star": row[10]
                },
                "created_at": row[11].isoformat() if row[11] else None,
                "updated_at": row[12].isoformat() if row[12] else None
            })
        
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "count": len(results),
            "data": results
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"查询失败: {str(e)}"
        )
