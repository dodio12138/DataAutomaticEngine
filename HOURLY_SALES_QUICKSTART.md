# 每小时销售数据分析系统 - 快速参考

## 🎯 核心功能

**目标：** 分析店铺每天每小时的订单量和销售额，并同步到飞书多维表格

## 📦 已创建的文件

### 1. 数据库
- ✅ `db/migrations/20260106_add_hourly_sales_table.sql` - 数据表迁移文件

### 2. ETL处理
- ✅ `etl/hourly_sales.py` - 每小时数据聚合脚本

### 3. 飞书同步
- ✅ `feishu_sync/hourly_sales.py` - 飞书多维表格同步脚本

### 4. API路由
- ✅ `api/routers/hourly_sales.py` - API端点
  - `POST /run/hourly-sales/aggregate` - 聚合数据
  - `POST /run/hourly-sales/sync-feishu` - 同步到飞书

### 5. Shell脚本
- ✅ `setup_hourly_sales_table.sh` - 一键建表
- ✅ `sync_hourly_sales.sh` - 聚合并同步（主要脚本）
- ✅ `import_all_hourly_sales.sh` - 导入所有历史数据
- ✅ `db_view_hourly_sales.sh` - 查看数据统计

### 6. 定时任务
- ✅ `scheduler/scheduler.cron` - 每天7:35和7:40自动执行

### 7. 文档
- ✅ `HOURLY_SALES_GUIDE.md` - 完整使用指南

## 🚀 快速使用（5步）

### 步骤 1：创建数据表
```bash
./setup_hourly_sales_table.sh
```

### 步骤 2：配置飞书表格
在 `.env` 文件添加：
```bash
FEISHU_HOURLY_SALES_APP_TOKEN=bascnxxxxxxxxxxxxx
FEISHU_HOURLY_SALES_TABLE_ID=tblxxxxxxxxxxxxx
```

### 步骤 3：导入历史数据
```bash
./import_all_hourly_sales.sh
```

### 步骤 4：重启服务
```bash
docker compose restart api scheduler
```

### 步骤 5：验证数据
```bash
./db_view_hourly_sales.sh
```

## 📊 飞书表格字段配置

| 字段名 | 类型 | 示例值 |
|-------|------|--------|
| 时间 | 日期时间 | 2026-01-06 14:00 |
| 日期 | 日期 | 2026-01-06 |
| 小时 | 数字 | 14 |
| 店铺 | 单选 | Piccadilly / Battersea / Brent / East / Soho / Tower Bridge |
| 平台 | 单选 | Deliveroo / Panda |
| 订单量 | 数字 | 23 |
| 销售额 | 数字 | 456.80 |

## 🔧 常用命令

### 同步单日数据
```bash
./sync_hourly_sales.sh 2026-01-05
```

### 同步日期范围
```bash
./sync_hourly_sales.sh --start-date 2026-01-01 --end-date 2026-01-05
```

### 只聚合不同步
```bash
./sync_hourly_sales.sh 2026-01-05 --aggregate-only
```

### 查看数据统计
```bash
./db_view_hourly_sales.sh 2026-01-05
```

## ⏰ 自动化任务

每天早上：
- **7:35 AM** - 聚合昨天的每小时数据
- **7:40 AM** - 同步到飞书多维表格

**无需手动操作！**

## 🔍 数据验证

```bash
# 查看最近的数据
docker exec delivery_postgres psql -U delivery_user -d delivery_data -c \
  "SELECT date, hour, store_code, platform, order_count, total_sales 
   FROM hourly_sales 
   ORDER BY date_time DESC 
   LIMIT 20"

# 按日期统计
docker exec delivery_postgres psql -U delivery_user -d delivery_data -c \
  "SELECT date, COUNT(*) as records, SUM(order_count) as orders, SUM(total_sales) as sales 
   FROM hourly_sales 
   GROUP BY date 
   ORDER BY date DESC 
   LIMIT 7"
```

## 🎨 数据分析示例

### 找出销售高峰时段
```sql
SELECT 
    hour,
    AVG(order_count) as avg_orders,
    AVG(total_sales) as avg_sales
FROM hourly_sales
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY hour
ORDER BY avg_sales DESC;
```

### 对比不同店铺的营业时段
```sql
SELECT 
    store_name,
    MIN(hour) as first_order_hour,
    MAX(hour) as last_order_hour,
    COUNT(DISTINCT hour) as active_hours
FROM hourly_sales
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
  AND order_count > 0
GROUP BY store_name;
```

### 周末 vs 工作日对比
```sql
SELECT 
    CASE 
        WHEN EXTRACT(DOW FROM date) IN (0, 6) THEN '周末'
        ELSE '工作日'
    END as day_type,
    hour,
    AVG(order_count) as avg_orders,
    AVG(total_sales) as avg_sales
FROM hourly_sales
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY day_type, hour
ORDER BY day_type, hour;
```

## 📈 飞书报表建议

在飞书多维表格中创建以下视图：

1. **今日实时** - 筛选今天的数据，按小时展示
2. **昨日回顾** - 昨天的完整数据
3. **本周趋势** - 最近7天的小时数据折线图
4. **高峰时段** - 按销售额排序，找出黄金时段
5. **店铺对比** - 不同店铺的同时段对比

## ⚠️ 注意事项

1. **数据依赖**：确保订单数据已经爬取（`orders` 和 `raw_orders` 表）
2. **时间范围**：只能聚合已有订单数据的日期范围
3. **飞书权限**：需要 `bitable:app` 权限才能同步
4. **重复聚合**：重新聚合会覆盖已存在的数据（安全）

## 🆘 问题排查

| 问题 | 解决方案 |
|------|---------|
| 表不存在 | `./setup_hourly_sales_table.sh` |
| 没有数据 | 先执行 `./import_all_hourly_sales.sh` |
| API 404 | `docker compose restart api` |
| 飞书同步失败 | 检查环境变量和权限 |
| 定时任务不执行 | 查看 `scheduler/scheduler.cron` |

## 📞 相关命令速查

```bash
# 重启服务
docker compose restart api scheduler

# 查看日志
tail -f api/logs/hourly_sales_*.log

# 查看定时任务状态
docker exec delivery_scheduler crontab -l

# 手动触发API
curl -X POST http://localhost:8000/run/hourly-sales/aggregate -H "Content-Type: application/json" -d '{}'
```

---

**完整文档：** [HOURLY_SALES_GUIDE.md](HOURLY_SALES_GUIDE.md)
