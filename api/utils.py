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


def ensure_image_exists(image_name: str, dockerfile_path: str = None):
    """
    检查 Docker 镜像是否存在，不存在则自动构建
    
    Args:
        image_name: 镜像名称，如 'dataautomaticengine-feishu-sync'
        dockerfile_path: Dockerfile 所在目录的相对路径（相对于项目根目录）
                        如 'feishu_sync' 或 'crawler'
    
    注意：需要在 docker-compose.yaml 中挂载项目根目录到 /workspace
    """
    try:
        client.images.get(image_name)
        # 镜像存在
        print(f"✅ 镜像 {image_name} 已存在")
        return
    except ImageNotFound:
        # 镜像不存在，自动构建
        if not dockerfile_path:
            service_name = image_name.replace('dataautomaticengine-', '')
            dockerfile_path = service_name.replace('-', '_')  # 转换名称，如 feishu-sync -> feishu_sync
        
        # 使用 /workspace 作为基础路径（项目根目录）
        build_path = f"/workspace/{dockerfile_path}"
        
        print(f"⚠️  镜像 {image_name} 不存在")
        print(f"🔨 开始自动构建镜像...")
        print(f"📁 构建路径: {build_path}")
        
        try:
            # 构建镜像
            image, build_logs = client.images.build(
                path=build_path,
                tag=image_name,
                rm=True,  # 删除中间容器
                forcerm=True  # 即使构建失败也删除中间容器
            )
            
            # 打印构建日志
            for log in build_logs:
                if 'stream' in log:
                    print(log['stream'].strip())
            
            print(f"✅ 镜像 {image_name} 构建成功")
            
        except BuildError as e:
            error_msg = f"构建镜像失败: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"构建过程出错: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)


def get_db_env_dict():
    """获取数据库环境变量字典"""
    return {
        "DB_HOST": os.environ.get("DB_HOST", "db"),
        "DB_PORT": os.environ.get("DB_PORT", "5432"),
        "DB_NAME": os.environ.get("DB_NAME", "delivery_data"),
        "DB_USER": os.environ.get("DB_USER", "delivery_user"),
        "DB_PASSWORD": os.environ.get("DB_PASSWORD", "delivery_pass"),
    }
