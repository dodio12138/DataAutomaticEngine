#!/bin/bash

# 通用订单详情导入脚本（整合全量导入与增量导入）
# 
# 用法：
#   ./import_orders.sh                        # 导入所有订单（全量导入）
#   ./import_orders.sh --days 1               # 导入最近1天的订单（增量导入）
#   ./import_orders.sh --days 7               # 导入最近7天的订单
#   ./import_orders.sh --date 2025-12-20      # 从指定日期开始导入
#   ./import_orders.sh --date-range 2025-12-20 2025-12-31  # 导入日期范围（未来扩展）
#   ./import_orders.sh --platform deliveroo --days 3  # 指定平台导入最近3天
#
# 参数说明：
#   --days N            导入最近N天的订单（增量导入）
#   --date YYYY-MM-DD   从指定日期开始导入
#   --platform NAME     指定平台（默认 deliveroo）
#   --help             显示此帮助信息

set -e

API_URL="http://localhost:8000"
ENDPOINT="/run/import-order-details"

# 默认参数
PLATFORM="deliveroo"
MODE="all"  # all, days, date, date-range
DAYS=""
START_DATE=""
END_DATE=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --days)
            MODE="days"
            DAYS="$2"
            shift 2
            ;;
        --date)
            MODE="date"
            START_DATE="$2"
            shift 2
            ;;
        --date-range)
            MODE="date-range"
            START_DATE="$2"
            END_DATE="$3"
            shift 3
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --help|-h)
            echo "通用订单详情导入脚本"
            echo ""
            echo "用法："
            echo "  $0                                  导入所有订单（全量导入）"
            echo "  $0 --days N                         导入最近N天的订单"
            echo "  $0 --date YYYY-MM-DD                从指定日期开始导入"
            echo "  $0 --platform NAME --days N         指定平台导入最近N天"
            echo ""
            echo "参数："
            echo "  --days N            导入最近N天的订单（增量导入）"
            echo "  --date YYYY-MM-DD   从指定日期开始导入"
            echo "  --platform NAME     指定平台（默认 deliveroo）"
            echo "  --help, -h          显示此帮助信息"
            echo ""
            echo "示例："
            echo "  $0                          # 全量导入所有订单"
            echo "  $0 --days 1                 # 每日增量导入"
            echo "  $0 --days 7                 # 补充最近一周"
            echo "  $0 --date 2025-12-20        # 从12月20日开始导入"
            echo ""
            exit 0
            ;;
        *)
            echo "❌ 未知参数: $1"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 显示导入信息
echo ""
echo "========================================="
echo "🚀 订单详情导入工具"
echo "========================================="
echo "平台: $PLATFORM"

case $MODE in
    all)
        echo "模式: 全量导入（所有订单）"
        ;;
    days)
        echo "模式: 增量导入（最近 $DAYS 天）"
        ;;
    date)
        echo "模式: 从指定日期开始导入"
        echo "起始日期: $START_DATE"
        ;;
    date-range)
        echo "模式: 日期范围导入"
        echo "起始日期: $START_DATE"
        echo "结束日期: $END_DATE"
        ;;
esac
echo "========================================="
echo ""

# 全量导入时显示数据统计和确认
if [ "$MODE" = "all" ]; then
    echo "📊 检查数据库中的订单数量..."
    
    TOTAL_ORDERS=$(docker exec delivery_postgres psql -U delivery_user -d delivery_data -t -c "
        SELECT COUNT(*) 
        FROM raw_orders 
        WHERE platform = '$PLATFORM'
    " | xargs)
    
    IMPORTED_ORDERS=$(docker exec delivery_postgres psql -U delivery_user -d delivery_data -t -c "
        SELECT COUNT(DISTINCT order_id) 
        FROM orders 
        WHERE platform = '$PLATFORM'
    " | xargs)
    
    echo "✅ raw_orders 表中有 $TOTAL_ORDERS 条 $PLATFORM 订单"
    echo "📦 已导入订单数量: $IMPORTED_ORDERS"
    echo "🆕 待导入订单数量: $((TOTAL_ORDERS - IMPORTED_ORDERS))"
    echo ""
    
    if [ $((TOTAL_ORDERS - IMPORTED_ORDERS)) -eq 0 ]; then
        echo "✅ 所有订单已导入完成，无需重复导入！"
        exit 0
    fi
    
    # 询问用户确认
    read -p "❓ 是否继续全量导入？(y/n): " CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo "❌ 取消导入"
        exit 0
    fi
    echo ""
fi

# 构建 API 请求 JSON
case $MODE in
    all)
        REQUEST_BODY="{\"platform\": \"$PLATFORM\"}"
        ;;
    days)
        REQUEST_BODY="{\"platform\": \"$PLATFORM\", \"days\": $DAYS}"
        ;;
    date)
        REQUEST_BODY="{\"platform\": \"$PLATFORM\", \"start_date\": \"$START_DATE\"}"
        ;;
    date-range)
        # 未来扩展：需要 API 支持 end_date 参数
        echo "⚠️  日期范围导入功能需要 API 扩展支持"
        echo "暂时使用 start_date 参数，从 $START_DATE 开始导入所有数据"
        REQUEST_BODY="{\"platform\": \"$PLATFORM\", \"start_date\": \"$START_DATE\"}"
        ;;
esac

echo "========================================="
echo "⏳ 正在导入订单详情..."
echo "========================================="
echo ""

# 发起导入请求
RESPONSE=$(curl -s -X POST "$API_URL$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY")

# 检查 curl 是否成功
if [ $? -ne 0 ]; then
    echo "❌ API 请求失败！"
    echo "请确保 API 服务正在运行: docker ps | grep delivery_api"
    exit 1
fi

# 提取关键信息
STATUS=$(echo "$RESPONSE" | jq -r '.status // "unknown"')
EXIT_CODE=$(echo "$RESPONSE" | jq -r '.exit_code // 999')
CONTAINER_NAME=$(echo "$RESPONSE" | jq -r '.container_name // "N/A"')
LOG_FILE=$(echo "$RESPONSE" | jq -r '.log_file // "N/A"')

echo "📋 导入任务信息："
echo "   状态: $STATUS"
echo "   容器: $CONTAINER_NAME"
echo "   退出码: $EXIT_CODE"
echo "   日志文件: $LOG_FILE"
echo ""

# 显示导入输出（最后500字符，包含统计信息）
if echo "$RESPONSE" | jq -e '.output' > /dev/null 2>&1; then
    echo "========================================="
    echo "📊 导入结果："
    echo "========================================="
    OUTPUT=$(echo "$RESPONSE" | jq -r '.output')
    
    # 如果输出太长，只显示最后部分
    if [ ${#OUTPUT} -gt 1000 ]; then
        echo "${OUTPUT: -1000}"
    else
        echo "$OUTPUT"
    fi
    echo ""
fi

# 检查退出码
if [ "$EXIT_CODE" -ne 0 ]; then
    echo "❌ 导入失败！退出码: $EXIT_CODE"
    echo "请查看日志文件: $LOG_FILE"
    exit 1
fi

# 增量导入时不需要等待和详细统计
if [ "$MODE" != "all" ]; then
    echo "✅ 增量导入完成！"
    echo ""
    echo "💡 查看详细统计："
    echo "  docker exec delivery_postgres psql -U delivery_user -d delivery_data -c \\"
    echo "    \"SELECT store_code, COUNT(*) FROM orders WHERE platform='$PLATFORM' GROUP BY store_code;\""
    echo ""
    exit 0
fi

# 全量导入时显示详细统计
echo "⏳ 等待 10 秒后查询最终导入结果..."
sleep 10

echo ""
echo "========================================="
echo "📊 最终导入统计"
echo "========================================="

# 查询导入后的统计
docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
    '订单总数' as "统计项目",
    COUNT(DISTINCT order_id)::text as "数量"
FROM orders
WHERE platform = '$PLATFORM'

UNION ALL

SELECT 
    '订单项总数',
    COUNT(*)::text
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
WHERE o.platform = '$PLATFORM'

UNION ALL

SELECT 
    '添加项总数',
    COUNT(*)::text
FROM order_item_modifiers oim
JOIN orders o ON oim.order_id = o.order_id
WHERE o.platform = '$PLATFORM'

UNION ALL

SELECT 
    '店铺数量',
    COUNT(DISTINCT store_code)::text
FROM orders
WHERE platform = '$PLATFORM';
EOF

echo ""
echo "========================================="
echo "🏪 各店铺订单分布"
echo "========================================="

docker exec delivery_postgres psql -U delivery_user -d delivery_data << EOF
SELECT 
    store_code as "店铺代码",
    COUNT(*) as "订单数",
    ROUND(SUM(total_amount)::numeric, 2) as "总金额"
FROM orders
WHERE platform = '$PLATFORM'
GROUP BY store_code
ORDER BY COUNT(*) DESC;
EOF

echo ""
echo "========================================="
echo "✅ 订单详情导入完成！"
echo "========================================="
echo ""

echo "💡 后续操作："
echo "  • 查看热门菜品: curl http://localhost:8000/stats/items/top?limit=10"
echo "  • 查看热门添加项: curl http://localhost:8000/stats/modifiers/top?limit=10"
echo "  • 在飞书查询: Top 10 (使用飞书机器人)"
echo ""
