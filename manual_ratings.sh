#!/bin/bash
# 手动触发 Deliveroo 店铺评分爬虫

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 默认值
STORES="all"

# 使用说明
usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -s, --stores     店铺代码列表，逗号分隔，默认 'all'"
    echo "                   示例: battersea_maocai,brent_maocai"
    echo "  -h, --help       显示帮助信息"
    echo ""
    echo "特性:"
    echo "  • 自动从 Deliveroo 页面动态获取店铺 branch_drn_id"
    echo "  • 评分数据为实时，记录日期为前一天"
    echo "  • 无需手动配置店铺 ID"
    echo "  • 支持批量爬取多个店铺"
    echo ""
    echo "示例:"
    echo "  $0                                    # 爬取所有店铺"
    echo "  $0 -s battersea_maocai                # 爬取指定店铺"
    echo "  $0 -s battersea_maocai,brent_maocai  # 爬取多个店铺"
    echo ""
    echo "可用店铺代码:"
    echo "  - piccadilly_hotpot    (海底捞火锅 Piccadilly)"
    echo "  - piccadilly_maocai    (海底捞冒菜 Piccadilly)"
    echo "  - east_maocai          (海底捞冒菜 东伦敦)"
    echo "  - battersea_maocai     (海底捞冒菜 巴特西)"
    echo "  - brent_maocai         (海底捞冒菜 Brent)"
    echo "  - towerbridge_maocai   (海底捞冒菜 塔桥)"
    exit 1
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stores)
            STORES="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        -*)
            echo -e "${RED}❌ 未知选项: $1${NC}"
            usage
            ;;
        *)
            echo -e "${RED}❌ 未知参数: $1${NC}"
            usage
            ;;
    esac
done

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🏪 Deliveroo 店铺评分爬虫${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🏬 店铺:${NC} $STORES"
echo -e "${YELLOW}📅 记录日期:${NC} 前一天（自动计算）"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查 API 服务是否运行
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}❌ API 服务未运行${NC}"
    echo "   请先启动服务: docker compose up -d"
    exit 1
fi

# 构建 JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
  "stores": ["$STORES"]
}
EOF
)

# 如果 stores 包含逗号，转换为数组
if [[ "$STORES" == *","* ]]; then
    # 转换逗号分隔为 JSON 数组
    STORE_ARRAY=$(echo "$STORES" | sed 's/,/","/g')
    JSON_PAYLOAD=$(cat <<EOF
{
  "stores": ["$STORE_ARRAY"]
}
EOF
    )
fi

echo -e "${YELLOW}🚀 正在触发评分爬虫...${NC}"
echo ""

# 调用 API
RESPONSE=$(curl -s -X POST "http://localhost:8000/run/store-ratings" \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD")

# 检查响应
if echo "$RESPONSE" | grep -q '"status":"executed"' && echo "$RESPONSE" | grep -q '"exit_code":{"StatusCode":0}'; then
    echo -e "${GREEN}✅ 评分爬虫执行成功${NC}"
    echo ""
    
    # 提取并显示日志（最后20行）
    if command -v jq &> /dev/null; then
        echo -e "${YELLOW}📋 执行日志（最后20行）:${NC}"
        echo "$RESPONSE" | jq -r '.output' | tail -n 20
    else
        echo "$RESPONSE" | python3 -m json.tool
    fi
    
else
    echo -e "${RED}❌ 评分爬虫执行失败${NC}"
    echo ""
    echo -e "${RED}错误详情:${NC}"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ 完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}💡 查看结果:${NC}"
echo "   curl \"http://localhost:8000/run/store-ratings/history\""
echo ""
