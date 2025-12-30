"""HungryPanda 日销售汇总计算路由（临时容器执行）"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, date, timedelta
from docker.errors import APIError
import os

from utils import client, LOG_DIR, ensure_image_exists, get_db_env_dict

router = APIRouter(prefix="/run", tags=["panda-summary"])


class PandaDailySummaryRequest(BaseModel):
    store_code: str | None = Field(None, description="英文店铺代码，或 'all'（默认 all）")
    stores: list[str] | None = Field(None, description="多个英文店铺代码数组，或包含 'all'")
    date: str | None = Field(None, description="单日 YYYY-MM-DD（优先级高于范围）")
    start_date: str | None = Field(None, description="开始日期 YYYY-MM-DD（与 end_date 组合使用）")
    end_date: str | None = Field(None, description="结束日期 YYYY-MM-DD（与 start_date 组合使用）")


@router.post("/panda/daily-summary")
def run_panda_daily_summary(req: PandaDailySummaryRequest):
    """
    创建临时容器计算 HungryPanda 每日销售汇总。
    
    - 从 orders 表读取订单数据并聚合计算
    - 默认跑所有店铺（--stores all）
    - 支持单店铺或多个店铺（英文代码）
    - 日期支持单日或范围，默认昨天
    - 日志写入到 /app/logs
    """
    # 确保镜像存在
    ensure_image_exists("dataautomaticengine-etl", "../etl")
    
    # 组装 stores 参数
    stores_arg = "all"
    if req.stores:
        if any(s.strip().lower() == "all" for s in req.stores):
            stores_arg = "all"
        else:
            stores_arg = ",".join([s.strip() for s in req.stores if s.strip()])
    elif req.store_code:
        stores_arg = "all" if req.store_code.strip().lower() == "all" else req.store_code.strip()
    
    # 组装 dates 参数
    if req.date:
        dates_arg = req.date.strip()
    elif req.start_date and req.end_date:
        dates_arg = f"{req.start_date.strip()},{req.end_date.strip()}"
    else:
        # 默认昨天
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        dates_arg = yesterday
    
    # 环境变量（数据库）
    env_dict = get_db_env_dict()
    
    # 日志与容器名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(LOG_DIR, f"panda_summary_{timestamp}.log")
    container_name = f"panda_summary_{timestamp}"
    
    # 覆盖命令：执行 ETL 脚本
    command = [
        "python", "panda_daily_summary.py",
        "--stores", stores_arg,
        "--dates", dates_arg,
    ]
    
    try:
        container = client.containers.run(
            image="dataautomaticengine-etl",
            name=container_name,
            environment=env_dict,
            network="dataautomaticengine_default",
            working_dir="/app",
            labels={
                "com.docker.compose.project": "dataautomaticengine",
                "com.docker.compose.service": "etl-temp"
            },
            command=command,
            remove=True,
            detach=True,
        )
        
        exit_code = container.wait()
        logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
        
        # 打印并写文件
        print(f"\n{'='*60}")
        print(f"[容器: {container_name}] HungryPanda 日销售汇总计算日志")
        print(f"{'='*60}")
        print(logs)
        print(f"{'='*60}\n")
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== HungryPanda Daily Summary Log ===\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Command: {' '.join(command)}\n")
            f.write(f"Exit Code: {exit_code}\n")
            f.write(f"Env: {env_dict}\n")
            f.write(f"======================================\n\n")
            f.write(logs)
        
        return {
            "status": "executed",
            "container_name": container_name,
            "container_id": container.id[:12],
            "exit_code": exit_code,
            "stores": stores_arg,
            "dates": dates_arg,
            "log_file": log_file,
            "output": logs,
        }
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"exec failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"error: {str(e)}")
