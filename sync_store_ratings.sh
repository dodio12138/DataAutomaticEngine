#!/bin/bash
# 同步店铺评分数据到飞书多维表格

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 帮助信息
show_help() {
    echo -e "${BLUE}⭐ 店铺评分数据飞书同步${NC}"
    echo "=============================="
    echo ""
    echo "用法: ./sync_store_ratings.sh [开始日期] [结束日期]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo ""
    echo "说明:"
    echo "  • 不传参数：默认同步昨天的数据"
    echo "  • 传1个日期：同步指定日期的数据"
    echo "  • 传2个日期：同步日期范围内所有数据"
    echo ""
    echo "示例:"
    echo "  ./sync_store_ratings.sh"
    echo "    → 同步昨天的数据"
    echo ""
    echo "  ./sync_store_ratings.sh 2026-01-15"
    echo "    → 同步 2026-01-15 当天的数据"
    echo ""
    echo "  ./sync_store_ratings.sh 2026-01-10 2026-01-15"
    echo "    → 同步 2026-01-10 至 2026-01-15 之间所有日期的数据"
    echo ""
    echo "数据流程:"
    echo "  评分爬虫 → store_ratings 表 → 飞书多维表格"
    echo ""
    echo "注意事项:"
    echo "  • 确保数据库中有对应日期的评分数据"
    echo "  • 使用 ./manual_ratings.sh 爬取评分数据"
    echo "  • 查看日志: ls -lt api/logs/store_ratings_sync_*.log"
    echo ""
    exit 0
}

# 参数处理
START_DATE=""
END_DATE=""

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        *)
            # 如果是日期格式
            if [[ $1 =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
                if [[ -z "$START_DATE" ]]; then
                    START_DATE="$1"
                elif [[ -z "$END_DATE" ]]; then
                    END_DATE="$1"
                else
                    echo -e "${RED}❌ 参数过多${NC}"
                    echo "使用 --help 查看帮助信息"
                    exit 1
                fi
            else
                echo -e "${RED}❌ 无效的日期格式: $1${NC}"
                echo "正确格式: YYYY-MM-DD"
                echo "使用 --help 查看帮助信息"
                exit 1
            fi
            shift
            ;;
    esac
done

# 如果只指定了开始日期，结束日期等于开始日期
if [[ -n "$START_DATE" ]] && [[ -z "$END_DATE" ]]; then
    END_DATE="$START_DATE"
fi

echo "⭐ 店铺评分数据飞书同步"
echo "=============================="
echo ""

# 默认使用昨天
if [[ -z "$START_DATE" ]] && [[ -z "$END_DATE" ]]; then
    YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
    START_DATE="$YESTERDAY"
    END_DATE="$YESTERDAY"
    echo "📅 未指定日期，默认使用昨天: $YESTERDAY"
fi

# 构建请求体
REQUEST_BODY="{}"
if [[ -n "$START_DATE" ]] && [[ -n "$END_DATE" ]]; then
    if [[ "$START_DATE" == "$END_DATE" ]]; then
        REQUEST_BODY="{\"date\":\"$START_DATE\"}"
        echo "📅 同步日期: $START_DATE"
    else
        REQUEST_BODY="{\"start_date\":\"$START_DATE\",\"end_date\":\"$END_DATE\"}"
        echo "📅 同步日期范围: $START_DATE ~ $END_DATE"
    fi
fi

echo ""

# API 基础地址
API_URL="http://localhost:8000/run/store-ratings/sync-feishu"

# 执行同步
echo "🚀 开始同步店铺评分数据到飞书..."
echo ""

RESPONSE=$(curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d "$REQUEST_BODY")

# 检查返回结果
if echo "$RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ 同步成功！${NC}"
    echo ""
    
    # 提取统计信息
    CREATED=$(echo "$RESPONSE" | grep -o '"created":[0-9]*' | grep -o '[0-9]*')
    UPDATED=$(echo "$RESPONSE" | grep -o '"updated":[0-9]*' | grep -o '[0-9]*')
    FAILED=$(echo "$RESPONSE" | grep -o '"failed":[0-9]*' | grep -o '[0-9]*')
    TOTAL=$(echo "$RESPONSE" | grep -o '"total":[0-9]*' | grep -o '[0-9]*')
    
    if [[ -n "$CREATED" ]] && [[ -n "$UPDATED" ]] && [[ -n "$TOTAL" ]]; then
        echo "📊 同步统计:"
        echo "   ✅ 创建: $CREATED 条"
        echo "   🔄 更新: $UPDATED 条"
        echo "   ❌ 失败: $FAILED 条"
        echo "   📝 总计: $TOTAL 条"
    fi
    
    # 提取日志文件
    LOG_FILE=$(echo "$RESPONSE" | grep -o '"log_file":"[^"]*"' | sed 's/"log_file":"//; s/"//')
    if [[ -n "$LOG_FILE" ]]; then
        echo ""
        echo "📋 详细日志: $LOG_FILE"
    fi
else
    echo -e "${RED}❌ 同步失败${NC}"
    echo ""
    echo "错误信息:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

echo ""
echo "=============================="
echo "✅ 同步完成"
