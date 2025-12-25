#!/bin/bash

# 查看数据库统计信息
# 用法: ./db_stats.sh

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  📈 数据库统计概览${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查数据库容器
if ! docker ps | grep -q delivery_postgres; then
    echo -e "${YELLOW}❌ 数据库容器未运行${NC}"
    exit 1
fi

# 1. 总订单数
echo -e "${CYAN}📦 订单总数:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -t -c "
    SELECT COUNT(*) as total_orders FROM raw_orders;
"

# 2. 按平台统计
echo -e "${CYAN}🔌 各平台订单统计:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        platform as 平台,
        COUNT(*) as 订单数,
        ROUND(SUM(estimated_revenue)::numeric, 2) as 总营收
    FROM raw_orders
    GROUP BY platform
    ORDER BY COUNT(*) DESC;
"

# 3. 按店铺统计
echo -e "${CYAN}🏪 各店铺订单统计:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        COALESCE(s.name_cn, r.store_name) as 店铺,
        COUNT(r.order_id) as 订单数,
        ROUND(SUM(r.estimated_revenue)::numeric, 2) as 总营收,
        ROUND(AVG(r.estimated_revenue)::numeric, 2) as 平均客单价
    FROM raw_orders r
    LEFT JOIN stores s ON r.store_code = s.code
    GROUP BY COALESCE(s.name_cn, r.store_name)
    ORDER BY COUNT(r.order_id) DESC;
"

# 4. 最近7天订单趋势
echo -e "${CYAN}📅 最近7天订单趋势:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        DATE(order_date) as 日期,
        COUNT(*) as 订单数,
        ROUND(SUM(estimated_revenue)::numeric, 2) as 营收
    FROM raw_orders
    WHERE order_date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY DATE(order_date)
    ORDER BY DATE(order_date) DESC;
"

# 5. 订单平台分布
echo -e "${CYAN}📊 订单平台分布:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        platform as 平台,
        COUNT(*) as 数量,
        ROUND(COUNT(*)::numeric * 100.0 / (SELECT COUNT(*) FROM raw_orders), 2) as 占比
    FROM raw_orders
    GROUP BY platform
    ORDER BY COUNT(*) DESC;
"

# 6. 数据最新时间
echo -e "${CYAN}⏰ 数据时间范围:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        MIN(DATE(order_date)) as 最早订单日期,
        MAX(DATE(order_date)) as 最新订单日期
    FROM raw_orders;
"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 统计查询完成${NC}"
echo -e "${GREEN}========================================${NC}"
