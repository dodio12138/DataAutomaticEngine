#!/bin/bash

# ============================================================
# 数据自动化引擎 - 完全清理并重新构建脚本
# ⚠️  警告：此脚本会删除所有容器、镜像和数据卷！
# ============================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# 打印标题
print_header() {
    echo ""
    echo "============================================================"
    echo -e "  ${RED}⚠️  完全清理并重新构建${NC}"
    echo "============================================================"
    echo ""
}

# 显示警告信息
show_warning() {
    echo -e "${RED}⚠️  警告：此操作将会：${NC}"
    echo ""
    echo "  1. 停止所有运行中的容器"
    echo "  2. 删除所有容器"
    echo "  3. 删除所有镜像"
    echo -e "  4. ${RED}删除所有数据卷（包括数据库数据！）${NC}"
    echo "  5. 清理所有网络"
    echo "  6. 重新构建所有镜像"
    echo "  7. 启动所有服务"
    echo ""
    echo -e "${YELLOW}📊 当前数据库订单数量：${NC}"
    
    # 尝试查询订单数量
    if docker ps --filter "name=delivery_postgres" --format "{{.Names}}" | grep -q "delivery_postgres"; then
        order_count=$(docker exec delivery_postgres psql -U delivery_user -d delivery_data -t -c "SELECT COUNT(*) FROM raw_orders;" 2>/dev/null || echo "无法查询")
        echo -e "   ${MAGENTA}订单数：${order_count}${NC}"
    else
        echo "   数据库容器未运行"
    fi
    
    echo ""
}

# 确认操作
confirm_action() {
    echo -e "${RED}================================================${NC}"
    echo -e "${RED}此操作无法撤销！所有数据将永久丢失！${NC}"
    echo -e "${RED}================================================${NC}"
    echo ""
    
    read -p "确认继续？请输入 'YES' (大写) 来确认: " confirmation
    
    if [ "$confirmation" != "YES" ]; then
        echo ""
        echo -e "${GREEN}✅ 已取消操作${NC}"
        exit 0
    fi
    
    echo ""
    echo -e "${YELLOW}最后确认，请再次输入 'DELETE ALL' (大写) 来确认删除所有数据：${NC}"
    read -p "> " final_confirmation
    
    if [ "$final_confirmation" != "DELETE ALL" ]; then
        echo ""
        echo -e "${GREEN}✅ 已取消操作${NC}"
        exit 0
    fi
    
    echo ""
    echo -e "${RED}开始清理...${NC}"
    echo ""
}

# 停止所有容器
stop_containers() {
    echo -e "${BLUE}[1/7]${NC} 停止所有容器..."
    docker-compose down 2>/dev/null || echo "没有运行中的容器"
    echo -e "${GREEN}✅ 容器已停止${NC}"
    echo ""
}

# 删除所有容器
remove_containers() {
    echo -e "${BLUE}[2/7]${NC} 删除所有容器..."
    
    # 获取所有容器 ID
    containers=$(docker ps -a -q 2>/dev/null)
    
    if [ -n "$containers" ]; then
        docker rm -f $containers
        echo -e "${GREEN}✅ 已删除 $(echo $containers | wc -w | tr -d ' ') 个容器${NC}"
    else
        echo "没有需要删除的容器"
    fi
    echo ""
}

# 删除所有镜像
remove_images() {
    echo -e "${BLUE}[3/7]${NC} 删除项目相关镜像..."
    
    # 删除项目镜像
    images_to_remove="dataautomaticengine-api dataautomaticengine-crawler dataautomaticengine-etl dataautomaticengine-scheduler"
    
    for image in $images_to_remove; do
        if docker images -q $image 2>/dev/null | grep -q .; then
            docker rmi -f $image 2>/dev/null && echo "  ✓ 已删除: $image" || echo "  ✗ 删除失败: $image"
        fi
    done
    
    echo -e "${GREEN}✅ 项目镜像已删除${NC}"
    echo ""
}

# 删除所有数据卷
remove_volumes() {
    echo -e "${BLUE}[4/7]${NC} ${RED}删除所有数据卷（包括数据库数据）...${NC}"
    docker-compose down -v 2>/dev/null || true
    
    # 删除项目相关的数据卷
    volumes=$(docker volume ls -q | grep -E "dataautomaticengine|delivery" 2>/dev/null || true)
    
    if [ -n "$volumes" ]; then
        echo "$volumes" | xargs docker volume rm 2>/dev/null || true
        echo -e "${GREEN}✅ 数据卷已删除${NC}"
    else
        echo "没有需要删除的数据卷"
    fi
    echo ""
}

# 清理网络
clean_networks() {
    echo -e "${BLUE}[5/7]${NC} 清理 Docker 网络..."
    docker network prune -f > /dev/null 2>&1
    echo -e "${GREEN}✅ 网络已清理${NC}"
    echo ""
}

# 重新构建所有镜像
rebuild_images() {
    echo -e "${BLUE}[6/7]${NC} 重新构建所有镜像..."
    echo "============================================================"
    
    # 构建 API 镜像
    echo "📦 1/4 构建 API 镜像..."
    docker-compose build --no-cache api
    echo -e "${GREEN}✅ API 镜像构建完成${NC}"
    echo ""
    
    # 构建 Crawler 镜像
    echo "📦 2/4 构建 Crawler 镜像..."
    docker build --no-cache -t dataautomaticengine-crawler ./crawler
    echo -e "${GREEN}✅ Crawler 镜像构建完成${NC}"
    echo ""
    
    # 构建 ETL 镜像
    echo "📦 3/4 构建 ETL 镜像..."
    docker build --no-cache -t dataautomaticengine-etl ./etl
    echo -e "${GREEN}✅ ETL 镜像构建完成${NC}"
    echo ""
    
    # 构建 Scheduler 镜像
    echo "📦 4/4 构建 Scheduler 镜像..."
    docker-compose build --no-cache scheduler
    echo -e "${GREEN}✅ Scheduler 镜像构建完成${NC}"
    
    echo "============================================================"
    echo -e "${GREEN}✅ 所有镜像构建完成！${NC}"
    echo ""
}

# 启动所有容器
start_containers() {
    echo -e "${BLUE}[7/7]${NC} 启动所有服务..."
    docker-compose up -d
    echo -e "${GREEN}✅ 所有服务已启动${NC}"
    echo ""
}

# 等待服务就绪
wait_for_services() {
    echo -e "${BLUE}⏳${NC} 等待服务就绪..."
    echo ""
    
    # 等待数据库
    echo "  ⏳ 等待数据库初始化（最多60秒）..."
    timeout=60
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker exec delivery_postgres pg_isready -U delivery_user -d delivery_data > /dev/null 2>&1; then
            echo -e "  ${GREEN}✅ 数据库已就绪${NC}"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    echo ""
    
    if [ $elapsed -ge $timeout ]; then
        echo -e "  ${YELLOW}⚠️  数据库启动超时，请手动检查${NC}"
    fi
    
    # 等待 API
    echo "  ⏳ 等待 API 服务启动（最多30秒）..."
    timeout=30
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "  ${GREEN}✅ API 服务已就绪${NC}"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    echo ""
    
    if [ $elapsed -ge $timeout ]; then
        echo -e "  ${YELLOW}⚠️  API 服务启动超时，请手动检查${NC}"
    fi
    
    echo ""
}

# 显示服务状态
show_status() {
    echo "============================================================"
    echo -e "${GREEN}📊 服务状态：${NC}"
    echo "============================================================"
    docker-compose ps
    echo ""
}

# 显示完成信息
show_completion() {
    echo "============================================================"
    echo -e "${GREEN}🎉 清理并重新构建完成！${NC}"
    echo "============================================================"
    echo ""
    echo "✅ 所有旧数据已删除"
    echo "✅ 所有镜像已重新构建"
    echo "✅ 所有服务已启动"
    echo ""
    echo "📝 下一步操作："
    echo "  1. 访问 http://localhost:8000/docs 查看 API"
    echo "  2. 在飞书群 @机器人 发送 '帮助' 测试"
    echo "  3. 运行爬虫获取数据：curl -X POST http://localhost:8000/run/crawler"
    echo ""
    echo "📊 查看日志："
    echo "  docker logs -f delivery_api"
    echo ""
}

# 显示数据库初始化提示
show_db_init_info() {
    echo "============================================================"
    echo -e "${BLUE}💡 数据库初始化说明${NC}"
    echo "============================================================"
    echo ""
    echo "数据库已重新创建，表结构来自 db/init.sql"
    echo ""
    echo "当前数据库是空的，需要运行爬虫来获取数据："
    echo ""
    echo "  方式1：通过 API 触发"
    echo "  curl -X POST http://localhost:8000/run/crawler \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"store_code\":\"all\",\"start_date\":\"2025-12-22\"}'"
    echo ""
    echo "  方式2：使用飞书机器人"
    echo "  在群里发送：@机器人 运行爬虫"
    echo ""
}

# 主函数
main() {
    print_header
    show_warning
    confirm_action
    
    echo "开始执行清理..."
    echo ""
    
    stop_containers
    remove_containers
    remove_images
    remove_volumes
    clean_networks
    rebuild_images
    start_containers
    wait_for_services
    show_status
    show_db_init_info
    show_completion
}

# 执行主函数
main
