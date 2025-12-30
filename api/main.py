"""FastAPI 应用主入口"""
from fastapi import FastAPI
from utils import get_db_conn
from routers import crawler, etl, reminder, feishu_bot, feishu_sync
from routers import deliveroo_summary, panda_summary
from contextlib import asynccontextmanager
import threading
import nest_asyncio

# 全局应用 nest-asyncio 以解决事件循环嵌套问题
nest_asyncio.apply()
print("✅ nest_asyncio 已全局应用")


# 启动长链接服务
def start_ws_service():
    """在后台线程启动飞书长链接服务（独立事件循环）"""
    try:
        from services.feishu_bot.ws_service import ws_service
        print("🔌 启动飞书长链接服务（后台线程）...")
        # ws_service.start() 会在当前线程创建新的事件循环
        ws_service.start()
    except Exception as e:
        print(f"⚠️  长链接服务启动失败: {e}")
        import traceback
        traceback.print_exc()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：在后台线程启动长链接服务
    ws_thread = threading.Thread(target=start_ws_service, daemon=True)
    ws_thread.start()
    print("✅ 飞书长链接服务已在后台启动")
    
    yield
    
    # 关闭时：清理资源（长链接会随守护线程自动结束）
    print("🛑 API 服务关闭")


app = FastAPI(
    title="数据自动化引擎 API",
    description="海底捞数据爬取与 ETL 处理服务",
    version="1.0.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(crawler.router)
app.include_router(deliveroo_summary.router)
app.include_router(panda_summary.router)
app.include_router(etl.router)
app.include_router(reminder.router)
app.include_router(feishu_bot.router)
app.include_router(feishu_sync.router)


@app.get("/")
def root():
    """根路径"""
    return {
        "service": "DataAutomaticEngine API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "crawler": "/run/crawler",
            "feishu_sync": "/run/feishu-sync",
            "etl": "/run/etl",
            "reminder": "/reminder/*",
            "feishu_bot": "/feishu/bot/*"
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
