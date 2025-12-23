#!/bin/bash

# ============================================================
# 数据自动化引擎 - 一键构建和启动脚本
# ============================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印标题
print_header() {
    echo ""
    echo "============================================================"
    echo "  🚀 海底捞数据自动化引擎 - 一键构建和启动"
    echo "============================================================"
    echo ""
}

# 检查 Docker 是否运行
check_docker() {
    log_info "检查 Docker 运行状态..."
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker 未运行，请先启动 Docker Desktop"
        exit 1
    fi
    log_success "Docker 运行正常"
}

# 检查环境变量文件
check_env_file() {
    log_info "检查环境变量配置..."
    if [ ! -f .env ]; then
        log_warning ".env 文件不存在，从 .env.example 创建"
        if [ -f .env.example ]; then
            cp .env.example .env
            log_success "已创建 .env 文件，请修改其中的配置"
        else
            log_error ".env 文件不存在，请手动创建"
            exit 1
        fi
    else
        log_success ".env 文件已存在"
    fi
}

# 停止现有容器
stop_containers() {
    log_info "停止现有容器..."
    if docker compose ps -q > /dev/null 2>&1; then
        docker compose down
        log_success "现有容器已停止"
    else
        log_info "没有运行中的容器"
    fi
}

# 构建所有镜像
build_images() {
    echo ""
    log_info "开始构建所有镜像..."
    echo "============================================================"
    
    # 构建 API 镜像
    log_info "1/4 构建 API 镜像..."
    docker compose build api
    log_success "API 镜像构建完成"
    
    # 构建 Crawler 镜像
    log_info "2/4 构建 Crawler 镜像..."
    docker build -t dataautomaticengine-crawler ./crawler
    log_success "Crawler 镜像构建完成"
    
    # 构建 ETL 镜像
    log_info "3/4 构建 ETL 镜像..."
    docker build -t dataautomaticengine-etl ./etl
    log_success "ETL 镜像构建完成"
    
    # 构建 Scheduler 镜像
    log_info "4/4 构建 Scheduler 镜像..."
    docker compose build scheduler
    log_success "Scheduler 镜像构建完成"
    
    echo "============================================================"
    log_success "所有镜像构建完成！"
    echo ""
}

# 启动所有容器
start_containers() {
    log_info "启动所有容器..."
    docker compose up -d
    log_success "所有容器已启动"
}

# 等待服务就绪
wait_for_services() {
    echo ""
    log_info "等待服务就绪..."
    
    # 等待数据库
    log_info "等待数据库启动（最多60秒）..."
    timeout=60
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker exec delivery_postgres pg_isready -U delivery_user -d delivery_data > /dev/null 2>&1; then
            log_success "数据库已就绪"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    
    if [ $elapsed -ge $timeout ]; then
        log_error "数据库启动超时"
        exit 1
    fi
    
    # 等待 API
    log_info "等待 API 服务启动（最多30秒）..."
    timeout=30
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            log_success "API 服务已就绪"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    
    if [ $elapsed -ge $timeout ]; then
        log_warning "API 服务启动超时，请手动检查"
    fi
    
    echo ""
}

# 显示服务状态
show_status() {
    echo ""
    echo "============================================================"
    log_info "服务状态："
    echo "============================================================"
    docker compose ps
    echo ""
}

# 显示日志查看命令
show_logs_info() {
    echo "============================================================"
    log_info "日志查看命令："
    echo "============================================================"
    echo "  查看所有日志:     docker compose logs -f"
    echo "  查看 API 日志:    docker logs -f delivery_api"
    echo "  查看数据库日志:    docker logs -f delivery_postgres"
    echo "  查看调度器日志:    docker logs -f delivery_scheduler"
    echo ""
}

# 显示访问信息
show_access_info() {
    echo "============================================================"
    log_info "访问信息："
    echo "============================================================"
    echo "  API 服务:         http://localhost:8000"
    echo "  API 文档:         http://localhost:8000/docs"
    echo "  健康检查:         http://localhost:8000/health"
    echo "  数据库:           localhost:5432"
    echo "    用户名:         delivery_user"
    echo "    密码:           delivery_pass"
    echo "    数据库:         delivery_data"
    echo ""
}

# 显示飞书机器人信息
show_feishu_info() {
    echo "============================================================"
    log_info "飞书机器人："
    echo "============================================================"
    echo "  长连接状态:       运行中（后台线程）"
    echo "  测试命令:         @机器人 帮助"
    echo "  查看连接状态:     docker logs delivery_api | grep -E '(connected|ping|pong)'"
    echo ""
}

# 显示下一步操作
show_next_steps() {
    echo "============================================================"
    log_success "🎉 部署完成！"
    echo "============================================================"
    echo ""
    echo "下一步操作："
    echo "  1. 访问 http://localhost:8000/docs 查看 API 文档"
    echo "  2. 在飞书群里 @机器人 发送 '帮助' 测试机器人"
    echo "  3. 运行爬虫测试：curl -X POST http://localhost:8000/run/crawler"
    echo ""
    echo "停止服务："
    echo "  docker compose down"
    echo ""
    echo "重启服务："
    echo "  docker compose restart"
    echo ""
}

# 清理函数（可选）
clean_all() {
    log_warning "清理所有容器、镜像和数据..."
    read -p "确认删除所有数据？(y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        docker compose down -v
        docker rmi dataautomaticengine-api dataautomaticengine-crawler dataautomaticengine-etl dataautomaticengine-scheduler 2>/dev/null || true
        log_success "清理完成"
    else
        log_info "已取消清理"
    fi
}

# 主函数
main() {
    print_header
    
    # 解析参数
    if [ "$1" = "clean" ]; then
        clean_all
        exit 0
    fi
    
    if [ "$1" = "rebuild" ]; then
        log_info "强制重建所有镜像..."
        stop_containers
        build_images
        start_containers
        wait_for_services
    elif [ "$1" = "restart" ]; then
        log_info "重启所有服务..."
        docker compose restart
        wait_for_services
    else
        # 默认流程：完整构建和启动
        check_docker
        check_env_file
        stop_containers
        build_images
        start_containers
        wait_for_services
    fi
    
    show_status
    show_logs_info
    show_access_info
    show_feishu_info
    show_next_steps
}

# 执行主函数
main "$@"
