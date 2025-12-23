#!/bin/bash

# 安全的 API 容器重启脚本
# 避免 VSCode 卡死的优化版本

set -e  # 遇到错误立即退出

echo "🔄 开始重启 API 容器..."
echo ""

# 1. 停止容器（不等待，立即返回）
echo "1️⃣ 停止现有容器..."
docker-compose stop api 2>/dev/null || true
docker rm -f delivery_api 2>/dev/null || true

# 2. 清理缓存文件（避免触发过多文件监控事件）
echo "2️⃣ 清理 Python 缓存..."
find /Users/levy/WorkSpace/Program/HaidilaoService/DataAutomaticEngine/api -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find /Users/levy/WorkSpace/Program/HaidilaoService/DataAutomaticEngine/api -type f -name "*.pyc" -delete 2>/dev/null || true

# 3. 后台构建（不阻塞终端）
echo "3️⃣ 构建镜像（后台运行）..."
cd /Users/levy/WorkSpace/Program/HaidilaoService/DataAutomaticEngine
docker-compose build api --quiet &
BUILD_PID=$!

# 4. 显示进度
echo -n "   构建中"
while kill -0 $BUILD_PID 2>/dev/null; do
    echo -n "."
    sleep 1
done
wait $BUILD_PID
echo " ✅"

# 5. 启动容器
echo "4️⃣ 启动容器..."
docker-compose up -d api

# 6. 等待服务就绪
echo "5️⃣ 等待服务启动..."
sleep 3

# 7. 检查健康状态
echo "6️⃣ 检查服务状态..."
if docker ps | grep -q delivery_api; then
    echo "   ✅ 容器运行正常"
    
    # 测试健康检查
    echo ""
    echo "7️⃣ 测试服务健康..."
    health_status=$(curl -s http://localhost:8000/feishu/bot/health 2>/dev/null || echo "FAILED")
    
    if echo "$health_status" | grep -q "ok"; then
        echo "   ✅ API 服务健康"
    else
        echo "   ⚠️  API 服务未响应，查看日志："
        docker logs delivery_api --tail 10
    fi
else
    echo "   ❌ 容器启动失败"
    echo ""
    echo "📋 错误日志："
    docker logs delivery_api --tail 20
    exit 1
fi

echo ""
echo "======================================"
echo "✅ API 容器重启完成！"
echo ""
echo "📊 容器状态："
docker ps --filter "name=delivery_api" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "📖 查看日志："
echo "   docker logs -f delivery_api"
echo ""
echo "🧪 测试接口："
echo "   curl http://localhost:8000/feishu/bot/health"
echo "======================================"
