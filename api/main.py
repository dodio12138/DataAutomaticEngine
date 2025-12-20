from fastapi import FastAPI, HTTPException
import docker
from docker.errors import ImageNotFound, APIError, NotFound
import psycopg2
import os
from docker.errors import DockerException

app = FastAPI()
client = docker.from_env()


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "delivery_data"),
        user=os.environ.get("DB_USER", "delivery_user"),
        password=os.environ.get("DB_PASSWORD", "delivery_pass"),
        connect_timeout=2,
    )


@app.get("/health")
def health():
    """健康检查：返回服务状态并尝试连接数据库。"""
    db_status = "ok"
    detail = None
    try:
        conn = get_conn()
        conn.close()
    except Exception as e:
        db_status = "error"
        detail = str(e)

    status = "ok" if db_status == "ok" else "error"
    resp = {"status": status, "db": db_status}
    if detail:
        resp["detail"] = detail
    return resp


@app.post("/run/crawler")
def run_crawler():
    """启动 docker-compose 定义的 crawler 容器（delivery_crawler），而非按镜像新建容器。"""
    container_name = "delivery_crawler"
    try:
        # 尝试按容器名获取已存在的 compose 容器
        container = client.containers.get(container_name)
        if container.status != "running":
            container.start()
        cid = getattr(container, "id", str(container))
        return {"status": "crawler started", "container_id": cid, "was_running": container.status == "running"}
    except NotFound:
        # 容器不存在（未用 compose 创建），提示用户使用 docker compose up
        raise HTTPException(status_code=404, detail=(
            f"compose-managed container '{container_name}' not found. "
            "Please create it with: 'docker compose up -d crawler'"
        ))
    except DockerException as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/run/etl")
def run_etl():
    """启动 docker-compose 定义的 etl 容器（delivery_etl），而非按镜像新建容器。"""
    container_name = "delivery_etl"
    try:
        container = client.containers.get(container_name)
        if container.status != "running":
            container.start()
        cid = getattr(container, "id", str(container))
        return {"status": "etl started", "container_id": cid, "was_running": container.status == "running"}
    except NotFound:
        raise HTTPException(status_code=404, detail=(
            f"compose-managed container '{container_name}' not found. "
            "Please create it with: 'docker compose up -d etl'"
        ))
    except DockerException as e:
        raise HTTPException(status_code=502, detail=str(e))
