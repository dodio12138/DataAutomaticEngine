#!/bin/bash
# 服务器部署前检查清单
# 确保服务器环境配置正确

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  📋 服务器部署检查清单${NC}"
echo -e "${BLUE}========================================${NC}\n"

PASSED=0
FAILED=0
WARNINGS=0

check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

# 1. 检查 Docker 和 Docker Compose
echo -e "${YELLOW}1️⃣  检查 Docker 环境...${NC}"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    check_pass "Docker 已安装: $DOCKER_VERSION"
else
    check_fail "Docker 未安装"
fi

if command -v docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version)
    check_pass "Docker Compose 已安装: $COMPOSE_VERSION"
else
    check_fail "Docker Compose 未安装"
fi
echo ""

# 2. 检查 .env 文件
echo -e "${YELLOW}2️⃣  检查 .env 文件...${NC}"
if [ -f .env ]; then
    check_pass ".env 文件存在"
    
    # 检查必需的环境变量
    required_vars=(
        "DB_HOST"
        "DB_PORT"
        "DB_NAME"
        "DB_USER"
        "DB_PASSWORD"
        "FEISHU_APP_ID"
        "FEISHU_APP_SECRET"
        "FEISHU_BITABLE_APP_TOKEN"
        "FEISHU_BITABLE_TABLE_ID"
    )
    
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env; then
            value=$(grep "^${var}=" .env | cut -d'=' -f2)
            if [ -n "$value" ]; then
                check_pass "$var 已配置"
            else
                check_fail "$var 已定义但为空"
            fi
        else
            check_fail "$var 未配置"
        fi
    done
    
    # 检查可选变量
    if grep -q "^FEISHU_USER_ACCESS_TOKEN=" .env; then
        value=$(grep "^FEISHU_USER_ACCESS_TOKEN=" .env | cut -d'=' -f2)
        if [ -n "$value" ]; then
            check_warn "FEISHU_USER_ACCESS_TOKEN 已配置（24小时有效期）"
        fi
    fi
else
    check_fail ".env 文件不存在"
fi
echo ""

# 3. 检查网络连通性
echo -e "${YELLOW}3️⃣  检查网络连通性...${NC}"
if curl -I -s -m 5 https://open.feishu.cn > /dev/null 2>&1; then
    check_pass "可以访问飞书 API (https://open.feishu.cn)"
else
    check_fail "无法访问飞书 API，检查防火墙或代理设置"
fi

if curl -I -s -m 5 https://www.google.com > /dev/null 2>&1; then
    check_pass "外网连接正常"
else
    check_warn "外网连接受限，可能影响某些功能"
fi
echo ""

# 4. 检查端口占用
echo -e "${YELLOW}4️⃣  检查端口占用...${NC}"
if lsof -i :8000 > /dev/null 2>&1; then
    check_warn "端口 8000 已被占用"
else
    check_pass "端口 8000 可用"
fi

if lsof -i :5432 > /dev/null 2>&1; then
    check_warn "端口 5432 已被占用（可能是已运行的数据库）"
else
    check_pass "端口 5432 可用"
fi
echo ""

# 5. 检查磁盘空间
echo -e "${YELLOW}5️⃣  检查磁盘空间...${NC}"
DISK_AVAILABLE=$(df -h . | awk 'NR==2 {print $4}')
echo -e "${BLUE}可用磁盘空间: $DISK_AVAILABLE${NC}"
check_pass "磁盘空间检查完成"
echo ""

# 6. 检查 Docker 镜像
echo -e "${YELLOW}6️⃣  检查 Docker 镜像...${NC}"
required_images=(
    "dataautomaticengine-api"
    "dataautomaticengine-crawler"
    "dataautomaticengine-etl"
    "dataautomaticengine-feishu-sync"
    "dataautomaticengine-scheduler"
    "postgres:15"
)

for image in "${required_images[@]}"; do
    if docker images | grep -q "$image"; then
        check_pass "$image 镜像存在"
    else
        check_warn "$image 镜像不存在（首次运行时会自动构建）"
    fi
done
echo ""

# 7. 检查 Docker 容器状态
echo -e "${YELLOW}7️⃣  检查 Docker 容器状态...${NC}"
if docker ps > /dev/null 2>&1; then
    if docker ps | grep -q "delivery_api"; then
        check_pass "API 容器运行中"
    else
        check_warn "API 容器未运行"
    fi
    
    if docker ps | grep -q "delivery_db"; then
        check_pass "数据库容器运行中"
    else
        check_warn "数据库容器未运行"
    fi
else
    check_fail "无法连接到 Docker daemon"
fi
echo ""

# 8. 测试飞书 API 连接
echo -e "${YELLOW}8️⃣  测试飞书 API 连接...${NC}"
if [ -f .env ]; then
    source .env
    
    if [ -n "$FEISHU_APP_ID" ] && [ -n "$FEISHU_APP_SECRET" ]; then
        TOKEN_RESPONSE=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
            -H "Content-Type: application/json" \
            -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}")
        
        TOKEN_CODE=$(echo "$TOKEN_RESPONSE" | grep -o '"code":[0-9]*' | cut -d':' -f2)
        if [ "$TOKEN_CODE" == "0" ]; then
            check_pass "飞书 tenant_access_token 获取成功"
        else
            check_fail "飞书 tenant_access_token 获取失败"
            echo "$TOKEN_RESPONSE"
        fi
    else
        check_warn "未配置飞书 App ID 和 Secret"
    fi
    
    if [ -n "$FEISHU_USER_ACCESS_TOKEN" ]; then
        USER_TOKEN_RESPONSE=$(curl -s -X GET "https://open.feishu.cn/open-apis/bitable/v1/apps/$FEISHU_BITABLE_APP_TOKEN/tables/$FEISHU_BITABLE_TABLE_ID/fields" \
            -H "Authorization: Bearer $FEISHU_USER_ACCESS_TOKEN")
        
        USER_TOKEN_CODE=$(echo "$USER_TOKEN_RESPONSE" | grep -o '"code":[0-9]*' | cut -d':' -f2)
        if [ "$USER_TOKEN_CODE" == "0" ]; then
            check_pass "飞书 user_access_token 有效"
        else
            check_fail "飞书 user_access_token 无效或过期"
        fi
    fi
else
    check_warn "未找到 .env 文件，跳过飞书 API 测试"
fi
echo ""

# 9. 检查文件权限
echo -e "${YELLOW}9️⃣  检查文件权限...${NC}"
scripts=(
    "build_and_start.sh"
    "manual_crawl.sh"
    "manual_panda_summary.sh"
    "manual_deliveroo_summary.sh"
    "sync_feishu_bitable.sh"
    "diagnose_feishu_sync.sh"
)

for script in "${scripts[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            check_pass "$script 有执行权限"
        else
            check_warn "$script 没有执行权限（运行: chmod +x $script）"
        fi
    else
        check_warn "$script 不存在"
    fi
done
echo ""

# 10. 总结
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  检查总结${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ 通过: $PASSED${NC}"
echo -e "${YELLOW}⚠️  警告: $WARNINGS${NC}"
echo -e "${RED}❌ 失败: $FAILED${NC}"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}有 $FAILED 项检查失败，请先解决这些问题再部署${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}有 $WARNINGS 项警告，建议检查后再部署${NC}"
    exit 0
else
    echo -e "${GREEN}所有检查通过，可以开始部署！${NC}"
    echo ""
    echo -e "${BLUE}建议的部署步骤：${NC}"
    echo -e "1. 构建并启动服务:  ${GREEN}./build_and_start.sh${NC}"
    echo -e "2. 检查服务状态:    ${GREEN}docker ps${NC}"
    echo -e "3. 查看日志:        ${GREEN}docker logs delivery_api${NC}"
    echo -e "4. 运行爬虫:        ${GREEN}./manual_crawl.sh 2026-01-03${NC}"
    echo -e "5. 计算汇总:        ${GREEN}./manual_panda_summary.sh 2026-01-03${NC}"
    echo -e "6. 同步到飞书:      ${GREEN}./sync_feishu_bitable.sh 2026-01-03${NC}"
    exit 0
fi
