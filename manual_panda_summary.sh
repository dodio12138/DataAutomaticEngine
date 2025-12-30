#!/bin/bash
# 手动触发 HungryPanda 每日销售汇总 ETL 计算
# 用法:
#   ./manual_panda_summary.sh                           # 昨天所有店铺
#   ./manual_panda_summary.sh 2025-12-22                # 指定日期
#   ./manual_panda_summary.sh 2025-12-20 2025-12-27     # 日期范围
#   ./manual_panda_summary.sh battersea 2025-12-22      # 指定店铺和日期

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
  🐼 HungryPanda 每日销售汇总 ETL 计算
========================================${NC}

${YELLOW}功能说明：${NC}
  从 raw_orders 表聚合计算每日销售汇总
  数据存储到 daily_sales_summary 表

${YELLOW}用法：${NC}
  $0 [店铺代码] [日期1] [日期2]

${YELLOW}参数说明：${NC}
  店铺代码    英文店铺代码（可选，默认 all）
              支持: battersea_maocai, piccadilly_maocai, brent_maocai, 
                    east_maocai, towerbridge_maocai, piccadilly_hotpot, all
  日期1       单日期 YYYY-MM-DD（可选，默认昨天）
  日期2       结束日期 YYYY-MM-DD（可选，与日期1组成范围）

${YELLOW}示例：${NC}
  ${GREEN}# 计算昨天所有店铺${NC}
  $0

  ${GREEN}# 计算指定日期所有店铺${NC}
  $0 2025-12-22

  ${GREEN}# 计算日期范围所有店铺（12-20 到 12-27）${NC}
  $0 2025-12-20 2025-12-27

  ${GREEN}# 计算指定店铺的指定日期${NC}
  $0 battersea_maocai 2025-12-22

  ${GREEN}# 计算指定店铺的日期范围${NC}
  $0 piccadilly_maocai 2025-12-20 2025-12-27

${YELLOW}注意事项：${NC}
  - 需要先运行订单爬虫获取原始数据（raw_orders 表）
  - 如果 raw_orders 无数据，计算结果为空
  - 使用 ./manual_crawl.sh 手动补全订单数据

${YELLOW}相关工具：${NC}
  ./manual_deliveroo_summary.sh  - Deliveroo 每日汇总爬虫
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
    JSON_DATA="{\"store_code\":\"$STORES\",\"date\":\"$DATE\"}"
    DATE_LABEL="$DATE"
else
    JSON_DATA="{\"store_code\":\"$STORES\",\"start_date\":\"$START_DATE\",\"end_date\":\"$END_DATE\"}"
    DATE_LABEL="$START_DATE 至 $END_DATE"
fi

STORE_LABEL="$STORES"
[ "$STORES" = "all" ] && STORE_LABEL="所有店铺"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  🐼 HungryPanda 每日销售汇总 ETL${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}店铺: ${STORE_LABEL}${NC}"
echo -e "${YELLOW}日期: ${DATE_LABEL}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 发送请求
echo -e "${YELLOW}⏳ 正在发起请求...${NC}"
RESPONSE=$(curl -s -X POST http://localhost:8000/run/panda/daily-summary \
    -H "Content-Type: application/json" \
    -d "$JSON_DATA")

# 检查响应
if echo "$RESPONSE" | grep -q '"exit_code":0' || echo "$RESPONSE" | grep -q '"exit_code": 0'; then
    echo -e "${GREEN}✅ 任务已提交成功${NC}"
    echo ""
    echo -e "${YELLOW}📝 提示：${NC}"
    echo "  - 任务将在后台执行，通常需要 10-30 秒"
    echo "  - 从 raw_orders 表聚合计算数据"
    echo "  - 结果写入 daily_sales_summary 表"
    echo "  - 使用以下命令查看结果："
    echo ""
    if [ -n "$DATE" ]; then
        echo -e "${BLUE}    ./db_view_daily_summary.sh --platform panda --date $DATE${NC}"
    else
        echo -e "${BLUE}    ./db_view_daily_summary.sh --platform panda --days 10${NC}"
    fi
    echo ""
elif echo "$RESPONSE" | grep -q 'detail'; then
    echo -e "${RED}❌ 请求失败${NC}"
    echo "$RESPONSE" | grep -o '"detail":"[^"]*"' | sed 's/"detail":"/错误: /' | sed 's/"$//'
    exit 1
else
    echo -e "${GREEN}✅ 请求已发送${NC}"
    echo "$RESPONSE"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 完成${NC}"
echo -e "${GREEN}========================================${NC}"
