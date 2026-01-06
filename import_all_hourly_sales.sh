#!/bin/bash
# 一键导入所有已知订单数据并聚合每小时销售数据
# 
# 用法:
#   ./import_all_hourly_sales.sh                        # 自动检测全部数据范围
#   ./import_all_hourly_sales.sh 2025-12-01             # 从 2025-12-01 到今天（含今天）
#   ./import_all_hourly_sales.sh 2025-12-01 2025-12-31  # 从 2025-12-01 到 2025-12-31（含 12-31）
#
# 注意: 日期范围包含开始日期和结束日期当天的所有数据

# 解析命令行参数
if [ $# -eq 2 ]; then
    # 用户提供了开始和结束日期
    CUSTOM_START_DATE=$1
    CUSTOM_END_DATE=$2
    echo "📅 使用指定日期范围: $CUSTOM_START_DATE ~ $CUSTOM_END_DATE (含两端日期)"
    USE_CUSTOM_RANGE=true
elif [ $# -eq 1 ]; then
    # 用户只提供了开始日期，结束日期默认为今天
    CUSTOM_START_DATE=$1
    CUSTOM_END_DATE=$(date +%Y-%m-%d)
    echo "📅 使用指定开始日期: $CUSTOM_START_DATE ~ $CUSTOM_END_DATE (含今天)"
    USE_CUSTOM_RANGE=true
elif [ $# -eq 0 ]; then
    # 没有参数，自动检测全部范围
    USE_CUSTOM_RANGE=false
else
    echo "❌ 参数错误"
    echo "用法:"
    echo "  $0                        # 自动检测全部数据范围"
    echo "  $0 2025-12-01             # 从 2025-12-01 到今天（含今天）"
    echo "  $0 2025-12-01 2025-12-31  # 从 2025-12-01 到 2025-12-31（含 12-31）"
    echo ""
    echo "注意: 日期范围包含开始日期和结束日期当天的所有数据"
    exit 1
fi

echo "🚀 批量导入历史数据 - 每小时销售分析"
echo "================================================"
echo ""

if [ "$USE_CUSTOM_RANGE" = true ]; then
    # 使用用户指定的日期范围
    START_DATE=$CUSTOM_START_DATE
    END_DATE=$CUSTOM_END_DATE
else
    # 自动检测数据库中的日期范围
    echo "🔍 检查数据库中的订单日期范围..."

    # 从 orders 表（Deliveroo）
    DELIVEROO_RANGE=$(docker exec delivery_postgres psql -U delivery_user -d delivery_data -t -c "
        SELECT 
            TO_CHAR(MIN(DATE(placed_at)), 'YYYY-MM-DD') as min_date,
            TO_CHAR(MAX(DATE(placed_at)), 'YYYY-MM-DD') as max_date
        FROM orders
        WHERE status = 'delivered' AND placed_at IS NOT NULL
    " 2>/dev/null | tr -d ' ')

    # 从 raw_orders 表（HungryPanda）
    PANDA_RANGE=$(docker exec delivery_postgres psql -U delivery_user -d delivery_data -t -c "
        SELECT 
            TO_CHAR(MIN(DATE(order_date)), 'YYYY-MM-DD') as min_date,
            TO_CHAR(MAX(DATE(order_date)), 'YYYY-MM-DD') as max_date
        FROM raw_orders
        WHERE platform = 'panda' AND order_date IS NOT NULL
    " 2>/dev/null | tr -d ' ')

    echo "  📦 Deliveroo 订单: $DELIVEROO_RANGE"
    echo "  🐼 HungryPanda 订单: $PANDA_RANGE"
    echo ""

    # 提取最早和最晚日期
    MIN_DATE_D=$(echo $DELIVEROO_RANGE | cut -d'|' -f1)
    MAX_DATE_D=$(echo $DELIVEROO_RANGE | cut -d'|' -f2)
    MIN_DATE_P=$(echo $PANDA_RANGE | cut -d'|' -f1)
    MAX_DATE_P=$(echo $PANDA_RANGE | cut -d'|' -f2)

    # 确定总体范围
    if [ -n "$MIN_DATE_D" ] && [ -n "$MIN_DATE_P" ]; then
        if [[ "$MIN_DATE_D" < "$MIN_DATE_P" ]]; then
            START_DATE=$MIN_DATE_D
        else
            START_DATE=$MIN_DATE_P
        fi
        
        if [[ "$MAX_DATE_D" > "$MAX_DATE_P" ]]; then
            END_DATE=$MAX_DATE_D
        else
            END_DATE=$MAX_DATE_P
        fi
    elif [ -n "$MIN_DATE_D" ]; then
        START_DATE=$MIN_DATE_D
        END_DATE=$MAX_DATE_D
    elif [ -n "$MIN_DATE_P" ]; then
        START_DATE=$MIN_DATE_P
        END_DATE=$MAX_DATE_P
    else
        echo "❌ 数据库中没有找到订单数据"
        exit 1
    fi
fi

echo "📅 总体数据范围: $START_DATE ~ $END_DATE (含两端日期)"
echo ""

# 确认
read -p "⚠️  将聚合从 $START_DATE 到 $END_DATE 的所有数据（含两端日期），确认继续？(y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "取消操作"
    exit 1
fi

echo ""
echo "🔄 开始批量聚合..."
echo "================================================"
echo ""

# 调用聚合脚本
./sync_hourly_sales.sh --start-date "$START_DATE" --end-date "$END_DATE"

echo ""
echo "================================================"
echo "✅ 全部完成！"
echo ""
echo "📊 查看结果:"
echo "   docker exec delivery_postgres psql -U delivery_user -d delivery_data -c \"SELECT date, COUNT(*) FROM hourly_sales GROUP BY date ORDER BY date DESC LIMIT 10\""
