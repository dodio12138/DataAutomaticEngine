#!/bin/bash
# 飞书同步问题诊断脚本
# 用于排查本地运行正常但服务器运行失败的问题

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  🔍 飞书同步问题诊断工具${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 1. 检查 .env 文件
echo -e "${YELLOW}1️⃣  检查 .env 文件配置...${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env 文件不存在！${NC}\n"
    exit 1
fi

required_vars=(
    "FEISHU_APP_ID"
    "FEISHU_APP_SECRET"
    "FEISHU_BITABLE_APP_TOKEN"
    "FEISHU_BITABLE_TABLE_ID"
)

for var in "${required_vars[@]}"; do
    if grep -q "^${var}=" .env; then
        value=$(grep "^${var}=" .env | cut -d'=' -f2)
        if [ -n "$value" ]; then
            echo -e "${GREEN}✅ $var: 已配置${NC}"
        else
            echo -e "${RED}❌ $var: 已定义但为空${NC}"
        fi
    else
        echo -e "${RED}❌ $var: 未配置${NC}"
    fi
done

# 检查可选的 USER_ACCESS_TOKEN
if grep -q "^FEISHU_USER_ACCESS_TOKEN=" .env; then
    value=$(grep "^FEISHU_USER_ACCESS_TOKEN=" .env | cut -d'=' -f2)
    if [ -n "$value" ]; then
        echo -e "${GREEN}✅ FEISHU_USER_ACCESS_TOKEN: 已配置（使用用户身份）${NC}"
    else
        echo -e "${YELLOW}⚠️  FEISHU_USER_ACCESS_TOKEN: 已定义但为空（将使用应用身份）${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  FEISHU_USER_ACCESS_TOKEN: 未配置（将使用应用身份）${NC}"
fi

echo ""

# 2. 检查 Docker 容器状态
echo -e "${YELLOW}2️⃣  检查 Docker 容器状态...${NC}"
if ! docker ps | grep -q "delivery_api"; then
    echo -e "${RED}❌ API 容器未运行！${NC}"
    echo -e "${YELLOW}请运行: docker compose up -d${NC}\n"
    exit 1
fi
echo -e "${GREEN}✅ API 容器运行中${NC}"

if ! docker ps | grep -q "delivery_db"; then
    echo -e "${RED}❌ 数据库容器未运行！${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 数据库容器运行中${NC}\n"

# 3. 检查 API 服务
echo -e "${YELLOW}3️⃣  检查 API 服务健康状态...${NC}"
if ! curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}❌ API 服务无响应！${NC}\n"
    exit 1
fi
echo -e "${GREEN}✅ API 服务正常${NC}\n"

# 4. 检查数据库中的数据
echo -e "${YELLOW}4️⃣  检查数据库中的 daily_sales_summary 数据...${NC}"
DATA_COUNT=$(docker exec delivery_db psql -U delivery_user -d delivery_data -t -c "SELECT COUNT(*) FROM daily_sales_summary;")
DATA_COUNT=$(echo $DATA_COUNT | xargs)  # 去除空白
echo -e "${BLUE}数据库中共有 $DATA_COUNT 条记录${NC}"

if [ "$DATA_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  数据库中没有数据，请先运行爬虫和汇总任务${NC}"
    echo -e "${BLUE}示例命令：${NC}"
    echo -e "  ./manual_crawl.sh 2026-01-03"
    echo -e "  ./manual_panda_summary.sh 2026-01-03"
    echo -e "  ./manual_deliveroo_summary.sh 2026-01-03"
    echo ""
fi

# 查看最近的几条数据
echo -e "\n${BLUE}最近的5条记录：${NC}"
docker exec delivery_db psql -U delivery_user -d delivery_data -c "SELECT date, store_code, platform, gross_sales, net_sales, order_count FROM daily_sales_summary ORDER BY date DESC LIMIT 5;"
echo ""

# 5. 测试飞书 API 连接
echo -e "${YELLOW}5️⃣  测试飞书 API 连接...${NC}"

# 获取环境变量
source .env

# 测试获取 tenant_access_token
if [ -n "$FEISHU_APP_ID" ] && [ -n "$FEISHU_APP_SECRET" ]; then
    echo -e "${BLUE}测试获取 tenant_access_token...${NC}"
    TOKEN_RESPONSE=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
        -H "Content-Type: application/json" \
        -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}")
    
    TOKEN_CODE=$(echo "$TOKEN_RESPONSE" | grep -o '"code":[0-9]*' | cut -d':' -f2)
    if [ "$TOKEN_CODE" == "0" ]; then
        echo -e "${GREEN}✅ 获取 tenant_access_token 成功${NC}"
    else
        echo -e "${RED}❌ 获取 tenant_access_token 失败${NC}"
        echo "$TOKEN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TOKEN_RESPONSE"
    fi
fi

# 测试 user_access_token（如果配置了）
if [ -n "$FEISHU_USER_ACCESS_TOKEN" ]; then
    echo -e "\n${BLUE}测试 user_access_token 有效性...${NC}"
    USER_TOKEN_RESPONSE=$(curl -s -X GET "https://open.feishu.cn/open-apis/bitable/v1/apps/$FEISHU_BITABLE_APP_TOKEN/tables/$FEISHU_BITABLE_TABLE_ID/fields" \
        -H "Authorization: Bearer $FEISHU_USER_ACCESS_TOKEN")
    
    USER_TOKEN_CODE=$(echo "$USER_TOKEN_RESPONSE" | grep -o '"code":[0-9]*' | cut -d':' -f2)
    if [ "$USER_TOKEN_CODE" == "0" ]; then
        echo -e "${GREEN}✅ user_access_token 有效${NC}"
    else
        echo -e "${RED}❌ user_access_token 无效或已过期${NC}"
        echo "$USER_TOKEN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$USER_TOKEN_RESPONSE"
        echo -e "\n${YELLOW}解决方法：${NC}"
        echo -e "1. 检查 token 是否正确"
        echo -e "2. User Access Token 可能已过期，需要重新获取"
        echo -e "3. 如果无法获取新的 User Access Token，可以删除 .env 中的 FEISHU_USER_ACCESS_TOKEN，使用应用身份"
    fi
fi
echo ""

# 6. 检查容器网络
echo -e "${YELLOW}6️⃣  检查 Docker 网络配置...${NC}"
if docker network inspect dataautomaticengine_default > /dev/null 2>&1; then
    echo -e "${GREEN}✅ dataautomaticengine_default 网络存在${NC}"
    
    # 检查 API 容器是否在该网络中
    API_IN_NETWORK=$(docker inspect delivery_api | grep -c "dataautomaticengine_default" || echo "0")
    if [ "$API_IN_NETWORK" -gt 0 ]; then
        echo -e "${GREEN}✅ API 容器在正确的网络中${NC}"
    else
        echo -e "${RED}❌ API 容器不在 dataautomaticengine_default 网络中${NC}"
    fi
else
    echo -e "${RED}❌ dataautomaticengine_default 网络不存在${NC}"
fi
echo ""

# 7. 检查最近的日志
echo -e "${YELLOW}7️⃣  检查最近的飞书同步日志...${NC}"
if [ -d "api/logs" ]; then
    LATEST_LOG=$(ls -t api/logs/feishu_sync_*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo -e "${BLUE}最新日志文件: $LATEST_LOG${NC}"
        echo -e "${BLUE}最后20行：${NC}"
        tail -20 "$LATEST_LOG"
    else
        echo -e "${YELLOW}⚠️  未找到飞书同步日志${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  api/logs 目录不存在${NC}"
fi
echo ""

# 8. 提供诊断建议
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  📋 诊断总结与建议${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${YELLOW}如果服务器上运行失败而本地正常，请检查：${NC}"
echo -e "1. ${GREEN}环境变量${NC} - 服务器上的 .env 文件是否正确配置"
echo -e "2. ${GREEN}网络访问${NC} - 服务器是否能访问飞书 API (https://open.feishu.cn)"
echo -e "3. ${GREEN}Token 有效性${NC} - User Access Token 是否过期（24小时有效期）"
echo -e "4. ${GREEN}权限问题${NC} - 飞书应用是否有多维表格的读写权限"
echo -e "5. ${GREEN}数据同步${NC} - 服务器数据库中是否有要同步的数据"
echo -e "6. ${GREEN}Docker 日志${NC} - 在服务器上运行: docker logs delivery_api"
echo -e ""

echo -e "${YELLOW}常见问题解决方法：${NC}"
echo -e "• ${BLUE}Internal Server Error${NC} - 通常是环境变量缺失或飞书 API 调用失败"
echo -e "  解决：检查上面的诊断结果，特别是第5步的飞书 API 连接测试"
echo -e ""
echo -e "• ${BLUE}User Access Token 过期${NC} - Token 有效期只有24小时"
echo -e "  解决：重新获取 token 或删除 .env 中的 FEISHU_USER_ACCESS_TOKEN"
echo -e ""
echo -e "• ${BLUE}没有退出码${NC} - 容器创建失败或立即崩溃"
echo -e "  解决：检查 Docker 网络和镜像是否正确构建"
echo -e ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  诊断完成！${NC}"
echo -e "${GREEN}========================================${NC}"
