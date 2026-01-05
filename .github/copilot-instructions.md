# Haidilao Data Automatic Engine - AI Coding Agent Guide

## Project Overview
海底捞数据自动化引擎是一个多层级数据采集、处理与分析平台，专为外卖订单数据的自动爬取、ETL处理与实时查询而设计。采用微服务架构，以Docker容器化部署。

**核心数据流：** HungryPanda/Deliveroo → Selenium爬虫 → PostgreSQL → Daily Summary计算 → FastAPI服务 → 飞书通知

## Architecture & Core Components

### Service Layer (Docker Containers)
- **API (FastAPI)** - 控制层，暴露 `/run/crawler`、`/run/deliveroo/daily-summary`、`/run/panda/daily-summary`、`/run/feishu-sync`、`/run/store-ratings`、`/run/import-order-details` 端点；支持Feishu机器人集成（Webhook + Long Connection）
- **Crawler (Selenium)** - 爬虫层，分为三类任务：
  - **订单爬取（`main.py`）**: 使用 Selenium 从 HungryPanda/Deliveroo 抓取订单详情，存入 `raw_orders` 表
  - **日汇总爬取（`run_daily_summary.py`）**: 直接从 Deliveroo Summary API 批量拉取日汇总数据，存入 `daily_sales_summary` 表
  - **评分爬取（`run_store_ratings.py`）**: 从 Deliveroo 抓取店铺评分数据，存入 `store_ratings` 表
- **ETL** - 数据处理层，两类任务：
  - HungryPanda 日汇总计算：从 `raw_orders` 解析 JSON 并入库 `daily_sales_summary` 表
  - Deliveroo 订单详情解析：从 `raw_orders` 解析 JSON 到 `orders/order_items/order_item_modifiers` 详细表结构
- **Feishu Sync** - 飞书同步层，将 `daily_sales_summary` 数据同步到飞书多维表格，支持增量更新和自动 token 刷新
- **Scheduler (cron)** - 定时调度层，运行 crontab 任务周期性触发爬虫/汇总计算/飞书同步（见 [scheduler/scheduler.cron](scheduler/scheduler.cron)）
- **Database (PostgreSQL)** - 数据持久化层，所有服务共享

### Data Layer (PostgreSQL)
核心表结构见 [db/init.sql](db/init.sql) 和 [db/migrations/](db/migrations/)：
- `stores` - 店铺元数据与平台映射（平台英文代码、店铺ID、登录凭证）
- `raw_orders` - 原始订单JSON（platform, store_code, order_id, payload）
- `daily_sales_summary` - **核心汇总表**，存储每店铺每日销售数据（gross_sales, net_sales, order_count）
- `store_ratings` - 店铺评分表，存储 Deliveroo 评分数据（average_rating, rating_count, 星级分布）
- **订单详情表系列**（仅 Deliveroo）：
  - `orders` - 订单主表（order_id, total_amount, status, 时间线）
  - `order_items` - 菜品表（item_name, quantity, price）
  - `order_item_modifiers` - 添加项表（modifier_name）
  - `v_item_sales_stats` - 菜品销量统计视图
  - `v_modifier_usage_stats` - 添加项使用统计视图

**关键区别：** 
- HungryPanda: 需要"爬订单→计算汇总"两阶段
- Deliveroo: 可直接获取汇总数据，但订单详情需从 `raw_orders` 解析到详细表

## Critical Developer Workflows

### Local Development & Debugging
1. **启动完整堆栈：**
   ```bash
   docker compose up -d
   # API 可访问 http://localhost:8000
   # PostgreSQL 可访问 localhost:5432
   ```

2. **触发爬虫任务（通过API）：**
   ```bash
   # 爬取订单详情（HungryPanda）
   curl -X POST http://localhost:8000/run/crawler \
     -H "Content-Type: application/json" \
     -d '{"platform":"panda","store_code":"battersea_maocai","start_date":"2025-12-20"}'
   
   # 爬取日汇总（Deliveroo）
   curl -X POST http://localhost:8000/run/deliveroo/daily-summary \
     -H "Content-Type: application/json" \
     -d '{"stores":["all"],"date":"2025-12-24"}'
   
   # 计算日汇总（HungryPanda ETL）
   curl -X POST http://localhost:8000/run/panda/daily-summary \
     -H "Content-Type: application/json" \
     -d '{"store_code":"all","date":"2025-12-24"}'
   
   # 同步到飞书多维表格
   curl -X POST http://localhost:8000/run/feishu-sync \
     -H "Content-Type: application/json" \
     -d '{"start_date":"2025-12-24","end_date":"2025-12-24"}'
   ```

3. **使用便捷脚本（推荐，根目录26+个shell工具）：**
   ```bash
   # === 爬虫相关 ===
   ./manual_crawl.sh 2025-12-24  # 爬取订单（当天所有店铺）
   ./manual_crawl.sh --platform hungrypanda 2025-12-20 2025-12-25  # 5天范围
   ./manual_deliveroo_summary.sh 2025-12-24  # 补爬 Deliveroo 日汇总
   ./manual_panda_summary.sh 2025-12-24  # 计算 HungryPanda 日汇总
   ./manual_ratings.sh 2025-12-24  # 爬取店铺评分
   
   # === 订单详情处理 ===
   ./import_orders.sh  # 导入订单详情（raw_orders → orders/order_items/modifiers）
   ./setup_order_details_tables.sh  # 初始化订单详情表结构
   
   # === 飞书同步 ===
   ./sync_feishu_bitable.sh 2025-12-24  # 同步到飞书多维表格
   ./diagnose_feishu_sync.sh  # 诊断飞书同步问题
   
   # === 数据库调试 ===
   ./db_shell.sh  # 进入 psql 交互式终端
   ./db_view_daily_summary.sh  # 快速查看汇总数据
   ./db_view_orders.sh  # 查看订单详情表
   ./db_view_ratings.sh  # 查看评分数据
   ./db_stats.sh  # 查看数据统计
   ./quick_stats.sh  # 快速概览（订单数/金额等）
   
   # === 构建部署 ===
   ./build_and_start.sh  # 构建镜像并启动
   ./clean_rebuild.sh  # 清理并重新构建
   ```

4. **监控日志：**
   - API容器日志：`docker logs delivery_api`
   - 爬虫日志：`tail -f api/logs/crawler_*.log`（临时容器的输出）
   - 数据库连接问题：检查 `.env` 中的 `DB_HOST/DB_PORT/DB_NAME` 是否与 docker compose.yaml 一致

5. **数据库调试：**
   ```bash
   ./db_shell.sh  # 进入 psql 交互式终端
   ./db_view_daily_summary.sh  # 快速查看汇总数据
   ./db_view_raw.sh  # 查看原始订单
   ./db_view_orders.sh  # 查看订单详情表（Deliveroo）
   ./db_view_order_stats.sh  # 菜品销量统计
   ./db_view_ratings.sh  # 评分数据
   ./db_stats.sh  # 查看数据统计
   ./show_all_tables.sh  # 列出所有表结构
   ```

### Critical Data Migration Pattern
数据库迁移文件存放在 `db/migrations/`，按时间顺序命名：
- 文件命名：`YYYYMMDD_description.sql`（如 `20260101_add_order_details_tables.sql`）
- 执行方式：PostgreSQL 容器启动时自动执行（见 docker-compose.yaml 挂载）
- **重要：** 新增字段/表时需创建迁移文件，不要直接修改 `init.sql`

**关键迁移示例：**
- [20251230_add_store_ratings.sql](db/migrations/20251230_add_store_ratings.sql) - 店铺评分表
- [20260101_add_order_details_tables.sql](db/migrations/20260101_add_order_details_tables.sql) - 订单详情表系列

### Docker Network Communication
- API、Crawler、ETL 通过 `dataautomaticengine_default` 网络通信
- 从容器内部连接数据库：使用 `DB_HOST=db`（docker compose 服务名）
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
# LOG_DIR = "/app/logs" → 挂载 docker compose 的 ./api/logs
```
**约定：** 容器失败时，从 `api/logs/` 目录查看历史日志，日志文件名格式为 `{service}_{YYYYMMDD_HHMMSS}.log`

### 6. Feishu Integration (Long Connection & Webhook)
飞书支持两种通信模式：
- **Webhook（被动）：** 飞书群 → HTTP POST → `/feishu/webhook` → 数据库查询
- **Long Connection（主动）：** API 周期性 POST 到 `/feishu/long-connection/start` 推送数据

见 [api/services/feishu_bot/](api/services/feishu_bot/) 模块化实现（message_handler、command_parser、responder）。

测试命令：
```bash
cd api && ./test_feishu_bot.sh
# 或手动测试：curl -X POST "http://localhost:8000/feishu/bot/test?text=查询2025-12-22"
```

### 7. Scheduler Automation Pattern
定时任务见 [scheduler/scheduler.cron](scheduler/scheduler.cron)，关键执行时间：
- **4:00 AM** - HungryPanda 订单爬取（`/run/crawler?platform=panda`）
- **5:00 AM** - Deliveroo 订单爬取（`/run/crawler?platform=deliveroo`）
- **5:30 AM** - Deliveroo 订单详情导入（`/run/import-order-details?days=1`）
- **6:00 AM** - Deliveroo 日汇总爬取（`/run/deliveroo/daily-summary`）
- **6:30 AM** - HungryPanda 日汇总计算（`/run/panda/daily-summary`）
- **7:00 AM** - 店铺评分爬取（`/run/store-ratings`）
- **7:30 AM** - 飞书多维表格同步（`/run/feishu-sync`）
- **9:00 AM** - 飞书推送昨日汇总（`/reminder/daily-summary`）

**关键原则：** 任务间有时间间隔，确保数据依赖完成（如订单爬取 → 订单详情导入 → 汇总计算 → 飞书同步）。

### 8. Feishu Bot Integration (Intelligent Query & Command Pattern)
飞书机器人支持智能查询（见 [api/services/feishu_bot/](api/services/feishu_bot/)）：
- **架构设计**：command_parser → message_handler → responder（三层分离）
- **命令解析器**：使用正则表达式模式匹配，支持灵活的自然语言输入
- **支持的查询类型**：
  - 日汇总查询：`查询 Battersea 2025-12-24` 或 `2025-12-20至2025-12-24`
  - 热门菜品：`Top 10 Battersea deliveroo main`（新格式）或 `热门主产品`（旧格式）
  - 店铺评分：`Battersea 评分` 或 `查询 Battersea 评分`
  - 帮助信息：`帮助` 或 `?`

**完整功能见：**
- [HOT_ITEMS_GUIDE.md](HOT_ITEMS_GUIDE.md) - 热门菜品查询详细说明
- [TOP_N_FORMAT_GUIDE.md](TOP_N_FORMAT_GUIDE.md) - Top N 格式规范
- [api/services/feishu_bot/QUICKSTART.md](api/services/feishu_bot/QUICKSTART.md) - 快速集成指南

测试命令：
```bash
cd api && ./test_feishu_bot.sh
# 或手动测试：curl -X POST "http://localhost:8000/feishu/bot/test?text=Top 10 Battersea"
```

### 9. Feishu Bitable Sync (Application Permission)
飞书多维表格同步服务（见 [feishu_sync/](feishu_sync/)）：
- **功能**：将 `daily_sales_summary` 数据同步到飞书多维表格
- **同步逻辑**：使用 `日期_店铺代码_平台` 作为唯一键，已存在则更新，不存在则创建
- **Token 管理**（关键特性）：
  - 使用应用权限：`FeishuTokenManager` 自动管理 tenant_access_token
  - 自动缓存和刷新，提前 5 分钟刷新过期 token
  - 需要在飞书开放平台申请多维表格相关权限
- **环境变量**：需配置 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_BITABLE_APP_TOKEN`、`FEISHU_BITABLE_TABLE_ID`
- **表格字段**：日期（日期类型）、店铺代码、店铺名称、平台、总销售额、净销售额、订单数、平均订单价值
- **测试命令**：`./sync_feishu_bitable.sh 2025-12-24`

**完整指南见：**
- [FEISHU_SYNC_TROUBLESHOOTING.md](FEISHU_SYNC_TROUBLESHOOTING.md) - 常见问题排查

## Integration Points & External Dependencies

### External Services
- **HungryPanda 平台：** Selenium 登录后通过 XHR 拉取订单数据（见 `crawler/services/panda/`）
- **Deliveroo 平台：** 
  - 订单爬取：`crawler/services/deliveroo/fetch_orders.py`（Selenium）
  - 日汇总爬取：`crawler/services/deliveroo/daily_summary.py`（直接 Summary API）
  - 评分爬取：`crawler/run_store_ratings.py`（Selenium 从 Ratings API）
- **Feishu 集成：** 
  - 群机器人（Webhook）：接收消息并智能解析查询命令
  - 长链接服务（WebSocket）：主动推送通知
  - 多维表格同步：定时将数据同步到飞书多维表格
  - 完整集成见 [api/services/feishu_bot/QUICKSTART.md](api/services/feishu_bot/QUICKSTART.md)

### Database Schema Dependencies
新增订单字段时需同步更新：
1. `raw_orders.payload` JSONB 结构（爬虫存入）
2. `daily_sales_summary` 表字段（两平台共享）
3. ETL 解析逻辑（`etl/panda_daily_summary.py`、`etl/import_order_details.py` 等）
4. 订单详情表（仅 Deliveroo）：`orders`、`order_items`、`order_item_modifiers` 及相关视图

**数据流关系：**
- HungryPanda: `raw_orders` → ETL计算 → `daily_sales_summary`
- Deliveroo 汇总: Summary API → `daily_sales_summary`（直接入库）
- Deliveroo 详情: `raw_orders` → ETL解析 → `orders/order_items/order_item_modifiers`（详细表）

## Environment Configuration

### Required Environment Variables
```bash
# Database (Docker 容器内访问)
DB_HOST=db
DB_PORT=5432
DB_NAME=delivery_data
DB_USER=delivery_user
DB_PASSWORD=delivery_pass

# Feishu Bot（群机器人推送）
FEISHU_BOT_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# Feishu App（多维表格同步 - 应用权限）
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxx
FEISHU_BITABLE_APP_TOKEN=bascnxxxxxxxxxxxxx   # 多维表格 app_token
FEISHU_BITABLE_TABLE_ID=tblxxxxxxxxxxxxx      # 数据表 table_id

# 店铺登录凭证（存储在 .env 或 stores 表）
# 见 crawler/store_config.py 中的配置示例
```

**飞书权限配置：**
1. 访问飞书开放平台：https://open.feishu.cn
2. 选择你的应用 → **权限管理**
3. 申请以下权限：
   - `bitable:app` - 读写多维表格
4. 提交审核并等待通过

## Code Style & Conventions

1. **Module Organization:** 功能按文件隔离，避免单一超大文件（参考 [REFACTOR.md](api/REFACTOR.md)）
2. **Function Naming：** 模块级函数使用英文蛇形命名（`get_db_conn`, `ensure_image_exists`）
3. **Database Access：** 所有数据库操作通过 `utils.get_db_conn()` 获取连接，使用 `cursor.execute()` 的参数化查询防止 SQL 注入
4. **Error Handling：** 数据库异常捕获、容器启动失败、网络超时需返回 HTTP 异常而非宕机
5. **Logging：** 使用 `print()` 到 stdout，日志由 Docker 捕获并持久化

## Common Pitfalls & Solutions

| 问题 | 原因 | 解决方案 |
|-----|------|--------|
| `DB connection timeout` | 容器内 DB_HOST 错误或数据库未启动 | 检查 .env 中 DB_HOST=db，确保 `docker compose up` 时 db 容器健康 |
| `Image not found` | 镜像未构建 | API 的 `ensure_image_exists()` 会自动构建，或手动 `docker build` |
| `Network error in crawler` | Selenium 网络隔离 | Crawler 容器需共享宿主网络或配置代理 |
| `Store code not found` | store_code_map 中无此映射 | 在 [store_config.py](crawler/store_config.py) 中新增店铺映射 |
| `Feishu webhook 403` | Bot Token 过期或无权限 | 检查 `.env` 中 FEISHU_BOT_WEBHOOK_URL 是否有效 |

## References
- 架构详解：[struct.MD](struct.MD)
- API 重构说明：[api/REFACTOR.md](api/REFACTOR.md)
- 店铺配置：[crawler/store_config.py](crawler/store_config.py)
- 数据库初始化：[db/init.sql](db/init.sql)
