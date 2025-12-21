"""通用工具函数"""
import os
import docker
from docker.errors import ImageNotFound, BuildError
import psycopg2

client = docker.from_env()

# 日志存储目录
LOG_DIR = "/app/logs"
os.makedirs(LOG_DIR, exist_ok=True)


def get_db_conn():
    """获取数据库连接"""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "delivery_data"),
        user=os.environ.get("DB_USER", "delivery_user"),
        password=os.environ.get("DB_PASSWORD", "delivery_pass"),
        connect_timeout=2,
    )


def ensure_image_exists(image_name: str, dockerfile_path: str):
    """检查镜像是否存在，不存在则构建"""
    try:
        client.images.get(image_name)
        # 镜像存在
        return
    except ImageNotFound:
        # 镜像不存在，自动构建
        print(f"镜像 {image_name} 不存在，正在构建...")
        try:
            client.images.build(
                path=dockerfile_path,
                tag=image_name,
                quiet=False
            )
            print(f"镜像 {image_name} 构建成功")
        except BuildError as e:
            raise RuntimeError(f"构建镜像失败: {str(e)}")


def get_db_env_dict():
    """获取数据库环境变量字典"""
    return {
        "DB_HOST": os.environ.get("DB_HOST", "db"),
        "DB_PORT": os.environ.get("DB_PORT", "5432"),
        "DB_NAME": os.environ.get("DB_NAME", "delivery_data"),
        "DB_USER": os.environ.get("DB_USER", "delivery_user"),
        "DB_PASSWORD": os.environ.get("DB_PASSWORD", "delivery_pass"),
    }
