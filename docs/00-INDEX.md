# 数据血缘项目文件索引

## 📚 文档文件

### 必读文档
- **[README.md](../README.md)** - 项目主文档，包含功能介绍、使用方法、技术架构
- **[01-QUICKSTART.md](01-QUICKSTART.md)** - 5 分钟快速上手指南，适合新用户
- **[03-SUMMARY.md](03-SUMMARY.md)** - 优化成果总结，展示所有改进内容

### 详细文档
- **[02-OPTIMIZATION_GUIDE.md](02-OPTIMIZATION_GUIDE.md)** - 详细优化说明、最佳实践、故障排查
- **[04-CHANGELOG.md](04-CHANGELOG.md)** - 版本变更记录，追踪所有更新
- **[05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md)** - 完整的故障排查指南
- **[06-SQLLINEAGE_FIX.md](06-SQLLINEAGE_FIX.md)** - SQLLineage bug 修复说明
- **[00-INDEX.md](00-INDEX.md)** - 本文件，项目文件索引

---

## 🔧 核心代码文件

### 主要模块

#### 1. open_metadata_lineage.py (25.8 KB) ⭐ 已优化
**核心血缘处理模块**

功能：
- SQL 血缘解析（服务端 + 本地备选）
- DataX JSON 解析
- FlinkSQL 解析
- Canal 配置解析
- 基础血缘添加方法

关键函数：
```python
add_lineage_by_sql()           # SQL 血缘添加（优化版）
add_lineage_by_datax_json()    # DataX 血缘添加（优化版）
add_lineage_by_flink_sql()     # FlinkSQL 血缘添加
add_lineage_by_canal_propertios()  # Canal 血缘添加
add_lineage()                  # 基础血缘添加方法
```

优化内容：
- ✅ 使用 OpenMetadata SDK 服务端解析
- ✅ 自动回退到本地解析
- ✅ 改进错误处理和日志
- ✅ 支持更多 SQL 方言

---

#### 2. starrocks_lineage_handler.py (13.2 KB) ⭐ 新增
**StarRocks 专用血缘处理器**

功能：
- StarRocks SQL 语法识别
- SQL 清理（移除特有语法）
- 任务元数据关联
- 多种 INSERT 格式支持

关键类：
```python
StarRocksLineageHandler         # StarRocks 处理器
DolphinSchedulerStarRocksIntegration  # DS 集成
```

关键函数：
```python
add_starrocks_lineage()         # 添加 StarRocks 血缘
add_starrocks_lineage_from_dolphin()  # 便捷函数
```

特性：
- ✅ 自动清理 StarRocks 特有语法
- ✅ 支持 INSERT OVERWRITE
- ✅ 完整的任务元数据关联
- ✅ 服务端 + 本地双重解析

---

#### 3. get_etl_add_lineage.py (42.5 KB) ⭐ 已优化
**ETL 平台数据提取模块**

功能：
- DolphinScheduler 血缘提取
- StreamPark 血缘提取
- Canal 血缘提取
- Demo 示例

关键类：
```python
GetDolphinSchedulerData()      # DS 数据提取
GetStreamParkData()             # StreamPark 数据提取
GetCanalData()                  # Canal 数据提取
AllDemo                         # 示例集合
```

优化内容：
- ✅ 自动识别 StarRocks 数据源
- ✅ 提取完整任务元数据
- ✅ 统计信息输出
- ✅ 改进错误处理

---

#### 4. open_metadata_db_info.py (14.1 KB)
**元数据批量注册模块**

功能：
- 数据库服务注册
- 域（Domain）创建
- 标签（Tag）创建
- 摄入管道（Ingestion Pipeline）创建和部署

关键类：
```python
MetaService                     # 元数据服务管理
```

---

## 🚀 执行脚本

### 1. execute_lineage_v2.py (4.9 KB) ⭐ 新增推荐
**优化版执行脚本**

功能：
- 改进的日志管理
- 执行统计和时间跟踪
- 支持选择性平台提取
- 更好的错误处理

使用：
```bash
# 提取所有平台
python execute_lineage_v2.py

# 提取特定平台
python execute_lineage_v2.py --platforms dolphinscheduler
```

---

### 2. execute_demo.py (1.0 KB)
**原始执行脚本**

功能：
- 简单的执行入口
- 调用各平台提取方法
- 支持定时任务

使用：
```bash
python execute_demo.py
```

---

## 🧪 测试文件

### test_starrocks_lineage.py (7.0 KB) ⭐ 新增
**StarRocks 血缘测试套件**

测试场景：
1. 基础 INSERT SELECT
2. INSERT OVERWRITE
3. DolphinScheduler 任务关联
4. 复杂 SQL（多表 JOIN + 聚合）
5. StarRocks 特有语法

使用：
```bash
python test_starrocks_lineage.py
```

---

### Test.py (0 KB)
**其他测试文件**（空文件）

---

## ⚙️ 配置文件

### config_example.py (3.9 KB) ⭐ 新增
**配置文件示例**

包含配置：
- OpenMetadata 连接配置
- DolphinScheduler 配置
- StreamPark 配置
- Canal 配置
- Archery 数据库配置
- URL 映射配置
- 血缘提取配置
- 任务过滤配置
- 重试配置
- 性能配置

使用：
```bash
cp config_example.py config.py
# 编辑 config.py 填入实际配置
```

---

## 📊 文件统计

### 代码文件
| 文件 | 大小 | 说明 | 状态 |
|------|------|------|------|
| open_metadata_lineage.py | 25.8 KB | 核心血缘处理 | ⭐ 已优化 |
| get_etl_add_lineage.py | 42.5 KB | ETL 平台提取 | ⭐ 已优化 |
| starrocks_lineage_handler.py | 13.2 KB | StarRocks 处理器 | ⭐ 新增 |
| open_metadata_db_info.py | 14.1 KB | 元数据注册 | - |
| execute_lineage_v2.py | 4.9 KB | 优化版执行脚本 | ⭐ 新增 |
| execute_demo.py | 1.0 KB | 原始执行脚本 | - |
| test_starrocks_lineage.py | 7.0 KB | 测试套件 | ⭐ 新增 |
| config_example.py | 3.9 KB | 配置示例 | ⭐ 新增 |

**总计代码：** ~112 KB

### 文档文件
| 文件 | 大小 | 说明 |
|------|------|------|
| README.md | 10.8 KB | 项目主文档 |
| SUMMARY.md | 13.7 KB | 优化总结 |
| OPTIMIZATION_GUIDE.md | 10.2 KB | 优化指南 |
| QUICKSTART.md | 5.6 KB | 快速开始 |
| CHANGELOG.md | 5.3 KB | 变更记录 |
| INDEX.md | 本文件 | 文件索引 |

**总计文档：** ~45 KB

---

## 🎯 使用路径

### 新用户
1. 阅读 [QUICKSTART.md](QUICKSTART.md)
2. 配置 config.py
3. 运行 execute_lineage_v2.py
4. 查看 OpenMetadata 中的血缘

### 现有用户
1. 阅读 [SUMMARY.md](SUMMARY.md) 了解优化内容
2. 阅读 [CHANGELOG.md](CHANGELOG.md) 了解变更
3. 可选：迁移到新的执行脚本
4. 可选：启用 StarRocks 专用处理器

### 开发者
1. 阅读 [OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md)
2. 查看代码注释和文档字符串
3. 运行测试套件验证功能
4. 参考示例代码进行扩展

---

## 🔗 快速链接

### 文档
- [项目主页](../README.md)
- [快速开始](01-QUICKSTART.md)
- [优化总结](03-SUMMARY.md)
- [详细指南](02-OPTIMIZATION_GUIDE.md)
- [故障排查](05-TROUBLESHOOTING.md)

### 代码
- [核心模块](../open_metadata_lineage.py)
- [StarRocks 处理器](../starrocks_lineage_handler.py)
- [ETL 提取](../get_etl_add_lineage.py)
- [执行脚本](../execute_lineage_v2.py)

### 测试
- [测试套件](../test_starrocks_lineage.py)
- [配置示例](../config_example.py)

### 外部资源
- [OpenMetadata 文档](https://docs.open-metadata.org/)
- [OpenMetadata Python SDK](https://docs.open-metadata.org/latest/sdk/python)
- [Lineage Mixin API](https://docs.open-metadata.org/latest/sdk/python/api-reference/lineage-mixin)

---

## 📝 更新日志

- 2024-12-01: v2.0 优化版本发布
  - 新增 StarRocks 专用处理器
  - 优化 SQL 解析和错误处理
  - 完善文档和测试

---

**最后更新：** 2024-12-01
**版本：** 2.0.0


---

[← 返回文档目录](README.md) | [返回项目主页](../README.md)
