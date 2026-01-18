"""店铺评分数据飞书同步 API 路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date, timedelta
from docker.errors import APIError
import os

from utils import client, LOG_DIR, ensure_image_exists, get_db_env_dict

router = APIRouter(prefix="/run", tags=["store-ratings-sync"])


class StoreRatingsSyncRequest(BaseModel):
    """店铺评分数据飞书同步请求"""
    start_date: str | None = Field(None, description="开始日期 YYYY-MM-DD（默认昨天）")
    end_date: str | None = Field(None, description="结束日期 YYYY-MM-DD（默认昨天）")
    date: str | None = Field(None, description="单个日期 YYYY-MM-DD（默认昨天）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2026-01-01",
                "end_date": "2026-01-05"
            }
        }


@router.post("/store-ratings/sync-feishu")
def sync_store_ratings_to_feishu(req: StoreRatingsSyncRequest):
    """
    同步店铺评分数据到飞书多维表格
    
    - 从 store_ratings 表读取数据
    - 同步到飞书多维表格
    - 使用"日期_店铺代码_平台"作为唯一键，已存在则更新，不存在则创建
    - 支持指定日期或日期范围
    - 默认同步昨天的数据（用于定时任务增量同步）
    """
    # 确保镜像存在
    ensure_image_exists("dataautomaticengine-feishu_sync", "./feishu_sync")
    
    # 环境变量（数据库 + 飞书配置）
    env_dict = get_db_env_dict()
    
    # 添加飞书配置
    feishu_config = {
        "FEISHU_APP_ID": os.environ.get("FEISHU_APP_ID"),
        "FEISHU_APP_SECRET": os.environ.get("FEISHU_APP_SECRET"),
        "FEISHU_RATINGS_APP_TOKEN": os.environ.get("FEISHU_RATINGS_APP_TOKEN"),
        "FEISHU_RATINGS_TABLE_ID": os.environ.get("FEISHU_RATINGS_TABLE_ID"),
    }
    env_dict.update(feishu_config)
    
    # 构建命令参数
    command = ["python", "store_ratings.py"]
    
    if req.date:
        command.extend(["--date", req.date])
    else:
        if req.start_date:
            command.extend(["--start-date", req.start_date])
        if req.end_date:
            command.extend(["--end-date", req.end_date])
    
    # 生成日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"store_ratings_sync_{timestamp}.log")
    
    try:
        # 创建并运行临时容器
        print(f"🚀 启动店铺评分飞书同步容器...")
        print(f"   命令: {' '.join(command)}")
        print(f"   日志: {log_file}")
        
        container = client.containers.run(
            image="dataautomaticengine-feishu_sync",
            command=command,
            environment=env_dict,
            network="dataautomaticengine_default",
            remove=False,  # 保留容器以便查看日志
            detach=True,
            name=f"store_ratings_sync_{timestamp}"
        )
        
        # 等待容器完成
        result = container.wait()
        exit_code = result.get("StatusCode", 1)
        
        # 获取日志
        logs = container.logs().decode("utf-8")
        
        # 保存日志到文件
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(logs)
        
        # 清理容器
        try:
            container.remove(force=True)
        except:
            pass
        
        if exit_code == 0:
            # 解析日志统计
            stats = _parse_sync_stats(logs)
            
            return {
                "success": True,
                "message": "店铺评分数据同步完成",
                "log_file": log_file,
                "stats": stats,
                "logs": logs
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"飞书同步失败（退出码 {exit_code}），详见日志: {log_file}\n\n{logs}"
            )
    
    except APIError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Docker API 错误: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"飞书同步失败: {str(e)}"
        )


def _parse_sync_stats(logs: str) -> dict:
    """从日志中解析同步统计信息"""
    stats = {
        "created": 0,
        "updated": 0,
        "failed": 0,
        "total": 0
    }
    
    try:
        for line in logs.split("\n"):
            if "✅ 创建:" in line:
                stats["created"] = int(line.split(":")[1].strip().split()[0])
            elif "🔄 更新:" in line:
                stats["updated"] = int(line.split(":")[1].strip().split()[0])
            elif "❌ 失败:" in line:
                stats["failed"] = int(line.split(":")[1].strip().split()[0])
            elif "📝 总计:" in line:
                stats["total"] = int(line.split(":")[1].strip().split()[0])
    except:
        pass
    
    return stats
