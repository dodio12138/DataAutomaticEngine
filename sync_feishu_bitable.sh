#!/bin/bash
# 飞书多维表格同步便捷脚本
# 用法:
#   ./sync_feishu_bitable.sh                           # 同步最近7天
#   ./sync_feishu_bitable.sh 2025-12-24                # 同步指定日期
#   ./sync_feishu_bitable.sh 2025-12-20 2025-12-25     # 同步日期范围

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# API 地址
API_URL="http://localhost:8000/run/feishu-sync"

# 帮助信息
show_help() {
    cat << EOF
${BLUE}========================================
  📊 飞书多维表格同步工具
========================================${NC}

${YELLOW}功能说明：${NC}
  同步 daily_sales_summary 数据到飞书多维表格
  支持增量更新（已存在则更新，不存在则创建）

${YELLOW}用法：${NC}
  $0 [起始日期] [结束日期]

${YELLOW}参数说明：${NC}
  起始日期      YYYY-MM-DD 格式（可选，默认7天前）
  结束日期      YYYY-MM-DD 格式（可选，默认今天）

${YELLOW}示例：${NC}
  ${GREEN}# 同步最近7天${NC}
  $0

  ${GREEN}# 同步昨天${NC}
  $0 \$(date -v-1d +%Y-%m-%d)

  ${GREEN}# 同步指定日期${NC}
  $0 2025-12-24

  ${GREEN}# 同步日期范围${NC}
  $0 2025-12-20 2025-12-25

${YELLOW}环境变量：${NC}
  需要在 .env 文件中配置以下变量：
  - FEISHU_APP_ID
  - FEISHU_APP_SECRET
  - FEISHU_BITABLE_APP_TOKEN
  - FEISHU_BITABLE_TABLE_ID

EOF
    exit 0
}

# 检查帮助参数
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    show_help
fi

# 检查 API 服务
echo -e "${BLUE}检查 API 服务...${NC}"
if ! curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}❌ API 服务未运行，请先启动：docker compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✅ API 服务正常${NC}\n"

# 解析参数
START_DATE=""
END_DATE=""

if [ -n "$1" ]; then
    START_DATE="$1"
fi

if [ -n "$2" ]; then
    END_DATE="$2"
fi

# 构建 JSON payload
if [ -n "$START_DATE" ] && [ -n "$END_DATE" ]; then
    JSON_DATA="{\"start_date\":\"$START_DATE\",\"end_date\":\"$END_DATE\"}"
    echo -e "${BLUE}同步日期范围: $START_DATE ~ $END_DATE${NC}\n"
elif [ -n "$START_DATE" ]; then
    JSON_DATA="{\"start_date\":\"$START_DATE\",\"end_date\":\"$START_DATE\"}"
    echo -e "${BLUE}同步日期: $START_DATE${NC}\n"
else
    JSON_DATA="{}"
    echo -e "${BLUE}同步最近7天数据${NC}\n"
fi

# 发送请求
echo -e "${YELLOW}开始同步...${NC}\n"

RESPONSE=$(curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d "$JSON_DATA")

# 解析响应
STATUS=$(echo "$RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

if [ "$STATUS" == "success" ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ 同步成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    LOG_FILE=$(echo "$RESPONSE" | grep -o '"log_file":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$LOG_FILE" ]; then
        echo -e "${BLUE}日志文件: $LOG_FILE${NC}"
        echo -e "${BLUE}查看详细日志: cat $LOG_FILE${NC}"
    fi
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ 同步失败${NC}"
    echo -e "${RED}========================================${NC}"
    
    EXIT_CODE=$(echo "$RESPONSE" | grep -o '"exit_code":[0-9]*' | cut -d':' -f2)
    echo -e "${RED}退出码: $EXIT_CODE${NC}"
    
    echo -e "\n${YELLOW}响应详情:${NC}"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    
    exit 1
fi
