#!/bin/bash
# 查看店铺评分数据

set -e

# 默认查询昨天的数据
DATE=${1:-$(date -v-1d +%Y-%m-%d)}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌟 店铺评分数据 - $DATE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

docker exec delivery_postgres psql -U delivery_user -d delivery_data -c "
SELECT 
    store_code as \"店铺代码\",
    store_name as \"店铺名称\",
    ROUND(average_rating::numeric, 2) as \"平均评分\",
    rating_count as \"评价总数\",
    five_star_count as \"5星\",
    four_star_count as \"4星\",
    three_star_count as \"3星\",
    two_star_count as \"2星\",
    one_star_count as \"1星\",
    TO_CHAR(created_at, 'HH24:MI:SS') as \"更新时间\"
FROM store_ratings 
WHERE date = '$DATE' AND platform = 'deliveroo'
ORDER BY rating_count DESC;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 统计汇总"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

docker exec delivery_postgres psql -U delivery_user -d delivery_data -c "
SELECT 
    COUNT(*) as \"店铺数量\",
    ROUND(AVG(average_rating)::numeric, 2) as \"平均评分\",
    SUM(rating_count) as \"评价总数\",
    SUM(five_star_count) as \"5星总数\",
    SUM(one_star_count) as \"1星总数\"
FROM store_ratings 
WHERE date = '$DATE' AND platform = 'deliveroo';
"

echo ""
