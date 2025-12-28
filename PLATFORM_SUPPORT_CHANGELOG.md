# 平台支持更新日志

## 更新日期：2025年12月27日

## 概述
本次更新为爬虫系统添加了多平台支持，现在可以同时从 **HungryPanda** 和 **Deliveroo** 两个平台抓取订单数据并保存到数据库。

## 主要变更

### 1. Deliveroo 平台数据库保存功能
**文件：** `crawler/services/deliveroo/storage.py`

- ✅ 新增 `save_orders_to_db()` 函数，支持将 Deliveroo 订单保存到 `raw_orders` 表
- ✅ 自动解析 Deliveroo 订单结构：
  - 订单ID：`order_id` 或 `id`
  - 订单时间：`timeline.placed_at` 或 `created_at`
  - 金额字段：从 `pricing` 对象解析（自动转换便士到英镑）
- ✅ 支持时间范围过滤和去重插入（基于 `platform + order_id`）

### 2. Deliveroo 爬虫集成数据库
**文件：** `crawler/services/deliveroo/fetch_orders.py`

- ✅ 导入 `save_orders_to_db` 和 `store_name_to_code`
- ✅ 在 `run()` 方法中添加数据库保存逻辑
- ✅ 自动将获取的订单详情保存到 PostgreSQL
- ✅ 添加错误处理和详细日志输出

### 3. 爬虫主入口支持多平台
**文件：** `crawler/main.py`

- ✅ 新增 `PLATFORM` 环境变量支持（默认 `panda`）
- ✅ 导入 `DeliverooScraper` 和相关配置
- ✅ 根据平台参数动态选择爬虫：
  - `platform=panda` → 使用 HungryPandaScraper
  - `platform=deliveroo` → 使用 DeliverooScraper
- ✅ 添加店铺配置验证（检查店铺是否在对应平台配置中）
- ✅ 改进日志输出，包含平台标识

### 4. API 路由支持平台参数
**文件：** `api/routers/crawler.py`

- ✅ `CrawlerRequest` 模型新增 `platform` 字段（默认 "panda"）
- ✅ 添加平台参数验证（仅支持 'panda' 和 'deliveroo'）
- ✅ 环境变量中传递 `PLATFORM` 参数到爬虫容器
- ✅ 容器名和日志文件名包含平台标识（如 `crawler_deliveroo_20251227_143000.log`）
- ✅ API 响应中返回平台信息

## 使用方法

### 通过 API 调用

#### HungryPanda 平台（默认）
```bash
curl -X POST http://localhost:8000/run/crawler \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "panda",
    "store_code": "towerbridge_maocai",
    "start_date": "2025-12-20",
    "end_date": "2025-12-21"
  }'
```

#### Deliveroo 平台
```bash
curl -X POST http://localhost:8000/run/crawler \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "deliveroo",
    "store_code": "piccadilly_maocai",
    "start_date": "2025-12-20",
    "end_date": "2025-12-21"
  }'
```

### 直接运行爬虫容器

#### HungryPanda
```bash
docker run --rm \
  --network dataautomaticengine_default \
  -e PLATFORM=panda \
  -e STORE_CODE=battersea_maocai \
  -e START_DATE=2025-12-20 \
  -e END_DATE=2025-12-21 \
  -e DB_HOST=db \
  -e DB_NAME=delivery_data \
  dataautomaticengine-crawler
```

#### Deliveroo
```bash
docker run --rm \
  --network dataautomaticengine_default \
  -e PLATFORM=deliveroo \
  -e STORE_CODE=piccadilly_hotpot \
  -e START_DATE=2025-12-20 \
  -e END_DATE=2025-12-21 \
  -e DB_HOST=db \
  -e DB_NAME=delivery_data \
  -e DELIVEROO_EMAIL=your-email@example.com \
  -e DELIVEROO_PASSWORD=your-password \
  dataautomaticengine-crawler
```

## 数据库结构

所有平台的订单数据统一保存到 `raw_orders` 表：

| 字段名 | 类型 | 说明 | Panda | Deliveroo |
|--------|------|------|-------|-----------|
| platform | TEXT | 平台标识 | "panda" | "deliveroo" |
| store_code | TEXT | 英文店铺代码 | ✅ | ✅ |
| store_name | TEXT | 中文店铺名 | ✅ | ✅ |
| order_id | TEXT | 订单ID | orderSn | order_id |
| order_date | TIMESTAMP | 订单时间 | createTimeStr | timeline.placed_at |
| estimated_revenue | NUMERIC | 预估收入 | feeInfoResqDTOList | pricing.total |
| product_amount | NUMERIC | 产品金额 | feeInfoResqDTOList | pricing.subtotal |
| discount_amount | NUMERIC | 折扣金额 | feeInfoResqDTOList | pricing.discounts |
| print_amount | NUMERIC | 打印金额 | 计算值 | 计算值 |
| payload | JSONB | 原始JSON | ✅ | ✅ |

## 环境变量

### 通用参数
- `PLATFORM` - 平台名称（"panda" 或 "deliveroo"，默认 "panda"）
- `STORE_CODE` - 店铺英文代码或 "all"
- `STORE_CODES` - 逗号分隔的店铺代码列表
- `START_DATE` - 开始日期 (YYYY-MM-DD)
- `END_DATE` - 结束日期 (YYYY-MM-DD)

### HungryPanda 特定
- `PHONE` - 登录手机号（可在 store_config.py 中配置）
- `PASSWORD` - 登录密码（可在 store_config.py 中配置）

### Deliveroo 特定
- `DELIVEROO_EMAIL` - 登录邮箱（默认：zheng499@hotmail.com）
- `DELIVEROO_PASSWORD` - 登录密码（默认：990924ng6666）
- `DELIVEROO_RESTAURANT_ID` - 可选，不提供则自动捕获

## 兼容性说明

### 向后兼容
- ✅ 未指定 `platform` 参数时默认使用 `panda`
- ✅ 现有的 HungryPanda 爬虫调用无需修改
- ✅ 数据库表结构保持不变（新增 platform 区分）

### 店铺配置检查
爬虫会自动验证店铺是否在对应平台配置中：
- Panda 店铺：检查 `store_dict_panda`
- Deliveroo 店铺：检查 `store_dict_deliveroo`
- 不在配置中的店铺会被跳过并输出警告

## 日志改进

### 容器命名
- Panda: `crawler_panda_20251227_143000`
- Deliveroo: `crawler_deliveroo_20251227_143000`

### 日志文件
- Panda: `api/logs/crawler_panda_20251227_143000.log`
- Deliveroo: `api/logs/crawler_deliveroo_20251227_143000.log`

### 控制台输出
```
✅ 开始爬取 [DELIVEROO] 平台数据
📅 时间范围：2025-12-20 - 2025-12-21
🏪 店铺列表：['piccadilly_hotpot']

============================================================
开始爬取店铺：海底捞火锅（Piccadilly）（piccadilly_hotpot）
============================================================

✅ 已写入数据库 15 条 Deliveroo 订单

✅ 店铺 海底捞火锅（Piccadilly） 爬取完成
```

## 后续 ETL 处理

数据保存到 `raw_orders` 表后，可以通过 ETL 流程进一步处理：

```bash
# 触发 ETL（通过 API）
curl -X POST http://localhost:8000/run/etl \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "deliveroo",
    "start_date": "2025-12-20"
  }'
```

ETL 会根据 `platform` 字段选择对应的解析器：
- `platform='panda'` → `etl/parsers/panda_parser.py`
- `platform='deliveroo'` → `etl/parsers/deliveroo_parser.py`（待实现）

## 测试建议

1. **测试 Panda 平台（确保向后兼容）**
   ```bash
   curl -X POST http://localhost:8000/run/crawler \
     -H "Content-Type: application/json" \
     -d '{"store_code":"battersea_maocai","start_date":"2025-12-20"}'
   ```

2. **测试 Deliveroo 平台**
   ```bash
   curl -X POST http://localhost:8000/run/crawler \
     -H "Content-Type: application/json" \
     -d '{"platform":"deliveroo","store_code":"piccadilly_hotpot","start_date":"2025-12-20"}'
   ```

3. **查询数据库验证**
   ```sql
   -- 查看不同平台的订单数量
   SELECT platform, COUNT(*) 
   FROM raw_orders 
   GROUP BY platform;
   
   -- 查看最新的 Deliveroo 订单
   SELECT order_id, order_date, estimated_revenue 
   FROM raw_orders 
   WHERE platform = 'deliveroo' 
   ORDER BY created_at DESC 
   LIMIT 10;
   ```

## 注意事项

1. **Deliveroo 店铺配置**
   - 确保要爬取的店铺已在 `store_config.py` 的 `store_dict_deliveroo` 中配置
   - 店铺ID格式为 `{org_id}-{branch_id}`

2. **登录凭证**
   - Deliveroo 使用邮箱登录，与 Panda 的手机号登录不同
   - 建议通过环境变量提供凭证，避免硬编码

3. **金额单位转换**
   - Deliveroo API 返回的金额单位是便士（pence）
   - `save_orders_to_db` 会自动除以 100 转换为英镑

4. **时间格式**
   - Deliveroo 使用 ISO 8601 格式（含时区）
   - 代码已处理 `Z` 结尾的 UTC 时间

## 相关文件清单

- ✅ `crawler/main.py` - 主入口，支持多平台
- ✅ `crawler/services/deliveroo/storage.py` - Deliveroo 数据保存
- ✅ `crawler/services/deliveroo/fetch_orders.py` - Deliveroo 爬虫
- ✅ `api/routers/crawler.py` - API 路由
- 📄 `crawler/store_config.py` - 店铺配置（已存在）
- 📄 `db/init.sql` - 数据库表结构（已存在）
