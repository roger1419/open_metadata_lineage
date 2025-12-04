# StarRocks SQL 解析器 - 实现总结

## 项目概述

创建了一个独立的 StarRocks SQL 解析器，用于解析 SQL 文件并将血缘信息自动导入到 OpenMetadata。

## 实现的文件

### 1. starrocks_sql_parser.py
**主程序文件**

**核心类：** `StarRocksSQLParser`

**主要方法：**
- `connect()` - 连接到 OpenMetadata
- `clean_sql()` - 清理 StarRocks 特有语法
- `parse_sql_file()` - 解析 SQL 文件，提取血缘关系
- `normalize_table_name()` - 规范化表名为 FQN 格式
- `get_table_entity()` - 从 OpenMetadata 获取表实体
- `add_lineage()` - 添加血缘关系到 OpenMetadata
- `process_sql_file()` - 完整处理流程（解析 + 导入）

**配置参数：**
```python
HOST_PORT = "http://192.168.100.214:4728/api"
JWT_TOKEN = "your_jwt_token"
SERVICE_NAME = "StarRocks_test"
DATABASE_NAME = "default"
SQL_FILE = "../sql/P_ads_bi_sv_user_recharge_expo_info_di.sql"
```

### 2. test_parser.py
**测试脚本**

**测试功能：**
- SQL 清理功能测试
- 表名规范化测试
- SQL 文件解析测试（不需要连接 OpenMetadata）

### 3. README.md
**使用文档**

包含：
- 功能特性
- 使用方法
- 测试结果
- 注意事项
- 常见问题

## 核心功能

### 1. SQL 清理

自动移除 StarRocks 特有语法，使 sqllineage 能够正确解析：

```python
# 移除注释
sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)

# 替换 INSERT OVERWRITE
sql = re.sub(r'\bINSERT\s+OVERWRITE\b', 'INSERT INTO', sql, flags=re.IGNORECASE)

# 移除 PROPERTIES
sql = re.sub(r'\bPROPERTIES\s*\([^)]*\)', '', sql, flags=re.IGNORECASE)

# 移除 DISTRIBUTED BY
sql = re.sub(r'\bDISTRIBUTED\s+BY\s+HASH\s*\([^)]*\)\s*BUCKETS\s+\d+', '', sql, flags=re.IGNORECASE)

# 移除键类型
sql = re.sub(r'\b(DUPLICATE|AGGREGATE|UNIQUE)\s+KEY\s*\([^)]*\)', '', sql, flags=re.IGNORECASE)
```

### 2. 表名规范化

支持多种表名格式，自动转换为 FQN：

```python
def normalize_table_name(self, table_name, default_schema='ads'):
    parts = table_name.split('.')
    
    if len(parts) == 1:
        # table -> service.database.schema.table
        return f"{self.service_name}.{self.database_name}.{default_schema}.{table_name}"
    elif len(parts) == 2:
        # schema.table -> service.database.schema.table
        return f"{self.service_name}.{self.database_name}.{parts[0]}.{parts[1]}"
    else:
        return table_name
```

### 3. 血缘关系导入

使用 OpenMetadata SDK 添加血缘：

```python
edge = EntitiesEdge(
    fromEntity=EntityReference(id=src_entity.id, type="table"),
    toEntity=EntityReference(id=target_entity.id, type="table")
)

lineage_request = AddLineageRequest(edge=edge)
self.metadata.add_lineage(lineage_request)
```

## 测试结果

### 测试脚本（test_parser.py）

```
✅ 所有测试通过

测试项目：
✓ SQL 清理 - 移除注释
✓ SQL 清理 - 替换 INSERT OVERWRITE
✓ SQL 清理 - 移除 DISTRIBUTED BY
✓ 表名规范化 - table1
✓ 表名规范化 - ads.table1
✓ 表名规范化 - ods.table2
✓ SQL 文件解析 - 成功解析 4 个源表
```

### 主程序（starrocks_sql_parser.py）

```
✅ 成功导入血缘关系

解析结果：
- 目标表：ads.ads_bi_sv_user_recharge_expo_info_di
- 源表数量：4
  [1] dim.dim_pub_code_mapping_dict (未找到)
  [2] dws.dws_user_short_video_wide_active_period_ed (未找到)
  [3] ods.ods_tidb_short_video_accountinfo ✓
  [4] ods_log.ods_sensors_cd_video_production_rechargeexposure ✓

导入结果：
- 成功创建 2 条血缘关系
- 2 个源表在 OpenMetadata 中存在
- 2 个源表未找到（需要先摄取元数据）
```

## 解析的 SQL 文件

**文件：** `sql/P_ads_bi_sv_user_recharge_expo_info_di.sql`

**SQL 类型：** INSERT INTO ... SELECT

**特点：**
- 使用 WITH 子句（CTE）
- 多表 JOIN
- 窗口函数（ROW_NUMBER）
- 数组操作（split、array_length）
- generate_series 函数

**血缘关系：**
```
ods_log.ods_sensors_cd_video_production_rechargeexposure
    ↓
ods.ods_tidb_short_video_accountinfo
    ↓
dws.dws_user_short_video_wide_active_period_ed
    ↓
dim.dim_pub_code_mapping_dict
    ↓
ads.ads_bi_sv_user_recharge_expo_info_di
```

## 技术栈

- **Python 3.10**
- **sqllineage** - SQL 血缘解析
- **openmetadata-ingestion** - OpenMetadata SDK
- **正则表达式** - SQL 清理

## 优势

1. **独立运行** - 不依赖其他模块
2. **自动清理** - 自动处理 StarRocks 特有语法
3. **灵活配置** - 支持自定义服务名、数据库名
4. **详细日志** - 每一步都有清晰的输出
5. **错误处理** - 优雅处理表不存在等情况
6. **易于测试** - 提供独立的测试脚本

## 使用场景

### 场景 1: 单个 SQL 文件
```bash
python starrocks_sql_parser.py
```

### 场景 2: 批量处理
```python
for sql_file in glob.glob("../sql/*.sql"):
    parser.process_sql_file(sql_file)
```

### 场景 3: 集成到 CI/CD
```bash
# 在 SQL 文件变更时自动更新血缘
python starrocks_sql_parser.py --sql $SQL_FILE
```

## 改进建议

### 短期改进

1. **命令行参数支持**
   ```bash
   python starrocks_sql_parser.py \
     --sql ../sql/example.sql \
     --service StarRocks_test \
     --database default
   ```

2. **批量处理模式**
   ```bash
   python starrocks_sql_parser.py --batch ../sql/*.sql
   ```

3. **配置文件支持**
   ```yaml
   # config.yaml
   openmetadata:
     host: http://192.168.100.214:4728/api
     token: xxx
   
   starrocks:
     service: StarRocks_test
     database: default
   ```

### 长期改进

1. **列级血缘**
   - 解析列之间的依赖关系
   - 使用 ColumnLineage

2. **增量更新**
   - 检查血缘是否已存在
   - 只更新变化的部分

3. **血缘验证**
   - 验证血缘关系的正确性
   - 生成血缘报告

4. **Web UI**
   - 提供 Web 界面上传 SQL
   - 可视化解析结果

## 文件结构

```
Starrocks_lineage/
├── starrocks_sql_parser.py    # 主程序
├── test_parser.py              # 测试脚本
├── README.md                   # 使用文档
└── IMPLEMENTATION_SUMMARY.md   # 实现总结（本文件）

sql/
└── P_ads_bi_sv_user_recharge_expo_info_di.sql  # 测试 SQL 文件
```

## 总结

✅ **成功实现了独立的 StarRocks SQL 解析器**

**核心功能：**
- SQL 文件解析
- StarRocks 语法清理
- 表名规范化
- 血缘关系导入

**测试结果：**
- 所有单元测试通过
- 成功解析测试 SQL 文件
- 成功导入 2 条血缘关系到 OpenMetadata

**代码质量：**
- 清晰的类结构
- 详细的注释
- 完善的错误处理
- 友好的日志输出

**文档完整：**
- 使用文档（README.md）
- 实现总结（本文件）
- 代码注释

---

**开发完成时间：** 2024-12-04  
**开发者：** Kiro AI Assistant  
**版本：** v1.0  
**状态：** ✅ 已完成并测试通过
