#!/bin/bash

# 手动触发爬虫脚本 - 支持日期范围
# 
# 爬虫时间逻辑：start_date=2025-12-24, end_date=2025-12-25 表示爬取12-24当天的数据
#
# 用法: ./manual_crawl.sh [起始日期] [结束日期] [店铺代码]
# 示例: 
#   ./manual_crawl.sh 2025-12-24                      # 爬取12-24当天，所有店铺
#   ./manual_crawl.sh 2025-12-24 battersea_maocai     # 爬取12-24当天，指定店铺
#   ./manual_crawl.sh 2025-12-20 2025-12-25           # 爬取12-20到12-24（5天），所有店铺
#   ./manual_crawl.sh 2025-12-20 2025-12-25 store_a   # 爬取12-20到12-24，指定店铺
#   ./manual_crawl.sh                                 # 爬取昨天，所有店铺

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 解析参数
START_DATE="${1}"
END_DATE="${2}"
STORE_CODE="${3:-all}"

# 如果第二个参数不是日期格式，判断为店铺代码
if [ -n "$2" ] && [[ ! "$2" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    STORE_CODE="$2"
    END_DATE=""
fi

# 如果没有指定起始日期，使用昨天
if [ -z "$START_DATE" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        START_DATE=$(date -v-1d +%Y-%m-%d)
    else
        # Linux
        START_DATE=$(date -d "yesterday" +%Y-%m-%d)
    fi
fi

# 如果没有指定结束日期，默认为起始日期+1天（爬取单日）
if [ -z "$END_DATE" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        END_DATE=$(date -j -v+1d -f "%Y-%m-%d" "$START_DATE" "+%Y-%m-%d")
    else
        # Linux
        END_DATE=$(date -I -d "$START_DATE + 1 day")
    fi
fi


echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  手动触发爬虫 - 批量模式${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${CYAN}起始日期: ${START_DATE}${NC}"
echo -e "${CYAN}结束日期: ${END_DATE}${NC}"
echo -e "${YELLOW}店铺代码: ${STORE_CODE}${NC}"
echo ""

# 检查API容器是否运行
if ! docker ps | grep -q delivery_api; then
    echo -e "${RED}❌ API 容器未运行，请先启动: docker compose up -d api${NC}"
    exit 1
fi

# 计算日期范围内的天数（爬虫逻辑：start到end-1天）
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    start_ts=$(date -j -f "%Y-%m-%d" "$START_DATE" "+%s")
    end_ts=$(date -j -f "%Y-%m-%d" "$END_DATE" "+%s")
else
    # Linux
    start_ts=$(date -d "$START_DATE" +%s)
    end_ts=$(date -d "$END_DATE" +%s)
fi

days=$(( (end_ts - start_ts) / 86400 ))

if [ $days -lt 1 ]; then
    echo -e "${RED}❌ 结束日期必须大于起始日期（爬虫逻辑：start_date 到 end_date 爬取 start_date 当天）${NC}"
    exit 1
fi

echo -e "${CYAN}📅 共需爬取 ${days} 天的数据 (${START_DATE} 到 $(date -j -v-1d -f "%Y-%m-%d" "$END_DATE" "+%Y-%m-%d" 2>/dev/null || date -I -d "$END_DATE - 1 day"))${NC}"
echo ""

# 循环遍历日期范围（按爬虫逻辑：每次传递 current_date 和 current_date+1）
current_date="$START_DATE"
success_count=0
fail_count=0

while [[ "$current_date" < "$END_DATE" ]]; do
    # 计算当天的 end_date（下一天）
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        next_date=$(date -j -v+1d -f "%Y-%m-%d" "$current_date" "+%Y-%m-%d")
    else
        # Linux
        next_date=$(date -I -d "$current_date + 1 day")
    fi
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🔄 正在爬取: ${current_date} (API参数: start=${current_date}, end=${next_date})${NC}"
    echo -e "${YELLOW}   店铺: ${STORE_CODE}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # 构建请求体（按爬虫逻辑：end_date 是下一天）
    REQUEST_BODY=$(cat <<EOF
{
  "store_code": "${STORE_CODE}",
  "start_date": "${current_date}",
  "end_date": "${next_date}"
}
EOF
)
    
    # 从scheduler容器内部调用API（使用Docker网络）
    response=$(docker exec delivery_scheduler sh -c "
        apk add --no-cache curl > /dev/null 2>&1
        curl -s -X POST http://api:8000/run/crawler \
          -H 'Content-Type: application/json' \
          -d '$REQUEST_BODY' \
          -w '\nHTTP_CODE:%{http_code}'
    " 2>&1)
    
    # 提取HTTP状态码
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    response_body=$(echo "$response" | grep -v "HTTP_CODE:")
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ ${current_date} 爬取任务已提交${NC}"
        success_count=$((success_count + 1))
    else
        echo -e "${RED}❌ ${current_date} 爬取任务提交失败 (HTTP ${http_code})${NC}"
        echo -e "${RED}   响应: ${response_body}${NC}"
        fail_count=$((fail_count + 1))
    fi
    
    echo ""
    
    # 移动到下一天
    current_date="$next_date"
    
    # 避免过快请求
    sleep 1
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  爬取任务汇总${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ 成功: ${success_count} 天${NC}"
echo -e "${RED}❌ 失败: ${fail_count} 天${NC}"
echo -e "${CYAN}📊 总计: ${days} 天${NC}"
echo ""
echo -e "${BLUE}查看实时日志:${NC}"
echo -e "  ${YELLOW}docker logs -f delivery_api${NC}"
echo ""
echo -e "${BLUE}查看爬虫日志文件:${NC}"
echo -e "  ${YELLOW}ls -lht api/logs/ | head -10${NC}"
echo ""

if [ $fail_count -gt 0 ]; then
    exit 1
fi
