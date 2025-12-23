# 飞书机器人模块

## 📋 模块架构

```
api/
├── routers/
│   └── feishu_bot.py          # 飞书回调路由（入口层）
└── services/
    └── feishu_bot/
        ├── __init__.py         # 模块导出
        ├── message_handler.py  # 消息处理器（核心层）
        ├── command_parser.py   # 命令解析器（解析层）
        └── responder.py        # 响应生成器（响应层）
```

## 🔧 模块功能

### 1. MessageHandler（消息处理器）
**职责：** 接收飞书事件，协调命令解析和响应生成

**主要方法：**
- `handle_event()` - 处理飞书推送的各种事件
- `_handle_url_verification()` - 处理URL验证事件
- `_handle_message_receive()` - 处理消息接收事件
- `_execute_command()` - 执行命令并生成响应

### 2. CommandParser（命令解析器）
**职责：** 解析用户输入的自然语言，识别命令和参数

**支持的命令：**
- **查询订单** - `查询2025-12-22` / `2025-12-22订单`
- **每日汇总** - `昨天汇总` / `今天数据` / `每日汇总`
- **店铺查询** - `Piccadilly店2025-12-22` / `2025-12-22 Battersea店`
- **帮助信息** - `帮助` / `help` / `?`

**扩展方式：**
```python
# 在 CommandParser.__init__ 的 self.patterns 中添加新模式
self.patterns = {
    'your_command': [
        r'正则表达式模式1',
        r'正则表达式模式2',
    ],
    ...
}
```

### 3. Responder（响应生成器）
**职责：** 根据命令执行结果生成飞书消息响应

**主要方法：**
- `create_order_query_response()` - 创建订单查询响应
- `create_daily_summary_response()` - 创建每日汇总响应
- `create_store_summary_response()` - 创建店铺汇总响应
- `create_help_response()` - 创建帮助信息响应
- `create_error_response()` - 创建错误响应

## 🚀 快速开始

### 1. 本地测试（无需配置飞书）

```bash
# 测试命令解析
curl -X POST "http://localhost:8000/feishu/bot/test?text=查询2025-12-22"

curl -X POST "http://localhost:8000/feishu/bot/test?text=昨天汇总"

curl -X POST "http://localhost:8000/feishu/bot/test?text=帮助"
```

### 2. 配置飞书机器人

#### 步骤1：创建飞书应用
1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret

#### 步骤2：配置事件订阅
1. 在应用管理页面，进入「事件订阅」
2. 配置请求地址：`http://your-domain:8000/feishu/bot/callback`
3. 订阅事件：`im.message.receive_v1`（接收消息）
4. 保存配置

#### 步骤3：配置权限
1. 进入「权限管理」
2. 添加权限：
   - `im:message` - 获取与发送单聊、群组消息
   - `im:message:send_as_bot` - 以应用的身份发消息

#### 步骤4：发布版本
1. 创建版本并提交审核
2. 审核通过后发布

#### 步骤5：添加机器人到群聊
1. 在飞书客户端创建群聊
2. 添加机器人到群聊
3. 在群里发送消息测试

### 3. 验证机器人状态

```bash
# 健康检查
curl http://localhost:8000/feishu/bot/health
```

## 📝 支持的命令示例

### 查询订单
```
查询2025-12-22
2025-12-22订单
```

### 每日汇总
```
昨天汇总
今天数据
每日汇总
前天报告
```

### 店铺查询
```
Piccadilly店2025-12-22
2025-12-22 Battersea店
东伦敦店铺2025-12-20
```

### 帮助信息
```
帮助
help
?
怎么用
```

## 🔌 扩展指南

### 添加新命令

#### 1. 在 CommandParser 中添加模式
```python
# command_parser.py
self.patterns = {
    'new_command': [
        r'新命令模式1',
        r'新命令模式2',
    ],
    # ... 其他命令
}
```

#### 2. 在 Responder 中添加响应方法
```python
# responder.py
def create_new_command_response(self, params: Dict) -> Dict:
    """创建新命令的响应"""
    # 处理逻辑
    result = your_service.do_something(params)
    return self._create_text_response(result)
```

#### 3. 在 MessageHandler 中添加命令分发
```python
# message_handler.py
def _execute_command(self, command: Dict, sender_id: str, message_id: str) -> Dict:
    command_type = command.get('type')
    
    if command_type == 'new_command':
        return self.responder.create_new_command_response(params)
    # ... 其他命令
```

### 支持卡片消息

在 Responder 中添加卡片消息生成方法：

```python
def _create_card_response(self, title: str, elements: list) -> Dict:
    """创建卡片消息响应"""
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": elements
        }
    }
```

## 🐛 调试

### 查看日志
```bash
# 查看API容器日志
docker logs -f delivery_api

# 查看实时飞书事件
# 所有飞书推送的事件会打印到控制台
```

### 测试命令解析
```python
from services.feishu_bot import CommandParser

parser = CommandParser()
result = parser.parse("查询2025-12-22")
print(result)
# 输出: {'type': 'query_orders', 'params': {'date': '2025-12-22'}, 'raw_text': '查询2025-12-22'}
```

## 📚 相关文档

- [飞书开放平台文档](https://open.feishu.cn/document/home/index)
- [飞书机器人开发指南](https://open.feishu.cn/document/home/develop-a-bot-in-5-minutes/create-an-app)
- [事件订阅概述](https://open.feishu.cn/document/ukTMukTMukTM/uUTNz4SN1MjL1UzM)

## 🔐 安全建议

1. **验证签名**：生产环境应验证飞书推送的签名
2. **权限控制**：限制可使用机器人的用户或群组
3. **敏感信息**：不要在消息中暴露敏感数据
4. **访问控制**：使用环境变量管理凭证

## 📞 常见问题

### Q: 机器人不回复消息？
A: 检查以下几点：
1. 事件订阅配置正确
2. 机器人有消息权限
3. 版本已发布
4. 查看API日志是否收到事件

### Q: 如何测试URL验证？
A: 使用 curl 模拟飞书的验证请求：
```bash
curl -X POST http://localhost:8000/feishu/bot/callback \
  -H "Content-Type: application/json" \
  -d '{"challenge":"test_challenge","type":"url_verification"}'
```

### Q: 如何添加图片、按钮等富文本？
A: 修改 Responder 中的响应格式，使用飞书的消息卡片格式。参考飞书文档的消息卡片章节。
