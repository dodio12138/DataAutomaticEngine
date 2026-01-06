#!/bin/bash
# 诊断服务器上的每小时销售飞书同步问题

echo "🔍 诊断每小时销售飞书同步问题"
echo "======================================"
echo ""

# 1. 检查环境变量
echo "1️⃣ 检查环境变量..."
echo "------------------------------------"
FEISHU_HOURLY_APP=$(docker exec delivery_api printenv FEISHU_HOURLY_SALES_APP_TOKEN 2>/dev/null)
FEISHU_HOURLY_TABLE=$(docker exec delivery_api printenv FEISHU_HOURLY_SALES_TABLE_ID 2>/dev/null)
FEISHU_APP_ID=$(docker exec delivery_api printenv FEISHU_APP_ID 2>/dev/null)
FEISHU_APP_SECRET=$(docker exec delivery_api printenv FEISHU_APP_SECRET 2>/dev/null)

if [ -z "$FEISHU_HOURLY_APP" ]; then
    echo "❌ 缺少环境变量: FEISHU_HOURLY_SALES_APP_TOKEN"
    MISSING_ENV=true
else
    echo "✅ FEISHU_HOURLY_SALES_APP_TOKEN: ${FEISHU_HOURLY_APP:0:20}..."
fi

if [ -z "$FEISHU_HOURLY_TABLE" ]; then
    echo "❌ 缺少环境变量: FEISHU_HOURLY_SALES_TABLE_ID"
    MISSING_ENV=true
else
    echo "✅ FEISHU_HOURLY_SALES_TABLE_ID: $FEISHU_HOURLY_TABLE"
fi

if [ -z "$FEISHU_APP_ID" ]; then
    echo "❌ 缺少环境变量: FEISHU_APP_ID"
    MISSING_ENV=true
else
    echo "✅ FEISHU_APP_ID: ${FEISHU_APP_ID:0:15}..."
fi

if [ -z "$FEISHU_APP_SECRET" ]; then
    echo "❌ 缺少环境变量: FEISHU_APP_SECRET"
    MISSING_ENV=true
else
    echo "✅ FEISHU_APP_SECRET: ${FEISHU_APP_SECRET:0:15}..."
fi

echo ""

# 2. 检查 Docker 镜像
echo "2️⃣ 检查 Docker 镜像..."
echo "------------------------------------"
IMAGE_EXISTS=$(docker images | grep "dataautomaticengine-feishu-sync")
if [ -z "$IMAGE_EXISTS" ]; then
    echo "❌ 镜像不存在: dataautomaticengine-feishu-sync"
    echo "   需要构建: docker build -t dataautomaticengine-feishu-sync ./feishu_sync"
else
    echo "✅ 镜像存在"
    docker images | grep "dataautomaticengine-feishu-sync"
fi

echo ""

# 3. 检查 hourly_sales.py 文件
echo "3️⃣ 检查 feishu_sync/hourly_sales.py..."
echo "------------------------------------"
if [ -f "feishu_sync/hourly_sales.py" ]; then
    echo "✅ 文件存在"
    echo "   文件大小: $(wc -c < feishu_sync/hourly_sales.py) bytes"
    echo "   最后修改: $(stat -f "%Sm" feishu_sync/hourly_sales.py 2>/dev/null || stat -c "%y" feishu_sync/hourly_sales.py 2>/dev/null)"
else
    echo "❌ 文件不存在: feishu_sync/hourly_sales.py"
fi

echo ""

# 4. 检查数据库中的 hourly_sales 表
echo "4️⃣ 检查数据库表..."
echo "------------------------------------"
TABLE_EXISTS=$(docker exec delivery_postgres psql -U delivery_user -d delivery_data -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'hourly_sales');" 2>/dev/null | tr -d ' ')
if [ "$TABLE_EXISTS" = "t" ]; then
    RECORD_COUNT=$(docker exec delivery_postgres psql -U delivery_user -d delivery_data -t -c "SELECT COUNT(*) FROM hourly_sales;" 2>/dev/null | tr -d ' ')
    echo "✅ hourly_sales 表存在"
    echo "   记录数: $RECORD_COUNT"
else
    echo "❌ hourly_sales 表不存在"
    echo "   需要创建: ./setup_hourly_sales_table.sh"
fi

echo ""

# 5. 测试飞书 Token 获取
echo "5️⃣ 测试飞书 Token 获取..."
echo "------------------------------------"
if [ -n "$FEISHU_APP_ID" ] && [ -n "$FEISHU_APP_SECRET" ]; then
    TOKEN_RESPONSE=$(docker exec delivery_api python3 -c "
import requests
import os
import json

app_id = os.environ.get('FEISHU_APP_ID')
app_secret = os.environ.get('FEISHU_APP_SECRET')

response = requests.post(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    json={'app_id': app_id, 'app_secret': app_secret}
)

result = response.json()
if result.get('code') == 0:
    print('✅ Token 获取成功')
    print(f\"   有效期: {result.get('expire', 0)} 秒\")
else:
    print('❌ Token 获取失败')
    print(f\"   错误: {result.get('msg', '未知错误')}\")
" 2>&1)
    echo "$TOKEN_RESPONSE"
else
    echo "⚠️  跳过（缺少 APP_ID 或 APP_SECRET）"
fi

echo ""

# 6. 查看最新日志
echo "6️⃣ 最新同步日志..."
echo "------------------------------------"
LATEST_LOG=$(ls -t api/logs/hourly_sales_sync_*.log 2>/dev/null | head -1)
if [ -n "$LATEST_LOG" ]; then
    echo "📄 日志文件: $LATEST_LOG"
    echo ""
    tail -20 "$LATEST_LOG"
else
    echo "⚠️  没有找到同步日志"
fi

echo ""
echo "======================================"

# 总结和建议
echo ""
echo "📋 总结与建议:"
echo "------------------------------------"

if [ "$MISSING_ENV" = true ]; then
    echo "❌ 需要在服务器 .env 文件中添加以下配置:"
    echo ""
    echo "   FEISHU_HOURLY_SALES_APP_TOKEN=Bd6rbEhmSa9CwBsLTjxc0PRPngg"
    echo "   FEISHU_HOURLY_SALES_TABLE_ID=tblXCo32CmpTcOGt"
    echo ""
    echo "   然后重启服务: docker compose restart api"
    echo ""
fi

if [ -z "$IMAGE_EXISTS" ]; then
    echo "❌ 需要构建镜像:"
    echo "   docker build -t dataautomaticengine-feishu-sync ./feishu_sync"
    echo ""
fi

if [ "$TABLE_EXISTS" != "t" ]; then
    echo "❌ 需要创建数据库表:"
    echo "   ./setup_hourly_sales_table.sh"
    echo ""
fi

if [ -z "$MISSING_ENV" ] && [ -n "$IMAGE_EXISTS" ] && [ "$TABLE_EXISTS" = "t" ]; then
    echo "✅ 配置看起来正常，可以尝试手动测试:"
    echo "   curl -X POST http://localhost:8000/run/hourly-sales/sync-feishu -d '{\"date\":\"2025-12-31\"}'"
fi
