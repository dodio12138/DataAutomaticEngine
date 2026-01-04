# 飞书同步故障排查指南

## 问题描述
本地运行 `./sync_feishu_bitable.sh` 正常，但服务器上运行失败，显示 "Internal Server Error"，没有退出码。

## 快速诊断

### 1️⃣ 运行诊断脚本（推荐）
```bash
./diagnose_feishu_sync.sh
```
该脚本会自动检查：
- .env 配置完整性
- Docker 容器状态
- API 服务健康状态
- 数据库数据
- 飞书 API 连接
- Docker 网络配置
- 最近的日志

### 2️⃣ 手动排查步骤

#### 检查 API 日志
```bash
docker logs delivery_api --tail 50
```
查找错误信息，特别注意：
- 环境变量缺失
- Docker 容器创建失败
- 飞书 API 调用错误

#### 检查飞书同步日志
```bash
ls -lt api/logs/feishu_sync_*.log | head -5
tail -50 api/logs/feishu_sync_20XXXXXX_XXXXXX.log
```

#### 检查数据库数据
```bash
./db_view_daily_summary.sh
```
确保数据库中有数据可同步。

## 常见问题及解决方案

### 问题 1: Internal Server Error (HTTP 500)

**可能原因：**
- 环境变量配置缺失或错误
- 飞书 API Token 无效或过期
- Docker 镜像未构建
- 数据库连接失败

**解决方法：**

1. **检查 .env 文件配置**
   ```bash
   # 确保服务器上的 .env 包含以下变量
   FEISHU_APP_ID=cli_xxxxxxxxxxxxx
   FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxx
   FEISHU_BITABLE_APP_TOKEN=bascnxxxxxxxxxxxxx
   FEISHU_BITABLE_TABLE_ID=tblxxxxxxxxxxxxx
   
   # 可选：使用 User Access Token（24小时有效）
   FEISHU_USER_ACCESS_TOKEN=u-xxxxxxxxxxxxxx
   ```

2. **测试飞书 API 连接**
   ```bash
   source .env
   
   # 测试 tenant_access_token
   curl -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
     -H "Content-Type: application/json" \
     -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}"
   
   # 测试 user_access_token（如果配置了）
   curl -X GET "https://open.feishu.cn/open-apis/bitable/v1/apps/$FEISHU_BITABLE_APP_TOKEN/tables/$FEISHU_BITABLE_TABLE_ID/fields" \
     -H "Authorization: Bearer $FEISHU_USER_ACCESS_TOKEN"
   ```

3. **重新构建 Docker 镜像**
   ```bash
   docker compose build feishu-sync
   docker compose up -d
   ```

### 问题 2: User Access Token 过期

**现象：**
- 本地正常运行，服务器上失败
- 错误信息包含 "Invalid access token" 或 "token expired"

**原因：**
User Access Token 只有 24 小时有效期

**解决方法：**

**方案 A：删除 User Access Token，使用应用身份**
```bash
# 编辑 .env 文件，删除或注释掉这一行
# FEISHU_USER_ACCESS_TOKEN=u-xxxxxxxxxxxxxx

# 重启 API 服务
docker compose restart api
```

**方案 B：重新获取 User Access Token**
参考 [FEISHU_USER_TOKEN_GUIDE.md](FEISHU_USER_TOKEN_GUIDE.md)

### 问题 3: 没有退出码

**现象：**
- 脚本输出显示 "⚠️ 未获取到退出码，可能是容器启动失败"
- API 返回 500 错误

**可能原因：**
- Docker 镜像不存在
- Docker 网络配置错误
- 容器立即崩溃

**解决方法：**

1. **检查 Docker 镜像**
   ```bash
   docker images | grep feishu-sync
   ```
   
   如果镜像不存在：
   ```bash
   docker compose build feishu-sync
   ```

2. **检查 Docker 网络**
   ```bash
   docker network inspect dataautomaticengine_default
   ```
   
   确保 API 容器在该网络中：
   ```bash
   docker inspect delivery_api | grep -A 10 Networks
   ```

3. **手动运行容器测试**
   ```bash
   source .env
   
   docker run --rm \
     -e DB_HOST=db \
     -e DB_PORT=5432 \
     -e DB_NAME=delivery_data \
     -e DB_USER=delivery_user \
     -e DB_PASSWORD=delivery_pass \
     -e FEISHU_APP_ID=$FEISHU_APP_ID \
     -e FEISHU_APP_SECRET=$FEISHU_APP_SECRET \
     -e FEISHU_BITABLE_APP_TOKEN=$FEISHU_BITABLE_APP_TOKEN \
     -e FEISHU_BITABLE_TABLE_ID=$FEISHU_BITABLE_TABLE_ID \
     --network dataautomaticengine_default \
     dataautomaticengine-feishu-sync \
     python main.py --start-date 2026-01-03 --end-date 2026-01-03
   ```

### 问题 4: 数据库中没有数据

**现象：**
- 同步成功但"没有数据需要同步"
- 日志显示 "从数据库获取 0 条记录"

**解决方法：**

1. **检查数据库**
   ```bash
   ./db_view_daily_summary.sh
   ```

2. **运行爬虫和汇总任务**
   ```bash
   # HungryPanda: 爬订单 → 计算汇总
   ./manual_crawl.sh 2026-01-03
   ./manual_panda_summary.sh 2026-01-03
   
   # Deliveroo: 直接获取汇总
   ./manual_deliveroo_summary.sh 2026-01-03
   ```

3. **验证数据**
   ```bash
   ./db_stats.sh
   ```

### 问题 5: 网络访问被阻止

**现象：**
- 本地正常，服务器上超时或连接失败
- 错误信息包含 "timeout" 或 "connection refused"

**解决方法：**

1. **测试网络连通性**
   ```bash
   # 在服务器上测试
   curl -I https://open.feishu.cn
   
   # 从 Docker 容器内测试
   docker run --rm alpine ping -c 3 open.feishu.cn
   ```

2. **检查防火墙/代理**
   - 确保服务器可以访问 `https://open.feishu.cn`
   - 检查是否需要配置 HTTP 代理

3. **配置代理（如果需要）**
   ```bash
   # 在 docker-compose.yaml 中为 feishu-sync 服务添加
   environment:
     - HTTP_PROXY=http://proxy.example.com:8080
     - HTTPS_PROXY=http://proxy.example.com:8080
   ```

## 环境差异对比

| 检查项 | 本地 | 服务器 | 说明 |
|--------|------|--------|------|
| .env 文件 | ✅ | ❓ | 确保内容完全一致 |
| Docker 版本 | ✅ | ❓ | `docker --version` |
| 网络访问 | ✅ | ❓ | 能否访问飞书 API |
| Token 有效期 | ✅ | ❓ | User Token 24小时有效 |
| 数据库数据 | ✅ | ❓ | 是否有数据可同步 |
| 时区设置 | ✅ | ❓ | 影响日期范围查询 |

## 逐步排查流程

1. **运行诊断脚本**
   ```bash
   ./diagnose_feishu_sync.sh
   ```

2. **对比本地和服务器的输出**
   特别关注：
   - 环境变量是否完整
   - 飞书 API 连接是否成功
   - 数据库中是否有数据

3. **查看详细日志**
   ```bash
   # API 日志
   docker logs delivery_api --tail 100
   
   # 飞书同步日志
   tail -100 api/logs/feishu_sync_*.log
   ```

4. **测试单个组件**
   ```bash
   # 测试数据库连接
   ./db_shell.sh
   
   # 手动运行同步容器
   docker run --rm \
     --env-file .env \
     --network dataautomaticengine_default \
     dataautomaticengine-feishu-sync \
     python main.py --start-date 2026-01-03
   ```

5. **逐步定位问题**
   - 如果诊断脚本全部通过，但同步失败 → 检查日志中的具体错误
   - 如果飞书 API 测试失败 → Token 问题
   - 如果容器启动失败 → Docker 配置问题
   - 如果数据库查询失败 → 网络或权限问题

## 调试技巧

### 启用详细日志
修改 [feishu_sync/main.py](feishu_sync/main.py)，在关键位置添加打印：

```python
print(f"DEBUG - 查询参数: start_date={start_date}, end_date={end_date}")
print(f"DEBUG - SQL: {query}")
print(f"DEBUG - 获取到 {len(records)} 条记录")
```

### 直接在容器内调试
```bash
# 启动交互式容器
docker run -it --rm \
  --env-file .env \
  --network dataautomaticengine_default \
  dataautomaticengine-feishu-sync \
  /bin/bash

# 在容器内手动运行
python main.py --start-date 2026-01-03
```

### 对比 API 请求
```bash
# 本地运行，启用详细输出
curl -v -X POST "http://localhost:8000/run/feishu-sync" \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2026-01-03","end_date":"2026-01-03"}'

# 保存响应到文件
curl -X POST "http://localhost:8000/run/feishu-sync" \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2026-01-03","end_date":"2026-01-03"}' \
  > response.json
  
# 格式化查看
cat response.json | python3 -m json.tool
```

## 预防措施

1. **使用应用身份而非用户身份**
   - Tenant Access Token 长期有效
   - User Access Token 24小时过期

2. **设置监控告警**
   - 定期检查同步任务状态
   - Token 过期前提醒

3. **保持环境一致**
   - 使用版本控制管理 .env.example
   - 文档化所有配置项

4. **定期备份**
   - 数据库定期备份
   - 飞书多维表格导出备份

## 联系支持

如果以上方法都无法解决问题，请提供以下信息：

1. 诊断脚本输出：`./diagnose_feishu_sync.sh`
2. API 日志：`docker logs delivery_api --tail 100`
3. 最新的飞书同步日志：`tail -100 api/logs/feishu_sync_*.log`
4. 错误截图或完整错误信息
5. 服务器环境信息：操作系统、Docker 版本等

## 相关文档

- [飞书同步实现文档](FEISHU_SYNC_IMPLEMENTATION.md)
- [飞书 User Token 获取指南](FEISHU_USER_TOKEN_GUIDE.md)
- [飞书同步使用指南](FEISHU_SYNC_GUIDE.md)
- [API 模块结构](api/MODULE_STRUCTURE.md)
