"""Deliveroo 订单详情导入路由（临时容器执行）"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from docker.errors import APIError
import os

from utils import client, LOG_DIR, ensure_image_exists, get_db_env_dict

router = APIRouter(prefix="/run", tags=["order-details"])


class OrderDetailsImportRequest(BaseModel):
    limit: int | None = Field(None, description="限制导入数量（None=全部）")
    platform: str = Field("deliveroo", description="平台名称（默认 deliveroo）")
    days: int | None = Field(None, description="导入最近N天的订单（增量导入）")
    start_date: str | None = Field(None, description="从指定日期开始导入（YYYY-MM-DD）")


@router.post("/import-order-details")
def import_order_details(req: OrderDetailsImportRequest):
    """
    创建临时容器导入订单详情数据。
    
    - 从 raw_orders 表解析 JSON 并导入到 orders/order_items/order_item_modifiers 表
    - 支持限制导入数量（测试用）
    - 支持增量导入：只导入最近N天的新订单
    - 自动排除已导入的订单（避免重复）
    - 日志写入到 /app/logs
    
    增量导入示例：
    - {"days": 1} - 导入最近1天的新订单（每日定时任务）
    - {"days": 7} - 导入最近7天的新订单
    - {"start_date": "2025-12-20"} - 导入从指定日期开始的新订单
    """
    # 确保镜像存在
    ensure_image_exists("dataautomaticengine-etl", "../etl")
    
    # 环境变量（数据库）
    env_dict = get_db_env_dict()
    
    # 添加导入参数
    if req.limit:
        env_dict['IMPORT_LIMIT'] = str(req.limit)
    if req.days:
        env_dict['IMPORT_DAYS'] = str(req.days)
    if req.start_date:
        env_dict['IMPORT_START_DATE'] = req.start_date
    env_dict['IMPORT_PLATFORM'] = req.platform
    
    # 日志与容器名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(LOG_DIR, f"order_details_import_{timestamp}.log")
    container_name = f"order_details_import_{timestamp}"
    
    # 命令：执行导入脚本
    command = ["python", "import_order_details.py"]
    if req.limit:
        command.append(str(req.limit))
    elif req.days:
        command.append(f"days={req.days}")
    elif req.start_date:
        command.append(req.start_date)
    
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
            remove=False,  # 先不删除，等获取日志后再删
            detach=True,
        )
        
        # 等待容器执行完成
        result = container.wait()
        exit_code = result.get('StatusCode', 0)
        
        # 获取日志
        logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
        
        # 删除容器
        try:
            container.remove()
        except:
            pass
        
        # 打印并写文件
        print(f"\n{'='*60}")
        print(f"[容器: {container_name}] 订单详情导入日志")
        print(f"{'='*60}")
        print(logs)
        print(f"{'='*60}\n")
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Order Details Import Log ===\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Platform: {req.platform}\n")
            f.write(f"Limit: {req.limit or 'ALL'}\n")
            f.write(f"Days: {req.days or 'N/A'}\n")
            f.write(f"Start Date: {req.start_date or 'N/A'}\n")
            f.write(f"Command: {' '.join(command)}\n")
            f.write(f"Exit Code: {exit_code}\n")
            f.write(f"================================\n\n")
            f.write(logs)
        
        return {
            "status": "executed",
            "container_name": container_name,
            "container_id": container.id[:12],
            "exit_code": exit_code,
            "platform": req.platform,
            "limit": req.limit or "all",
            "days": req.days,
            "start_date": req.start_date,
            "log_file": log_file,
            "output": logs,
        }
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"Docker exec failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import error: {str(e)}")
