#!/bin/bash
# ETL服务诊断脚本

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  ETL服务诊断工具${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 检查镜像是否存在
echo -e "${YELLOW}[1/6] 检查Docker镜像...${NC}"
if docker images | grep -q "dataautomaticengine-etl"; then
    echo -e "${GREEN}✅ 镜像存在${NC}"
    docker images | grep dataautomaticengine-etl | head -1
else
    echo -e "${RED}❌ 镜像不存在${NC}"
    echo -e "${YELLOW}建议执行: docker compose build etl${NC}"
    exit 1
fi
echo ""

# 2. 检查镜像内文件结构
echo -e "${YELLOW}[2/6] 检查容器内文件结构...${NC}"
echo "文件列表:"
docker run --rm dataautomaticengine-etl ls -lh /app/
echo ""

# 3. 检查Python脚本是否可执行
echo -e "${YELLOW}[3/6] 检查Python脚本...${NC}"
if docker run --rm dataautomaticengine-etl test -f /app/panda_daily_summary.py; then
    echo -e "${GREEN}✅ panda_daily_summary.py 存在${NC}"
else
    echo -e "${RED}❌ panda_daily_summary.py 不存在${NC}"
    exit 1
fi
echo ""

# 4. 检查数据库连接
echo -e "${YELLOW}[4/6] 检查数据库连接...${NC}"
if docker run --rm --env-file .env --network dataautomaticengine_default \
    dataautomaticengine-etl \
    python -c "import psycopg2, os; conn=psycopg2.connect(host=os.getenv('DB_HOST','db'), port=os.getenv('DB_PORT','5432'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD')); print('连接成功'); conn.close()" 2>/dev/null; then
    echo -e "${GREEN}✅ 数据库连接正常${NC}"
else
    echo -e "${RED}❌ 数据库连接失败${NC}"
    echo -e "${YELLOW}请检查 .env 文件和数据库服务状态${NC}"
    exit 1
fi
echo ""

# 5. 检查环境变量
echo -e "${YELLOW}[5/6] 检查环境变量...${NC}"
if [ -f .env ]; then
    echo -e "${GREEN}✅ .env 文件存在${NC}"
    echo "关键配置:"
    grep -E "^(DB_HOST|DB_PORT|DB_NAME|DB_USER)" .env | while read line; do
        echo "  $line"
    done
else
    echo -e "${RED}❌ .env 文件不存在${NC}"
    exit 1
fi
echo ""

# 6. 测试ETL脚本执行
echo -e "${YELLOW}[6/6] 测试ETL脚本执行...${NC}"
echo "运行测试: 2025-12-24 battersea_maocai"
if docker run --rm --env-file .env --network dataautomaticengine_default \
    dataautomaticengine-etl \
    python panda_daily_summary.py --stores battersea_maocai --dates 2025-12-24 2>&1 | head -20; then
    echo -e "${GREEN}✅ ETL脚本执行成功${NC}"
else
    echo -e "${RED}❌ ETL脚本执行失败${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ 诊断完成${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}如果所有检查都通过，但服务器上仍报错，请：${NC}"
echo -e "1. 在服务器上重新构建镜像: ${BLUE}docker compose build etl${NC}"
echo -e "2. 检查服务器上的 .env 文件是否完整"
echo -e "3. 确认报错信息的具体内容"
