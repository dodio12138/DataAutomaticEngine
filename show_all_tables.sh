#!/bin/bash

# 订单详情数据全表查询显示
# 用法: ./show_all_tables.sh [store_code]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

STORE_CODE=${1:-}

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Deliveroo 订单详情数据 - 全表查询                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 构建WHERE条件
STORE_FILTER=""
if [ -n "$STORE_CODE" ]; then
  STORE_FILTER="AND store_code = '$STORE_CODE'"
  echo "🏪 店铺筛选: $STORE_CODE"
  echo ""
fi

# 1. 订单主表统计
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 1. ORDERS 订单主表"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
  '总订单数' as metric,
  COUNT(*)::text as value
FROM orders
WHERE 1=1 $STORE_FILTER

UNION ALL

SELECT 
  '已完成订单',
  COUNT(*)::text
FROM orders
WHERE status = 'delivered' $STORE_FILTER

UNION ALL

SELECT 
  '总销售额',
  '£' || ROUND(SUM(total_amount)::numeric, 2)::text
FROM orders
WHERE status = 'delivered' $STORE_FILTER

UNION ALL

SELECT 
  '平均订单额',
  '£' || ROUND(AVG(total_amount)::numeric, 2)::text
FROM orders
WHERE status = 'delivered' $STORE_FILTER;
EOF

echo ""
echo "📊 按店铺分布:"
docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
  store_code as "店铺代码",
  COUNT(*) as "订单数",
  '£' || ROUND(SUM(total_amount)::numeric, 2) as "总销售额",
  '£' || ROUND(AVG(total_amount)::numeric, 2) as "平均订单额"
FROM orders
WHERE status = 'delivered' $STORE_FILTER
GROUP BY store_code
ORDER BY COUNT(*) DESC;
EOF

echo ""
echo "📅 最近7天订单趋势:"
docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
  DATE(placed_at) as "日期",
  COUNT(*) as "订单数",
  '£' || ROUND(SUM(total_amount)::numeric, 2) as "销售额"
FROM orders
WHERE status = 'delivered' 
  AND placed_at >= CURRENT_DATE - INTERVAL '7 days'
  $STORE_FILTER
GROUP BY DATE(placed_at)
ORDER BY DATE(placed_at) DESC;
EOF

# 2. 菜品表统计
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🍜 2. ORDER_ITEMS 订单菜品表"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
  '菜品记录总数' as metric,
  COUNT(*)::text as value
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'delivered' $STORE_FILTER

UNION ALL

SELECT 
  '不同菜品种类',
  COUNT(DISTINCT oi.item_name)::text
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'delivered' $STORE_FILTER

UNION ALL

SELECT 
  '总销售数量',
  SUM(oi.quantity)::text
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'delivered' $STORE_FILTER;
EOF

echo ""
echo "🏆 Top 10 畅销菜品:"
docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
  LEFT(item_name, 40) as "菜品名称",
  order_count as "点单次数",
  total_quantity as "总数量",
  '£' || avg_price as "平均价格",
  '£' || total_revenue as "总收入"
FROM v_item_sales_stats
WHERE 1=1 ${STORE_FILTER:+AND $STORE_FILTER}
ORDER BY total_revenue DESC
LIMIT 10;
EOF

# 3. 添加项表统计
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🥗 3. ORDER_ITEM_MODIFIERS 菜品添加项表"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
  '添加项记录总数' as metric,
  COUNT(*)::text as value
FROM order_item_modifiers oim
JOIN orders o ON oim.order_id = o.order_id
WHERE o.status = 'delivered' $STORE_FILTER

UNION ALL

SELECT 
  '不同添加项种类',
  COUNT(DISTINCT oim.modifier_name)::text
FROM order_item_modifiers oim
JOIN orders o ON oim.order_id = o.order_id
WHERE o.status = 'delivered' $STORE_FILTER;
EOF

echo ""
echo "⭐ Top 10 热门添加项:"
docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
  LEFT(modifier_name, 40) as "添加项名称",
  order_count as "使用次数",
  unique_orders as "不同订单数",
  avg_per_order as "平均每单"
FROM v_modifier_sales_stats
WHERE 1=1 ${STORE_FILTER:+AND $STORE_FILTER}
ORDER BY order_count DESC
LIMIT 10;
EOF

# 4. 统计视图数据
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📈 4. 统计视图数据"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "🔥 Top 5 菜品+添加项组合:"
docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
  LEFT(item_name, 30) as "主菜品",
  LEFT(modifier_name, 25) as "添加项",
  combination_count as "组合次数"
FROM v_item_modifier_combination
WHERE 1=1 ${STORE_FILTER:+AND $STORE_FILTER}
ORDER BY combination_count DESC
LIMIT 5;
EOF

echo ""
echo "⏰ 今日各时段订单分布:"
docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
  order_hour as "小时",
  order_count as "订单数",
  '£' || total_revenue as "销售额",
  '£' || avg_order_value as "平均客单价"
FROM v_hourly_sales
WHERE order_date = CURRENT_DATE $STORE_FILTER
ORDER BY order_hour;
EOF

# 5. 最新订单示例
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 5. 最新5条订单详情"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
  LEFT(order_id, 12) || '...' as "订单ID",
  short_drn as "短单号",
  store_code as "店铺",
  '£' || total_amount as "金额",
  status as "状态",
  TO_CHAR(placed_at, 'MM-DD HH24:MI') as "下单时间",
  LEFT(item_name, 25) as "菜品"
FROM v_order_details
WHERE 1=1 ${STORE_FILTER:+AND $STORE_FILTER}
ORDER BY placed_at DESC
LIMIT 5;
EOF

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                     查询完成                                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "💡 使用方法:"
echo "   ./show_all_tables.sh                    # 显示所有店铺数据"
echo "   ./show_all_tables.sh piccadilly_maocai  # 只显示指定店铺"
echo ""
