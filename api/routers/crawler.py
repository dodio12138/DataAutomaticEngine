"""爬虫相关路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from docker.errors import APIError
import os

from utils import client, LOG_DIR, ensure_image_exists, get_db_env_dict

router = APIRouter(prefix="/run", tags=["crawler"])


class CrawlerRequest(BaseModel):
    store_code: str = Field(None, description="英文店铺代码，如 towerbridge_maocai，或 'all'")
    store_codes: list[str] | None = Field(None, description="多个英文店铺代码数组，或包含 'all'")
    store_name: str = Field(None, description="中文店铺名，可选（单个）")
    start_date: str = Field(None, description="开始日期 YYYY-MM-DD")
    end_date: str = Field(None, description="结束日期 YYYY-MM-DD")


@router.post("/crawler")
def run_crawler(req: CrawlerRequest):
    """
    创建临时容器执行爬虫任务，并保存日志。

    逻辑：
    - 检查镜像是否存在，不存在则自动构建
    - 构建环境变量（包括 DB 连接信息）
    - 创建临时容器执行爬虫（连接到 docker compose 网络）
    - 保存日志到 /app/logs
    """
    # 确保镜像存在
    ensure_image_exists("dataautomaticengine-crawler", "../crawler")
    
    # 校验店铺入参：必须传入 store_code/store_codes/store_name 之一；支持 'all'
    has_store = bool(req.store_code or req.store_codes or req.store_name)
    if not has_store:
        raise HTTPException(status_code=400, detail="必须提供店铺：store_code、store_codes 或 store_name；支持 'all'")

    # 构建环境变量（包含 DB 环境变量）
    env_dict = get_db_env_dict()
    
    # 添加爬虫参数
    if req.store_codes:
        if any(code.strip().lower() == "all" for code in req.store_codes):
            env_dict["STORE_CODE"] = "all"
        else:
            env_dict["STORE_CODES"] = ",".join(req.store_codes)
    elif req.store_code:
        if req.store_code.strip().lower() == "all":
            env_dict["STORE_CODE"] = "all"
        else:
            env_dict["STORE_CODE"] = req.store_code
    elif req.store_name:
        env_dict["STORE_NAME"] = req.store_name

    if req.start_date:
        env_dict["START_DATE"] = req.start_date
    if req.end_date:
        env_dict["END_DATE"] = req.end_date

    # 生成时间戳用于日志文件名和容器名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(LOG_DIR, f"crawler_{timestamp}.log")
    container_name = f"crawler_{timestamp}"  # 固定命名格式

    try:
        # 创建临时容器（连接到 docker compose 网络）
        container = client.containers.run(
            image="dataautomaticengine-crawler",  # 使用编译的镜像名
            name=container_name,  # 设置容器名
            environment=env_dict,
            network="dataautomaticengine_default",  # 连接到 docker compose 网络
            volumes={"/var/lib/postgresql": {"bind": "/var/lib/postgresql", "mode": "ro"}},
            working_dir="/app",
            shm_size="1g",  # 设置共享内存大小为 2GB，确保 Chrome/Selenium 有足够内存
            labels={
                "com.docker.compose.project": "dataautomaticengine",
                "com.docker.compose.service": "crawler-temp"
            },
            remove=True,  # 执行完后自动删除容器
            detach=True  # 后台运行
        )
        
        # 等待容器执行完成
        exit_code = container.wait()
        
        # 获取完整日志
        logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
        
        # 实时打印日志到控制台
        print(f"\n{'='*60}")
        print(f"[容器: {container_name}] 爬虫执行日志")
        print(f"{'='*60}")
        print(logs)
        print(f"{'='*60}\n")
        
        # 保存日志到文件
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Crawler Log ===\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Parameters: {env_dict}\n")
            f.write(f"Exit Code: {exit_code}\n")
            f.write(f"===================\n\n")
            f.write(logs)
        
        return {
            "status": "crawler executed",
            "container_id": container.id[:12],
            "container_name": container_name,
            "exit_code": exit_code,
            "output": logs,
            "log_file": log_file,
            "env": env_dict,
        }
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"exec failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"error: {str(e)}")
