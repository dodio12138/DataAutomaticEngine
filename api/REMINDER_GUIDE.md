# 定时提醒功能使用指南

## 概述

独立的定时提醒路由模块，专门用于定时发送消息到飞书 Webhook。

## 路由列表

### 1. 每日汇总提醒
```bash
POST /reminder/daily-summary
```

**功能：** 发送昨日所有店铺的订单汇总到飞书群

**返回示例：**
```json
{
  "status": "ok",
  "message": "每日汇总已发送",
  "timestamp": "2025-12-21T09:00:00",
  "summary": "📊 2025-12-20 订单数据汇总\n..."
}
```

**定时任务配置：**
```cron
# 每天早上9点发送
0 9 * * * curl -s -X POST http://api:8000/reminder/daily-summary
```

---

### 2. 自定义消息
```bash
POST /reminder/custom
Content-Type: application/json

{
  "message": "你的消息内容",
  "webhook_url": "可选的自定义webhook"
}
```

**功能：** 发送自定义消息到飞书群

**使用示例：**
```bash
# 使用默认 webhook
curl -X POST http://localhost:8000/reminder/custom \
  -H "Content-Type: application/json" \
  -d '{"message":"重要提醒：今日有新订单"}'

# 使用自定义 webhook
curl -X POST http://localhost:8000/reminder/custom \
  -H "Content-Type: application/json" \
  -d '{
    "message":"测试消息",
    "webhook_url":"https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  }'
```

**定时任务配置：**
```cron
# 每天下午5点发送提醒
0 17 * * * curl -s -X POST http://api:8000/reminder/custom \
  -H "Content-Type: application/json" \
  -d '{"message":"📢 下班前提醒：请检查今日订单"}'
```

---

### 3. 店铺汇总
```bash
POST /reminder/store-summary?store_name={店铺名}&date={日期}
```

**功能：** 发送指定店铺的订单汇总

**参数：**
- `store_name`: 店铺名称（必填）
- `date`: 日期 YYYY-MM-DD（可选，默认昨天）

**使用示例：**
```bash
# 发送 Battersea 店昨日数据
curl -X POST "http://localhost:8000/reminder/store-summary?store_name=Battersea"

# 发送指定日期数据
curl -X POST "http://localhost:8000/reminder/store-summary?store_name=Battersea&date=2025-12-20"
```

**定时任务配置：**
```cron
# 每天早上10点发送重点店铺汇总
0 10 * * * curl -s -X POST "http://api:8000/reminder/store-summary?store_name=Battersea"
```

---

### 4. 测试配置
```bash
GET /reminder/test
```

**功能：** 测试 Webhook 配置状态（不发送消息）

**返回示例：**
```json
{
  "status": "configured",
  "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/...",
  "message": "Webhook 已配置"
}
```

---

### 5. 测试发送
```bash
POST /reminder/test-send
```

**功能：** 发送测试消息，验证配置是否正确

**使用示例：**
```bash
curl -X POST http://localhost:8000/reminder/test-send
```

---

## 配置说明

### 环境变量配置

在 `.env` 文件中配置飞书 Webhook URL：

```bash
# 飞书机器人 Webhook URL
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-url-here
```

### 获取飞书 Webhook URL

1. 在飞书群聊中，点击右上角 `···` → `设置`
2. 选择 `群机器人` → `添加机器人` → `自定义机器人`
3. 设置机器人名称和描述
4. 复制生成的 Webhook 地址到 `.env` 文件

---

## 常见定时任务配置

### 在 scheduler/crontab 中配置

```cron
# 每天早上9点发送昨日汇总
0 9 * * * curl -s -X POST http://api:8000/reminder/daily-summary

# 每天下午5点发送下班提醒
0 17 * * * curl -s -X POST http://api:8000/reminder/custom -H "Content-Type: application/json" -d '{"message":"📢 下班前提醒：请检查今日订单"}'

# 每周一早上10点发送周报提醒
0 10 * * 1 curl -s -X POST http://api:8000/reminder/custom -H "Content-Type: application/json" -d '{"message":"📊 本周开始，请准备周报数据"}'

# 每小时发送重点店铺实时数据（工作时间：10-22点）
0 10-22 * * * curl -s -X POST "http://api:8000/reminder/store-summary?store_name=Battersea"
```

---

## 错误处理

### 常见错误

**1. 未配置 Webhook URL**
```json
{
  "detail": "发送失败: 未配置飞书 Webhook URL"
}
```
**解决方案：** 在 `.env` 文件中配置 `FEISHU_WEBHOOK_URL`

**2. Webhook URL 无效**
```json
{
  "detail": "发送失败: HTTPError..."
}
```
**解决方案：** 检查 Webhook URL 是否正确，是否过期

**3. 网络超时**
```json
{
  "detail": "发送失败: timeout..."
}
```
**解决方案：** 检查网络连接，或增加超时时间

---

## 最佳实践

1. **测试配置：** 在配置定时任务前，先调用 `/reminder/test-send` 测试
2. **避免频繁发送：** 建议定时任务间隔至少 1 小时
3. **消息格式：** 使用清晰的 emoji 和格式化文本
4. **错误监控：** 定期检查 API 日志确保消息正常发送
5. **多 Webhook：** 不同类型消息可配置到不同的群聊

---

## 查看 API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
