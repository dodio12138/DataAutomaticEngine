#!/bin/bash

# 查看某天的详细汇总
# 用法: ./db_daily_summary.sh [日期]
# 示例: ./db_daily_summary.sh 2025-12-24
#      ./db_daily_summary.sh  # 查看昨天

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 默认日期：昨天
if [ -z "$1" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        DATE=$(date -v-1d +%Y-%m-%d)
    else
        DATE=$(date -d "yesterday" +%Y-%m-%d)
    fi
else
    DATE="$1"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  📊 ${DATE} 每日汇总${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查数据库容器
if ! docker ps | grep -q delivery_postgres; then
    echo -e "${YELLOW}❌ 数据库容器未运行${NC}"
    exit 1
fi

# 1. 总体数据
echo -e "${CYAN}📈 当天总体数据:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        COUNT(*) as 总订单数,
        ROUND(SUM(estimated_revenue)::numeric, 2) as 总营收,
        ROUND(AVG(estimated_revenue)::numeric, 2) as 平均客单价,
        ROUND(SUM(product_amount)::numeric, 2) as 商品金额,
        ROUND(SUM(discount_amount)::numeric, 2) as 优惠金额
    FROM raw_orders
    WHERE DATE(order_date) = '$DATE';
"

# 2. 各店铺数据
echo -e "${CYAN}🏪 各店铺数据:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        COALESCE(s.name_cn, r.store_name) as 店铺,
        COUNT(r.order_id) as 订单数,
        ROUND(SUM(r.estimated_revenue)::numeric, 2) as 营收,
        ROUND(AVG(r.estimated_revenue)::numeric, 2) as 客单价,
        ROUND(SUM(r.discount_amount)::numeric, 2) as 优惠
    FROM raw_orders r
    LEFT JOIN stores s ON r.store_code = s.code
    WHERE DATE(r.order_date) = '$DATE'
    GROUP BY COALESCE(s.name_cn, r.store_name)
    ORDER BY COUNT(r.order_id) DESC;
"

# 3. 订单平台分布
echo -e "${CYAN}📊 订单平台分布:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        platform as 平台,
        COUNT(*) as 数量,
        ROUND(SUM(estimated_revenue)::numeric, 2) as 营收
    FROM raw_orders
    WHERE DATE(order_date) = '$DATE'
    GROUP BY platform
    ORDER BY COUNT(*) DESC;
"

# 4. 小时分布（订单高峰时段）
echo -e "${CYAN}⏰ 订单时段分布:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        EXTRACT(HOUR FROM order_date) as 时段,
        COUNT(*) as 订单数,
        ROUND(SUM(estimated_revenue)::numeric, 2) as 营收
    FROM raw_orders
    WHERE DATE(order_date) = '$DATE'
    GROUP BY EXTRACT(HOUR FROM order_date)
    ORDER BY EXTRACT(HOUR FROM order_date);
"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 汇总查询完成${NC}"
echo -e "${GREEN}========================================${NC}"
