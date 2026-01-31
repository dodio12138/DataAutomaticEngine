#!/bin/bash

# 容器重构脚本
# 用法: ./rebuild.sh [选项] [服务名...]

show_help() {
    cat << 'EOF'
容器重构脚本 (rebuild.sh)

功能说明：
  重构 Docker 镜像和容器，但保留数据库数据卷。
  适用于代码更新后需要重新构建服务的场景。

用法：
  ./rebuild.sh [选项] [服务名...]

选项：
  --help, -h         显示此帮助信息
  --clean-images     删除旧镜像（释放磁盘空间）
  --clear-cache      清除 Docker 构建缓存（prune build cache）

参数：
  服务名             要重构的服务名称（多个用空格分隔）
                     可用服务：api, crawler, etl, feishu-sync, scheduler, db, sql_ui, superset
                     省略则重构所有主要服务（db, api, scheduler, sql_ui, superset）

注意：
  - crawler、etl 和 feishu-sync 镜像会自动重构（无论是否指定）
  - 默认使用 --no-cache 确保完全重新构建

示例：
  ./rebuild.sh                      # 重构所有主要服务（保留数据库数据）
  ./rebuild.sh api                  # 仅重构 api 服务（crawler、etl、feishu-sync 也会重构）
  ./rebuild.sh --clean-images       # 重构所有服务并删除旧镜像
  ./rebuild.sh --clear-cache        # 重构并清除 Docker 构建缓存
  ./rebuild.sh --clean-images --clear-cache  # 清理镜像和缓存
  ./rebuild.sh --clean-images api   # 重构 api 并删除旧镜像
  ./rebuild.sh api scheduler        # 重构 api 和 scheduler 服务

执行流程：
  1. 停止指定服务的容器
  2. 删除指定服务的容器
  3. [可选] 删除旧镜像（--clean-images）
  4. 使用 docker compose build --no-cache 重新构建
  5. 启动服务并等待数据库健康检查

注意事项：
  - 数据库数据会保留在 Docker 卷中，不会丢失
  - 使用 --no-cache 确保完全重新构建
  - 重构 db 服务时会等待数据库就绪
  - 执行前会显示确认提示

依赖：
  - Docker
  - docker compose

相关工具：
  - docker-compose.yaml - 服务定义文件
  - manual_crawl.sh - 手动触发爬虫
  - db_*.sh - 数据库查询工具

EOF
    exit 0
}

# 检查帮助选项
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 可用服务列表
AVAILABLE_SERVICES=("api" "crawler" "etl" "feishu-sync" "scheduler" "db" "sql_ui" "superset")
ALL_SERVICES=("db" "api" "scheduler" "sql_ui" "superset")  # 默认重构的服务（需构建的）

# 解析参数
CLEAN_IMAGES=false
CLEAR_CACHE=false
SERVICES_TO_REBUILD=()

for arg in "$@"; do
    if [ "$arg" = "--clean-images" ]; then
        CLEAN_IMAGES=true
    elif [ "$arg" = "--clear-cache" ]; then
        CLEAR_CACHE=true
    else
        SERVICES_TO_REBUILD+=("$arg")
    fi
done

# 如果没有指定服务，使用默认列表
if [ ${#SERVICES_TO_REBUILD[@]} -eq 0 ]; then
    SERVICES_TO_REBUILD=("${ALL_SERVICES[@]}")
    echo -e "${CYAN}📦 重构模式: 全部服务${NC}"
else
    echo -e "${CYAN}📦 重构模式: 指定服务 [${SERVICES_TO_REBUILD[*]}]${NC}"
fi

if [ "$CLEAN_IMAGES" = true ]; then
    echo -e "${YELLOW}🗑️  镜像清理: 启用（将删除旧镜像）${NC}"
else
    echo -e "${CYAN}💾 镜像清理: 禁用（保留旧镜像）${NC}"
fi

if [ "$CLEAR_CACHE" = true ]; then
    echo -e "${YELLOW}🧹 构建缓存: 清除（prune build cache）${NC}"
else
    echo -e "${CYAN}📦 构建缓存: 保留${NC}"
fi

echo -e "${GREEN}🔄 Crawler、ETL、Feishu-Sync 镜像: 总是重构${NC}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  容器重构脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 验证服务名是否有效
for service in "${SERVICES_TO_REBUILD[@]}"; do
    valid=false
    for available in "${AVAILABLE_SERVICES[@]}"; do
        if [ "$service" = "$available" ]; then
            valid=true
            break
        fi
    done
    
    if [ "$valid" = false ]; then
        echo -e "${RED}❌ 无效的服务名: $service${NC}"
        echo -e "${YELLOW}可用服务: ${AVAILABLE_SERVICES[*]}${NC}"
        echo -e "${YELLOW}可用选项: --clean-images${NC}"
        exit 1
    fi
done

echo -e "${YELLOW}准备重构的服务:${NC}"
for service in "${SERVICES_TO_REBUILD[@]}"; do
    echo -e "  - ${service}"
done
echo ""

# 确认操作
read -p "$(echo -e ${YELLOW}是否继续？[y/N]: ${NC})" confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ 操作已取消${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}步骤 1/4: 停止容器${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 停止指定服务
for service in "${SERVICES_TO_REBUILD[@]}"; do
    echo -e "${YELLOW}🛑 停止服务: ${service}${NC}"
    docker compose stop "$service"
done

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}步骤 2/5: 移除容器（保留数据卷）${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

for service in "${SERVICES_TO_REBUILD[@]}"; do
    echo -e "${YELLOW}🗑️  移除容器: ${service}${NC}"
    docker compose rm -f "$service"
done

# 如果启用了镜像清理
if [ "$CLEAN_IMAGES" = true ]; then
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}步骤 3/5: 删除旧镜像${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # 始终清理 crawler、etl 和 feishu-sync 镜像
    for img in "crawler" "etl" "feishu-sync"; do
        image_name="dataautomaticengine-${img}"
        echo -e "${YELLOW}🗑️  删除镜像: ${image_name}${NC}"
        if docker images -q "${image_name}" 2>/dev/null | grep -q .; then
            docker rmi -f "${image_name}" 2>/dev/null || echo -e "${YELLOW}⚠️  镜像 ${image_name} 可能正在被使用，跳过删除${NC}"
        else
            echo -e "${CYAN}ℹ️  镜像 ${image_name} 不存在，无需删除${NC}"
        fi
    done
    
    for service in "${SERVICES_TO_REBUILD[@]}"; do
        if [ "$service" = "db" ] || [ "$service" = "superset" ]; then
            echo -e "${YELLOW}⏭️  跳过 db 镜像（使用官方镜像）${NC}"
            continue
        fi
        
        # 跳过已处理的独立镜像
        if [ "$service" = "crawler" ] || [ "$service" = "etl" ] || [ "$service" = "feishu-sync" ]; then
            continue
        fi
        
        image_name="dataautomaticengine-${service}"
        echo -e "${YELLOW}🗑️  删除镜像: ${image_name}${NC}"
        
        # 尝试删除镜像（如果存在）
        if docker images -q "$image_name" 2>/dev/null | grep -q .; then
            docker rmi -f "$image_name" 2>/dev/null || echo -e "${YELLOW}⚠️  镜像 ${image_name} 可能正在被使用，跳过删除${NC}"
        else
            echo -e "${CYAN}ℹ️  镜像 ${image_name} 不存在，无需删除${NC}"
        fi
    done
    
    STEP_BUILD="4/5"
    STEP_START="5/5"
else
    STEP_BUILD="3/4"
    STEP_START="4/4"
fi

# 如果启用了缓存清除
if [ "$CLEAR_CACHE" = true ]; then
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}步骤额外: 清除 Docker 构建缓存${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo -e "${YELLOW}🧹 清除构建缓存...${NC}"
    docker builder prune -af
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 构建缓存已清除${NC}"
    else
        echo -e "${YELLOW}⚠️  清除构建缓存失败，继续执行${NC}"
    fi
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}步骤 ${STEP_BUILD}: 重新构建镜像${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 需要构建的服务（不包括 db/superset，因为使用官方镜像）
BUILD_SERVICES=()
for service in "${SERVICES_TO_REBUILD[@]}"; do
    if [ "$service" != "db" ] && [ "$service" != "superset" ]; then
        BUILD_SERVICES+=("$service")
    fi
done

# 始终构建 crawler、etl 和 feishu-sync 镜像（即使不在服务列表中）
echo -e "${YELLOW}🔨 构建 crawler 镜像（独立镜像）${NC}"
docker build --no-cache -t dataautomaticengine-crawler ./crawler

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ crawler 镜像构建失败${NC}"
    exit 1
fi
echo -e "${GREEN}✅ crawler 镜像构建完成${NC}"

echo -e "${YELLOW}🔨 构建 etl 镜像（独立镜像）${NC}"
docker build --no-cache -t dataautomaticengine-etl ./etl

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ etl 镜像构建失败${NC}"
    exit 1
fi
echo -e "${GREEN}✅ etl 镜像构建完成${NC}"

echo -e "${YELLOW}🔨 构建 feishu-sync 镜像（独立镜像）${NC}"
docker build --no-cache -t dataautomaticengine-feishu-sync ./feishu_sync

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ feishu-sync 镜像构建失败${NC}"
    exit 1
fi
echo -e "${GREEN}✅ feishu-sync 镜像构建完成${NC}"

if [ ${#BUILD_SERVICES[@]} -gt 0 ]; then
    echo -e "${YELLOW}🔨 构建服务镜像: ${BUILD_SERVICES[*]}${NC}"
    docker compose build --no-cache "${BUILD_SERVICES[@]}"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 镜像构建失败${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ 服务镜像构建完成${NC}"
else
    echo -e "${YELLOW}ℹ️  无需构建服务镜像（仅重启 db 服务）${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}步骤 ${STEP_START}: 启动容器${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 如果重构 db，需要等待数据库健康检查
db_included=false
for service in "${SERVICES_TO_REBUILD[@]}"; do
    if [ "$service" = "db" ]; then
        db_included=true
        break
    fi
done

if [ "$db_included" = true ]; then
    echo -e "${YELLOW}🚀 启动数据库服务（优先）${NC}"
    docker compose up -d db
    
    echo -e "${YELLOW}⏳ 等待数据库健康检查...${NC}"
    timeout=60
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker compose ps db | grep -q "healthy"; then
            echo -e "${GREEN}✅ 数据库已就绪${NC}"
            break
        fi
        echo -n "."
        sleep 2
        elapsed=$((elapsed + 2))
    done
    echo ""
    
    if [ $elapsed -ge $timeout ]; then
        echo -e "${RED}⚠️  数据库健康检查超时，但继续启动其他服务${NC}"
    fi
fi

# 启动其他服务
other_services=()
for service in "${SERVICES_TO_REBUILD[@]}"; do
    if [ "$service" != "db" ]; then
        other_services+=("$service")
    fi
done

if [ ${#other_services[@]} -gt 0 ]; then
    echo -e "${YELLOW}🚀 启动服务: ${other_services[*]}${NC}"
    docker compose up -d "${other_services[@]}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}验证: 服务状态${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

sleep 3
echo ""
docker compose ps

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ 重构完成${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${CYAN}📊 数据库数据已保留${NC}"
echo -e "${CYAN}🔍 查看服务日志:${NC}"
echo ""
for service in "${SERVICES_TO_REBUILD[@]}"; do
    container_name=""
    case "$service" in
        "api") container_name="delivery_api" ;;
        "db") container_name="delivery_postgres" ;;
        "scheduler") container_name="delivery_scheduler" ;;
        "crawler") echo -e "  ${YELLOW}docker logs <crawler_container_id>${NC} ${CYAN}# 临时容器${NC}" ;;
        "etl") echo -e "  ${YELLOW}docker logs <etl_container_id>${NC} ${CYAN}# 临时容器${NC}" ;;
    esac
    
    if [ -n "$container_name" ]; then
        echo -e "  ${YELLOW}docker logs -f ${container_name}${NC}"
    fi
done

echo ""
echo -e "${CYAN}🧪 测试 API:${NC}"
echo -e "  ${YELLOW}curl http://localhost:8000/health${NC}"
echo ""
echo -e "${CYAN}📈 查看数据库:${NC}"
echo -e "  ${YELLOW}./db_stats.sh${NC}"
echo ""
