# 飞书机器人快速入门

## 📦 已创建的文件

```
api/
├── routers/
│   └── feishu_bot.py                  # ✅ 飞书回调路由
├── services/
│   └── feishu_bot/
│       ├── __init__.py                # ✅ 模块导出
│       ├── message_handler.py         # ✅ 消息处理器
│       ├── command_parser.py          # ✅ 命令解析器
│       ├── responder.py               # ✅ 响应生成器
│       ├── README.md                  # ✅ 使用文档
│       └── ARCHITECTURE.md            # ✅ 架构设计文档
├── test_feishu_bot.sh                 # ✅ 测试脚本
└── main.py                            # ✅ 已注册路由
```

## 🚀 快速测试（5分钟）

### 1. 启动服务
```bash
cd /Users/levy/WorkSpace/Program/HaidilaoService/DataAutomaticEngine
docker-compose up -d
```

### 2. 运行测试脚本
```bash
cd api
./test_feishu_bot.sh
```

### 3. 手动测试命令

#### 查询订单
```bash
curl -X POST "http://localhost:8000/feishu/bot/test?text=查询2025-12-22"
```

#### 每日汇总
```bash
curl -X POST "http://localhost:8000/feishu/bot/test?text=昨天汇总"
```

#### 帮助信息
```bash
curl -X POST "http://localhost:8000/feishu/bot/test?text=帮助"
```

## 🔌 接入飞书（生产环境）

### 第一步：创建飞书应用

1. 访问 https://open.feishu.cn/
2. 创建企业自建应用
3. 记录 App ID 和 App Secret

### 第二步：配置机器人

1. 在应用管理页面，进入「机器人」
2. 启用机器人功能
3. 配置机器人名称和描述

### 第三步：配置事件订阅

1. 进入「事件订阅」
2. 配置请求地址：
   ```
   http://your-domain:8000/feishu/bot/callback
   ```
3. 订阅事件：
   - `im.message.receive_v1` - 接收消息

### 第四步：配置权限

1. 进入「权限管理」
2. 添加权限：
   - `im:message` - 获取与发送消息
   - `im:message:send_as_bot` - 以应用身份发送消息

### 第五步：发布版本

1. 创建版本
2. 提交审核
3. 审核通过后发布

### 第六步：添加到群聊

1. 创建飞书群聊
2. 添加机器人到群聊
3. 在群里发送消息测试

## 💬 支持的命令

### 基础命令

| 命令示例 | 功能 | 返回内容 |
|---------|------|---------|
| `查询2025-12-22` | 查询指定日期订单 | 该日期所有店铺订单汇总 |
| `2025-12-22订单` | 同上 | 同上 |
| `昨天汇总` | 查询昨天订单 | 昨天所有店铺订单汇总 |
| `今天数据` | 查询今天订单 | 今天所有店铺订单汇总 |
| `每日汇总` | 查询昨天订单 | 昨天所有店铺订单汇总 |
| `Piccadilly店2025-12-22` | 查询店铺订单 | 指定店铺指定日期订单 |
| `2025-12-22 Battersea店` | 同上 | 同上 |
| `帮助` / `help` / `?` | 查看帮助 | 命令使用说明 |

### 响应示例

发送：`查询2025-12-22`

收到：
```
📊 熊猫外卖 2025-12-22 订单数据汇总
========================================

🏪 海底捞冒菜（Piccadilly）
   📦 订单：56 单
   💰 实收金额：£1693.32
   💵 打印单金额：£1461.91
   💸 预计收入：£1069.67

🏪 海底捞冒菜（东伦敦）
   📦 订单：17 单
   💰 实收金额：£563.06
   💵 打印单金额：£471.50
   💸 预计收入：£353.10

...

========================================
📈 总计：91 单
💷 实收总额：£2902.12
📤 打印单总额：£2513.10
💹 预计总收入：£1863.27
```

## 🔧 开发与扩展

### 添加新命令（3步骤）

#### 1. 在 CommandParser 中添加模式
```python
# api/services/feishu_bot/command_parser.py

self.patterns = {
    'new_command': [
        r'新命令的正则模式',
        r'另一个匹配模式',
    ],
    # ... 现有命令
}
```

#### 2. 在 Responder 中添加响应方法
```python
# api/services/feishu_bot/responder.py

def create_new_command_response(self, params: Dict) -> Dict:
    """创建新命令的响应"""
    # 处理业务逻辑
    result = some_service.process(params)
    
    # 返回飞书消息格式
    return self._create_text_response(result)
```

#### 3. 在 MessageHandler 中添加分发
```python
# api/services/feishu_bot/message_handler.py

def _execute_command(self, command: Dict, sender_id: str, message_id: str) -> Dict:
    command_type = command.get('type')
    
    if command_type == 'new_command':
        return self.responder.create_new_command_response(params)
    
    # ... 其他命令
```

### 修改响应格式

当前使用纯文本消息，可以改为卡片消息：

```python
# responder.py

def _create_card_response(self, title: str, content: str) -> Dict:
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": content}
                }
            ]
        }
    }
```

## 📊 监控与调试

### 查看日志
```bash
# 实时查看API日志
docker logs -f delivery_api

# 所有飞书事件都会打印到日志
```

### 测试命令解析
```python
from services.feishu_bot import CommandParser

parser = CommandParser()
result = parser.parse("查询2025-12-22")
print(result)
# {'type': 'query_orders', 'params': {'date': '2025-12-22'}, 'raw_text': '查询2025-12-22'}
```

### 验证URL回调
```bash
curl -X POST http://localhost:8000/feishu/bot/callback \
  -H "Content-Type: application/json" \
  -d '{
    "challenge": "test_challenge",
    "header": {"event_type": "url_verification"}
  }'
```

## 🐛 常见问题

### Q1: 机器人不回复消息？

**检查清单：**
1. ✅ 事件订阅配置正确
2. ✅ 回调URL可访问
3. ✅ 机器人有消息权限
4. ✅ 版本已发布
5. ✅ 查看API日志是否收到事件

### Q2: URL验证失败？

**解决方案：**
```bash
# 测试回调接口是否正常
curl -X POST http://your-domain:8000/feishu/bot/callback \
  -H "Content-Type: application/json" \
  -d '{"challenge":"test","header":{"event_type":"url_verification"}}'
  
# 应该返回: {"challenge":"test"}
```

### Q3: 命令无法识别？

**调试步骤：**
1. 使用测试接口检查：
   ```bash
   curl -X POST "http://localhost:8000/feishu/bot/test?text=你的命令"
   ```
2. 查看返回的 command 字段
3. 如果为 null，则需要在 CommandParser 中添加新模式

### Q4: 如何限制用户权限？

**在 MessageHandler 中添加权限检查：**
```python
def _execute_command(self, command: Dict, sender_id: str, message_id: str) -> Dict:
    # 检查用户权限
    if command_type in ['trigger_crawler', 'admin_command']:
        if not self._is_admin(sender_id):
            return self.responder.create_error_response("权限不足")
    
    # 执行命令...
```

## 📚 相关资源

- [README.md](./services/feishu_bot/README.md) - 详细使用文档
- [ARCHITECTURE.md](./services/feishu_bot/ARCHITECTURE.md) - 架构设计文档
- [飞书开放平台](https://open.feishu.cn/document/home/index) - 官方文档

## 🎯 下一步

1. ✅ 基础框架已完成
2. ⬜ 配置生产环境飞书webhook
3. ⬜ 添加更多自定义命令
4. ⬜ 实现卡片消息响应
5. ⬜ 添加权限控制
6. ⬜ 实现异步任务处理
7. ⬜ 添加监控和日志
8. ⬜ 编写单元测试

## 💡 提示

- 使用 `test_feishu_bot.sh` 快速验证所有功能
- 修改代码后重启API：`docker restart delivery_api`
- 所有配置都在 `services/feishu_bot/` 目录下
- 模块化设计，易于扩展和维护
