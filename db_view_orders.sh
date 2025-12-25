#!/bin/bash

# 查看订单数据脚本
# 用法: ./db_view_orders.sh [日期] [店铺代码] [限制条数]
# 示例: ./db_view_orders.sh 2025-12-24 battersea_maocai 10
#      ./db_view_orders.sh 2025-12-24  # 查看某天所有店铺
#      ./db_view_orders.sh  # 查看最近10条

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

DATE="${1}"
STORE="${2}"
LIMIT="${3:-10}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  📊 订单数据查询${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查数据库容器
if ! docker ps | grep -q delivery_postgres; then
    echo -e "${YELLOW}❌ 数据库容器未运行${NC}"
    exit 1
fi

# 构建SQL查询
if [ -n "$DATE" ] && [ -n "$STORE" ]; then
    # 指定日期和店铺
    SQL="SELECT 
        r.order_id,
        COALESCE(s.name_cn, r.store_name) as store_name,
        TO_CHAR(r.order_date, 'YYYY-MM-DD HH24:MI') as order_time,
        r.platform,
        r.estimated_revenue as revenue,
        r.product_amount,
        r.discount_amount
    FROM raw_orders r
    LEFT JOIN stores s ON r.store_code = s.code
    WHERE DATE(r.order_date) = '$DATE' AND r.store_code = '$STORE'
    ORDER BY r.order_date DESC
    LIMIT $LIMIT;"
    
    echo -e "${YELLOW}📅 日期: $DATE${NC}"
    echo -e "${YELLOW}🏪 店铺: $STORE${NC}"
    
elif [ -n "$DATE" ]; then
    # 只指定日期
    SQL="SELECT 
        r.order_id,
        COALESCE(s.name_cn, r.store_name) as store_name,
        TO_CHAR(r.order_date, 'YYYY-MM-DD HH24:MI') as order_time,
        r.platform,
        r.estimated_revenue as revenue,
        r.product_amount
    FROM raw_orders r
    LEFT JOIN stores s ON r.store_code = s.code
    WHERE DATE(r.order_date) = '$DATE'
    ORDER BY r.order_date DESC
    LIMIT $LIMIT;"
    
    echo -e "${YELLOW}📅 日期: $DATE${NC}"
    
else
    # 最近的订单
    SQL="SELECT 
        r.order_id,
        COALESCE(s.name_cn, r.store_name) as store_name,
        TO_CHAR(r.order_date, 'YYYY-MM-DD HH24:MI') as order_time,
        r.platform,
        r.estimated_revenue as revenue,
        r.product_amount
    FROM raw_orders r
    LEFT JOIN stores s ON r.store_code = s.code
    ORDER BY r.order_date DESC
    LIMIT $LIMIT;"
    
    echo -e "${YELLOW}📊 最近 $LIMIT 条订单${NC}"
fi

echo ""

# 执行查询
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "$SQL"

echo ""
echo -e "${GREEN}✅ 查询完成${NC}"
