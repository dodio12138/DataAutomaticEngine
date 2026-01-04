#!/bin/bash

# 测试飞书机器人热门菜品查询功能（显示实际文本）

BASE_URL="http://localhost:8000"

echo "========================================="
echo "飞书机器人热门菜品查询功能测试"
echo "========================================="
echo ""

test_command() {
    local text="$1"
    local encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$text'))")
    
    echo "📝 测试指令: $text"
    echo "----------------------------------------"
    
    result=$(curl -s -X POST "$BASE_URL/feishu/bot/test?text=$encoded")
    
    # 检查是否识别命令
    command_type=$(echo "$result" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('command', {}).get('type', 'unknown'))")
    
    if [ "$command_type" = "null" ] || [ "$command_type" = "unknown" ]; then
        echo "❌ 命令未识别"
    else
        echo "✅ 命令类型: $command_type"
        echo ""
        # 提取并显示响应文本
        echo "$result" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('response', {}).get('content', {}).get('text', '无响应'))"
    fi
    
    echo ""
    echo "========================================="
    echo ""
}

# 测试各种命令
test_command "热门菜品"
test_command "热门主产品"
test_command "热门添加项"
test_command "Piccadilly店 热门菜品"
test_command "2025-12-27 热门主产品"
test_command "battersea 热门添加项 deliveroo"

echo "✅ 所有测试完成！"
echo ""
echo "💡 支持的指令格式："
echo "  • 热门菜品 / 热门汇总 - 显示主产品和添加项 TOP 5"
echo "  • 热门主产品 - 显示主产品 TOP 10"
echo "  • 热门添加项 - 显示添加项 TOP 10"
echo "  • [店铺名] 热门菜品 - 指定店铺查询"
echo "  • [日期] 热门主产品 - 指定日期查询"
echo "  • [店铺] [日期] 热门添加项 [平台] - 综合筛选"
