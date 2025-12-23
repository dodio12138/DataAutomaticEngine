#!/bin/bash

# 快速重启 API 容器（不重新构建）
# 适用于代码修改后的快速测试

echo "⚡ 快速重启 API 容器..."

cd /Users/levy/WorkSpace/Program/HaidilaoService/DataAutomaticEngine

# 重启容器（利用 --reload 模式，代码会自动重载）
docker compose restart api

echo ""
echo "⏳ 等待服务启动..."
sleep 3

# 检查状态
if curl -s http://localhost:8000/feishu/bot/health | grep -q "ok"; then
    echo "✅ API 服务已就绪"
    echo ""
    echo "📖 查看日志："
    echo "   docker logs -f delivery_api"
else
    echo "⚠️  服务未响应，查看日志："
    docker logs delivery_api --tail 20
fi
