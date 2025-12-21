# API 代码重构说明

## 重构前后对比

### 重构前
- 所有代码都在 `main.py` 中（约 246 行）
- 包含 FastAPI 应用、路由、工具函数、Docker 操作等所有逻辑
- 代码耦合度高，不易维护和扩展

### 重构后
```
api/
├── main.py          # FastAPI 应用主入口（约 45 行）
├── utils.py         # 通用工具函数
├── routers/         # 路由模块
│   ├── __init__.py
│   ├── crawler.py   # 爬虫相关路由
│   └── etl.py       # ETL 相关路由
├── logs/            # 日志文件目录
├── Dockerfile
└── requirements.txt
```

## 模块职责

### 1. main.py（主入口）
**职责：** FastAPI 应用初始化和路由注册

**功能：**
- 创建 FastAPI 应用实例
- 注册路由模块（crawler、etl）
- 提供根路径和健康检查接口

**代码量：** 约 45 行

### 2. utils.py（工具模块）
**职责：** 通用工具函数和配置

**功能：**
- Docker 客户端初始化
- 数据库连接函数 `get_db_conn()`
- Docker 镜像检查和构建 `ensure_image_exists()`
- 数据库环境变量构建 `get_db_env_dict()`
- 日志目录配置

**代码量：** 约 55 行

### 3. routers/crawler.py（爬虫路由）
**职责：** 爬虫相关的 API 路由

**功能：**
- POST `/run/crawler` - 执行爬虫任务
- 参数验证（store_code/store_codes/store_name）
- 创建临时 Docker 容器
- 容器日志收集和保存
- 实时日志打印到控制台

**代码量：** 约 100 行

### 4. routers/etl.py（ETL 路由）
**职责：** ETL 相关的 API 路由

**功能：**
- POST `/run/etl` - 执行 ETL 任务
- 创建临时 Docker 容器
- 容器日志收集和保存
- 实时日志打印到控制台

**代码量：** 约 70 行

## API 端点

### 1. 根路径
```
GET /
```
返回 API 信息和可用端点列表

### 2. 健康检查
```
GET /health
```
检查服务状态和数据库连接

### 3. 爬虫执行
```
POST /run/crawler
Content-Type: application/json

{
  "store_code": "battersea_maocai",  // 单店代码或 "all"
  "store_codes": ["store1", "store2"],  // 多店代码（可选）
  "store_name": "店铺中文名",  // 中文名称（可选）
  "start_date": "2025-12-20",  // 开始日期（可选）
  "end_date": "2025-12-21"     // 结束日期（可选）
}
```

### 4. ETL 执行
```
POST /run/etl
```
无参数，执行数据清洗和转换

## 扩展指南

### 添加新的业务模块

1. **创建新的路由文件**
```bash
# 例如：添加报表功能
touch api/routers/report.py
```

2. **编写路由代码**
```python
# api/routers/report.py
from fastapi import APIRouter
from utils import get_db_conn

router = APIRouter(prefix="/report", tags=["report"])

@router.get("/daily")
def daily_report():
    """生成日报"""
    conn = get_db_conn()
    # 实现报表逻辑
    conn.close()
    return {"status": "ok"}
```

3. **在 main.py 中注册路由**
```python
# api/main.py
from routers import crawler, etl, report  # 添加 import

app.include_router(report.router)  # 注册路由
```

### 添加通用工具函数

在 `utils.py` 中添加：
```python
def new_utility_function():
    """新的工具函数"""
    pass
```

在路由中使用：
```python
from utils import new_utility_function
```

## 优势

1. **模块化**：每个模块职责清晰，易于理解和维护
2. **可扩展性**：添加新功能只需创建新路由文件，不影响现有代码
3. **可测试性**：模块分离后更容易编写单元测试
4. **代码复用**：通用功能提取到 utils.py，避免重复代码
5. **团队协作**：多人可以同时开发不同的路由模块，减少冲突

## 测试验证

所有功能已验证正常：
- ✅ 健康检查正常
- ✅ 单店爬取正常
- ✅ 多店爬取正常
- ✅ 全店爬取正常
- ✅ 日志保存正常
- ✅ 数据库连接正常
