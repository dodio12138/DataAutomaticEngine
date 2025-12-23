#!/bin/bash
# 飞书机器人测试脚本

API_URL="http://localhost:8000"

echo "🤖 飞书机器人功能测试"
echo "================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试健康检查
echo -e "${BLUE}1. 测试健康检查${NC}"
response=$(curl -s "$API_URL/feishu/bot/health")
if echo "$response" | grep -q "ok"; then
    echo -e "${GREEN}✓ 健康检查通过${NC}"
else
    echo -e "${RED}✗ 健康检查失败${NC}"
fi
echo ""

# 测试命令：查询订单
echo -e "${BLUE}2. 测试命令：查询2025-12-22${NC}"
response=$(curl -s -X POST "$API_URL/feishu/bot/test?text=%E6%9F%A5%E8%AF%A22025-12-22")
if echo "$response" | grep -q "query_orders"; then
    echo -e "${GREEN}✓ 命令解析成功${NC}"
    echo "  - 命令类型: query_orders"
    echo "  - 参数: date=2025-12-22"
else
    echo -e "${RED}✗ 命令解析失败${NC}"
fi
echo ""

# 测试命令：每日汇总
echo -e "${BLUE}3. 测试命令：昨天汇总${NC}"
response=$(curl -s -X POST "$API_URL/feishu/bot/test?text=%E6%98%A8%E5%A4%A9%E6%B1%87%E6%80%BB")
if echo "$response" | grep -q "daily_summary"; then
    echo -e "${GREEN}✓ 命令解析成功${NC}"
    echo "  - 命令类型: daily_summary"
else
    echo -e "${RED}✗ 命令解析失败${NC}"
fi
echo ""

# 测试命令：店铺查询
echo -e "${BLUE}4. 测试命令：Piccadilly店2025-12-22${NC}"
response=$(curl -s -X POST "$API_URL/feishu/bot/test?text=Piccadilly%E5%BA%972025-12-22")
if echo "$response" | grep -q "store_summary"; then
    echo -e "${GREEN}✓ 命令解析成功${NC}"
    echo "  - 命令类型: store_summary"
    echo "  - 参数: store_name=Piccadilly, date=2025-12-22"
else
    echo -e "${RED}✗ 命令解析失败${NC}"
fi
echo ""

# 测试命令：帮助
echo -e "${BLUE}5. 测试命令：帮助${NC}"
response=$(curl -s -X POST "$API_URL/feishu/bot/test?text=%E5%B8%AE%E5%8A%A9")
if echo "$response" | grep -q "help"; then
    echo -e "${GREEN}✓ 命令解析成功${NC}"
    echo "  - 命令类型: help"
else
    echo -e "${RED}✗ 命令解析失败${NC}"
fi
echo ""

# 测试命令：未知命令
echo -e "${BLUE}6. 测试未知命令${NC}"
response=$(curl -s -X POST "$API_URL/feishu/bot/test?text=%E9%9A%8F%E4%BE%BF%E8%AF%B4%E7%82%B9%E4%BB%80%E4%B9%88")
if echo "$response" | grep -q "null"; then
    echo -e "${GREEN}✓ 正确识别为未知命令${NC}"
else
    echo -e "${RED}✗ 未知命令处理异常${NC}"
fi
echo ""

# 测试URL验证
echo -e "${BLUE}7. 测试URL验证事件${NC}"
response=$(curl -s -X POST "$API_URL/feishu/bot/callback" \
    -H "Content-Type: application/json" \
    -d '{"challenge":"test_challenge","header":{"event_type":"url_verification"}}')
if echo "$response" | grep -q "test_challenge"; then
    echo -e "${GREEN}✓ URL验证通过${NC}"
else
    echo -e "${RED}✗ URL验证失败${NC}"
fi
echo ""

echo "================================"
echo -e "${GREEN}✅ 测试完成${NC}"
echo ""
echo "💡 使用说明："
echo "  - 所有测试通过表示机器人功能正常"
echo "  - 如需配置飞书webhook，请参考 services/feishu_bot/README.md"
echo "  - 测试接口：$API_URL/feishu/bot/test"
echo "  - 回调接口：$API_URL/feishu/bot/callback"
