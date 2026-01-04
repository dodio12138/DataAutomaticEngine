#!/bin/bash

# 测试飞书机器人热门菜品查询功能

BASE_URL="http://localhost:8000"

echo "========================================="
echo "测试飞书机器人热门菜品查询功能"
echo "========================================="
echo ""

echo "📝 测试指令格式："
echo "1. 热门菜品（汇总）"
echo "2. 热门主产品"
echo "3. 热门添加项"
echo "4. Piccadilly店 热门菜品"
echo "5. 2025-12-27 热门主产品"
echo "6. battersea 2025-12-27 热门添加项"
echo "7. 热门菜品 deliveroo"
echo ""
echo "========================================="
echo ""

# 测试1：基础热门菜品汇总
echo "🔍 测试1：热门菜品（汇总）"
curl -s -X POST "$BASE_URL/feishu/bot/test?text=热门菜品" | jq -r '.response.content.text'
echo ""
echo "========================================="
echo ""

# 测试2：热门主产品
echo "🔍 测试2：热门主产品"
curl -s -X POST "$BASE_URL/feishu/bot/test?text=热门主产品" | jq -r '.response.content.text'
echo ""
echo "========================================="
echo ""

# 测试3：热门添加项
echo "🔍 测试3：热门添加项"
curl -s -X POST "$BASE_URL/feishu/bot/test?text=热门添加项" | jq -r '.response.content.text'
echo ""
echo "========================================="
echo ""

# 测试4：指定店铺
echo "🔍 测试4：Piccadilly店 热门菜品"
curl -s -X POST "$BASE_URL/feishu/bot/test?text=Piccadilly店%20热门菜品" | jq -r '.response.content.text'
echo ""
echo "========================================="
echo ""

# 测试5：指定日期
echo "🔍 测试5：2025-12-27 热门主产品"
curl -s -X POST "$BASE_URL/feishu/bot/test?text=2025-12-27%20热门主产品" | jq -r '.response.content.text'
echo ""
echo "========================================="
echo ""

# 测试6：店铺 + 日期
echo "🔍 测试6：battersea 2025-12-27 热门添加项"
curl -s -X POST "$BASE_URL/feishu/bot/test?text=battersea%202025-12-27%20热门添加项" | jq -r '.response.content.text'
echo ""
echo "========================================="
echo ""

# 测试7：平台筛选
echo "🔍 测试7：热门菜品 deliveroo"
curl -s -X POST "$BASE_URL/feishu/bot/test?text=热门菜品%20deliveroo" | jq -r '.response.content.text'
echo ""
echo "========================================="
echo ""

# 测试8：API 直接查询（验证底层API功能）
echo "🔍 测试8：API 直接查询 - Top Items"
curl -s "$BASE_URL/stats/items/top?limit=5" | jq '.'
echo ""
echo "========================================="
echo ""

echo "🔍 测试9：API 直接查询 - Top Modifiers"
curl -s "$BASE_URL/stats/modifiers/top?limit=5" | jq '.'
echo ""
echo "========================================="
echo ""

echo "🔍 测试10：API 查询 - 指定店铺和日期"
curl -s "$BASE_URL/stats/items/top?store_code=piccadilly_maocai&date=2025-12-27&limit=3" | jq '.'
echo ""
echo "========================================="
echo ""

echo "✅ 测试完成！"
echo ""
echo "💡 提示："
echo "  - 所有查询支持可选参数：店铺、日期、平台"
echo "  - 汇总查询同时显示主产品和添加项的 TOP 5"
echo "  - 单独查询显示完整 TOP 10 榜单"
echo "  - 支持平台筛选：panda/熊猫/🐼 或 deliveroo/roo/袋鼠/🦘"
