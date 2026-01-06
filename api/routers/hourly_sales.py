"""每小时销售数据 API 路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date, timedelta
from docker.errors import APIError
import os

from utils import client, LOG_DIR, ensure_image_exists, get_db_env_dict

router = APIRouter(prefix="/run", tags=["hourly-sales"])


class HourlySalesAggregateRequest(BaseModel):
    """每小时销售数据聚合请求"""
    start_date: str | None = Field(None, description="开始日期 YYYY-MM-DD（默认昨天）")
    end_date: str | None = Field(None, description="结束日期 YYYY-MM-DD（默认昨天）")
    date: str | None = Field(None, description="单个日期 YYYY-MM-DD（默认昨天）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-01-05"
            }
        }


class HourlySalesSyncRequest(BaseModel):
    """每小时销售数据飞书同步请求"""
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


@router.post("/hourly-sales/aggregate")
def aggregate_hourly_sales(req: HourlySalesAggregateRequest):
    """
    聚合每小时销售数据（ETL）
    
    - 从 orders 表（Deliveroo）和 raw_orders（HungryPanda）聚合数据
    - 按小时统计订单量和销售额
    - 存入 hourly_sales 表
    - 支持指定日期或日期范围
    - 默认处理昨天的数据
    """
    # 确保镜像存在
    ensure_image_exists("dataautomaticengine-etl", "../etl")
    
    # 环境变量（数据库）
    env_dict = get_db_env_dict()
    
    # 构建命令参数
    command = ["python", "hourly_sales.py"]
    
    if req.date:
        command.extend(["--date", req.date])
    else:
        if req.start_date:
            command.extend(["--start-date", req.start_date])
        if req.end_date:
            command.extend(["--end-date", req.end_date])
    
    # 生成日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"hourly_sales_aggregate_{timestamp}.log")
    
    try:
        # 创建并运行临时容器
        print(f"🚀 启动每小时销售数据聚合容器...")
        print(f"   命令: {' '.join(command)}")
        print(f"   日志: {log_file}")
        
        container = client.containers.run(
            image="dataautomaticengine-etl",
            command=command,
            environment=env_dict,
            network="dataautomaticengine_default",
            remove=False,  # 保留容器以便查看日志
            detach=True,
            name=f"hourly_sales_aggregate_{timestamp}"
        )
        
        # 等待容器完成
        result = container.wait()
        exit_code = result.get("StatusCode", 1)
        
        # 获取日志
        logs = container.logs().decode("utf-8")
        
        # 保存日志到文件
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(logs)
        
        # 删除容器
        container.remove()
        
        if exit_code == 0:
            return {
                "status": "success",
                "message": "每小时销售数据聚合完成",
                "container_name": container.name,
                "exit_code": exit_code,
                "output": logs,
                "log_file": log_file
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"聚合失败（退出码: {exit_code}），日志: {log_file}"
            )
    
    except APIError as e:
        raise HTTPException(status_code=500, detail=f"Docker 错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行错误: {str(e)}")


@router.post("/hourly-sales/sync-feishu")
def sync_hourly_sales_to_feishu(req: HourlySalesSyncRequest):
    """
    同步每小时销售数据到飞书多维表格
    
    - 从 hourly_sales 表读取数据
    - 同步到飞书多维表格（需配置 FEISHU_HOURLY_SALES_APP_TOKEN 和 TABLE_ID）
    - 支持指定日期或日期范围
    - 默认同步昨天的数据
    """
    # 确保镜像存在
    ensure_image_exists("dataautomaticengine-feishu-sync", "../feishu_sync")
    
    # 环境变量（数据库 + 飞书配置）
    env_dict = get_db_env_dict()
    env_dict.update({
        "FEISHU_APP_ID": os.environ.get("FEISHU_APP_ID", ""),
        "FEISHU_APP_SECRET": os.environ.get("FEISHU_APP_SECRET", ""),
        "FEISHU_HOURLY_SALES_APP_TOKEN": os.environ.get("FEISHU_HOURLY_SALES_APP_TOKEN", ""),
        "FEISHU_HOURLY_SALES_TABLE_ID": os.environ.get("FEISHU_HOURLY_SALES_TABLE_ID", ""),
    })
    
    # 构建命令参数
    command = ["python", "hourly_sales.py"]
    
    if req.date:
        command.extend(["--date", req.date])
    else:
        if req.start_date:
            command.extend(["--start-date", req.start_date])
        if req.end_date:
            command.extend(["--end-date", req.end_date])
    
    # 生成日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"hourly_sales_sync_{timestamp}.log")
    
    try:
        # 创建并运行临时容器
        print(f"🚀 启动每小时销售数据飞书同步容器...")
        print(f"   命令: {' '.join(command)}")
        print(f"   日志: {log_file}")
        
        container = client.containers.run(
            image="dataautomaticengine-feishu-sync",
            command=command,
            environment=env_dict,
            network="dataautomaticengine_default",
            remove=False,
            detach=True,
            name=f"hourly_sales_sync_{timestamp}"
        )
        
        # 等待容器完成
        result = container.wait()
        exit_code = result.get("StatusCode", 1)
        
        # 获取日志
        logs = container.logs().decode("utf-8")
        
        # 保存日志到文件
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(logs)
        
        # 删除容器
        container.remove()
        
        if exit_code == 0:
            return {
                "status": "success",
                "message": "每小时销售数据飞书同步完成",
                "container_name": container.name,
                "exit_code": exit_code,
                "output": logs,
                "log_file": log_file
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"同步失败（退出码: {exit_code}），日志: {log_file}"
            )
    
    except APIError as e:
        raise HTTPException(status_code=500, detail=f"Docker 错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行错误: {str(e)}")
