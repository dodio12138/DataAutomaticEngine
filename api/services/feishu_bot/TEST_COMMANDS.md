# 飞书机器人测试命令速查表

## 快速开始

```bash
# 1. 启动完整测试流程
./start_feishu_test.sh

# 2. 测试签名验证
./test_feishu_signature.sh

# 3. 健康检查
curl http://localhost:8000/feishu/bot/health
```

## 本地测试接口

### 1. 查询订单（指定日期）

```bash
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
```

**示例响应：**
```json
{
  "command": "query_orders",
  "params": {
    "date": "2025-12-22"
  },
  "response": "📊 2025-12-22 订单统计\n\n订单总数: 91\n..."
}
```

### 2. 日常汇总（今天/昨天）

```bash
# 今天汇总
curl -X POST http://localhost:8000/feishu/bot/test \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "message": {
        "content": "{\"text\":\"今天汇总\"}"
      },
      "sender": {
        "sender_id": {
          "user_id": "test_user"
        }
      }
    }
  }'

# 昨天汇总
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
```

### 3. 店铺汇总

```bash
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

### 4. 帮助命令

```bash
curl -X POST http://localhost:8000/feishu/bot/test \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "message": {
        "content": "{\"text\":\"帮助\"}"
      },
      "sender": {
        "sender_id": {
          "user_id": "test_user"
        }
      }
    }
  }'
```

## 飞书实际消息格式示例

当用户在飞书群聊中发送消息时，飞书会推送如下格式：

### URL 验证事件

```json
{
  "challenge": "ajls384kdjx98XX",
  "token": "xxxxxxxxxxxxxx",
  "type": "url_verification"
}
```

**期望响应：**
```json
{
  "challenge": "ajls384kdjx98XX"
}
```

### 接收消息事件

```json
{
  "schema": "2.0",
  "header": {
    "event_id": "5e3702a84e847582be8db7fb73283c02",
    "event_type": "im.message.receive_v1",
    "create_time": "1609430400000",
    "token": "verification_token",
    "app_id": "cli_xxx",
    "tenant_key": "tenant_xxx"
  },
  "event": {
    "sender": {
      "sender_id": {
        "union_id": "on_xxx",
        "user_id": "ou_xxx",
        "open_id": "ou_xxx"
      },
      "sender_type": "user",
      "tenant_key": "tenant_xxx"
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

## 命令解析逻辑

### 支持的自然语言模式

| 用户输入 | 解析命令 | 提取参数 |
|---------|---------|---------|
| "查询2025-12-22的订单" | query_orders | date: "2025-12-22" |
| "查询12月22日订单" | query_orders | date: "2025-12-22" |
| "今天汇总" | daily_summary | date: "2025-12-22" (自动计算) |
| "昨天汇总" | daily_summary | date: "2025-12-21" |
| "查看battersea_maocai的汇总" | store_summary | store_code: "battersea_maocai" |
| "帮助" / "help" | help | 无 |

### 店铺代码列表

参考 `crawler/store_config.py`：

```python
store_code_map = {
    "battersea_maocai": "battersea_maocai",
    "battersea_hotpot": "battersea_hotpot",
    "kingscross_maocai": "kingscross_maocai",
    # ... 更多店铺
}
```

## ngrok 配置

### 1. 启动 ngrok

```bash
ngrok http 8000
```

**输出示例：**
```
Session Status                online
Account                       your-account (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Forwarding                    https://abc123.ngrok.io -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

### 2. 配置飞书事件订阅

**请求地址：** `https://abc123.ngrok.io/feishu/bot/callback`

**签名验证：**
- Encrypt Key: `87HaAXRNUyYyznYWNXK6fganVPzw5BgA`
- 验证方式：已在代码中自动处理

### 3. 测试回调

使用 ngrok Web Interface 监控请求：
- 访问：http://127.0.0.1:4040
- 可查看所有 HTTP 请求详情
- 支持重放请求

## 调试技巧

### 1. 实时监控 API 日志

```bash
docker logs -f delivery_api
```

### 2. 检查数据库中的订单数据

```bash
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c \
  "SELECT DATE(order_date) as date, COUNT(*) as count FROM raw_orders GROUP BY DATE(order_date) ORDER BY date DESC LIMIT 5;"
```

### 3. 测试命令解析（不查数据库）

使用 `/test` 端点可以测试命令解析逻辑，不会实际查询数据库：

```bash
curl -X POST http://localhost:8000/feishu/bot/test \
  -H "Content-Type: application/json" \
  -d '{"event":{"message":{"content":"{\"text\":\"测试命令\"}"}, "sender":{"sender_id":{"user_id":"test"}}}}'
```

### 4. 模拟飞书签名请求

```bash
timestamp=$(date +%s)
nonce="test_nonce"
body='{"type":"url_verification","challenge":"test123"}'
encrypt_key="87HaAXRNUyYyznYWNXK6fganVPzw5BgA"

# 计算签名
sign_string="${timestamp}${nonce}${encrypt_key}"
signature=$(echo -n "$sign_string" | openssl dgst -sha256 -hex | awk '{print $2}')

# 发送请求
curl -X POST http://localhost:8000/feishu/bot/callback \
  -H "Content-Type: application/json" \
  -H "X-Lark-Request-Timestamp: ${timestamp}" \
  -H "X-Lark-Request-Nonce: ${nonce}" \
  -H "X-Lark-Signature: ${signature}" \
  -d "${body}"
```

## 常见错误处理

### 错误：签名验证失败

```json
{
  "detail": "Invalid signature"
}
```

**排查步骤：**
1. 检查 `.env` 中的 `FEISHU_ENCRYPT_KEY` 是否正确
2. 确认 API 容器已重启：`docker-compose up -d --force-recreate api`
3. 查看日志：`docker logs delivery_api --tail 50`

### 错误：未找到数据

```json
{
  "response": "未找到指定日期的订单数据"
}
```

**排查步骤：**
1. 确认数据库中有该日期的订单：
   ```sql
   SELECT * FROM raw_orders WHERE DATE(order_date) = '2025-12-22' LIMIT 5;
   ```
2. 检查日期格式是否正确（YYYY-MM-DD）
3. 确认爬虫是否已运行并保存数据

### 错误：命令无法识别

**排查步骤：**
1. 查看支持的命令列表（发送"帮助"命令）
2. 检查命令格式是否符合要求
3. 查看 API 日志中的解析结果

## 性能测试

### 并发请求测试

```bash
# 使用 Apache Bench 测试
ab -n 100 -c 10 -T application/json -p test_payload.json http://localhost:8000/feishu/bot/test

# 或使用 hey
hey -n 100 -c 10 -m POST -T application/json -D test_payload.json http://localhost:8000/feishu/bot/test
```

### 响应时间监控

在 ngrok Web Interface (http://127.0.0.1:4040) 中可以看到每个请求的响应时间。

## 生产环境清单

- [ ] 使用固定域名（不要使用 ngrok 免费版随机域名）
- [ ] 配置 HTTPS（生产环境必须）
- [ ] 定期轮换 Encrypt Key
- [ ] 添加请求频率限制
- [ ] 配置日志聚合与监控
- [ ] 设置告警机制
- [ ] 准备回滚方案
- [ ] 编写运维文档

## 参考资料

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [事件订阅概述](https://open.feishu.cn/document/ukTMukTMukTM/uUTNz4SN1MjL1UzM)
- [接收消息事件](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/events/receive)
- [签名验证机制](https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-subscription-configure-/encrypt-key-encryption-configuration-case)
