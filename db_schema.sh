#!/bin/bash

# 查看数据库表结构
# 用法: ./db_schema.sh [表名]
# 示例: ./db_schema.sh orders
#      ./db_schema.sh  # 查看所有表

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

TABLE="${1}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  📋 数据库表结构${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查数据库容器
if ! docker ps | grep -q delivery_postgres; then
    echo -e "${YELLOW}❌ 数据库容器未运行${NC}"
    exit 1
fi

if [ -n "$TABLE" ]; then
    # 查看指定表的详细结构
    echo -e "${CYAN}📊 表: ${TABLE}${NC}"
    echo ""
    
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "\\d $TABLE"
    
    echo ""
    echo -e "${CYAN}📈 行数:${NC}"
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -t -c "SELECT COUNT(*) FROM $TABLE;"
    
else
    # 查看所有表
    echo -e "${CYAN}📚 所有表列表:${NC}"
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
        SELECT 
            schemaname as 架构,
            tablename as 表名,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as 大小
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY tablename;
    "
    
    echo ""
    echo -e "${CYAN}📊 各表行数统计:${NC}"
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
        SELECT 
            'stores' as 表名,
            COUNT(*) as 行数
        FROM stores
        UNION ALL
        SELECT 'raw_orders', COUNT(*) FROM raw_orders;
    "
fi

echo ""
echo -e "${GREEN}✅ 查询完成${NC}"
echo ""
echo -e "${YELLOW}💡 提示: 使用 ./db_schema.sh orders 查看 orders 表详细结构${NC}"
