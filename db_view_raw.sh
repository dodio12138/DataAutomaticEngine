#!/bin/bash

# 查看原始订单JSON数据
# 用法: ./db_view_raw.sh [平台] [店铺代码] [限制条数]
# 示例: ./db_view_raw.sh hungrypanda battersea_maocai 5
#      ./db_view_raw.sh hungrypanda  # 查看某平台最近10条
#      ./db_view_raw.sh  # 查看最近5条

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

PLATFORM="${1}"
STORE="${2}"
LIMIT="${3:-5}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  📦 原始订单数据查询${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查数据库容器
if ! docker ps | grep -q delivery_postgres; then
    echo -e "${YELLOW}❌ 数据库容器未运行${NC}"
    exit 1
fi

# 构建SQL查询
if [ -n "$PLATFORM" ] && [ -n "$STORE" ]; then
    # 指定平台和店铺
    SQL="SELECT 
        id,
        platform,
        store_code,
        order_id,
        TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_time,
        jsonb_pretty(payload) as order_json
    FROM raw_orders
    WHERE platform = '$PLATFORM' AND store_code = '$STORE'
    ORDER BY created_at DESC
    LIMIT $LIMIT;"
    
    echo -e "${YELLOW}🔌 平台: $PLATFORM${NC}"
    echo -e "${YELLOW}🏪 店铺: $STORE${NC}"
    
elif [ -n "$PLATFORM" ]; then
    # 只指定平台
    SQL="SELECT 
        id,
        platform,
        store_code,
        order_id,
        TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_time
    FROM raw_orders
    WHERE platform = '$PLATFORM'
    ORDER BY created_at DESC
    LIMIT $LIMIT;"
    
    echo -e "${YELLOW}🔌 平台: $PLATFORM${NC}"
    echo -e "${YELLOW}💡 提示: 添加店铺代码参数查看完整JSON${NC}"
    
else
    # 最近的原始订单
    SQL="SELECT 
        id,
        platform,
        store_code,
        order_id,
        TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_time
    FROM raw_orders
    ORDER BY created_at DESC
    LIMIT $LIMIT;"
    
    echo -e "${YELLOW}📊 最近 $LIMIT 条原始订单${NC}"
    echo -e "${YELLOW}💡 提示: 添加平台和店铺参数查看完整JSON${NC}"
fi

echo ""

# 执行查询
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "$SQL"

echo ""
echo -e "${GREEN}✅ 查询完成${NC}"
