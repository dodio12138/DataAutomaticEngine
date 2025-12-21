"""FastAPI 应用主入口"""
from fastapi import FastAPI
from utils import get_db_conn
from routers import crawler, etl, reminder

app = FastAPI(
    title="数据自动化引擎 API",
    description="海底捞数据爬取与 ETL 处理服务",
    version="1.0.0"
)

# 注册路由
app.include_router(crawler.router)
app.include_router(etl.router)
app.include_router(reminder.router)


@app.get("/")
def root():
    """根路径"""
    return {
        "service": "DataAutomaticEngine API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "crawler": "/run/crawler",
            "etl": "/run/etl",
            "reminder": "/reminder/*"
        }
    }


@app.get("/health")
def health():
    """健康检查：返回服务状态并尝试连接数据库"""
    db_status = "ok"
    detail = None
    try:
        conn = get_db_conn()
        conn.close()
    except Exception as e:
        db_status = "error"
        detail = str(e)

    status = "ok" if db_status == "ok" else "error"
    resp = {"status": status, "db": db_status}
    if detail:
        resp["detail"] = detail
    return resp
