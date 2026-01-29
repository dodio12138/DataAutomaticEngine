# 数据库 SQL 函数说明

本文档说明当前项目中新增的 `raw_orders` 相关 SQL 函数与用法示例。

## 1) raw_orders_keyword_count

**用途**：统计 `raw_orders.payload` 中包含指定关键词的记录数量，支持平台/店铺筛选，日期不传默认本月。

**签名**：
```sql
raw_orders_keyword_count(
  p_keyword TEXT,
  p_start_date DATE DEFAULT NULL,
  p_end_date DATE DEFAULT NULL,
  p_platform TEXT DEFAULT NULL,
  p_store_code TEXT DEFAULT NULL
) RETURNS BIGINT
```

**示例**：
```sql
-- 默认本月 + 全平台 + 全店铺
SELECT raw_orders_keyword_count('猪肉水饺', NULL, NULL, NULL, NULL);

-- 指定平台
SELECT raw_orders_keyword_count('猪肉水饺', NULL, NULL, 'panda', NULL);

-- 指定平台 + 店铺 + 日期范围
SELECT raw_orders_keyword_count('猪肉水饺', '2025-12-01', '2025-12-31', 'deliveroo', 'battersea_maocai');
```

---

## 2) raw_orders_repeat_rate

**用途**：按平台统计复购率（下单次数 ≥ 2 的用户占比），支持店铺与日期范围过滤。日期不传默认本月；平台不传默认返回两平台。

**用户标识**：
- **panda**：`payload->'data'->'merchantOrderAddressResVO'->>'consigneeTelMask'`
- **deliveroo**：`payload->'customer'->>'id'`

**签名**：
```sql
raw_orders_repeat_rate(
  p_platform TEXT DEFAULT NULL,
  p_store_code TEXT DEFAULT NULL,
  p_start_date DATE DEFAULT NULL,
  p_end_date DATE DEFAULT NULL
) RETURNS TABLE(
  platform TEXT,
  store_code TEXT,
  repeat_users BIGINT,
  total_users BIGINT,
  repeat_rate NUMERIC
)
```

**示例**：
```sql
-- 平台不传，默认本月，返回两平台
SELECT * FROM raw_orders_repeat_rate(NULL, NULL, NULL, NULL);

-- panda 平台，默认本月，全店铺
SELECT * FROM raw_orders_repeat_rate('panda', NULL, NULL, NULL);

-- deliveroo 平台，指定店铺与日期范围
SELECT * FROM raw_orders_repeat_rate('deliveroo', 'battersea_maocai', '2025-12-01', '2025-12-31');
```

---

## 3) raw_orders_cross_store_customers

**用途**：统计两个店铺在同一平台下的交叉顾客数量（按平台分别返回）。日期不传默认本月；平台不传默认返回两平台。

**用户标识**：
- **panda**：`payload->'data'->'merchantOrderAddressResVO'->>'consigneeTelMask'`
- **deliveroo**：`payload->'customer'->>'id'`

**签名**：
```sql
raw_orders_cross_store_customers(
  p_store_code_a TEXT,
  p_store_code_b TEXT,
  p_platform TEXT DEFAULT NULL,
  p_start_date DATE DEFAULT NULL,
  p_end_date DATE DEFAULT NULL
) RETURNS TABLE(
  platform TEXT,
  shared_customers BIGINT
)
```

**示例**：
```sql
-- 本月，统计两个店铺在两平台的交叉顾客数量
SELECT * FROM raw_orders_cross_store_customers('east_maocai', 'piccadilly_maocai', NULL, NULL, NULL);

-- 指定平台
SELECT * FROM raw_orders_cross_store_customers('east_maocai', 'piccadilly_maocai', 'deliveroo', NULL, NULL);

-- 指定日期范围
SELECT * FROM raw_orders_cross_store_customers('battersea_maocai', 'piccadilly_maocai', NULL, '2025-12-01', '2025-12-31');
```

---

## psql 中查看函数

```sql
\df raw_orders*
\df+ raw_orders_repeat_rate
\df+ raw_orders_cross_store_customers
\sf raw_orders_repeat_rate
\sf raw_orders_cross_store_customers
```
