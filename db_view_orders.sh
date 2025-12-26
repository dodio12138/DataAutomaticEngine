#!/bin/bash

# 查看订单数据脚本
# 用法: ./db_view_orders.sh [日期] [店铺代码] [限制条数]

show_help() {
    cat << 'EOF'
订单数据查询工具 (db_view_orders.sh)

功能说明：
  查询并显示 raw_orders 表中的订单数据，支持按日期、店铺过滤，
  并可限制返回条数。

用法：
  ./db_view_orders.sh [选项] [日期] [店铺代码] [限制条数]

选项：
  --help, -h    显示此帮助信息

参数：
  日期          订单日期，格式 YYYY-MM-DD（可选）
  店铺代码      店铺英文代码，如 battersea_maocai（可选）
  限制条数      返回的最大记录数，默认 10

参数组合逻辑：
  - 无参数：返回最近 10 条订单
  - 仅日期：返回该日期所有店铺的订单（最多 10 条）
  - 日期+店铺：返回该日期该店铺的订单（最多 10 条）
  - 日期+店铺+限制：返回指定条数的订单

示例：
  ./db_view_orders.sh                           # 查看最近 10 条订单
  ./db_view_orders.sh 2025-12-24                # 查看 12-24 日所有店铺订单
  ./db_view_orders.sh 2025-12-24 battersea_maocai # 查看特定店铺订单
  ./db_view_orders.sh 2025-12-24 battersea_maocai 20 # 返回 20 条订单

输出内容：
  - 订单 ID
  - 平台（HungryPanda / Deliveroo）
  - 店铺代码
  - 抓取时间
  - 原始 JSON 数据（payload 字段）

注意事项：
  - 日期基于 payload JSON 中的订单日期，不是抓取时间
  - 店铺代码需与数据库中的 store_code 字段完全匹配
  - 输出包含完整 JSON 数据，可能较长

依赖：
  - Docker
  - delivery_postgres 容器运行中
  - raw_orders 表存在

相关工具：
  - db_view_raw.sh - 仅查看原始 JSON（更简洁）
  - db_daily_summary.sh - 查看日期汇总（无详细数据）
  - db_stats.sh - 查看全局统计信息
  - manual_crawl.sh - 触发新的数据抓取

可用店铺代码：
  battersea_maocai, battersea_restaurant, camden_maocai,
  dublin_maocai, dublin_restaurant, nottingham_restaurant,
  glasgow_restaurant

EOF
    exit 0
}

# 检查帮助选项
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
fi

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
