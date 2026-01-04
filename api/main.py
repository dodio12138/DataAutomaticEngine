"""FastAPI 应用主入口"""
from fastapi import FastAPI
from utils import get_db_conn
from routers import crawler, etl, reminder, feishu_bot, feishu_sync
from routers import deliveroo_summary, panda_summary, store_ratings, order_details, order_stats
from contextlib import asynccontextmanager
import threading
import nest_asyncio
import logging
import warnings

# 过滤 asyncio 的事件循环警告
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
warnings.filterwarnings('ignore', category=RuntimeWarning, module='asyncio')

# 全局应用 nest-asyncio 以解决事件循环嵌套问题
nest_asyncio.apply()
print("✅ nest_asyncio 已全局应用")
print("✅ asyncio 警告日志已过滤")


# 启动长链接服务
def start_ws_service():
    """在后台线程启动飞书长链接服务（独立事件循环）"""
    import sys
    import os
    
    # 过滤标准错误中的 RuntimeError 输出
    class FilteredStderr:
        def __init__(self, original):
            self.original = original
            self.buffer = ""
            
        def write(self, text):
            # 过滤包含 RuntimeError 和 Context 相关的错误
            if 'RuntimeError' in text and 'Context' in text:
                return
            if 'cannot enter context' in text:
                return
            if 'Event loop stopped before Future completed' in text:
                return
            self.original.write(text)
            
        def flush(self):
            self.original.flush()
    
    # 替换 stderr
    sys.stderr = FilteredStderr(sys.stderr)
    
    try:
        from services.feishu_bot.ws_service import ws_service
        print("🔌 启动飞书长链接服务（后台线程）...")
        # ws_service.start() 会在当前线程创建新的事件循环
        ws_service.start()
    except Exception as e:
        if 'cannot enter context' not in str(e) and 'Event loop stopped' not in str(e):
            print(f"⚠️  长链接服务启动失败: {e}")
            import traceback
            traceback.print_exc()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 在独立守护线程启动长链接服务（避免与 FastAPI 事件循环冲突）
    ws_thread = threading.Thread(target=start_ws_service, daemon=True, name="FeishuWebSocket")
    ws_thread.start()
    print("✅ 飞书长链接服务已在后台线程启动（机器人可随时问答）")
    
    yield
    
    # 关闭时：清理资源（守护线程会自动结束）
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
app.include_router(store_ratings.router)
app.include_router(order_details.router)
app.include_router(order_stats.router)
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
