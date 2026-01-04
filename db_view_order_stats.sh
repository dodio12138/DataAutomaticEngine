#!/bin/bash

# 查看订单详情统计
# 用法: ./db_view_order_stats.sh [type] [store_code] [date]
# type: items, modifiers, combinations, daily, orders, hourly, summary
# store_code: 店铺代码（可选，不指定则显示所有店铺）
# date: 日期 YYYY-MM-DD（可选，仅用于 orders 和 daily 类型）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

TYPE=${1:-items}
STORE_CODE=${2:-}
DATE=${3:-}

# 构建 WHERE 条件
WHERE_CLAUSE=""
if [ -n "$STORE_CODE" ]; then
  WHERE_CLAUSE="WHERE store_code = '$STORE_CODE'"
fi

if [ -n "$DATE" ]; then
  if [ -n "$WHERE_CLAUSE" ]; then
    WHERE_CLAUSE="$WHERE_CLAUSE AND DATE(placed_at) = '$DATE'"
  else
    WHERE_CLAUSE="WHERE DATE(placed_at) = '$DATE'"
  fi
fi

case $TYPE in
  items)
    echo "📊 主菜品销售统计 (Top 20)"
    [ -n "$STORE_CODE" ] && echo "   店铺: $STORE_CODE"
    echo "==========================================="
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
      SELECT 
        store_code,
        item_name,
        order_count,
        total_quantity,
        avg_price,
        total_revenue
      FROM v_item_sales_stats
      ${WHERE_CLAUSE}
      ORDER BY total_revenue DESC
      LIMIT 20;
    "
    ;;
  
  modifiers)
    echo "🍜 添加项销售统计 (Top 20)"
    [ -n "$STORE_CODE" ] && echo "   店铺: $STORE_CODE"
    echo "==========================================="
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
      SELECT 
        store_code,
        modifier_name,
        order_count,
        unique_orders,
        avg_per_order
      FROM v_modifier_sales_stats
      ${WHERE_CLAUSE}
      ORDER BY order_count DESC
      LIMIT 20;
    "
    ;;
  
  combinations)
    echo "🔥 菜品+添加项组合统计 (Top 20)"
    [ -n "$STORE_CODE" ] && echo "   店铺: $STORE_CODE"
    echo "==========================================="
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
      SELECT 
        store_code,
        item_name,
        modifier_name,
        combination_count
      FROM v_item_modifier_combination
      ${WHERE_CLAUSE}
      ORDER BY combination_count DESC
      LIMIT 20;
    "
    ;;
  
  daily)
    echo "📈 每日销售趋势 (最近7天)"
    [ -n "$STORE_CODE" ] && echo "   店铺: $STORE_CODE"
    [ -n "$DATE" ] && echo "   日期: $DATE"
    echo "==========================================="
    
    DATE_FILTER=""
    if [ -n "$DATE" ]; then
      DATE_FILTER="AND order_date = '$DATE'"
    else
      DATE_FILTER="AND order_date >= CURRENT_DATE - INTERVAL '7 days'"
    fi
    
    STORE_FILTER=""
    [ -n "$STORE_CODE" ] && STORE_FILTER="AND store_code = '$STORE_CODE'"
    
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
      SELECT 
        store_code,
        order_date,
        item_name,
        order_count,
        total_quantity,
        total_revenue
      FROM v_daily_item_sales
      WHERE 1=1 $DATE_FILTER $STORE_FILTER
      ORDER BY order_date DESC, total_revenue DESC
      LIMIT 30;
    "
    ;;
  
  orders)
    echo "📋 订单详情列表"
    [ -n "$STORE_CODE" ] && echo "   店铺: $STORE_CODE"
    [ -n "$DATE" ] && echo "   日期: $DATE"
    echo "==========================================="
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
      SELECT 
        order_id,
        short_drn,
        order_number,
        store_code,
        total_amount,
        status,
        TO_CHAR(placed_at, 'YYYY-MM-DD HH24:MI') as placed_at,
        item_name,
        quantity,
        total_price,
        modifiers
      FROM v_order_details
      ${WHERE_CLAUSE}
      ORDER BY placed_at DESC
      LIMIT 30;
    "
    ;;
  
  hourly)
    echo "⏰ 按小时销售统计"
    [ -n "$STORE_CODE" ] && echo "   店铺: $STORE_CODE"
    [ -n "$DATE" ] && echo "   日期: $DATE"
    echo "==========================================="
    
    DATE_FILTER=""
    if [ -n "$DATE" ]; then
      DATE_FILTER="AND order_date = '$DATE'"
    else
      DATE_FILTER="AND order_date >= CURRENT_DATE - INTERVAL '7 days'"
    fi
    
    STORE_FILTER=""
    [ -n "$STORE_CODE" ] && STORE_FILTER="AND store_code = '$STORE_CODE'"
    
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
      SELECT 
        store_code,
        order_date,
        order_hour,
        order_count,
        total_revenue,
        avg_order_value
      FROM v_hourly_sales
      WHERE 1=1 $DATE_FILTER $STORE_FILTER
      ORDER BY order_date DESC, order_hour;
    "
    ;;
  
  summary)
    echo "📊 数据概览"
    [ -n "$STORE_CODE" ] && echo "   店铺: $STORE_CODE"
    echo "==========================================="
    
    STORE_FILTER=""
    [ -n "$STORE_CODE" ] && STORE_FILTER="AND store_code = '$STORE_CODE'"
    
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
      SELECT 
        '订单总数' as metric,
        COUNT(*)::text as value
      FROM orders
      WHERE status = 'delivered' $STORE_FILTER
      UNION ALL
      SELECT 
        '菜品总数',
        COUNT(*)::text
      FROM order_items oi
      JOIN orders o ON oi.order_id = o.order_id
      WHERE o.status = 'delivered' $STORE_FILTER
      UNION ALL
      SELECT 
        '添加项总数',
        COUNT(*)::text
      FROM order_item_modifiers oim
      JOIN orders o ON oim.order_id = o.order_id
      WHERE o.status = 'delivered' $STORE_FILTER
      UNION ALL
      SELECT 
        '不同菜品种类',
        COUNT(DISTINCT item_name)::text
      FROM order_items oi
      JOIN orders o ON oi.order_id = o.order_id
      WHERE o.status = 'delivered' $STORE_FILTER
      UNION ALL
      SELECT 
        '不同添加项种类',
        COUNT(DISTINCT modifier_name)::text
      FROM order_item_modifiers oim
      JOIN orders o ON oim.order_id = o.order_id
      WHERE o.status = 'delivered' $STORE_FILTER;
    "
    ;;
  
  *)
    echo "用法: $0 [type] [store_code] [date]"
    echo ""
    echo "type 选项:"
    echo "  items        - 主菜品销售统计"
    echo "  modifiers    - 添加项销售统计"
    echo "  combinations - 菜品+添加项组合统计"
    echo "  daily        - 每日销售趋势"
    echo "  orders       - 订单详情列表（包含订单ID、时间）"
    echo "  hourly       - 按小时销售统计"
    echo "  summary      - 数据概览"
    echo ""
    echo "示例:"
    echo "  $0 items                          # 所有店铺的主菜品统计"
    echo "  $0 items battersea_maocai         # 指定店铺的主菜品统计"
    echo "  $0 orders battersea_maocai        # 指定店铺的订单列表"
    echo "  $0 orders '' 2025-12-24           # 指定日期的所有订单"
    echo "  $0 hourly battersea_maocai        # 指定店铺的小时统计"
    exit 1
    ;;
esac

echo ""
