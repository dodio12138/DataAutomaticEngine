#!/bin/bash
# 聚合每小时销售数据并同步到飞书

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "📊 每小时销售数据聚合与同步"
echo "=============================="
echo ""

# 参数处理
START_DATE=""
END_DATE=""
AGGREGATE_ONLY=false
SYNC_ONLY=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --aggregate-only)
            AGGREGATE_ONLY=true
            shift
            ;;
        --sync-only)
            SYNC_ONLY=true
            shift
            ;;
        --start-date)
            START_DATE="$2"
            shift 2
            ;;
        --end-date)
            END_DATE="$2"
            shift 2
            ;;
        *)
            # 如果是日期格式，作为单个日期
            if [[ $1 =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
                START_DATE="$1"
                END_DATE="$1"
            fi
            shift
            ;;
    esac
done

# 默认使用昨天
if [ -z "$START_DATE" ]; then
    START_DATE=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
    END_DATE=$START_DATE
    echo -e "${YELLOW}📅 未指定日期，使用昨天: $START_DATE${NC}"
    echo ""
fi

# 构建 JSON 数据
if [ -n "$END_DATE" ] && [ "$START_DATE" != "$END_DATE" ]; then
    JSON_DATA="{\"start_date\":\"$START_DATE\",\"end_date\":\"$END_DATE\"}"
    echo "📆 日期范围: $START_DATE ~ $END_DATE"
else
    JSON_DATA="{\"date\":\"$START_DATE\"}"
    echo "📆 日期: $START_DATE"
fi

echo ""

# 步骤1：聚合数据
if [ "$SYNC_ONLY" = false ]; then
    echo "🔄 步骤 1/2: 聚合每小时销售数据..."
    echo "-------------------------------------------------------"
    
    RESPONSE=$(curl -s -X POST http://localhost:8000/run/hourly-sales/aggregate \
        -H "Content-Type: application/json" \
        -d "$JSON_DATA")
    
    STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))" 2>/dev/null)
    
    if [ "$STATUS" = "success" ]; then
        echo -e "${GREEN}✅ 聚合完成${NC}"
        echo "$RESPONSE" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('output', ''))" 2>/dev/null | head -30
    else
        echo -e "${RED}❌ 聚合失败${NC}"
        echo "$RESPONSE"
        exit 1
    fi
    
    echo ""
fi

# 步骤2：同步到飞书
if [ "$AGGREGATE_ONLY" = false ]; then
    echo "🔄 步骤 2/2: 同步到飞书多维表格..."
    echo "-------------------------------------------------------"
    
    RESPONSE=$(curl -s -X POST http://localhost:8000/run/hourly-sales/sync-feishu \
        -H "Content-Type: application/json" \
        -d "$JSON_DATA")
    
    STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))" 2>/dev/null)
    
    if [ "$STATUS" = "success" ]; then
        echo -e "${GREEN}✅ 同步完成${NC}"
        echo "$RESPONSE" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('output', ''))" 2>/dev/null | head -30
    else
        echo -e "${RED}❌ 同步失败${NC}"
        echo "$RESPONSE"
        exit 1
    fi
    
    echo ""
fi

echo "=============================="
echo -e "${GREEN}🎉 全部完成！${NC}"
echo ""
echo "💡 提示："
echo "   - 聚合所有数据: $0 --start-date 2025-01-01 --end-date 2026-01-05"
echo "   - 只聚合不同步: $0 2026-01-05 --aggregate-only"
echo "   - 只同步不聚合: $0 2026-01-05 --sync-only"
