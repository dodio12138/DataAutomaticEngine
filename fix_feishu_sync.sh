#!/bin/bash
# 飞书同步快速修复脚本
# 自动修复常见的同步问题

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  🔧 飞书同步快速修复工具${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 检查是否在项目根目录
if [ ! -f "docker-compose.yaml" ]; then
    echo -e "${RED}❌ 请在项目根目录运行此脚本${NC}"
    exit 1
fi

echo -e "${YELLOW}开始自动修复...${NC}\n"

# 1. 重新构建飞书同步镜像
echo -e "${BLUE}1️⃣  重新构建飞书同步镜像...${NC}"
docker compose build feishu-sync
echo -e "${GREEN}✅ 镜像构建完成${NC}\n"

# 2. 重启 API 服务（重新加载环境变量）
echo -e "${BLUE}2️⃣  重启 API 服务...${NC}"
docker compose restart api
sleep 3
echo -e "${GREEN}✅ API 服务已重启${NC}\n"

# 3. 检查 API 健康状态
echo -e "${BLUE}3️⃣  检查 API 健康状态...${NC}"
MAX_RETRIES=10
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API 服务正常${NC}\n"
        break
    else
        ((RETRY++))
        echo -e "${YELLOW}等待 API 服务启动... ($RETRY/$MAX_RETRIES)${NC}"
        sleep 2
    fi
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ API 服务启动失败${NC}"
    echo -e "${YELLOW}查看日志: docker logs delivery_api${NC}"
    exit 1
fi

# 4. 清理旧的临时容器
echo -e "${BLUE}4️⃣  清理旧的临时容器...${NC}"
OLD_CONTAINERS=$(docker ps -a --filter "name=feishu_sync_" --format "{{.Names}}" | wc -l)
if [ $OLD_CONTAINERS -gt 0 ]; then
    docker ps -a --filter "name=feishu_sync_" --format "{{.Names}}" | xargs docker rm -f 2>/dev/null || true
    echo -e "${GREEN}✅ 清理了 $OLD_CONTAINERS 个旧容器${NC}\n"
else
    echo -e "${GREEN}✅ 没有需要清理的容器${NC}\n"
fi

# 5. 测试飞书 API 连接
echo -e "${BLUE}5️⃣  测试飞书 API 连接...${NC}"
if [ -f .env ]; then
    source .env
    
    if [ -n "$FEISHU_APP_ID" ] && [ -n "$FEISHU_APP_SECRET" ]; then
        TOKEN_RESPONSE=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
            -H "Content-Type: application/json" \
            -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}")
        
        TOKEN_CODE=$(echo "$TOKEN_RESPONSE" | grep -o '"code":[0-9]*' | cut -d':' -f2)
        if [ "$TOKEN_CODE" == "0" ]; then
            echo -e "${GREEN}✅ 飞书 API 连接正常${NC}\n"
        else
            echo -e "${RED}❌ 飞书 API 连接失败${NC}"
            echo "$TOKEN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TOKEN_RESPONSE"
            echo ""
            
            echo -e "${YELLOW}建议：${NC}"
            echo -e "1. 检查 .env 中的 FEISHU_APP_ID 和 FEISHU_APP_SECRET"
            echo -e "2. 确认飞书应用是否启用"
            echo -e "3. 检查网络连接"
            echo ""
        fi
    fi
    
    # 检查 User Access Token
    if [ -n "$FEISHU_USER_ACCESS_TOKEN" ]; then
        USER_TOKEN_RESPONSE=$(curl -s -X GET "https://open.feishu.cn/open-apis/bitable/v1/apps/$FEISHU_BITABLE_APP_TOKEN/tables/$FEISHU_BITABLE_TABLE_ID/fields" \
            -H "Authorization: Bearer $FEISHU_USER_ACCESS_TOKEN")
        
        USER_TOKEN_CODE=$(echo "$USER_TOKEN_RESPONSE" | grep -o '"code":[0-9]*' | cut -d':' -f2)
        if [ "$USER_TOKEN_CODE" == "0" ]; then
            echo -e "${GREEN}✅ User Access Token 有效${NC}\n"
        else
            echo -e "${RED}❌ User Access Token 无效或过期${NC}\n"
            
            echo -e "${YELLOW}自动修复：删除过期的 User Access Token...${NC}"
            # 备份 .env
            cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
            # 注释掉 FEISHU_USER_ACCESS_TOKEN
            sed -i.bak 's/^FEISHU_USER_ACCESS_TOKEN=/#FEISHU_USER_ACCESS_TOKEN=/' .env
            echo -e "${GREEN}✅ 已注释掉过期的 token，将使用应用身份${NC}"
            echo -e "${BLUE}原配置已备份到 .env.backup.* ${NC}\n"
            
            # 重启 API 服务
            echo -e "${BLUE}重启 API 服务以加载新配置...${NC}"
            docker compose restart api
            sleep 3
            echo -e "${GREEN}✅ 配置已更新${NC}\n"
        fi
    fi
fi

# 6. 测试同步功能
echo -e "${BLUE}6️⃣  测试同步功能...${NC}"
echo -e "${YELLOW}运行测试同步（使用昨天的日期）...${NC}"

YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)

TEST_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "http://localhost:8000/run/feishu-sync" \
    -H "Content-Type: application/json" \
    -d "{\"start_date\":\"$YESTERDAY\",\"end_date\":\"$YESTERDAY\"}")

HTTP_BODY=$(echo "$TEST_RESPONSE" | sed -e 's/HTTP_STATUS\:.*//g')
HTTP_STATUS=$(echo "$TEST_RESPONSE" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

if [ "$HTTP_STATUS" == "200" ]; then
    STATUS=$(echo "$HTTP_BODY" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$STATUS" == "success" ]; then
        echo -e "${GREEN}✅ 测试同步成功！${NC}\n"
    else
        EXIT_CODE=$(echo "$HTTP_BODY" | grep -o '"exit_code":[0-9]*' | cut -d':' -f2)
        echo -e "${YELLOW}⚠️  同步执行完成但有警告（退出码: $EXIT_CODE）${NC}"
        echo -e "${BLUE}可能原因：数据库中没有昨天的数据${NC}\n"
    fi
else
    echo -e "${RED}❌ 测试同步失败 (HTTP $HTTP_STATUS)${NC}"
    echo "$HTTP_BODY" | python3 -m json.tool 2>/dev/null || echo "$HTTP_BODY"
    echo ""
fi

# 7. 总结
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  修复总结${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${GREEN}已完成以下操作：${NC}"
echo -e "✅ 重新构建飞书同步镜像"
echo -e "✅ 重启 API 服务"
echo -e "✅ 清理旧的临时容器"
echo -e "✅ 测试飞书 API 连接"
echo -e "✅ 测试同步功能"
echo ""

echo -e "${YELLOW}后续步骤：${NC}"
echo -e "1. 如果仍然失败，运行诊断脚本: ${GREEN}./diagnose_feishu_sync.sh${NC}"
echo -e "2. 查看详细故障排查文档: ${GREEN}FEISHU_SYNC_TROUBLESHOOTING.md${NC}"
echo -e "3. 查看最近的日志: ${GREEN}tail -50 api/logs/feishu_sync_*.log${NC}"
echo ""

echo -e "${GREEN}修复完成！${NC}"
