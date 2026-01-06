# 每小时销售数据分析系统 - 使用指南

## 📋 功能概述

自动分析店铺每天每小时的订单量和销售额，支持：
- ✅ 从 Deliveroo 和 HungryPanda 订单聚合每小时数据
- ✅ 存储到 `hourly_sales` 数据表
- ✅ 同步到飞书多维表格
- ✅ 定时自动更新（每天早上7:35 - 7:40）
- ✅ 一键导入所有历史数据
- ✅ 支持指定日期或日期范围

## 🗄️ 数据表结构

### hourly_sales 表

| 字段名 | 类型 | 说明 |
|-------|-----|------|
| date_time | TIMESTAMP | 日期时间（如 2026-01-06 14:00:00）|
| date | DATE | 日期（冗余字段，便于查询）|
| hour | INTEGER | 小时（0-23）|
| store_code | VARCHAR(64) | 店铺代码 |
| store_name | VARCHAR(128) | 店铺名称 |
| platform | VARCHAR(32) | 平台（deliveroo/hungrypanda）|
| order_count | INTEGER | 该小时的订单数量 |
| total_sales | DECIMAL(10,2) | 该小时的总销售额 |

**唯一约束：** 同一店铺同一平台同一小时只有一条记录

## 🚀 快速开始

### 1. 创建数据表

**方式一：自动迁移（推荐）**
```bash
# 重启数据库容器，自动执行迁移
docker compose restart db
```

**方式二：手动执行**
```bash
./setup_hourly_sales_table.sh
```

### 2. 导入历史数据

```bash
# 一键导入所有已知订单数据
./import_all_hourly_sales.sh
```

这会：
1. 自动检测数据库中的订单日期范围
2. 聚合所有历史数据
3. 同步到飞书多维表格

### 3. 配置飞书多维表格

在 `.env` 文件中添加：

```bash
# 每小时销售数据飞书表格配置
FEISHU_HOURLY_SALES_APP_TOKEN=bascnxxxxxxxxxxxxx
FEISHU_HOURLY_SALES_TABLE_ID=tblxxxxxxxxxxxxx
```

**飞书表格字段配置：**

| 字段名 | 字段类型 | 说明 |
|-------|---------|------|
| 时间 | 日期时间 | 2026-01-06 14:00 |
| 日期 | 日期 | 2026-01-06（冗余但便于查询）|
| 小时 | 数字 | 14 |
| 店铺 | 单选 | Piccadilly / Soho / ... |
| 平台 | 单选 | Deliveroo / Panda |
| 订单量 | 数字 | 23 |
| 销售额 | 数字 | 456.80 |

## 📖 使用指南

### 通过 Shell 脚本（推荐）

#### 同步单个日期
```bash
./sync_hourly_sales.sh 2026-01-05
```

#### 同步日期范围
```bash
./sync_hourly_sales.sh --start-date 2026-01-01 --end-date 2026-01-05
```

#### 只聚合，不同步到飞书
```bash
./sync_hourly_sales.sh 2026-01-05 --aggregate-only
```

#### 只同步到飞书，不聚合
```bash
./sync_hourly_sales.sh 2026-01-05 --sync-only
```

### 通过 API

#### 聚合每小时数据
```bash
# 聚合昨天的数据（默认）
curl -X POST http://localhost:8000/run/hourly-sales/aggregate \
  -H "Content-Type: application/json" \
  -d '{}'

# 聚合指定日期
curl -X POST http://localhost:8000/run/hourly-sales/aggregate \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-01-05"}'

# 聚合日期范围
curl -X POST http://localhost:8000/run/hourly-sales/aggregate \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2026-01-01","end_date":"2026-01-05"}'
```

#### 同步到飞书
```bash
# 同步昨天的数据（默认）
curl -X POST http://localhost:8000/run/hourly-sales/sync-feishu \
  -H "Content-Type: application/json" \
  -d '{}'

# 同步指定日期范围
curl -X POST http://localhost:8000/run/hourly-sales/sync-feishu \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2026-01-01","end_date":"2026-01-05"}'
```

### 查看数据统计

```bash
# 查看最近7天的数据
./db_view_hourly_sales.sh

# 查看特定日期
./db_view_hourly_sales.sh 2026-01-05
```

## ⏰ 定时任务

系统每天自动执行以下任务：

| 时间 | 任务 | 说明 |
|-----|------|-----|
| 7:35 AM | 聚合每小时数据 | 聚合昨天的每小时订单量和销售额 |
| 7:40 AM | 同步到飞书 | 将聚合数据同步到飞书多维表格 |

配置文件：[scheduler/scheduler.cron](scheduler/scheduler.cron)

## 🔧 数据聚合逻辑

### Deliveroo（从 orders 表）
- 数据源：`orders` 表（订单详情）
- 时间字段：`placed_at`（下单时间）
- 筛选条件：`status = 'delivered'`
- 聚合维度：每小时 + 店铺 + 平台

### HungryPanda（从 raw_orders 表）
- 数据源：`raw_orders` 表（原始订单JSON）
- 时间字段：`order_date`
- 筛选条件：`platform = 'panda'`
- 聚合维度：每小时 + 店铺 + 平台

## 📊 数据分析示例

### SQL 查询示例

```sql
-- 查看某天的每小时销售趋势
SELECT 
    hour,
    SUM(order_count) as total_orders,
    SUM(total_sales) as total_sales
FROM hourly_sales
WHERE date = '2026-01-05'
GROUP BY hour
ORDER BY hour;

-- 对比不同店铺的高峰时段
SELECT 
    store_name,
    hour,
    AVG(order_count) as avg_orders
FROM hourly_sales
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY store_name, hour
ORDER BY store_name, hour;

-- 查找销售高峰时段
SELECT 
    hour,
    AVG(total_sales) as avg_sales,
    COUNT(*) as days_count
FROM hourly_sales
GROUP BY hour
ORDER BY avg_sales DESC
LIMIT 5;
```

## 🆘 常见问题

### Q1: 数据表不存在怎么办？
```bash
# 执行迁移脚本
./setup_hourly_sales_table.sh

# 或手动执行
docker exec delivery_postgres psql -U delivery_user -d delivery_data \
  -f /docker-entrypoint-initdb.d/20260106_add_hourly_sales_table.sql
```

### Q2: 如何验证数据是否正确聚合？
```bash
# 查看数据统计
./db_view_hourly_sales.sh 2026-01-05

# 或直接查询
docker exec delivery_postgres psql -U delivery_user -d delivery_data \
  -c "SELECT date, COUNT(*), SUM(order_count) FROM hourly_sales WHERE date='2026-01-05' GROUP BY date"
```

### Q3: 飞书同步失败怎么办？
1. 检查环境变量：
   ```bash
   docker exec delivery_api env | grep FEISHU_HOURLY
   ```

2. 查看日志：
   ```bash
   tail -f api/logs/hourly_sales_sync_*.log
   ```

3. 验证飞书权限：确保应用已申请 `bitable:app` 权限

### Q4: 如何重新聚合某天的数据？
```bash
# 重新聚合会自动覆盖已存在的数据（ON CONFLICT DO UPDATE）
./sync_hourly_sales.sh 2026-01-05
```

## 📚 相关文档

- [数据库迁移文件](db/migrations/20260106_add_hourly_sales_table.sql)
- [ETL 脚本](etl/hourly_sales.py)
- [飞书同步脚本](feishu_sync/hourly_sales.py)
- [API 路由](api/routers/hourly_sales.py)
- [定时任务配置](scheduler/scheduler.cron)

## 🎯 最佳实践

1. **首次使用**：先执行 `./import_all_hourly_sales.sh` 导入历史数据
2. **日常使用**：依赖定时任务自动更新（无需手动操作）
3. **数据验证**：定期使用 `./db_view_hourly_sales.sh` 检查数据完整性
4. **飞书表格**：建议设置视图和筛选器，便于快速分析

## ✅ 验证清单

- [ ] 数据表已创建（`hourly_sales`）
- [ ] 环境变量已配置（`FEISHU_HOURLY_SALES_APP_TOKEN` 等）
- [ ] 飞书表格已创建并配置字段
- [ ] 历史数据已导入（`./import_all_hourly_sales.sh`）
- [ ] 定时任务已启用（检查 `scheduler/scheduler.cron`）
- [ ] 数据统计正常（`./db_view_hourly_sales.sh`）

---

**创建日期：** 2026-01-06
**版本：** v1.0
