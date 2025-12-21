"""ETL 相关路由"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from docker.errors import APIError
import os

from utils import client, LOG_DIR, ensure_image_exists, get_db_env_dict

router = APIRouter(prefix="/run", tags=["etl"])


@router.post("/etl")
def run_etl():
    """
    创建临时容器执行 ETL 任务，并保存日志。

    逻辑：
    - 检查镜像是否存在，不存在则自动构建
    - 构建环境变量（包括 DB 连接信息）
    - 创建临时容器执行 ETL（连接到 docker-compose 网络）
    - 保存日志到 /app/logs
    """
    # 确保镜像存在
    ensure_image_exists("dataautomaticengine-etl", "../etl")
    
    # 构建环境变量（包含 DB 环境变量）
    env_dict = get_db_env_dict()

    # 生成时间戳用于日志文件名和容器名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(LOG_DIR, f"etl_{timestamp}.log")
    container_name = f"etl_{timestamp}"  # 固定命名格式

    try:
        # 创建临时容器（连接到 docker-compose 网络）
        container = client.containers.run(
            image="dataautomaticengine-etl",  # 使用编译的镜像名
            name=container_name,  # 设置容器名
            environment=env_dict,
            network="dataautomaticengine_default",  # 连接到 docker-compose 网络
            working_dir="/app",
            remove=True,  # 执行完后自动删除容器
            detach=True  # 后台运行
        )
        
        # 等待容器执行完成
        exit_code = container.wait()
        
        # 获取完整日志
        logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
        
        # 实时打印日志到控制台
        print(f"\n{'='*60}")
        print(f"[容器: {container_name}] ETL 执行日志")
        print(f"{'='*60}")
        print(logs)
        print(f"{'='*60}\n")
        
        # 保存日志到文件
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== ETL Log ===\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Environment: {env_dict}\n")
            f.write(f"Exit Code: {exit_code}\n")
            f.write(f"===============\n\n")
            f.write(logs)
        
        return {
            "status": "etl executed",
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
