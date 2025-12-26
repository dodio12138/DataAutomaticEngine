#!/bin/bash

# 查看原始订单JSON数据
# 用法: ./db_view_raw.sh [平台] [店铺代码] [限制条数]

show_help() {
    cat << 'EOF'
原始订单数据查询工具 (db_view_raw.sh)

功能说明：
  查询并格式化显示 raw_orders 表中的原始 JSON 数据（payload 字段），
  支持按平台、店铺过滤，并使用 jq 进行美化输出。

用法：
  ./db_view_raw.sh [选项] [平台] [店铺代码] [限制条数]

选项：
  --help, -h    显示此帮助信息

参数：
  平台          平台名称，如 hungrypanda 或 deliveroo（可选）
  店铺代码      店铺英文代码，如 battersea_maocai（可选）
  限制条数      返回的最大记录数，默认 5

参数组合逻辑：
  - 无参数：返回最近 5 条订单的原始 JSON
  - 仅平台：返回该平台最近 5 条订单
  - 平台+店铺：返回该平台该店铺的订单（最多 5 条）
  - 平台+店铺+限制：返回指定条数的订单

示例：
  ./db_view_raw.sh                                  # 查看最近 5 条原始 JSON
  ./db_view_raw.sh hungrypanda                      # 查看 HungryPanda 平台最近 5 条
  ./db_view_raw.sh hungrypanda battersea_maocai     # 查看特定店铺订单
  ./db_view_raw.sh hungrypanda battersea_maocai 10  # 返回 10 条订单

输出内容：
  每条订单显示：
  - 订单 ID
  - 平台
  - 店铺代码
  - 美化格式的 JSON 数据（使用 jq 格式化）

数据格式：
  HungryPanda JSON 示例：
  {
    "orderId": "HP12345",
    "orderTime": "2025-12-24T10:00:00",
    "totalAmount": 28.50,
    "items": [...]
  }

注意事项：
  - 仅显示 payload 字段（原始 JSON），不解析为表格
  - 使用 jq 工具美化输出（容器内置）
  - 默认限制 5 条以避免输出过长

依赖：
  - Docker
  - delivery_postgres 容器运行中
  - jq（JSON 处理工具，容器内置）

相关工具：
  - db_view_orders.sh - 查看订单详情（包含表格）
  - db_daily_summary.sh - 查看日期汇总
  - db_stats.sh - 查看全局统计
  - manual_crawl.sh - 触发新的数据抓取

可用平台：
  hungrypanda, deliveroo

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
