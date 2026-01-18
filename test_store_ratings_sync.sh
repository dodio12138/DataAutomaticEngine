#!/bin/bash
# 测试店铺评分飞书同步 API

echo "🧪 测试店铺评分飞书同步 API"
echo "=============================="
echo ""

# 检查 API 服务是否运行
echo "1️⃣ 检查 API 服务..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ API 服务未运行，请先启动: docker compose up -d"
    exit 1
fi
echo "✅ API 服务正常"
echo ""

# 测试默认同步（昨天）
echo "2️⃣ 测试默认同步（昨天的数据）..."
echo "请求: POST /run/store-ratings/sync-feishu"
echo "{}"
echo ""

RESPONSE=$(curl -s -X POST http://localhost:8000/run/store-ratings/sync-feishu \
    -H "Content-Type: application/json" \
    -d '{}')

echo "响应:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# 检查是否成功
if echo "$RESPONSE" | grep -q '"success":true'; then
    echo "✅ 默认同步测试通过"
else
    echo "⚠️ 默认同步测试失败（可能是数据库无数据）"
fi

echo ""
echo "=============================="
echo "✅ 测试完成"
echo ""
echo "💡 提示："
echo "  - 如果同步失败，请先运行评分爬虫："
echo "    ./manual_ratings.sh"
echo ""
echo "  - 查看详细日志："
echo "    ls -lt api/logs/store_ratings_sync_*.log | head -1"
echo ""
echo "  - 手动同步指定日期："
echo "    ./sync_store_ratings.sh 2026-01-15"
