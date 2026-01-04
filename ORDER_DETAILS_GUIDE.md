# Deliveroo 订单详情导入 - 使用指南

## 📋 功能概述

自动从 `raw_orders` 表解析 Deliveroo 订单 JSON，导入到详细的关系型表结构中，支持：
- ✅ 订单主表（orders）- 订单基本信息、时间线、金额
- ✅ 菜品表（order_items）- 主菜品名称、数量、价格
- ✅ 添加项表（order_item_modifiers）- 配料、加料等
- ✅ 多个统计视图 - 自动计算销售数据
- ✅ 增量导入 - 只导入新订单，避免重复

## 🔄 定时任务流程

### 每日自动执行（scheduler容器）

```
05:00 - Deliveroo 订单爬虫
  ↓ 订单保存到 raw_orders 表
05:30 - 订单详情增量导入 ⭐
  ↓ 解析 JSON 到 orders/order_items/order_item_modifiers
  ↓ 统计视图自动更新
06:00 - Deliveroo 日汇总计算
```

**关键配置** (scheduler/scheduler.cron):
```bash
# 每天凌晨5点30分执行订单详情导入（导入昨天的新订单）
30 5 * * * curl -X POST http://api:8000/run/import-order-details \
  -H "Content-Type: application/json" \
  -d '{"days":1}' >> /var/log/cron-order-import.log 2>&1
```

## 📊 数据表结构

### 1. orders（订单主表）
- order_id, short_drn, order_number
- **store_code**, restaurant_id, platform
- total_amount, status
- **placed_at**, accepted_at, confirmed_at, delivery_picked_up_at
- raw_data (JSONB - 保留完整JSON)

### 2. order_items（菜品表）
- order_id (FK)
- **item_name**, category_name
- quantity, unit_price, total_price

### 3. order_item_modifiers（添加项表）
- order_item_id (FK), order_id
- **modifier_name**

### 4. 统计视图（自动更新）
- `v_item_sales_stats` - 主菜品销量统计（按店铺）
- `v_modifier_sales_stats` - 添加项销量统计（按店铺）
- `v_item_modifier_combination` - 菜品+添加项组合
- `v_daily_item_sales` - 每日销售趋势
- `v_order_details` - 订单完整详情（含时间、ID）
- `v_hourly_sales` - 按小时销售统计

## 🚀 使用方法

### 1. 增量导入（推荐，每日自动）

```bash
# 方法1：使用便捷脚本
./daily_import_orders.sh          # 导入最近1天的新订单
./daily_import_orders.sh 7        # 导入最近7天的新订单

# 方法2：直接调用API
curl -X POST "http://localhost:8000/run/import-order-details" \
  -H "Content-Type: application/json" \
  -d '{"days": 1}'
```

### 2. 全量导入（首次使用）

```bash
# 导入所有订单
curl -X POST "http://localhost:8000/run/import-order-details" \
  -H "Content-Type: application/json" \
  -d '{}'

# 或指定起始日期
curl -X POST "http://localhost:8000/run/import-order-details" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-12-20"}'
```

### 3. 测试导入（限制数量）

```bash
curl -X POST "http://localhost:8000/run/import-order-details" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```

## 📈 数据查询

### Shell 脚本查询

```bash
# 查看所有表的完整数据
./show_all_tables.sh                      # 所有店铺
./show_all_tables.sh piccadilly_maocai    # 指定店铺

# 按类型查看统计
./db_view_order_stats.sh items            # 畅销菜品
./db_view_order_stats.sh modifiers        # 热门添加项
./db_view_order_stats.sh combinations     # 菜品组合
./db_view_order_stats.sh orders piccadilly_maocai  # 订单列表
./db_view_order_stats.sh hourly piccadilly_maocai  # 小时统计
./db_view_order_stats.sh summary          # 数据概览
```

### API 查询

```bash
# 订单统计
curl "http://localhost:8000/stats/orders/summary"
curl "http://localhost:8000/stats/orders/summary?store_code=piccadilly_maocai"

# 畅销菜品
curl "http://localhost:8000/stats/items/top?limit=10"
curl "http://localhost:8000/stats/items/top?store_code=east_maocai&limit=20"

# 订单详情
curl "http://localhost:8000/stats/orders/details?limit=30"
curl "http://localhost:8000/stats/orders/details?store_code=piccadilly_maocai&date=2025-12-27"
```

### SQL 直接查询

```sql
-- 按店铺统计
SELECT store_code, COUNT(*), SUM(total_amount) as revenue
FROM orders
WHERE status = 'delivered' AND DATE(placed_at) >= '2025-12-20'
GROUP BY store_code;

-- 畅销菜品（指定店铺）
SELECT item_name, order_count, total_revenue
FROM v_item_sales_stats
WHERE store_code = 'piccadilly_maocai'
ORDER BY total_revenue DESC
LIMIT 10;

-- 订单详情（带时间和ID）
SELECT order_id, short_drn, store_code, total_amount, 
       placed_at, item_name, modifiers
FROM v_order_details
WHERE store_code = 'piccadilly_maocai' 
  AND DATE(placed_at) = '2025-12-27'
ORDER BY placed_at DESC;

-- 高峰时段分析
SELECT order_hour, SUM(order_count) as total_orders, 
       SUM(total_revenue) as revenue
FROM v_hourly_sales
WHERE order_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY order_hour
ORDER BY order_hour;
```

## 🔧 故障排查

### 查看导入日志
```bash
docker logs delivery_api --tail 50
ls -lh api/logs/order_details_import_*.log
cat api/logs/order_details_import_20260101_*.log
```

### 检查 Cron 任务
```bash
docker exec delivery_scheduler crontab -l | grep "订单详情"
docker logs delivery_scheduler --tail 20
cat /var/log/cron-order-import.log  # 在容器内
```

### 验证数据
```bash
# 检查各表记录数
docker exec delivery_postgres psql -U delivery_user -d delivery_data -c "
SELECT 'orders' as table_name, COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'modifiers', COUNT(*) FROM order_item_modifiers;
"

# 检查最新导入时间
docker exec delivery_postgres psql -U delivery_user -d delivery_data -c "
SELECT MAX(created_at) as latest_order FROM orders;
"
```

## ⚡ 性能优化

- ✅ 所有关键字段已建立索引
- ✅ 增量导入避免全表扫描
- ✅ 使用 `ON CONFLICT` 避免重复导入
- ✅ 统计视图预计算，查询速度快
- ✅ 原始 JSON 保留在 raw_data 字段，可重新解析

## 📝 注意事项

1. **增量导入原理**：通过 `order_id NOT IN (SELECT DISTINCT order_id FROM orders)` 排除已导入订单
2. **时区处理**：所有时间使用 UTC，scheduler 容器设置为 Europe/London
3. **数据一致性**：orders 表的 `UNIQUE (order_id, platform)` 约束确保不重复
4. **视图更新**：统计视图会自动反映最新数据，无需手动刷新
5. **日志轮转**：定期清理 `api/logs/` 目录下的旧日志

## 🎯 最佳实践

1. **每日增量导入**：使用 `{"days": 1}` 只导入昨天的新订单
2. **按店铺分析**：在所有查询中使用 `store_code` 过滤
3. **时间范围查询**：使用 `DATE(placed_at)` 索引进行日期过滤
4. **监控导入状态**：检查 cron 日志确保任务正常执行
5. **定期备份**：导出 `orders`, `order_items`, `order_item_modifiers` 表

## 📞 相关文件

- `etl/import_order_details.py` - 导入脚本
- `api/routers/order_details.py` - API 端点
- `api/routers/order_stats.py` - 统计查询端点
- `scheduler/scheduler.cron` - 定时任务配置
- `db/migrations/20260101_add_order_details_tables.sql` - 数据库结构
- `show_all_tables.sh` - 全表查询脚本
- `daily_import_orders.sh` - 增量导入脚本
- `test_full_pipeline.sh` - 完整流程测试
