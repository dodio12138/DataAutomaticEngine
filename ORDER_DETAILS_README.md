# Deliveroo 订单详情数据分析

## 概述

此模块用于将 Deliveroo 订单的 JSON 数据拆分成多个表，以便进行详细的菜品和添加项统计分析。

## 数据库结构

### 主表

1. **orders** - 订单主表
   - 存储订单基本信息（订单号、金额、状态、时间线）
   - 保留完整 JSON 数据在 `raw_data` 字段（JSONB）

2. **order_items** - 订单菜品表
   - 存储每个订单中的主菜品
   - 包含菜品名称、分类、数量、价格等

3. **order_item_modifiers** - 菜品添加项表
   - 存储每个菜品的添加项（配料、加料等）
   - 通过外键关联到 order_items

### 统计视图

1. **v_item_sales_stats** - 主菜品销售统计
   - 统计每个菜品的订单数、总销量、平均价格、总收入

2. **v_modifier_sales_stats** - 添加项销售统计
   - 统计每个添加项的订单数、出现次数、平均每单使用量

3. **v_item_modifier_combination** - 菜品+添加项组合统计
   - 分析哪些菜品和添加项的组合最常见

4. **v_daily_item_sales** - 每日菜品销售趋势
   - 按日期统计每个菜品的销售情况

## 使用步骤

### 1. 应用数据库迁移

```bash
# 方法1: 直接执行 SQL 文件
docker exec -i delivery_postgres psql -U delivery_user -d delivery_data < db/migrations/20260101_add_order_details_tables.sql

# 方法2: 进入 psql shell 执行
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data
\i /path/to/20260101_add_order_details_tables.sql
```

### 2. 导入订单数据

```bash
# 导入所有 Deliveroo 订单
./import_deliveroo_details.sh

# 或者限制导入数量（测试用）
./import_deliveroo_details.sh 100
```

### 3. 查看统计数据

```bash
# 查看主菜品销售统计
./db_view_order_stats.sh items

# 查看添加项销售统计
./db_view_order_stats.sh modifiers

# 查看菜品+添加项组合统计
./db_view_order_stats.sh combinations

# 查看每日销售趋势
./db_view_order_stats.sh daily

# 查看数据概览
./db_view_order_stats.sh summary
```

## SQL 查询示例

### 最畅销的菜品

```sql
SELECT 
  item_name,
  order_count,
  total_quantity,
  ROUND(total_revenue::numeric, 2) as total_revenue
FROM v_item_sales_stats
ORDER BY total_revenue DESC
LIMIT 10;
```

### 最受欢迎的添加项

```sql
SELECT 
  modifier_name,
  order_count,
  unique_orders
FROM v_modifier_sales_stats
ORDER BY order_count DESC
LIMIT 10;
```

### 特定菜品的热门组合

```sql
SELECT 
  item_name,
  modifier_name,
  combination_count
FROM v_item_modifier_combination
WHERE item_name LIKE '%Mini Pot%'
ORDER BY combination_count DESC
LIMIT 20;
```

### 某个店铺的销售情况

```sql
SELECT 
  oi.item_name,
  COUNT(DISTINCT o.order_id) as order_count,
  SUM(oi.quantity) as total_quantity,
  ROUND(SUM(oi.total_price)::numeric, 2) as total_revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.restaurant_id = 'your_restaurant_id'
GROUP BY oi.item_name
ORDER BY total_revenue DESC;
```

### 添加项的平均使用频率

```sql
SELECT 
  modifier_name,
  COUNT(*) as total_usage,
  COUNT(DISTINCT order_id) as unique_orders,
  ROUND(COUNT(*)::numeric / COUNT(DISTINCT order_id)::numeric, 2) as avg_per_order
FROM order_item_modifiers
GROUP BY modifier_name
ORDER BY total_usage DESC
LIMIT 20;
```

### 时间段分析（比如查看某周的销售）

```sql
SELECT 
  DATE(placed_at) as sale_date,
  COUNT(*) as order_count,
  ROUND(SUM(total_amount)::numeric, 2) as total_revenue
FROM orders
WHERE placed_at >= '2025-12-20' AND placed_at < '2025-12-27'
GROUP BY DATE(placed_at)
ORDER BY sale_date;
```

## 数据流

```
raw_orders (JSON)
    ↓
import_order_details.py
    ↓
┌─────────────────┐
│  orders 表       │
│  (订单主信息)    │
└────────┬────────┘
         ↓
┌─────────────────┐
│ order_items 表   │
│ (主菜品)         │
└────────┬────────┘
         ↓
┌──────────────────────┐
│ order_item_modifiers │
│ (添加项)              │
└──────────────────────┘
         ↓
    统计视图
```

## 注意事项

1. **数据完整性**: 所有表都使用外键约束，确保数据一致性
2. **JSON 备份**: orders 表的 `raw_data` 字段保留完整 JSON，便于后续重新解析
3. **索引优化**: 所有关键字段都建立了索引，查询性能良好
4. **重复导入**: orders 表使用 `ON CONFLICT` 防止重复，已存在的订单会更新状态
5. **平台区分**: orders 表有 `platform` 字段（默认 'deliveroo'），支持多平台扩展

## 扩展功能

可以基于这些数据实现：

- 📊 菜品销售排行榜
- 🔥 热门组合推荐
- 📈 销售趋势分析
- 🎯 客户偏好分析
- 💰 收入贡献分析
- 🍜 库存需求预测

## 相关文件

- `db/migrations/20260101_add_order_details_tables.sql` - 数据库迁移文件
- `etl/import_order_details.py` - 数据导入脚本
- `import_deliveroo_details.sh` - 导入执行脚本
- `db_view_order_stats.sh` - 数据查询脚本
