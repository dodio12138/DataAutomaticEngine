# API 模块化架构说明

## 目录结构

```
api/
├── main.py                    # FastAPI 应用主入口
├── utils.py                   # 通用工具函数（数据库连接、Docker 操作等）
├── routers/                   # 路由层（只负责 HTTP 请求/响应处理）
│   ├── __init__.py
│   ├── crawler.py             # 爬虫任务路由
│   ├── etl.py                 # ETL 任务路由
│   └── feishu.py              # 飞书机器人路由
├── services/                  # 业务逻辑层（核心功能实现）
│   ├── __init__.py
│   ├── feishu_service.py      # 飞书消息发送服务
│   └── report_service.py      # 报告生成服务
└── logs/                      # 日志目录
```

## 分层职责

### 1. Routers 层（路由层）
**职责：** 处理 HTTP 请求和响应
- 参数验证
- 调用 Service 层执行业务逻辑
- 格式化 HTTP 响应
- 异常处理

**示例：** `routers/feishu.py`
```python
@router.post("/reminder/daily-summary")
def send_daily_summary_reminder():
    summary = report_service.generate_daily_summary_text()
    result = feishu_service.send_with_default_webhook(summary)
    if result['success']:
        return {'status': 'ok', 'message': '每日汇总已发送'}
    raise HTTPException(status_code=500, detail=result['error'])
```

### 2. Services 层（业务逻辑层）
**职责：** 实现核心业务逻辑
- 数据处理
- 外部 API 调用
- 业务规则实现
- 可被多个路由复用

**示例：** `services/feishu_service.py`
```python
def send_message(webhook_url: str, message: str) -> dict:
    """发送消息到飞书"""
    # 具体实现...
    
def send_with_default_webhook(message: str) -> dict:
    """使用默认配置发送消息"""
    # 具体实现...
```

**示例：** `services/report_service.py`
```python
def query_order_summary(date_str: str, store_name: Optional[str] = None) -> dict:
    """查询订单汇总数据"""
    # 数据库查询逻辑...
    
def generate_daily_summary_text(date_str: Optional[str] = None) -> str:
    """生成每日汇总报告文本"""
    # 格式化报告逻辑...
```

### 3. Utils 层（工具层）
**职责：** 提供通用工具函数
- 数据库连接
- Docker 客户端操作
- 环境变量处理
- 日志管理

## 飞书提醒功能 API

### 1. 每日汇总提醒
```bash
POST /feishu/reminder/daily-summary
```
发送昨日订单汇总报告到飞书群

### 2. 自定义提醒
```bash
POST /feishu/reminder/custom?message=你的消息内容
```
发送自定义消息到飞书群

### 3. 手动查询
```bash
POST /feishu/query?store_name=Battersea&date=2025-12-20
```
查询指定店铺的订单数据

## 定时任务配置

在 `scheduler/crontab` 中配置：

```cron
# 每天早上9点发送昨日汇总
0 9 * * * curl -s -X POST http://api:8000/feishu/reminder/daily-summary

# 每10分钟执行爬虫
*/10 * * * * curl -s -X POST http://api:8000/run/crawler -H "Content-Type: application/json" -d '{"store_code":"all"}'
```

## 环境变量配置

在 `.env` 文件中配置飞书 Webhook：

```bash
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-url-here
```

## 模块化优势

1. **代码清晰：** 每个模块职责单一，易于理解和维护
2. **易于测试：** Service 层可独立测试，不依赖 HTTP 框架
3. **复用性高：** Service 层可被多个路由复用
4. **扩展方便：** 新增功能只需添加新的 Service 和 Router
5. **团队协作：** 不同开发者可并行开发不同模块
