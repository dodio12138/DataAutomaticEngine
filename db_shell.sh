#!/bin/bash

# 直接连接到数据库的交互式命令行
# 用法: ./db_shell.sh

# 颜色定义
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  🔧 PostgreSQL 交互式命令行${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查数据库容器
if ! docker ps | grep -q delivery_postgres; then
    echo -e "${YELLOW}❌ 数据库容器未运行${NC}"
    exit 1
fi

echo -e "${GREEN}常用命令:${NC}"
echo -e "  ${YELLOW}\\dt${NC}          - 查看所有表"
echo -e "  ${YELLOW}\\d orders${NC}    - 查看 orders 表结构"
echo -e "  ${YELLOW}\\q${NC}           - 退出"
echo ""
echo -e "${GREEN}已连接到数据库: delivery_data${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 进入交互式命令行
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data
