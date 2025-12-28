#!/bin/bash

# 显示帮助信息
show_help() {
    cat << EOF
${BLUE}========================================
  📊 数据库每日汇总工具
========================================${NC}

${CYAN}功能说明：${NC}
  查看指定日期或时间段的订单详细汇总，包括总体数据、店铺分布、
  平台分布、每日趋势和时段分布。

${CYAN}用法：${NC}
  ./db_daily_summary.sh [选项] [起始日期] [结束日期]

${CYAN}选项：${NC}
  --help, -h           显示此帮助信息
  --platform, -p       指定平台 (hungrypanda, deliveroo 或 all, 默认: all)

${CYAN}参数：${NC}
  起始日期      查询的开始日期 (YYYY-MM-DD 格式，可选)
  结束日期      查询的结束日期 (YYYY-MM-DD 格式，可选)
  
  ${YELLOW}注意：${NC}
  - 不提供参数时，默认查询昨天的数据
  - 只提供一个日期时，查询该日期的单日数据
  - 提供两个日期时，查询日期范围内的数据

${CYAN}示例：${NC}
  ${GREEN}# 查看昨天的数据（所有平台）${NC}
  ./db_daily_summary.sh

  ${GREEN}# 查看昨天仅 HungryPanda 平台数据${NC}
  ./db_daily_summary.sh --platform hungrypanda

  ${GREEN}# 查看昨天仅 Deliveroo 平台数据${NC}
  ./db_daily_summary.sh -p deliveroo

  ${GREEN}# 查看指定日期（2025-12-24）${NC}
  ./db_daily_summary.sh 2025-12-24

  ${GREEN}# 查看指定日期仅 Deliveroo 平台${NC}
  ./db_daily_summary.sh --platform deliveroo 2025-12-24

  ${GREEN}# 查看日期范围（2025-12-20 到 2025-12-24）${NC}
  ./db_daily_summary.sh 2025-12-20 2025-12-24

  ${GREEN}# 查看本周数据（仅 HungryPanda）${NC}
  ./db_daily_summary.sh -p hungrypanda 2025-12-23 2025-12-26

${CYAN}输出内容：${NC}
  📈 时段总体数据    - 总订单数、总营收、平均客单价等
  🏪 各店铺数据      - 每个店铺的订单数和营收
  📊 订单平台分布    - 各外卖平台的订单数量和营收
  📅 每日数据趋势    - 每天的订单和营收趋势（多日查询时显示）
  ⏰ 订单时段分布    - 按小时统计订单分布

${CYAN}依赖：${NC}
  - Docker 容器 delivery_postgres 必须运行
  - PostgreSQL 数据库中的 raw_orders 表

${CYAN}相关工具：${NC}
  ./db_stats.sh          - 查看数据库整体统计
  ./db_view_orders.sh    - 查看订单明细
  ./manual_crawl.sh      - 手动触发爬虫

EOF
    exit 0
}

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

# 检查帮助选项
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
fi

# 解析平台参数
PLATFORM_FILTER=""
if [ "$1" = "--platform" ] || [ "$1" = "-p" ]; then
    PLATFORM_ARG="$2"
    if [ "$PLATFORM_ARG" != "all" ]; then
        PLATFORM_FILTER="AND platform = '$PLATFORM_ARG'"
    fi
    shift 2
fi

# 默认日期：昨天
if [ -z "$1" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        START_DATE=$(date -v-1d +%Y-%m-%d)
    else
        START_DATE=$(date -d "yesterday" +%Y-%m-%d)
    fi
    END_DATE="$START_DATE"
    DATE_LABEL="$START_DATE"
else
    START_DATE="$1"
    if [ -z "$2" ]; then
        END_DATE="$1"
        DATE_LABEL="$START_DATE"
    else
        END_DATE="$2"
        DATE_LABEL="${START_DATE} 至 ${END_DATE}"
    fi
fi

PLATFORM_LABEL=""
[ -n "$PLATFORM_ARG" ] && [ "$PLATFORM_ARG" != "all" ] && PLATFORM_LABEL=" (${PLATFORM_ARG})"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  📊 ${DATE_LABEL} 汇总${PLATFORM_LABEL}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查数据库容器
if ! docker ps | grep -q delivery_postgres; then
    echo -e "${RED}❌ 数据库容器未运行${NC}"
    exit 1
fi

# 1. 总体数据
echo -e "${CYAN}📈 时段总体数据:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        COUNT(DISTINCT order_id) as 总订单数,
        ROUND(SUM(estimated_revenue)::numeric, 2) as 总营收,
        ROUND(AVG(estimated_revenue)::numeric, 2) as 平均客单价,
        ROUND(SUM(product_amount)::numeric, 2) as 商品金额,
        ROUND(SUM(discount_amount)::numeric, 2) as 优惠金额
    FROM raw_orders
    WHERE DATE(order_date) >= '$START_DATE' AND DATE(order_date) <= '$END_DATE' $PLATFORM_FILTER;
"

# 2. 各店铺数据
echo -e "${CYAN}🏪 各店铺数据:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        COALESCE(s.name_cn, r.store_name) as 店铺,
        COUNT(DISTINCT r.order_id) as 订单数,
        ROUND(SUM(r.estimated_revenue)::numeric, 2) as 营收,
        ROUND(AVG(r.estimated_revenue)::numeric, 2) as 客单价,
        ROUND(SUM(r.discount_amount)::numeric, 2) as 优惠
    FROM raw_orders r
    LEFT JOIN stores s ON r.store_code = s.code
    WHERE DATE(r.order_date) >= '$START_DATE' AND DATE(r.order_date) <= '$END_DATE' $PLATFORM_FILTER
    GROUP BY COALESCE(s.name_cn, r.store_name)
    ORDER BY COUNT(DISTINCT r.order_id) DESC;
"

# 3. 订单平台分布
echo -e "${CYAN}📊 订单平台分布:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        platform as 平台,
        COUNT(DISTINCT order_id) as 数量,
        ROUND(SUM(estimated_revenue)::numeric, 2) as 营收
    FROM raw_orders
    WHERE DATE(order_date) >= '$START_DATE' AND DATE(order_date) <= '$END_DATE' $PLATFORM_FILTER
    GROUP BY platform
    ORDER BY COUNT(DISTINCT order_id) DESC;
"

# 4. 按日期汇总（多日时显示每日数据）
if [ "$START_DATE" != "$END_DATE" ]; then
    echo -e "${CYAN}📅 每日数据趋势:${NC}"
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
        SELECT 
            DATE(order_date) as 日期,
            COUNT(DISTINCT order_id) as 订单数,
            ROUND(SUM(estimated_revenue)::numeric, 2) as 营收,
            ROUND(AVG(estimated_revenue)::numeric, 2) as 客单价
        FROM raw_orders
        WHERE DATE(order_date) >= '$START_DATE' AND DATE(order_date) <= '$END_DATE' $PLATFORM_FILTER
        GROUP BY DATE(order_date)
        ORDER BY DATE(order_date);
    "
fi

# 5. 小时分布（订单高峰时段）
echo -e "${CYAN}⏰ 订单时段分布:${NC}"
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        EXTRACT(HOUR FROM order_date) as 时段,
        COUNT(DISTINCT order_id) as 订单数,
        ROUND(SUM(estimated_revenue)::numeric, 2) as 营收
    FROM raw_orders
    WHERE DATE(order_date) >= '$START_DATE' AND DATE(order_date) <= '$END_DATE' $PLATFORM_FILTER
    GROUP BY EXTRACT(HOUR FROM order_date)
    ORDER BY EXTRACT(HOUR FROM order_date);
"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 汇总查询完成${NC}"
echo -e "${GREEN}========================================${NC}"
