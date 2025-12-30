#!/bin/bash
# 手动触发 Deliveroo 每日销售汇总爬虫
# 用法:
#   ./manual_deliveroo_summary.sh                           # 昨天所有店铺
#   ./manual_deliveroo_summary.sh 2025-12-22                # 指定日期
#   ./manual_deliveroo_summary.sh 2025-12-20 2025-12-27     # 日期范围
#   ./manual_deliveroo_summary.sh battersea 2025-12-22      # 指定店铺和日期

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 默认参数
STORES="all"
DATE=""
START_DATE=""
END_DATE=""

# 帮助信息
show_help() {
    cat << EOF
${BLUE}========================================
  🦘 Deliveroo 每日销售汇总爬虫
========================================${NC}

${YELLOW}功能说明：${NC}
  从 Deliveroo Summary API 爬取每日销售汇总数据
  数据存储到 daily_sales_summary 表

${YELLOW}用法：${NC}
  $0 [店铺代码] [日期1] [日期2]

${YELLOW}参数说明：${NC}
  店铺代码    英文店铺代码（可选，默认 all）
              支持: battersea, piccadilly, brent, east, towerbridge, all
  日期1       单日期 YYYY-MM-DD（可选，默认昨天）
  日期2       结束日期 YYYY-MM-DD（可选，与日期1组成范围）

${YELLOW}示例：${NC}
  ${GREEN}# 补全昨天所有店铺数据${NC}
  $0

  ${GREEN}# 补全指定日期所有店铺${NC}
  $0 2025-12-22

  ${GREEN}# 补全日期范围所有店铺（12-20 到 12-27）${NC}
  $0 2025-12-20 2025-12-27

  ${GREEN}# 补全指定店铺的指定日期${NC}
  $0 battersea 2025-12-22

  ${GREEN}# 补全指定店铺的日期范围${NC}
  $0 piccadilly 2025-12-20 2025-12-27

${YELLOW}相关工具：${NC}
  ./manual_panda_summary.sh      - HungryPanda 每日汇总计算
  ./manual_crawl.sh              - 订单数据爬虫
  ./db_view_daily_summary.sh     - 查看汇总数据

EOF
    exit 0
}

# 检查帮助参数
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
fi

# 解析参数
if [ $# -eq 0 ]; then
    # 无参数：昨天所有店铺
    if [[ "$OSTYPE" == "darwin"* ]]; then
        DATE=$(date -v-1d +%Y-%m-%d)
    else
        DATE=$(date -d "yesterday" +%Y-%m-%d)
    fi
elif [ $# -eq 1 ]; then
    # 一个参数：判断是店铺还是日期
    if [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        # 是日期格式
        DATE="$1"
    else
        # 是店铺代码
        STORES="$1"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            DATE=$(date -v-1d +%Y-%m-%d)
        else
            DATE=$(date -d "yesterday" +%Y-%m-%d)
        fi
    fi
elif [ $# -eq 2 ]; then
    # 两个参数：判断是"店铺+日期"还是"日期范围"
    if [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        # 第一个是日期，那就是日期范围
        START_DATE="$1"
        END_DATE="$2"
    else
        # 第一个是店铺代码
        STORES="$1"
        DATE="$2"
    fi
elif [ $# -eq 3 ]; then
    # 三个参数：店铺 + 日期范围
    STORES="$1"
    START_DATE="$2"
    END_DATE="$3"
else
    echo -e "${RED}错误: 参数过多${NC}"
    echo "使用 --help 查看帮助"
    exit 1
fi

# 验证日期格式
validate_date() {
    if ! [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo -e "${RED}错误: 无效的日期格式 '$1'${NC}"
        echo "请使用 YYYY-MM-DD 格式（例如: 2025-12-22）"
        exit 1
    fi
}

if [ -n "$DATE" ]; then
    validate_date "$DATE"
fi
if [ -n "$START_DATE" ]; then
    validate_date "$START_DATE"
    validate_date "$END_DATE"
fi

# 构建请求 JSON
if [ -n "$DATE" ]; then
    JSON_DATA="{\"stores\":[\"$STORES\"],\"date\":\"$DATE\"}"
    DATE_LABEL="$DATE"
else
    JSON_DATA="{\"stores\":[\"$STORES\"],\"start_date\":\"$START_DATE\",\"end_date\":\"$END_DATE\"}"
    DATE_LABEL="$START_DATE 至 $END_DATE"
fi

STORE_LABEL="$STORES"
[ "$STORES" = "all" ] && STORE_LABEL="所有店铺"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  🦘 Deliveroo 每日销售汇总爬虫${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}店铺: ${STORE_LABEL}${NC}"
echo -e "${YELLOW}日期: ${DATE_LABEL}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 发送请求
echo -e "${YELLOW}⏳ 正在发起请求...${NC}"
RESPONSE=$(curl -s -X POST http://localhost:8000/run/deliveroo/daily-summary \
    -H "Content-Type: application/json" \
    -d "$JSON_DATA")

# 检查响应
if [ -z "$RESPONSE" ]; then
    echo -e "${RED}❌ 无响应，请检查 API 服务是否运行${NC}"
    exit 1
fi

# 检查是否包含严重错误（排除 409 日志错误）
if echo "$RESPONSE" | grep -q '"detail"' && ! echo "$RESPONSE" | grep -q '409 Client Error'; then
    echo -e "${RED}❌ 请求失败${NC}"
    echo "$RESPONSE" | grep -o '"detail":"[^"]*"' | sed 's/"detail":"/错误: /' | sed 's/"$//'
    exit 1
fi

# 409 错误通常是日志获取冲突，但任务已执行，直接验证数据
if echo "$RESPONSE" | grep -q '409 Client Error'; then
    echo -e "${YELLOW}⚠️  容器日志获取冲突（409），但任务可能已执行${NC}"
    echo -e "${YELLOW}⏳ 正在验证数据...${NC}"
    sleep 2
else
    echo -e "${GREEN}✅ 任务已提交${NC}"
fi

# 验证数据是否成功写入
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}📊 数据验证${NC}"
echo -e "${BLUE}========================================${NC}"

if [ -n "$DATE" ]; then
    # 单日查询
    QUERY="SELECT store_code, store_name, gross_sales, net_sales, order_count, avg_order_value FROM daily_sales_summary WHERE date = '$DATE' AND platform = 'deliveroo'"
    if [ "$STORES" != "all" ]; then
        QUERY="$QUERY AND store_code = '$STORES'"
    fi
    QUERY="$QUERY ORDER BY store_code;"
else
    # 日期范围查询
    QUERY="SELECT date, store_code, SUM(gross_sales) as gross_sales, SUM(net_sales) as net_sales, SUM(order_count) as order_count FROM daily_sales_summary WHERE date BETWEEN '$START_DATE' AND '$END_DATE' AND platform = 'deliveroo'"
    if [ "$STORES" != "all" ]; then
        QUERY="$QUERY AND store_code = '$STORES'"
    fi
    QUERY="$QUERY GROUP BY date, store_code ORDER BY date DESC, store_code;"
fi

RESULT=$(docker exec delivery_postgres psql -U delivery_user -d delivery_data -t -c "$QUERY" 2>&1)

if [ $? -eq 0 ] && [ -n "$RESULT" ] && [ "$(echo "$RESULT" | grep -v '^$' | wc -l)" -gt 0 ]; then
    echo -e "${GREEN}✅ 数据已成功写入${NC}"
    echo "$RESULT"
    echo ""
    echo -e "${YELLOW}📝 完整查看：${NC}"
    if [ -n "$DATE" ]; then
        echo -e "${BLUE}    ./db_view_daily_summary.sh --platform deliveroo --date $DATE${NC}"
    else
        echo -e "${BLUE}    ./db_view_daily_summary.sh --platform deliveroo --date $START_DATE${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  未找到数据或数据为空${NC}"
    echo -e "${YELLOW}可能原因：${NC}"
    echo -e "  1. raw_orders 表中无对应日期的订单数据"
    echo -e "  2. 任务仍在执行中，请稍后查询"
    echo ""
    echo -e "${YELLOW}📝 手动查询：${NC}"
    if [ -n "$DATE" ]; then
        echo -e "${BLUE}    ./db_view_daily_summary.sh --platform deliveroo --date $DATE${NC}"
    else
        echo -e "${BLUE}    ./db_view_daily_summary.sh --platform deliveroo --days 10${NC}"
    fi
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 完成${NC}"
echo -e "${GREEN}========================================${NC}"
