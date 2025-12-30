#!/bin/bash
# 飞书同步服务快速测试脚本

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  飞书同步服务测试${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 检查环境变量
echo -e "${YELLOW}1. 检查环境变量配置...${NC}"

if [ ! -f .env ]; then
    echo -e "${RED}❌ 未找到 .env 文件${NC}"
    echo -e "${YELLOW}请复制 .env.example 并配置飞书参数${NC}"
    exit 1
fi

REQUIRED_VARS=(
    "FEISHU_APP_ID"
    "FEISHU_APP_SECRET"
    "FEISHU_BITABLE_APP_TOKEN"
    "FEISHU_BITABLE_TABLE_ID"
)

for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "^${var}=.*xxx" .env; then
        echo -e "${RED}❌ 环境变量 ${var} 未正确配置${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ 环境变量配置正常${NC}\n"

# 检查镜像
echo -e "${YELLOW}2. 检查 Docker 镜像...${NC}"

if ! docker images | grep -q "dataautomaticengine-feishu-sync"; then
    echo -e "${YELLOW}⚠️  镜像不存在，正在构建...${NC}"
    docker build -t dataautomaticengine-feishu-sync ./feishu_sync
fi

echo -e "${GREEN}✅ Docker 镜像存在${NC}\n"

# 检查数据库数据
echo -e "${YELLOW}3. 检查数据库数据...${NC}"

RECORD_COUNT=$(docker exec delivery_postgres psql -U delivery_user -d delivery_data -tAc \
    "SELECT COUNT(*) FROM daily_sales_summary WHERE date >= CURRENT_DATE - INTERVAL '7 days';")

if [ "$RECORD_COUNT" -eq 0 ]; then
    echo -e "${RED}❌ 最近7天没有数据，请先运行爬虫和汇总任务${NC}"
    echo -e "${YELLOW}提示：运行 ./manual_crawl.sh 或 ./manual_deliveroo_summary.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 找到 ${RECORD_COUNT} 条最近7天的数据${NC}\n"

# 测试同步
echo -e "${YELLOW}4. 测试同步到飞书...${NC}"
echo -e "${BLUE}同步最近1天的数据（测试模式）${NC}\n"

# 获取昨天日期
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d yesterday +%Y-%m-%d 2>/dev/null)

# 运行同步容器
docker run --rm \
    --env-file .env \
    --network dataautomaticengine_default \
    dataautomaticengine-feishu-sync \
    python main.py --start-date "$YESTERDAY" --end-date "$YESTERDAY"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ 测试成功！${NC}"
    echo -e "${GREEN}========================================${NC}\n"
    echo -e "${BLUE}下一步：${NC}"
    echo -e "1. 检查飞书多维表格中是否有数据"
    echo -e "2. 使用 ./sync_feishu_bitable.sh 同步更多数据"
    echo -e "3. 启动定时任务：docker compose up -d\n"
else
    echo -e "\n${RED}========================================${NC}"
    echo -e "${RED}❌ 测试失败（退出码：${EXIT_CODE}）${NC}"
    echo -e "${RED}========================================${NC}\n"
    echo -e "${YELLOW}故障排查：${NC}"
    echo -e "1. 检查飞书应用权限是否正确配置"
    echo -e "2. 检查 FEISHU_BITABLE_APP_TOKEN 和 TABLE_ID 是否正确"
    echo -e "3. 查看详细日志了解错误原因"
    echo -e "4. 参考 FEISHU_SYNC_GUIDE.md 进行排查\n"
    exit 1
fi
