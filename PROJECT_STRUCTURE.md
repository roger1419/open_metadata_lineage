# 项目结构说明

## 目录结构

```
open_metadata_lineage/
│
├── 📚 文档 (docs/)
│   ├── README.md                      # 文档目录说明
│   ├── 00-INDEX.md                    # 完整文件索引
│   ├── 01-QUICKSTART.md               # 快速开始指南 ⭐
│   ├── 02-OPTIMIZATION_GUIDE.md       # 优化详细说明
│   ├── 03-SUMMARY.md                  # 优化成果总结
│   ├── 04-CHANGELOG.md                # 版本变更记录
│   ├── 05-TROUBLESHOOTING.md          # 故障排查指南 ⭐
│   └── 06-SQLLINEAGE_FIX.md           # SQLLineage 修复说明
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
├── ⚙️ 配置文件
│   └── config_example.py              # 配置文件示例 ⭐
│
└── 📄 项目文档
    ├── README.md                      # 项目主文档 ⭐
    └── PROJECT_STRUCTURE.md           # 本文件
```

## 文件说明

### 核心模块

#### open_metadata_lineage.py (25.8 KB)
**核心血缘处理模块**

- SQL 血缘解析（服务端 + 本地备选）
- DataX JSON 解析
- FlinkSQL 解析
- Canal 配置解析
- 基础血缘添加方法

**关键函数：**
- `add_lineage_by_sql()` - SQL 血缘添加（优化版）
- `add_lineage_by_datax_json()` - DataX 血缘添加（优化版）
- `add_lineage_by_flink_sql()` - FlinkSQL 血缘添加
- `add_lineage()` - 基础血缘添加方法

#### starrocks_lineage_handler.py (13.2 KB) ⭐ 新增
**StarRocks 专用血缘处理器**

- StarRocks SQL 语法识别
- SQL 清理（移除特有语法）
- 任务元数据关联
- 多种 INSERT 格式支持

**关键类：**
- `StarRocksLineageHandler` - StarRocks 处理器
- `DolphinSchedulerStarRocksIntegration` - DS 集成

#### get_etl_add_lineage.py (42.5 KB)
**ETL 平台数据提取模块**

- DolphinScheduler 血缘提取
- StreamPark 血缘提取
- Canal 血缘提取
- Demo 示例

**关键类：**
- `GetDolphinSchedulerData()` - DS 数据提取
- `GetStreamParkData()` - StreamPark 数据提取
- `GetCanalData()` - Canal 数据提取

#### open_metadata_db_info.py (14.1 KB)
**元数据批量注册模块**

- 数据库服务注册
- 域（Domain）创建
- 标签（Tag）创建
- 摄入管道创建和部署

### 执行脚本

#### execute_lineage_v2.py (4.9 KB) ⭐ 推荐
**优化版执行脚本**

- 改进的日志管理
- 执行统计和时间跟踪
- 支持选择性平台提取
- 更好的错误处理

#### execute_demo.py (1.0 KB)
**原始执行脚本**

- 简单的执行入口
- 调用各平台提取方法

### 测试文件

#### test_starrocks_lineage.py (7.0 KB) ⭐
**StarRocks 血缘测试套件**

包含 5 个测试场景：
1. 基础 INSERT SELECT
2. INSERT OVERWRITE
3. DolphinScheduler 任务关联
4. 复杂 SQL（多表 JOIN + 聚合）
5. StarRocks 特有语法

### 配置文件

#### config_example.py (3.9 KB) ⭐
**配置文件示例**

包含所有必要的配置项：
- OpenMetadata 连接配置
- DolphinScheduler 配置
- StreamPark 配置
- Canal 配置
- 数据库配置
- 血缘提取配置

## 文档编号说明

文档按照使用顺序和重要性编号：

- **00** - 索引和导航
- **01** - 快速开始（最重要）
- **02** - 详细技术说明
- **03** - 项目总结
- **04** - 版本历史
- **05** - 故障排查（重要）
- **06** - 特定问题修复

## 使用建议

### 新用户
1. 阅读 `README.md`
2. 查看 `docs/01-QUICKSTART.md`
3. 配置 `config_example.py` → `config.py`
4. 运行 `execute_lineage_v2.py`

### 开发者
1. 阅读 `docs/03-SUMMARY.md`
2. 查看 `docs/02-OPTIMIZATION_GUIDE.md`
3. 研究核心代码模块
4. 运行测试套件

### 运维人员
1. 阅读 `docs/01-QUICKSTART.md`
2. 配置定时任务
3. 查看 `docs/05-TROUBLESHOOTING.md`
4. 监控日志文件

## 文件大小统计

| 类型 | 文件数 | 总大小 |
|------|--------|--------|
| 核心代码 | 4 | ~96 KB |
| 执行脚本 | 2 | ~6 KB |
| 测试文件 | 2 | ~7 KB |
| 配置文件 | 1 | ~4 KB |
| 文档文件 | 8 | ~50 KB |
| **总计** | **17** | **~163 KB** |

## 版本信息

- **当前版本：** 2.0.0
- **最后更新：** 2024-12-01
- **Python 版本：** 3.7+
- **主要依赖：** openmetadata-ingestion, sqllineage>=1.5.0

## 相关链接

- [项目主页](README.md)
- [文档目录](docs/README.md)
- [快速开始](docs/01-QUICKSTART.md)
- [故障排查](docs/05-TROUBLESHOOTING.md)

---

**最后更新：** 2024-12-01
