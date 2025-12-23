# 飞书机器人本地测试配置指南

## 一、前置条件

已完成配置：
- ✅ 飞书 Encrypt Key 已添加到 `.env` 文件
- ✅ 签名验证功能已实现并集成
- ✅ API 容器已重启并加载新配置

环境信息：
```bash
FEISHU_ENCRYPT_KEY=87HaAXRNUyYyznYWNXK6fganVPzw5BgA
API 服务: http://localhost:8000
回调接口: http://localhost:8000/feishu/bot/callback
测试接口: http://localhost:8000/feishu/bot/test
健康检查: http://localhost:8000/feishu/bot/health
```

## 二、本地测试方案

### 方案 A：使用 ngrok 进行内网穿透（推荐）

#### 1. 安装 ngrok
```bash
# macOS 安装
brew install ngrok

# 或下载二进制文件
# https://ngrok.com/download
```

#### 2. 启动 ngrok 隧道
```bash
ngrok http 8000
```

输出示例：
```
Session Status                online
Account                       your-account (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Forwarding                    https://abc123.ngrok.io -> http://localhost:8000
```

记录生成的公网地址：`https://abc123.ngrok.io`

#### 3. 配置飞书开发者后台

访问：https://open.feishu.cn/app

a) 事件订阅配置：
   - 请求地址：`https://abc123.ngrok.io/feishu/bot/callback`
   - 加密策略：已启用（使用你的 Encrypt Key）
   - 点击「验证」，等待飞书发送验证请求

b) 订阅事件：
   - 进入「事件与回调」→「添加事件」
   - 订阅：`接收消息 v2.0 (im.message.receive_v1)`
   - 所需权限：
     - ✅ 获取与发送单聊、群组消息
     - ✅ 以应用身份读取单聊消息

c) 机器人配置：
   - 进入「机器人」→「启用机器人」
   - 记录 Bot ID 和 Bot Secret（如需主动发送消息）

#### 4. 发布版本
   - 创建新版本
   - 选择可用范围（企业内部/测试用户）
   - 发布并等待审核

### 方案 B：使用测试接口进行本地调试

不需要外网访问时，可直接使用测试接口：

```bash
# 测试命令解析（不实际查询数据库）
curl -X POST http://localhost:8000/feishu/bot/test \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "message": {
        "content": "{\"text\":\"查询2025-12-22的订单\"}"
      },
      "sender": {
        "sender_id": {
          "user_id": "test_user"
        }
      }
    }
  }'

# 测试日常汇总
curl -X POST http://localhost:8000/feishu/bot/test \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "message": {
        "content": "{\"text\":\"昨天汇总\"}"
      },
      "sender": {
        "sender_id": {
          "user_id": "test_user"
        }
      }
    }
  }'

# 测试店铺汇总
curl -X POST http://localhost:8000/feishu/bot/test \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "message": {
        "content": "{\"text\":\"查看battersea_maocai的汇总\"}"
      },
      "sender": {
        "sender_id": {
          "user_id": "test_user"
        }
      }
    }
  }'
```

## 三、URL 验证流程

飞书配置回调地址时会发送验证请求：

**请求示例：**
```json
{
  "challenge": "ajls384kdjx98XX",
  "token": "xxxxxxxxxxxxxx",
  "type": "url_verification"
}
```

**响应要求：**
```json
{
  "challenge": "ajls384kdjx98XX"
}
```

我们的 `MessageHandler.handle_event()` 已经实现自动处理。

## 四、签名验证机制

飞书发送请求时会携带以下 Headers：

```
X-Lark-Request-Timestamp: 1609430400
X-Lark-Request-Nonce: 4ca44d1c
X-Lark-Signature: e18c3a7fc70d90c1a5f3e0dd79e3e14f9a8f5c26
```

**验证算法：**
```python
# 拼接字符串
sign_string = timestamp + nonce + encrypt_key

# 计算 SHA256
signature = hashlib.sha256(sign_string.encode()).hexdigest()

# 比对签名
if signature == request_signature:
    # 验证通过
```

我们的 `SignatureVerifier` 已实现该逻辑，验证失败会返回 401 Unauthorized。

## 五、消息接收事件结构

用户在群聊中 @机器人 或私聊机器人时，飞书会推送：

```json
{
  "schema": "2.0",
  "header": {
    "event_id": "xxx",
    "event_type": "im.message.receive_v1",
    "create_time": "1609430400000",
    "token": "xxx",
    "app_id": "cli_xxx",
    "tenant_key": "xxx"
  },
  "event": {
    "sender": {
      "sender_id": {
        "union_id": "on_xxx",
        "user_id": "ou_xxx",
        "open_id": "ou_xxx"
      },
      "sender_type": "user",
      "tenant_key": "xxx"
    },
    "message": {
      "message_id": "om_xxx",
      "root_id": "om_xxx",
      "parent_id": "om_xxx",
      "create_time": "1609430400000",
      "chat_id": "oc_xxx",
      "chat_type": "group",
      "message_type": "text",
      "content": "{\"text\":\"@_user_1 查询今天的订单\"}"
    }
  }
}
```

## 六、支持的命令列表

| 命令类型 | 示例 | 说明 |
|---------|-----|-----|
| 订单查询 | "查询2025-12-22的订单" | 查看指定日期的订单统计 |
| 日常汇总 | "今天汇总"、"昨天汇总" | 按日期分组查看各店铺订单 |
| 店铺汇总 | "查看battersea_maocai的汇总" | 查看指定店铺的历史订单汇总 |
| 帮助文档 | "帮助"、"help" | 显示所有可用命令 |

## 七、调试技巧

### 1. 查看 API 日志
```bash
docker logs -f delivery_api
```

### 2. 监控 ngrok 请求
访问：http://127.0.0.1:4040（ngrok 启动后自动开启）

可以看到：
- 所有传入请求的详细信息
- 请求头、请求体
- 响应内容
- 重放请求功能

### 3. 测试签名验证
```bash
# 生成测试签名
timestamp=$(date +%s)
nonce="test_nonce"
body='{"type":"url_verification","challenge":"test123"}'
encrypt_key="87HaAXRNUyYyznYWNXK6fganVPzw5BgA"

# 计算签名
signature=$(echo -n "${timestamp}${nonce}${encrypt_key}${body}" | openssl dgst -sha256 -hex | awk '{print $2}')

# 发送请求
curl -X POST http://localhost:8000/feishu/bot/callback \
  -H "Content-Type: application/json" \
  -H "X-Lark-Request-Timestamp: ${timestamp}" \
  -H "X-Lark-Request-Nonce: ${nonce}" \
  -H "X-Lark-Signature: ${signature}" \
  -d "${body}"
```

## 八、常见问题

### Q1: URL 验证失败
**检查：**
- ngrok 隧道是否正常运行
- API 服务是否启动（`docker ps` 确认 delivery_api 状态）
- 回调地址格式是否正确（必须包含 `/feishu/bot/callback`）

### Q2: 签名验证失败
**检查：**
- `.env` 中的 `FEISHU_ENCRYPT_KEY` 是否正确
- API 容器是否已重启（`docker restart delivery_api`）
- 飞书后台加密策略是否启用

### Q3: 机器人无响应
**检查：**
- 是否已订阅 `im.message.receive_v1` 事件
- 是否已发布版本并添加机器人到群聊
- 用户是否 @机器人（群聊中需要 @）
- API 日志是否有错误信息

### Q4: 数据查询返回空
**检查：**
- 数据库中是否有对应日期的订单
```sql
SELECT DATE(order_date) as date, COUNT(*) as count 
FROM raw_orders 
GROUP BY DATE(order_date) 
ORDER BY date DESC;
```
- 店铺代码是否正确（参考 `crawler/store_config.py`）

## 九、生产环境部署

### 1. 使用固定域名

不建议使用 ngrok 的免费随机域名，考虑：
- 申请付费版 ngrok 获得固定域名
- 使用云服务器并配置固定 IP
- 使用企业内网穿透方案

### 2. 配置 HTTPS

飞书要求生产环境必须使用 HTTPS：
- ngrok 默认提供 HTTPS
- 自建服务器需配置 SSL 证书（Let's Encrypt）

### 3. 添加监控告警

建议监控：
- API 服务可用性
- 数据库连接状态
- 回调接口响应时间
- 错误日志聚合

### 4. 权限管理

配置飞书机器人权限：
- 最小权限原则
- 定期轮换 Encrypt Key
- 监控异常访问

## 十、下一步开发建议

当前已实现功能：
- ✅ 基础命令解析（订单查询、日常汇总、店铺汇总）
- ✅ 数据库查询服务
- ✅ 签名验证安全机制
- ✅ 模块化架构

可扩展功能：
- [ ] 主动推送消息（定时发送日报）
- [ ] 富文本卡片消息（交互式按钮）
- [ ] 多语言支持
- [ ] 用户权限管理
- [ ] 数据可视化图表
- [ ] 自然语言增强（AI 对话）

---

**快速开始：**
```bash
# 1. 启动 ngrok
ngrok http 8000

# 2. 配置飞书后台（使用 ngrok 提供的 URL）

# 3. 发布版本

# 4. 在群聊中测试
@机器人 查询今天的订单
```
