```mermaid
flowchart TB
    subgraph Platform[外卖平台]
        P1[HungryPanda 后台]
        P2[其他平台 Deliveroo / 自建]
    end

    subgraph Crawler[数据采集层 · Docker 爬虫]
        C1[Selenium + Chrome]
        C2[订单抓取]
        C3[菜品原始名称]
    end

    subgraph DB[数据层 · 共享数据库]
        D1[(orders 原始订单表)]
        D2[(order_items 菜品明细表)]
        D3[(item_alias 菜品别名表)]
        D4[(standard_items 标准菜品表)]
        D5[(weekly_stats 周统计表)]
    end

    subgraph NLP[语义处理 / 聚类层]
        N1[文本清洗]
        N2[Embedding 向量化]
        N3[语义聚类]
        N4[出现次数最多 → 标准名]
    end

    subgraph API[分析 & 服务层 · Docker API]
        A1[FastAPI]
        A2[/stats 周销量 / 点击]
        A3[/items 标准菜品]
    end

    subgraph Notify[通知 & 展示]
        F1[飞书群机器人 Webhook]
        F2[飞书小工具 / Dashboard]
        F3[人工决策：下周备货]
    end

    %% 流程连接
    P1 --> C1
    P2 --> C1
    C1 --> C2 --> C3
    C3 --> D1
    C3 --> D2

    D2 --> N1 --> N2 --> N3 --> N4
    N4 --> D3
    N4 --> D4

    D1 --> A1
    D2 --> A1
    D4 --> A1
    A1 --> D5

    A1 --> F1
    A1 --> F2
    F2 --> F3
```

---

## 📁 项目顶层目录结构（多 Docker · 模块化 · 可扩展）

```text
food-data-platform/
├── docker-compose.yml        # ⭐ 本地 / 服务器统一入口，定义所有 Docker 服务
├── .env                      # ⭐ 全局环境变量（数据库、密钥、环境区分）
├── README.md                 # 项目说明、启动方式、整体架构说明
│
├── crawler/                  # 🕷️ 数据采集层（只负责“拿数据”）
│   ├── Dockerfile            # Crawler 容器构建文件（Chrome + Selenium）
│   ├── requirements.txt      # Selenium / selenium-wire / requests 等依赖
│   ├── main.py               # 爬虫主入口（定时 or 被 scheduler 调用）
│   ├── panda/                # HungryPanda 采集逻辑（平台隔离）
│   │   ├── login.py           # 登录、cookie 维持
│   │   ├── fetch_orders.py    # 拉取订单 JSON
│   │   └── selectors.py       # 页面元素 / XHR 定位（方便平台变更时维护）
│   ├── deliveroo/            # Deliveroo 采集逻辑
│   │   ├── auth.py
│   │   └── fetch_orders.py
│   └── storage.py            # 将 raw JSON 写入 raw_orders 表（不解析）
│
├── etl/                      # 🔄 解析 & 清洗 & 入库层（系统核心）
│   ├── Dockerfile            # ETL 容器（纯 Python，无浏览器）
│   ├── requirements.txt      # pandas / sqlalchemy / pydantic / sklearn
│   ├── main.py               # ETL 主入口（批量解析 raw_orders）
│   ├── parsers/              # 平台解析器（强烈建议一平台一文件）
│   │   ├── base.py            # 抽象基类：parse_order()
│   │   ├── panda_parser.py   # Panda JSON → 标准结构
│   │   └── deliveroo_parser.py
│   ├── models/               # 数据库 ORM 模型（统一数据结构）
│   │   ├── order.py           # orders 表
│   │   ├── order_item.py      # order_items 表
│   │   └── raw_order.py       # raw_orders 表
│   ├── services/             # 业务服务层（不关心平台）
│   │   ├── order_writer.py    # 增量写入、幂等控制
│   │   └── deduplicate.py    # 去重逻辑（platform + order_id）
│   └── clustering/           # 🍜 菜品语义归一化（你后面要用）
│       ├── embedder.py        # 文本向量化（sentence-transformers）
│       ├── cluster.py         # 聚类 / 相似度匹配
│       └── mapping.py         # name → standard_name 映射表生成
│
├── api/                      # 🌐 服务层（只读数据库，对外）
│   ├── Dockerfile            # FastAPI 容器
│   ├── requirements.txt      # fastapi / uvicorn / sqlalchemy
│   ├── main.py               # API 入口
│   ├── routers/              # 路由拆分
│   │   ├── orders.py          # 订单查询
│   │   ├── stats.py           # 周统计 / 菜品统计
│   │   └── health.py          # 健康检查（给 Docker / 云监控用）
│   ├── services/             # 业务服务（统计逻辑）
│   │   └── sales_analysis.py
│   └── integrations/         # 🔔 外部系统集成
│       └── feishu.py          # 飞书群机器人 / Webhook
│
├── scheduler/                # ⏱️ 调度层（可选，但推荐）
│   ├── Dockerfile            # 定时调度容器
│   └── crontab               # 定时规则（如每 10 分钟拉订单）
│
├── db/                       # 🗄️ 数据库相关
│   ├── init.sql              # 初始化建表 SQL
│   └── migrations/           # Alembic 数据库迁移
│
└── scripts/                  # 🧪 本地调试 / 一次性脚本
    ├── replay_raw_orders.py  # 用历史 JSON 重新跑解析（非常重要）
    └── backfill_stats.py     # 历史统计回填
```

---

## 🔧 关键结构优化说明（为什么要这样分）

### 1️⃣ crawler / etl / api **严格解耦**

* Crawler **永远不关心业务结构**
* ETL **永远不关心页面和反爬**
* API **永远不写原始数据**

👉 任何一层炸了，其他层不受影响

---

### 2️⃣ raw_orders 是“安全气囊”

* 平台改字段 → 只重跑 ETL
* 统计口径变 → 不用重爬
* 你以后写论文 / 算法 → 有原始数据可复现

---

### 3️⃣ parsers + models = 可长期维护

* 新平台 = 新 parser
* 数据库结构不变
* 历史统计自动生效

---

### 4️⃣ clustering 单独成模块（非常重要）

你现在提到的：

> “语义一致但名字不同的菜品”

这个目录 **未来一定会膨胀**，单独拆出来是对的。

---

### 5️⃣ Docker 启动慢？只慢一次

* Selenium 容器：常驻 or 定时启动
* ETL / API：秒级启动

👉 **整体系统不会因为 Docker 慢而慢**

---

如果你愿意，下一步我可以直接：

* 给你一份 **docker-compose.yml（可直接跑）**
* 或 **ETL 中 Panda / Deliveroo parser 的真实代码示例**

你只要说你想先落地哪一块即可。
