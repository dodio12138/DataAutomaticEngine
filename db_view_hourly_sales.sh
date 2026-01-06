#!/bin/bash
# 查看每小时销售数据统计

echo "📊 每小时销售数据统计"
echo "=============================="
echo ""

# 参数处理
if [ -n "$1" ]; then
    DATE_FILTER="WHERE date = '$1'"
    echo "📆 查询日期: $1"
else
    DATE_FILTER="WHERE date >= CURRENT_DATE - INTERVAL '7 days'"
    echo "📆 查询范围: 最近7天"
fi

echo ""

# 总体统计
echo "🔢 总体统计:"
echo "------------------------------"
docker exec delivery_postgres psql -U delivery_user -d delivery_data -c "
SELECT 
    COUNT(*) as 总记录数,
    COUNT(DISTINCT date) as 天数,
    COUNT(DISTINCT store_code) as 店铺数,
    SUM(order_count) as 总订单数,
    TO_CHAR(SUM(total_sales), 'FM999,999,999.00') as 总销售额
FROM hourly_sales
$DATE_FILTER
"

echo ""
echo "📈 按日期统计:"
echo "------------------------------"
docker exec delivery_postgres psql -U delivery_user -d delivery_data -c "
SELECT 
    date as 日期,
    COUNT(*) as 时段数,
    SUM(order_count) as 订单数,
    TO_CHAR(SUM(total_sales), 'FM999,999.00') as 销售额,
    TO_CHAR(AVG(total_sales), 'FM999.00') as 平均每时段
FROM hourly_sales
$DATE_FILTER
GROUP BY date
ORDER BY date DESC
LIMIT 10
"

echo ""
echo "🏪 按店铺统计:"
echo "------------------------------"
docker exec delivery_postgres psql -U delivery_user -d delivery_data -c "
SELECT 
    store_code as 店铺,
    platform as 平台,
    COUNT(DISTINCT date) as 天数,
    SUM(order_count) as 订单数,
    TO_CHAR(SUM(total_sales), 'FM999,999.00') as 销售额
FROM hourly_sales
$DATE_FILTER
GROUP BY store_code, platform
ORDER BY SUM(total_sales) DESC
"

echo ""
echo "⏰ 热门时段分析（按小时）:"
echo "------------------------------"
docker exec delivery_postgres psql -U delivery_user -d delivery_data -c "
SELECT 
    hour as 小时,
    COUNT(*) as 记录数,
    SUM(order_count) as 订单数,
    TO_CHAR(SUM(total_sales), 'FM999,999.00') as 销售额,
    TO_CHAR(AVG(order_count), 'FM999.0') as 平均订单,
    TO_CHAR(AVG(total_sales), 'FM999.00') as 平均销售
FROM hourly_sales
$DATE_FILTER
GROUP BY hour
ORDER BY hour
"

echo ""
echo "💡 提示："
echo "   - 查看特定日期: $0 2026-01-05"
echo "   - 默认显示最近7天"
