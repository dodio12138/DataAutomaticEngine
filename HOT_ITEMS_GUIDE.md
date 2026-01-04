# 飞书机器人热门菜品查询功能

## 🎉 功能概述

新增飞书机器人热门菜品查询功能，支持查询 Deliveroo 订单详情数据中的畅销菜品和热门添加项。

## 📝 支持的查询指令

### 1. 汇总查询（主产品 + 添加项 TOP 5）
```
热门菜品
热门汇总
```

**返回内容：**
- 🍜 热门主产品 TOP 5（含销量、营收、订单数）
- 🎯 热门添加项 TOP 5（含使用次数、订单数）

### 2. 主产品详细榜单（TOP 10）
```
热门主产品
热门主菜
畅销菜品
```

**返回内容：**
- 🥇 TOP 10 主产品完整列表
- 📦 销量、💰 营收、📝 订单数、💵 均价

### 3. 添加项详细榜单（TOP 10）
```
热门添加项
热门配料
畅销添加项
```

**返回内容：**
- 🥇 TOP 10 添加项完整列表
- 🔢 使用次数、📝 订单数、📊 平均每单

## 🔍 可选筛选参数

所有查询都支持以下可选参数的任意组合：

### 店铺筛选
```
Piccadilly店 热门菜品
battersea 热门主产品
east 热门添加项
```

**支持店铺：**
- piccadilly_maocai / piccadilly_hotpot
- battersea_maocai
- east_maocai
- brent_maocai
- towerbridge_maocai

### 日期筛选
```
2025-12-27 热门菜品
2025-12-24 热门主产品
```

**格式：** YYYY-MM-DD

### 平台筛选
```
热门菜品 deliveroo
热门主产品 panda
```

**关键词：**
- Deliveroo: `deliveroo`, `roo`, `袋鼠`, `🦘`
- HungryPanda: `panda`, `hungrypanda`, `熊猫`, `🐼`
- 不指定：查询所有平台

## 💡 综合查询示例

```
# 基础查询
热门菜品                          # 全部店铺、全部时间、全部平台

# 单条件筛选
Piccadilly店 热门菜品            # 指定店铺
2025-12-27 热门主产品            # 指定日期
热门添加项 deliveroo             # 指定平台

# 多条件组合
battersea 2025-12-27 热门主产品  # 店铺 + 日期
Piccadilly店 热门添加项 panda    # 店铺 + 平台
2025-12-24 热门菜品 deliveroo    # 日期 + 平台
```

## 🎨 响应格式示例

### 汇总查询响应
```
🔥 热门菜品汇总
📍 店铺: Piccadilly
📅 时间: 2025-12-27

🍜 热门主产品 TOP 5:
🥇 Create Your Own Mini Pot: 54份 | £1598.10 | 26单
🥈 Mini HotPot For Two people: 32份 | £1188.94 | 16单
...

🎯 热门添加项 TOP 5:
🥇 米饭 Rice: 82次 | 31单
🥈 米饭 Rice: 66次 | 32单
...

💡 发送'热门主产品'或'热门添加项'查看完整榜单
```

### 详细榜单响应
```
🍜 热门主产品 TOP 10 (DELIVEROO)
📍 店铺: Piccadilly
📅 时间: 2025-12-27

🥇 Create Your Own Mini Pot
   📦 销量: 54份 | 💰 营收: £1598.10
   📝 订单: 26单 | 💵 均价: £0.00
...
```

## 🔧 技术实现

### 1. 命令解析（CommandParser）
- 正则模式匹配：`热门(主产品|添加项|汇总|菜品)`
- 参数提取：店铺名、日期、平台
- 类型识别：items / modifiers / summary

### 2. API 调用
- `/stats/items/top` - 主产品查询
- `/stats/modifiers/top` - 添加项查询
- 参数：`store_code`, `date`, `platform`, `limit`

### 3. 响应生成（Responder）
- `_query_hot_items()` - 调用 API 获取数据
- `_format_hot_items_summary()` - 格式化汇总响应
- `_format_hot_items_single()` - 格式化详细榜单

### 4. 店铺映射
- `map_store_name_to_code()` - 将中英文店铺名映射到 store_code
- 支持精确匹配和模糊匹配

## 📊 数据来源

- **数据表：** `orders`, `order_items`, `order_item_modifiers`
- **统计视图：** `v_item_sales_stats`, `v_modifier_sales_stats`
- **数据范围：** Deliveroo 订单详情（已导入 233 条订单）

## 🧪 测试

### 测试脚本
```bash
# 完整测试（包含 API 直接调用）
./test_hot_items_bot.sh

# 简化测试（仅机器人响应）
./test_hot_items_simple.sh
```

### 手动测试
```bash
# 使用测试端点
curl -X POST "http://localhost:8000/feishu/bot/test?text=热门菜品"

# 直接调用 API
curl "http://localhost:8000/stats/items/top?store_code=piccadilly_maocai&limit=5"
curl "http://localhost:8000/stats/modifiers/top?date=2025-12-27&platform=deliveroo"
```

## 🚀 部署

功能已集成到 API 容器，无需额外配置。只需重启 API 容器即可：

```bash
docker compose restart api
```

## 📝 相关文件

- `api/services/feishu_bot/command_parser.py` - 命令解析逻辑
- `api/services/feishu_bot/responder.py` - 响应生成逻辑
- `api/services/report_service.py` - 店铺名映射函数
- `api/routers/order_stats.py` - 统计查询 API
- `api/routers/feishu_bot.py` - 飞书机器人路由

## ✅ 功能特性

- ✅ 支持汇总和详细两种查询模式
- ✅ 支持店铺、日期、平台三维筛选
- ✅ 支持中英文店铺名和模糊匹配
- ✅ 数据实时查询（无缓存）
- ✅ 响应格式友好（Emoji + 对齐）
- ✅ 完整错误处理
- ✅ 测试覆盖完整

## 💬 用户体验

用户可以在飞书群中直接向机器人发送自然语言查询，例如：
- "热门菜品" - 快速查看汇总
- "Piccadilly店 热门主产品" - 查看特定店铺畅销菜
- "2025-12-27 热门添加项 deliveroo" - 分析特定日期的配料数据

无需记忆复杂命令，支持灵活的自然语言表达！
