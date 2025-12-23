# 一键部署脚本使用指南

## 可用脚本

### 1. 完整构建和启动（首次使用或更新代码后）
```bash
./build_and_start.sh
```
**功能：**
- ✅ 检查 Docker 运行状态
- ✅ 检查 .env 配置文件
- ✅ 停止现有容器
- ✅ 构建所有镜像（API, Crawler, ETL, Scheduler）
- ✅ 启动所有容器
- ✅ 等待服务就绪
- ✅ 显示服务状态

**适用场景：**
- 首次部署
- 修改了代码，需要重新构建镜像
- 添加了新的依赖包

---

### 2. 快速启动（镜像已构建）
```bash
./quick_start.sh
```
**功能：**
- 🚀 快速启动所有已构建的容器
- 📊 显示服务状态

**适用场景：**
- 停止后重新启动
- 电脑重启后启动服务

---

### 3. 停止所有服务
```bash
./stop.sh
```
**功能：**
- 🛑 停止所有运行中的容器
- 保留数据卷和镜像

---

### 4. 完全清理并重建（⚠️ 删除所有数据）
```bash
./clean_rebuild.sh
```
**功能：**
- 🗑️ 停止并删除所有容器
- 🗑️ 删除所有项目镜像
- 🗑️ **删除所有数据卷（会清空数据库！）**
- 🔄 重新构建所有镜像
- 🚀 启动所有服务

**⚠️ 警告：**
- 此操作会**永久删除数据库中的所有订单数据**！
- 需要**两次确认**才能执行（输入 'YES' 和 'DELETE ALL'）
- 执行前会显示当前数据库订单数量
- 适合：彻底重置环境、解决严重问题、开发测试

**安全措施：**
- 双重确认机制
- 显示当前数据量
- 详细的操作说明

---

### 5. 强制重建（修改代码后）
```bash
./build_and_start.sh rebuild
```
**功能：**
- 🔄 强制重新构建所有镜像
- 🚀 启动服务

**适用场景：**
- 修改了 requirements.txt
- 修改了 Dockerfile
- 代码更新后需要重新构建

---

### 6. 重启服务（不重建镜像）
```bash
./build_and_start.sh restart
```
**功能：**
- 🔄 重启所有容器
- 不重新构建镜像

**适用场景：**
- 修改了 .env 配置
- 服务异常需要重启

---

## 使用流程

### 首次部署
```bash
# 1. 检查 .env 配置
cat .env

# 2. 构建并启动
./build_and_start.sh

# 3. 查看日志
docker logs -f delivery_api
```

### 日常使用
```bash
# 启动
./quick_start.sh

# 停止
./stop.sh
```

### 代码更新后
```bash
# 停止服务
./stop.sh

# 重新构建并启动
./build_and_start.sh rebuild
```

---

## 服务访问

### API 服务
- **地址：** http://localhost:8000
- **文档：** http://localhost:8000/docs
- **健康检查：** http://localhost:8000/health

### 数据库
- **地址：** localhost:5432
- **用户名：** delivery_user
- **密码：** delivery_pass
- **数据库：** delivery_data

### 飞书机器人
- **状态：** 长连接自动运行
- **测试：** 在飞书群 @机器人 发送 "帮助"

---

## 常用命令

### 查看日志
```bash
# 所有服务日志
docker-compose logs -f

# API 服务日志
docker logs -f delivery_api

# 数据库日志
docker logs -f delivery_postgres

# 调度器日志
docker logs -f delivery_scheduler
```

### 查看服务状态
```bash
docker-compose ps
```

### 进入容器
```bash
# 进入 API 容器
docker exec -it delivery_api bash

# 进入数据库容器
docker exec -it delivery_postgres bash
```

### 数据库操作
```bash
# 连接数据库
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data

# 查询订单数量
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "SELECT COUNT(*) FROM raw_orders;"
```

### 手动触发任务
```bash
# 触发爬虫
curl -X POST http://localhost:8000/run/crawler \
  -H "Content-Type: application/json" \
  -d '{"store_code":"all","start_date":"2025-12-22"}'

# 触发 ETL
curl -X POST http://localhost:8000/run/etl
```

---

## 故障排查

### 问题：Docker 启动失败
**解决方案：**
```bash
# 检查 Docker 是否运行
docker info

# 启动 Docker Desktop
open -a Docker
```

### 问题：端口冲突
**解决方案：**
```bash
# 检查端口占用
lsof -i :8000
lsof -i :5432

# 停止占用端口的进程
kill -9 <PID>
```

### 问题：数据库连接失败
**解决方案：**
```bash
# 检查数据库状态
docker logs delivery_postgres

# 重启数据库
docker restart delivery_postgres
```

### 问题：飞书机器人无响应
**解决方案：**
```bash
# 查看长连接状态
docker logs delivery_api | grep -E '(connected|ping|pong)'

# 查看消息处理日志
docker logs delivery_api | grep -E '(收到飞书消息|识别命令|发送响应)'

# 重启 API
docker restart delivery_api
```

---

## 性能优化

### 减少重建时间
```bash
# 仅重建 API（最常修改）
docker-compose build api && docker-compose up -d api

# 仅重建 Crawler
docker build -t dataautomaticengine-crawler ./crawler
```

### 清理未使用的资源
```bash
# 清理悬挂镜像
docker image prune -f

# 清理未使用的容器
docker container prune -f

# 清理未使用的网络
docker network prune -f
```

---

## 备份与恢复

### 备份数据库
```bash
docker exec delivery_postgres pg_dump -U delivery_user delivery_data > backup_$(date +%Y%m%d).sql
```

### 恢复数据库
```bash
cat backup_20251223.sql | docker exec -i delivery_postgres psql -U delivery_user -d delivery_data
```

---

## 生产环境部署

### 关闭自动重载（提升性能）
修改 [docker-compose.yaml](docker-compose.yaml)：
```yaml
api:
  command: uvicorn main:app --host 0.0.0.0 --port 8000
  # 移除 --reload 选项
```

### 配置环境变量
生产环境使用独立的 `.env.prod` 文件：
```bash
cp .env .env.prod
# 修改 .env.prod 中的配置

# 使用生产配置启动
docker-compose --env-file .env.prod up -d
```

---

## 更多帮助

查看详细文档：
- API 架构：[api/MODULE_STRUCTURE.md](api/MODULE_STRUCTURE.md)
- 飞书机器人配置：[api/services/feishu_bot/SETUP_LONG_CONNECTION.md](api/services/feishu_bot/SETUP_LONG_CONNECTION.md)
- 项目结构：[struct.MD](struct.MD)
