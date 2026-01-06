#!/bin/bash
# 通用环境变量重新载入脚本
# 用法: ./reload_env.sh [服务名称]
#   不带参数: 重启所有依赖 .env 的服务（api, scheduler）
#   带参数: 只重启指定服务，如 ./reload_env.sh api

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔄 重新载入环境变量..."
echo "======================================"
echo ""

# 检查 .env 文件是否存在
if [ ! -f ".env" ]; then
    echo "❌ .env 文件不存在"
    exit 1
fi

echo "1️⃣ 当前 .env 关键配置..."
echo "------------------------------------"
echo -e "${YELLOW}数据库配置:${NC}"
grep "^DB_" .env | sed 's/=.*/=***/' || echo "  未找到数据库配置"

echo ""
echo -e "${YELLOW}飞书配置:${NC}"
grep "^FEISHU_" .env | head -10 | sed 's/=.*/=***/' || echo "  未找到飞书配置"

# 确定要重启的服务
if [ -n "$1" ]; then
    SERVICES="$1"
    echo ""
    echo "2️⃣ 重启指定服务: $SERVICES"
else
    SERVICES="api scheduler"
    echo ""
    echo "2️⃣ 重启所有依赖环境变量的服务..."
fi

echo "------------------------------------"
for service in $SERVICES; do
    echo "🔄 重启 $service 容器..."
    docker compose restart $service
    if [ $? -eq 0 ]; then
        echo "✅ $service 重启成功"
    else
        echo "❌ $service 重启失败"
    fi
done

echo ""
echo "3️⃣ 等待容器启动..."
sleep 5

echo ""
echo "4️⃣ 验证关键环境变量..."
echo "------------------------------------"

# 检查 API 容器环境变量
if docker ps --format '{{.Names}}' | grep -q "delivery_api"; then
    echo -e "${GREEN}API 容器环境变量:${NC}"
    
    # 数据库配置
    echo "  DB_HOST: $(docker exec delivery_api printenv DB_HOST 2>/dev/null || echo '未设置')"
    echo "  DB_NAME: $(docker exec delivery_api printenv DB_NAME 2>/dev/null || echo '未设置')"
    
    # 飞书配置
    FEISHU_BOT=$(docker exec delivery_api printenv FEISHU_BOT_WEBHOOK_URL 2>/dev/null)
    if [ -n "$FEISHU_BOT" ]; then
        echo "  FEISHU_BOT_WEBHOOK_URL: ${FEISHU_BOT:0:40}..."
    fi
    
    FEISHU_APP_ID=$(docker exec delivery_api printenv FEISHU_APP_ID 2>/dev/null)
    if [ -n "$FEISHU_APP_ID" ]; then
        echo "  FEISHU_APP_ID: ${FEISHU_APP_ID:0:15}..."
    fi
    
    # 多维表格配置
    BITABLE_TOKEN=$(docker exec delivery_api printenv FEISHU_BITABLE_APP_TOKEN 2>/dev/null)
    if [ -n "$BITABLE_TOKEN" ]; then
        echo "  FEISHU_BITABLE_APP_TOKEN: ${BITABLE_TOKEN:0:20}..."
    fi
    
    # 每小时销售配置
    HOURLY_TOKEN=$(docker exec delivery_api printenv FEISHU_HOURLY_SALES_APP_TOKEN 2>/dev/null)
    if [ -n "$HOURLY_TOKEN" ]; then
        echo "  FEISHU_HOURLY_SALES_APP_TOKEN: ${HOURLY_TOKEN:0:20}..."
    fi
fi

echo ""
echo "======================================"
echo -e "${GREEN}✅ 环境变量重新载入完成！${NC}"
echo ""
echo "💡 提示:"
echo "   - 查看所有环境变量: docker exec delivery_api env"
echo "   - 只重启 API: ./reload_env.sh api"
echo "   - 只重启 Scheduler: ./reload_env.sh scheduler"
echo "   - 测试 API: curl http://localhost:8000/docs"
