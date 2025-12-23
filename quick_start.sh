#!/bin/bash
# 快速启动脚本 - 仅启动已构建的容器

echo "🚀 快速启动所有服务..."
docker compose up -d

echo ""
echo "⏳ 等待服务就绪..."
sleep 5

echo ""
echo "✅ 服务状态："
docker compose ps

echo ""
echo "📝 实时日志："
echo "   docker logs -f delivery_api"
echo ""
