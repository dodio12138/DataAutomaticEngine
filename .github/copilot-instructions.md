# Haidilao Data Automatic Engine - AI Coding Agent Guide

## Project Overview
海底捞数据自动化引擎是一个多层级数据采集、处理与分析平台，专为外卖订单数据的自动爬取、ETL处理与实时查询而设计。采用微服务架构，以Docker容器化部署。

**核心数据流：** HungryPanda/Deliveroo → Selenium爬虫 → PostgreSQL → ETL处理 → FastAPI服务 → 飞书通知

## Architecture & Core Components

### Service Layer (Docker Containers)
- **API (FastAPI)** - 控制层，暴露 `/run/crawler` 和 `/run/etl` 端点；支持Feishu Webhook回调处理
- **Crawler (Selenium)** - 爬虫层，使用 Selenium/Chrome 从 HungryPanda/Deliveroo 抓取订单原始数据，存入 `raw_orders` 表
- **ETL** - 数据处理层，解析原始订单 JSON，标准化数据结构，入库 `orders` 和 `order_items` 表
- **Scheduler (cron)** - 定时调度层，运行 crontab 任务周期性触发爬虫/ETL
- **Database (PostgreSQL)** - 数据持久化层，所有服务共享

### Data Layer (PostgreSQL)
核心表结构见 [db/init.sql](db/init.sql)：
- `stores` - 店铺元数据与平台映射（平台英文代码、店铺ID、登录凭证）
- `raw_orders` - 原始订单JSON（platform, store_code, order_id, payload）
- `orders` / `order_items` - 标准化订单与菜品明细（后续ETL阶段创建）

## Critical Developer Workflows

### Local Development & Debugging
1. **启动完整堆栈：**
   ```bash
   docker-compose up -d
   # API 可访问 http://localhost:8000
   # PostgreSQL 可访问 localhost:5432
   ```

2. **触发爬虫任务（通过API）：**
   ```bash
   curl -X POST http://localhost:8000/run/crawler \
     -H "Content-Type: application/json" \
     -d '{"store_code":"battersea_maocai","start_date":"2025-12-20"}'
   ```

3. **监控日志：**
   - API容器日志：`docker logs delivery_api`
   - 爬虫日志：`tail -f api/logs/crawler_*.log`（临时容器的输出）
   - 数据库连接问题：检查 `.env` 中的 `DB_HOST/DB_PORT/DB_NAME` 是否与 docker-compose.yaml 一致

### Docker Network Communication
- API、Crawler、ETL 通过 `dataautomaticengine_default` 网络通信
- 从容器内部连接数据库：使用 `DB_HOST=db`（docker-compose 服务名）
- 从主机连接数据库：使用 `DB_HOST=localhost` 或 `127.0.0.1`
- **关键：** API容器挂载 `/var/run/docker.sock` 以支持动态容器创建

### Store Configuration & Multi-Tenant Pattern
店铺管理采用配置驱动：
- 英文代码映射：`crawdler/store_config.py` 中定义 `store_code_map`、`store_name_to_code`、`store_dict_panda`、`store_dict_deliveroo`
- 爬虫支持 `store_code='all'` 或 `store_codes=['code1','code2']` 批量执行
- 环境变量解析：爬虫 [main.py](crawler/main.py) 中 `_resolve_stores_from_env()` 负责将前端参数转换为店铺代码列表

## Project-Specific Patterns & Conventions

### 1. Router Modularization (api/)
所有API路由按功能模块划分到 `api/routers/` 子目录，main.py 仅负责路由注册：
```python
# api/main.py
app.include_router(crawler.router)  # prefix="/run"
app.include_router(etl.router)      # prefix="/run"
app.include_router(feishu.router)   # prefix="/feishu"
```
**约定：** 新增功能（如报表API）应在 `routers/` 下创建新文件，实现模块化隔离。

### 2. Temporary Docker Container Pattern
API 不直接执行爬虫，而是创建临时容器并立即删除（`remove=True`）：
```python
# api/routers/crawler.py
container = client.containers.run(
    image="dataautomaticengine-crawler",
    environment=env_dict,          # 注入 DB_HOST, DB_NAME 等
    network="dataautomaticengine_default",
    remove=True,                   # 自动清理
    detach=True                    # 异步执行
)
```
**目的：** 隔离爬虫进程、便于资源管理、支持并发任务。

### 3. Environment Variable Driven Configuration
所有跨容器通信依赖环境变量，避免硬编码：
- `.env` 文件定义全局变量（DB_HOST, DB_NAME, 登录凭证等）
- `api/utils.py` 中 `get_db_env_dict()` 统一构建数据库环境变量字典
- **约定：** 新增配置项应先在 `.env` 中定义，再通过代码读取

### 4. Store Code Mapping (3-Layer Resolution)
爬虫支持三种店铺指定方式（优先级递减）：
```python
# crawler/main.py
STORE_CODES (逗号分隔)  → _resolve_stores_from_env() → 英文代码列表
STORE_CODE (单个或 'all')
STORE_NAME (中文名)  → 通过 store_name_to_code 映射
```
**原因：** 前端（飞书命令）可能提供中文店铺名，需要映射到爬虫可用的英文代码。

### 5. Log Aggregation & Persistence
所有临时容器的日志持久化到主机：
```python
log_file = os.path.join(LOG_DIR, f"crawler_{timestamp}.log")
# LOG_DIR = "/app/logs" → 挂载 docker-compose 的 ./api/logs
```
**约定：** 容器失败时，从 `api/logs/` 目录查看历史日志，日志文件名格式为 `{service}_{YYYYMMDD_HHMMSS}.log`

### 6. Feishu Integration (Long Connection & Webhook)
飞书支持两种通信模式：
- **Webhook（被动）：** 飞书群 → HTTP POST → `/feishu/webhook` → 数据库查询
- **Long Connection（主动）：** API 周期性 POST 到 `/feishu/long-connection/start` 推送数据

见 [api/routers/feishu.py](api/routers/feishu.py) 中 `parse_query_command()` 和 `query_order_count()` 的实现。

## Integration Points & External Dependencies

### External Services
- **HungryPanda 平台：** Selenium 登录后通过 XHR 拉取订单数据（见 `crawler/services/panda/`）
- **Deliveroo 平台：** API 集成（待实现，目前代码结构已预留）
- **Feishu 群机器人：** 
  - 接收消息：Webhook 回调（Feishu → API）
  - 发送消息：HTTP POST 到飞书 API 端点

### Database Schema Dependencies
新增订单字段时需同步更新：
1. `raw_orders.payload` JSONB 结构（爬虫存入）
2. `orders` / `order_items` 表结构（ETL解析后入库）
3. ETL 解析逻辑（`etl/parsers/panda_parser.py` 等）

### Environment Variables (Critical)
```bash
# .env
DB_HOST=db                      # Docker 容器内访问
DB_PORT=5432
DB_NAME=delivery_data
DB_USER=delivery_user
DB_PASSWORD=delivery_pass

# Optional: Feishu Bot Token
FEISHU_BOT_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

## Code Style & Conventions

1. **Module Organization:** 功能按文件隔离，避免单一超大文件（参考 [REFACTOR.md](api/REFACTOR.md)）
2. **Function Naming：** 模块级函数使用英文蛇形命名（`get_db_conn`, `ensure_image_exists`）
3. **Database Access：** 所有数据库操作通过 `utils.get_db_conn()` 获取连接，使用 `cursor.execute()` 的参数化查询防止 SQL 注入
4. **Error Handling：** 数据库异常捕获、容器启动失败、网络超时需返回 HTTP 异常而非宕机
5. **Logging：** 使用 `print()` 到 stdout，日志由 Docker 捕获并持久化

## Common Pitfalls & Solutions

| 问题 | 原因 | 解决方案 |
|-----|------|--------|
| `DB connection timeout` | 容器内 DB_HOST 错误或数据库未启动 | 检查 .env 中 DB_HOST=db，确保 `docker-compose up` 时 db 容器健康 |
| `Image not found` | 镜像未构建 | API 的 `ensure_image_exists()` 会自动构建，或手动 `docker build` |
| `Network error in crawler` | Selenium 网络隔离 | Crawler 容器需共享宿主网络或配置代理 |
| `Store code not found` | store_code_map 中无此映射 | 在 [store_config.py](crawler/store_config.py) 中新增店铺映射 |
| `Feishu webhook 403` | Bot Token 过期或无权限 | 检查 `.env` 中 FEISHU_BOT_WEBHOOK_URL 是否有效 |

## References
- 架构详解：[struct.MD](struct.MD)
- API 重构说明：[api/REFACTOR.md](api/REFACTOR.md)
- 店铺配置：[crawler/store_config.py](crawler/store_config.py)
- 数据库初始化：[db/init.sql](db/init.sql)
