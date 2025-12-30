#!/bin/bash
# 查看 daily_sales_summary 表数据 - 每日销售汇总视图
# 用法: 
#   ./db_view_daily_summary.sh                          # 查看最近7天所有数据
#   ./db_view_daily_summary.sh --date 2025-12-22        # 查看指定日期
#   ./db_view_daily_summary.sh --platform panda         # 查看指定平台
#   ./db_view_daily_summary.sh --store piccadilly       # 查看包含店铺名称的数据
#   ./db_view_daily_summary.sh --days 30                # 查看最近30天
#   ./db_view_daily_summary.sh --stats                  # 查看汇总统计

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

# 默认参数
DAYS=7
DATE=""
PLATFORM=""
STORE=""
STATS=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --date)
            DATE="$2"
            shift 2
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --store)
            STORE="$2"
            shift 2
            ;;
        --days)
            DAYS="$2"
            shift 2
            ;;
        --stats)
            STATS=true
            shift
            ;;
        -h|--help)
            cat << EOF
${BLUE}========================================
  📊 Daily Sales Summary 数据查看工具
========================================${NC}

${CYAN}用法:${NC} $0 [选项]

${CYAN}选项:${NC}
  --date DATE         查看指定日期 (YYYY-MM-DD)
  --platform PLATFORM 筛选平台 (panda/deliveroo)
  --store STORE       筛选店铺代码（模糊匹配）
  --days N            查看最近N天 (默认7)
  --stats             显示汇总统计
  -h, --help          显示帮助信息

${CYAN}示例:${NC}
  ${GREEN}# 最近7天所有数据${NC}
  $0

  ${GREEN}# 查看12月22日${NC}
  $0 --date 2025-12-22

  ${GREEN}# Panda平台最近30天${NC}
  $0 --platform panda --days 30

  ${GREEN}# Piccadilly店铺数据${NC}
  $0 --store piccadilly

  ${GREEN}# 汇总统计${NC}
  $0 --stats

  ${GREEN}# 组合筛选（Deliveroo平台，最近14天）${NC}
  $0 --platform deliveroo --days 14

EOF
            exit 0
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 检查数据库容器
if ! docker ps | grep -q delivery_postgres; then
    echo -e "${RED}❌ 数据库容器未运行${NC}"
    exit 1
fi

# 构建 WHERE 条件
WHERE_CLAUSE=""

if [ -n "$DATE" ]; then
    WHERE_CLAUSE="date = '$DATE'"
else
    WHERE_CLAUSE="date >= CURRENT_DATE - INTERVAL '$DAYS days'"
fi

if [ -n "$PLATFORM" ]; then
    WHERE_CLAUSE="$WHERE_CLAUSE AND platform = '$PLATFORM'"
fi

if [ -n "$STORE" ]; then
    WHERE_CLAUSE="$WHERE_CLAUSE AND store_code ILIKE '%$STORE%'"
fi

# 显示筛选信息
FILTER_INFO=""
[ -n "$DATE" ] && FILTER_INFO="${FILTER_INFO}日期: $DATE  "
[ -z "$DATE" ] && FILTER_INFO="${FILTER_INFO}最近: ${DAYS}天  "
[ -n "$PLATFORM" ] && FILTER_INFO="${FILTER_INFO}平台: $PLATFORM  "
[ -n "$STORE" ] && FILTER_INFO="${FILTER_INFO}店铺: *$STORE*  "

# 执行查询
if [ "$STATS" = true ]; then
    # 汇总统计
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  📊 每日销售汇总统计${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "${YELLOW}筛选: $FILTER_INFO${NC}"
    echo ""
    
    # 按平台汇总
    echo -e "${CYAN}📱 按平台汇总:${NC}"
    docker exec -i delivery_postgres psql -U delivery_user -d delivery_data <<EOF
SELECT 
    platform AS "平台",
    COUNT(DISTINCT date) AS "日期数",
    COUNT(DISTINCT store_code) AS "店铺数",
    SUM(order_count) AS "总订单数",
    CONCAT('£', ROUND(SUM(gross_sales), 2)) AS "总销售额(折前)",
    CONCAT('£', ROUND(SUM(net_sales), 2)) AS "净销售额(折后)",
    CONCAT('£', ROUND(AVG(avg_order_value), 2)) AS "平均客单价",
    CONCAT(ROUND((1 - SUM(net_sales) / NULLIF(SUM(gross_sales), 0)) * 100, 1), '%') AS "折扣率"
FROM daily_sales_summary
WHERE $WHERE_CLAUSE
GROUP BY platform
ORDER BY platform;
EOF
    
    echo ""
    echo -e "${CYAN}📅 按日期汇总 (Top 10):${NC}"
    docker exec -i delivery_postgres psql -U delivery_user -d delivery_data <<EOF
SELECT 
    date AS "日期",
    TO_CHAR(date, 'Dy') AS "星期",
    COUNT(DISTINCT platform) AS "平台",
    COUNT(DISTINCT store_code) AS "店铺",
    SUM(order_count) AS "订单",
    CONCAT('£', ROUND(SUM(gross_sales), 2)) AS "销售额(折前)",
    CONCAT('£', ROUND(SUM(net_sales), 2)) AS "净销售额",
    CONCAT('£', ROUND(AVG(avg_order_value), 2)) AS "客单价"
FROM daily_sales_summary
WHERE $WHERE_CLAUSE
GROUP BY date
ORDER BY date DESC
LIMIT 10;
EOF
    
    echo ""
    echo -e "${CYAN}🏪 按店铺汇总 (Top 10):${NC}"
    docker exec -i delivery_postgres psql -U delivery_user -d delivery_data <<EOF
SELECT 
    store_code AS "店铺代码",
    MAX(store_name) AS "店铺名称",
    COUNT(DISTINCT platform) AS "平台",
    COUNT(DISTINCT date) AS "日期",
    SUM(order_count) AS "订单",
    CONCAT('£', ROUND(SUM(gross_sales), 2)) AS "销售额(折前)",
    CONCAT('£', ROUND(SUM(net_sales), 2)) AS "净销售额",
    CONCAT('£', ROUND(AVG(avg_order_value), 2)) AS "客单价"
FROM daily_sales_summary
WHERE $WHERE_CLAUSE
GROUP BY store_code
ORDER BY SUM(net_sales) DESC
LIMIT 10;
EOF

    echo ""
    echo -e "${CYAN}💰 销售额排行 (单日Top 10):${NC}"
    docker exec -i delivery_postgres psql -U delivery_user -d delivery_data <<EOF
SELECT 
    date AS "日期",
    platform AS "平台",
    store_code AS "店铺",
    order_count AS "订单",
    CONCAT('£', net_sales) AS "净销售额",
    CONCAT('£', avg_order_value) AS "客单价"
FROM daily_sales_summary
WHERE $WHERE_CLAUSE
ORDER BY net_sales DESC
LIMIT 10;
EOF

else
    # 详细数据
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  📊 每日销售汇总明细${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "${YELLOW}筛选: $FILTER_INFO${NC}"
    echo ""
    
    docker exec -i delivery_postgres psql -U delivery_user -d delivery_data <<EOF
SELECT 
    date AS "日期",
    TO_CHAR(date, 'Dy') AS "星期",
    platform AS "平台",
    store_code AS "店铺代码",
    store_name AS "店铺名称",
    order_count AS "订单",
    CONCAT('£', gross_sales) AS "销售额(折前)",
    CONCAT('£', net_sales) AS "净销售额",
    CONCAT('£', avg_order_value) AS "客单价",
    TO_CHAR(updated_at, 'MM-DD HH24:MI') AS "更新时间"
FROM daily_sales_summary
WHERE $WHERE_CLAUSE
ORDER BY date DESC, platform, net_sales DESC;
EOF

    # 显示记录总数
    echo ""
    TOTAL=$(docker exec -i delivery_postgres psql -U delivery_user -d delivery_data -t -c "SELECT COUNT(*) FROM daily_sales_summary WHERE $WHERE_CLAUSE;")
    echo -e "${GREEN}📝 共 ${TOTAL// /} 条记录${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 查询完成${NC}"
echo -e "${GREEN}========================================${NC}"
