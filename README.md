# 数据血缘摄取脚本

本目录下的脚本用于自动化提取和录入数据血缘信息，支持多种数据平台和ETL工具，包括 DolphinScheduler、StreamPark、Canal、FlinkSQL、DataX 等。血缘信息将自动同步到 OpenMetadata 元数据平台，便于数据治理和溯源。

## 版本更新

**v2.0 优化版本**
- ✅ 使用 OpenMetadata SDK 服务端 SQL 解析能力，提升解析准确性
- ✅ 新增 StarRocks 专用血缘处理器，支持 StarRocks 特有语法
- ✅ 增强 DolphinScheduler 任务元数据关联
- ✅ 改进错误处理和日志输出
- ✅ 支持表级和字段级血缘自动识别
- ✅ 支持 StarRocks 表关联到 DolphinScheduler 任务

## 支持的血缘类型

| 序号 | 血缘来源                            | 已支持                                                  | 优化内容                       |
| ---- | ------------------------------------ | -------------------------------------------------------- | ---------------------------- |
| 0    | 元数据同步（平台自带） |  视图血缘                      | -                  |
| 1    | 离线ETL平台 DolphinScheduler | SQL、DATAX                                               | ✅ StarRocks SQL 优化、任务关联                  |
| 2    | 实时ETL平台 StreamPark               | FlinkSQL（starrocks、mongo-cdc、mysql-cdc、jdbc、kafka） | 规划中: elasticsearch、jar |
| 3    | Canal                                | mysql --> canal --> kafka                                | -                           |

## 依赖环境

- Python 3.7+
- 依赖包安装：
  ```bash
  pip install openmetadata-ingestion pymysql requests django mirage-crypto
  pip install "sqllineage>=1.5.0"  # 修复 1.3.7 的 bug
  ```

> ⚠️ **重要提示：** 如果遇到 `sqllineage 1.3.7` 导入错误（`TypeError: 'str' object is not callable`），请参考 [docs/06-SQLLINEAGE_FIX.md](docs/06-SQLLINEAGE_FIX.md) 解决。

## 项目文件结构

```
.
├── 📚 文档
│   ├── README.md                      # 项目说明文档（本文件）
│   ├── PROJECT_STRUCTURE.md           # 项目结构详细说明
│   └── docs/                          # 详细文档目录
│       ├── README.md                  # 文档目录说明
│       ├── 00-INDEX.md                # 文件索引和导航 ⭐
│       ├── 01-QUICKSTART.md           # 快速开始指南 ⭐
│       ├── 02-OPTIMIZATION_GUIDE.md   # 优化详细说明 ⭐
│       ├── 03-SUMMARY.md              # 优化成果总结 ⭐
│       ├── 04-CHANGELOG.md            # 版本变更记录 ⭐
│       ├── 05-TROUBLESHOOTING.md      # 故障排查指南 ⭐
│       └── 06-SQLLINEAGE_FIX.md       # SQLLineage 修复说明 ⭐
│
├── 🔧 核心代码
│   ├── open_metadata_lineage.py       # 核心血缘处理模块（已优化）
│   ├── starrocks_lineage_handler.py   # StarRocks 专用处理器 ⭐ 新增
│   ├── get_etl_add_lineage.py         # ETL 平台数据提取（已优化）
│   └── open_metadata_db_info.py       # 元数据批量注册
│
├── 🚀 执行脚本
│   ├── execute_lineage_v2.py          # 优化版执行脚本 ⭐ 推荐
│   └── execute_demo.py                # 原始执行脚本
│
├── 🧪 测试文件
│   ├── test_starrocks_lineage.py      # StarRocks 测试套件 ⭐
│   └── Test.py                        # 其他测试
│
└── ⚙️ 配置文件
    └── config_example.py              # 配置文件示例 ⭐
```

> 💡 **提示：** 
> - 查看 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) 了解详细的项目结构
> - 查看 [docs/README.md](docs/README.md) 浏览文档目录
> - 查看 [docs/00-INDEX.md](docs/00-INDEX.md) 获取完整的文件索引

## 主要脚本说明

### 核心模块
- **`open_metadata_lineage.py`**  
  核心血缘提取与写入 OpenMetadata 的实现，支持 SQL、DataX、FlinkSQL、Canal 等多种方式。
  - 使用 OpenMetadata SDK 的 `add_lineage_by_query` 方法进行服务端 SQL 解析
  - 支持本地 sqllineage 解析作为备选方案
  - 自动处理表级和字段级血缘关系

- **`starrocks_lineage_handler.py`** ⭐ 新增
  StarRocks 专用血缘处理器，支持：
  - StarRocks 特有 SQL 语法（DUPLICATE KEY、AGGREGATE KEY、DISTRIBUTED BY 等）
  - INSERT INTO/OVERWRITE 语句解析
  - 与 DolphinScheduler 任务的元数据关联
  - 自动清理 StarRocks 特有语法以提升解析成功率

- **`get_etl_add_lineage.py`**  
  各平台（DolphinScheduler、StreamPark、Canal）血缘提取入口。
  - 自动识别 StarRocks 数据源并使用专用处理器
  - 增强的错误处理和统计信息
  - 支持任务级元数据关联

- **`execute_demo.py`**  
  脚本入口，定时任务可直接调用，自动批量提取并写入血缘信息。

- **`open_metadata_db_info.py`**  
  数据库服务、域、标签等元数据的批量注册与同步脚本。

## 快速开始

### 1. 安装依赖
```bash
pip install openmetadata-ingestion pymysql requests django mirage-crypto
pip install "sqllineage>=1.5.0"
```

### 2. 测试功能（推荐先运行）
```bash
# 测试 SQL 解析功能（无需 OpenMetadata 连接）
python test_sql_parsing.py
```

### 3. 配置连接
复制配置文件并修改：
```bash
cp config_example.py config.py
# 编辑 config.py 填入实际配置
```

编辑 `open_metadata_lineage.py` 配置 OpenMetadata 连接：
```python
hostPort = "http://your-server:8585/api"
jwtToken = "your_jwt_token"
```

### 4. 执行血缘提取
```bash
# 使用优化版脚本（推荐）
python execute_lineage_v2.py

# 或使用原始脚本
python execute_demo.py
```

> 📖 **详细说明：** 
> - 查看 [docs/01-QUICKSTART.md](docs/01-QUICKSTART.md) 获取完整的快速开始指南
> - 查看 [docs/07-TESTING_GUIDE.md](docs/07-TESTING_GUIDE.md) 了解测试方法

### StarRocks 专用功能

使用 StarRocks 血缘处理器：

```python
from starrocks_lineage_handler import add_starrocks_lineage_from_dolphin

# 从 DolphinScheduler 添加 StarRocks 血缘
success = add_starrocks_lineage_from_dolphin(
    service_name='uat-starrocks',
    database_name='dsj_ods',
    sql='INSERT INTO target_table SELECT * FROM source_table',
    project_name='数据中台',
    workflow_name='ODS层数据同步',
    task_name='同步用户表',
    task_url='https://ds.example.com/ui/projects/123/task/definitions'
)
```

### 定时任务配置

在 Linux 服务器上配置 crontab：

```bash
# 编辑 crontab
crontab -e

# 每天 19:05 执行血缘提取
05 19 * * * /usr/local/bin/python3 /data/scripts/data_lineage/execute_demo.py > /data/scripts/data_lineage/data_lineage.log 2>&1
```

## 注意事项

### 前置条件
- ✅ 需提前在 OpenMetadata 平台配置好服务、域、标签等基础元数据
- ✅ 确保数据库表已在 OpenMetadata 中注册（可使用 `open_metadata_db_info.py` 批量注册）
- ✅ 配置 `open_metadata_url_service` 表，用于 URL 与服务名称的映射

### 安全建议
- 🔒 数据库连接、平台 API Token 等敏感信息请妥善保管
- 🔒 建议使用环境变量或配置文件管理敏感信息
- 🔒 生产环境建议使用只读账号进行元数据提取

### 扩展开发
- 如需支持新的数据源，在 `open_metadata_lineage.py` 中添加相应方法
- 如需支持新的 SQL 方言，可参考 `starrocks_lineage_handler.py` 创建专用处理器
- 血缘解析优先使用 OpenMetadata 服务端能力，失败时自动回退到本地解析

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    数据源平台                                 │
│  DolphinScheduler │ StreamPark │ Canal │ 其他ETL平台          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  血缘提取层                                   │
│  get_etl_add_lineage.py                                     │
│  - GetDolphinSchedulerData (SQL/DataX)                      │
│  - GetStreamParkData (FlinkSQL)                             │
│  - GetCanalData (Properties)                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  血缘解析层                                   │
│  open_metadata_lineage.py + starrocks_lineage_handler.py   │
│  - SQL 解析 (服务端 + 本地备选)                              │
│  - DataX JSON 解析                                          │
│  - FlinkSQL 解析                                            │
│  - StarRocks 专用处理                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              OpenMetadata SDK                               │
│  - add_lineage_by_query (服务端解析)                        │
│  - add_lineage (直接添加)                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              OpenMetadata 平台                               │
│  表血缘 + 字段血缘 + 任务元数据                               │
└─────────────────────────────────────────────────────────────┘
```

## 文档导航

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [README.md](README.md) | 项目主文档 | 所有用户 |
| [docs/01-QUICKSTART.md](docs/01-QUICKSTART.md) | 5分钟快速上手 | 新用户 ⭐ |
| [docs/02-OPTIMIZATION_GUIDE.md](docs/02-OPTIMIZATION_GUIDE.md) | 详细优化说明 | 开发者 |
| [docs/03-SUMMARY.md](docs/03-SUMMARY.md) | 优化成果总结 | 项目管理者 |
| [docs/04-CHANGELOG.md](docs/04-CHANGELOG.md) | 版本变更记录 | 所有用户 |
| [docs/05-TROUBLESHOOTING.md](docs/05-TROUBLESHOOTING.md) | 故障排查指南 | 运维人员 ⭐ |
| [docs/06-SQLLINEAGE_FIX.md](docs/06-SQLLINEAGE_FIX.md) | SQLLineage 修复 | 遇到导入错误的用户 |
| [docs/00-INDEX.md](docs/00-INDEX.md) | 完整文件索引 | 所有用户 |

## 常见问题

> 📖 **完整的故障排查指南：** 查看 [docs/05-TROUBLESHOOTING.md](docs/05-TROUBLESHOOTING.md)

### Q: 血缘解析失败怎么办？
A: 系统会自动尝试两种解析方式：
1. 优先使用 OpenMetadata 服务端解析（支持更多 SQL 方言）
2. 失败时自动回退到本地 sqllineage 解析
3. 查看日志中的详细错误信息进行排查

### Q: StarRocks SQL 解析不准确？
A: 使用新增的 `starrocks_lineage_handler.py` 模块，它会：
- 自动清理 StarRocks 特有语法
- 支持 INSERT OVERWRITE 等特殊语句
- 提供更准确的字段级血缘

### Q: 如何关联 DolphinScheduler 任务信息？
A: 系统会自动提取并关联以下信息：
- 项目名称、工作流名称、任务名称
- 任务代码、所属用户
- 任务链接地址
这些信息会添加到血缘的 description 中

### Q: 支持哪些数据库？
A: 当前支持：
- MySQL / MariaDB
- StarRocks
- MongoDB
- Kafka (作为消息队列)
- 其他 JDBC 兼容数据库

