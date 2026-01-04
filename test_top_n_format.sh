#!/bin/bash

# 测试新的 Top N P 格式热门菜品查询

BASE_URL="http://localhost:8000"

echo "========================================="
echo "测试 Top N P 格式热门菜品查询"
echo "========================================="
echo ""

test_command() {
    local text="$1"
    local desc="$2"
    local encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$text'))")
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 测试: $desc"
    echo "指令: $text"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    result=$(curl -s -X POST "$BASE_URL/feishu/bot/test?text=$encoded")
    
    # 检查是否识别命令
    command_type=$(echo "$result" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('command', {}).get('type', 'unknown'))")
    
    if [ "$command_type" = "null" ] || [ "$command_type" = "unknown" ]; then
        echo "❌ 命令未识别"
    else:
        echo "✅ 命令类型: $command_type"
        
        # 提取参数
        echo ""
        echo "📋 解析参数:"
        echo "$result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
params = data.get('command', {}).get('params', {})
for key, value in params.items():
    print(f'  • {key}: {value}')
"
        
        echo ""
        echo "📊 响应内容:"
        # 提取并显示响应文本
        echo "$result" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('response', {}).get('content', {}).get('text', '无响应'))" | head -20
    fi
    
    echo ""
    echo ""
}

# 基础格式测试
echo "========================================="
echo "1️⃣ 基础格式测试"
echo "========================================="
echo ""

test_command "Top 5" "显示前5名（默认汇总）"
test_command "Top 10" "显示前10名（默认汇总）"
test_command "Top 3" "显示前3名（测试小数量）"

# 时间范围测试
echo "========================================="
echo "2️⃣ 时间范围测试（前P天）"
echo "========================================="
echo ""

test_command "Top 5 7" "前5名，最近7天"
test_command "Top 10 30" "前10名，最近30天"
test_command "Top 8 14" "前8名，最近14天"

# 店铺筛选测试
echo "========================================="
echo "3️⃣ 店铺筛选测试"
echo "========================================="
echo ""

test_command "Top 5 7 Battersea" "巴特西店，最近7天，前5名"
test_command "Top 10 14 piccadilly" "Piccadilly店，最近14天，前10名"
test_command "Top 3 east" "East店，所有时间，前3名"

# 平台筛选测试
echo "========================================="
echo "4️⃣ 平台筛选测试"
echo "========================================="
echo ""

test_command "Top 5 10 Battersea deliveroo" "巴特西店，最近10天，Deliveroo平台，前5名"
test_command "Top 8 7 piccadilly panda" "Piccadilly店，最近7天，Panda平台，前8名"

# 类型筛选测试
echo "========================================="
echo "5️⃣ 类型筛选测试"
echo "========================================="
echo ""

test_command "Top 5 10 Battersea deliveroo main" "巴特西店，最近10天，Deliveroo，主产品，前5名"
test_command "Top 8 14 piccadilly panda modifier" "Piccadilly店，最近14天，Panda，添加项，前8名"
test_command "Top 10 7 east deliveroo summary" "East店，最近7天，Deliveroo，汇总，前10名"

# 完整参数测试
echo "========================================="
echo "6️⃣ 完整参数组合测试"
echo "========================================="
echo ""

test_command "Top 3 30 Battersea deliveroo modifier" "完整参数：巴特西，30天，Deliveroo，添加项，前3"
test_command "Top 7 14 piccadilly panda main" "完整参数：Piccadilly，14天，Panda，主产品，前7"

# 旧格式兼容性测试
echo "========================================="
echo "7️⃣ 旧格式兼容性测试"
echo "========================================="
echo ""

test_command "热门菜品" "旧格式：热门菜品"
test_command "热门主产品" "旧格式：热门主产品"
test_command "Piccadilly店 热门添加项" "旧格式：店铺+热门添加项"

echo "========================================="
echo "✅ 测试完成！"
echo "========================================="
echo ""

echo "💡 新格式总结："
echo "  Top N [P] [店铺] [平台] [类型]"
echo ""
echo "  • N: 显示数量（必填，1-50）"
echo "  • P: 前P天数据（可选）"
echo "  • 店铺: 店铺名称（可选，英文/中文）"
echo "  • 平台: deliveroo/panda（可选）"
echo "  • 类型: main/modifier/summary（可选，默认summary）"
echo ""
echo "📖 示例："
echo "  Top 5              - 前5名，所有时间，所有店铺，所有平台，汇总"
echo "  Top 5 7            - 前5名，最近7天"
echo "  Top 5 7 Battersea  - 前5名，最近7天，巴特西店"
echo "  Top 5 10 Battersea deliveroo      - 前5名，最近10天，巴特西，Deliveroo"
echo "  Top 5 10 Battersea deliveroo main - 前5名，最近10天，巴特西，Deliveroo，主产品"
