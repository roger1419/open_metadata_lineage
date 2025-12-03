# 数据血缘项目优化指南

## 优化概述

本次优化主要针对 StarRocks SQL 解析和 DolphinScheduler 任务数据解析，结合 OpenMetadata Python SDK 的最佳实践，提升血缘关系的准确性和可靠性。

## 主要优化内容

### 1. 使用 OpenMetadata SDK 服务端解析

**优化前：**
```python
# 仅使用本地 sqllineage 库解析
result = LineageRunner(sql, dialect="ansi")
lineage = result.get_column_lineage()
```

**优化后：**
```python
# 优先使用 OpenMetadata 服务端解析
metadata.add_lineage_by_query(
    service_name=database_service,
    query=sql,
    database_name=database_name,
    schema_name='default',
    timeout_seconds=60
)
# 失败时自动回退到本地解析
```

**优势：**
- ✅ 支持更多 SQL 方言（MySQL, PostgreSQL, StarRocks, Hive 等）
- ✅ 自动关联到 OpenMetadata 中的实体
- ✅ 更准确的字段级血缘解析
- ✅ 服务端缓存提升性能

**参考文档：**
https://docs.open-metadata.org/latest/sdk/python/api-reference/lineage-mixin

---

### 2. StarRocks 专用血缘处理器

**新增模块：** `starrocks_lineage_handler.py`

**功能特性：**

#### 2.1 StarRocks 语法识别
```python
# 自动识别 StarRocks 特有关键字
starrocks_keywords = [
    'DUPLICATE KEY', 'AGGREGATE KEY', 'UNIQUE KEY', 'PRIMARY KEY',
    'DISTRIBUTED BY HASH', 'BUCKETS', 'PROPERTIES',
    'BITMAP_UNION', 'HLL_UNION', 'PERCENTILE_UNION',
]
```

#### 2.2 SQL 清理功能
```python
# 移除 StarRocks 特有语法，提升解析成功率
cleaned_sql = handler._clean_starrocks_sql(sql)
# 移除: PROPERTIES(...), DISTRIBUTED BY HASH(...) BUCKETS N
```

#### 2.3 支持多种 INSERT 格式
- `INSERT INTO ... SELECT`
- `INSERT OVERWRITE ... SELECT`
- 带 PROPERTIES 的 INSERT 语句

#### 2.4 任务元数据关联
```python
task_info = {
    'platform': 'DolphinScheduler',
    'project_name': '数据中台',
    'workflow_name': 'ODS层数据同步',
    'task_name': '同步用户表',
    'task_url': 'https://...'
}
```

**使用示例：**
```python
from starrocks_lineage_handler import StarRocksLineageHandler

handler = StarRocksLineageHandler()
success = handler.add_starrocks_lineage(
    service_name='uat-starrocks',
    database_name='dsj_ods',
    sql=sql,
    description='StarRocks SQL',
    task_info=task_info
)
```

---

### 3. DolphinScheduler 集成优化

**优化内容：**

#### 3.1 自动识别 StarRocks 数据源
```python
# 检测数据源类型
is_starrocks = 'starrocks' in service.lower() or 'starrocks' in raw_service_url.lower()

if is_starrocks:
    # 使用 StarRocks 专用处理器
    handler = StarRocksLineageHandler()
    success = handler.add_starrocks_lineage(...)
else:
    # 使用通用 SQL 处理
    success = add_lineage_by_sql(...)
```

#### 3.2 增强的任务信息提取
```python
# 提取完整的任务元数据
task_info = {
    'platform': 'DolphinScheduler',
    'project_name': project_name,
    'workflow_name': process_definition_name,
    'task_name': task_name,
    'task_code': task_code,
    'task_url': f"{self.url}/ui/projects/{project_code}/task/definitions"
}
```

#### 3.3 改进的错误处理
```python
# 返回明确的处理状态
return 'success'  # 成功处理
return 'skip'     # 跳过（不符合条件）
return 'fail'     # 处理失败

# 统计信息
print(f"总任务数: {total_tasks}")
print(f"成功: {success_tasks}, 跳过: {skip_tasks}, 失败: {fail_tasks}")
```

---

### 4. DataX JSON 解析优化

**优化内容：**

#### 4.1 支持多种 Reader 配置格式
```python
# 支持 querySql 配置
if 'querySql' in reader_connection:
    query_sql = reader_connection['querySql'][0]

# 支持 table 配置
elif 'table' in reader_connection:
    reader_table = reader_connection['table'][0]
    query_sql = f"SELECT * FROM {reader_table}"
```

#### 4.2 智能字段映射
```python
# 处理通配符
if writer_columns == ['*']:
    writer_columns = reader_columns

# 字段数量不一致时，降级为表级血缘
if len(reader_columns) != len(writer_columns):
    # 只添加表级血缘
    add_lineage(from_table, "*", to_table, "*", ...)
```

#### 4.3 详细的日志输出
```python
print(f"  上游表: {from_table_fqn}")
print(f"  下游表: {to_table_fqn}")
print(f"  → 添加字段级血缘: {len(reader_columns)} 个字段映射")
print(f"  字段级血缘: 成功 {success_count}, 失败 {fail_count}")
```

---

### 5. 错误处理和日志优化

**优化内容：**

#### 5.1 分层错误处理
```python
try:
    # 服务端解析
    metadata.add_lineage_by_query(...)
    return True
except Exception as exc:
    # 自动回退到本地解析
    return _add_lineage_by_sql_local_fallback(...)
```

#### 5.2 详细的日志输出
```python
# 使用统一的日志格式
print("=========SQL 血缘解析开始=============")
print(f"Service: {service}, Database: {db_name}")
print(f"  ✓ 成功")  # 成功
print(f"  ✗ 失败")  # 失败
print(f"  ⊘ 跳过")  # 跳过
print(f"  → 提示")  # 提示信息
```

#### 5.3 异常堆栈跟踪
```python
except Exception as exc:
    print(f"✗ 处理失败: {exc}")
    import traceback
    traceback.print_exc()
```

---

## 使用指南

### 基础使用

#### 1. 提取所有平台血缘
```bash
python execute_lineage_v2.py
```

#### 2. 提取特定平台血缘
```python
from execute_lineage_v2 import LineageExtractor

extractor = LineageExtractor()
extractor.run(platforms=['dolphinscheduler'])
```

#### 3. 测试 StarRocks 血缘
```bash
python test_starrocks_lineage.py
```

### 高级使用

#### 1. 自定义 StarRocks 血缘处理
```python
from starrocks_lineage_handler import StarRocksLineageHandler

handler = StarRocksLineageHandler()

# 解析 StarRocks INSERT 语句
parse_result = handler.parse_starrocks_insert(sql)
print(f"目标表: {parse_result['target_table']}")
print(f"源表: {parse_result['source_tables']}")

# 添加血缘
success = handler.add_starrocks_lineage(
    service_name='uat-starrocks',
    database_name='dsj_ods',
    sql=sql,
    description='自定义描述',
    task_info={...}
)
```

#### 2. 集成到 DolphinScheduler
```python
from starrocks_lineage_handler import DolphinSchedulerStarRocksIntegration

integration = DolphinSchedulerStarRocksIntegration(
    dolphin_client=dolphin_client,
    metadata_client=metadata_client
)

success = integration.process_starrocks_task(
    project_code='123',
    task_code='456',
    task_data={...}
)
```

---

## 性能优化建议

### 1. 批量处理
```python
# 批量提取任务，减少 API 调用
tasks = get_all_tasks(batch_size=100)
for batch in chunks(tasks, 10):
    process_batch(batch)
```

### 2. 缓存机制
```python
# 缓存数据源映射
url_service_mapping = load_url_service_mapping()

# 缓存 OpenMetadata 实体
entity_cache = {}
```

### 3. 并发处理
```python
# 谨慎使用并发，避免 API 限流
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(process_task, task) for task in tasks]
```

---

## 故障排查

### 问题 1: SQL 解析失败

**症状：**
```
✗ 服务端血缘解析失败: ...
→ 尝试使用本地 sqllineage 解析...
✗ 本地 SQL 解析也失败: ...
```

**解决方案：**
1. 检查 SQL 语法是否正确
2. 确认数据库服务在 OpenMetadata 中已注册
3. 确认表在 OpenMetadata 中已存在
4. 查看详细错误日志

### 问题 2: StarRocks 特有语法导致解析失败

**症状：**
```
SQL 包含 DISTRIBUTED BY HASH(...) BUCKETS 32
```

**解决方案：**
使用 StarRocks 专用处理器，它会自动清理这些语法：
```python
handler = StarRocksLineageHandler()
cleaned_sql = handler._clean_starrocks_sql(sql)
```

### 问题 3: 字段级血缘缺失

**症状：**
```
只有表级血缘，没有字段级血缘
```

**解决方案：**
1. 确认 SQL 中字段映射清晰
2. 避免使用 `SELECT *`
3. 使用服务端解析（更准确）
4. 检查字段名是否包含函数或表达式

### 问题 4: 数据源映射错误

**症状：**
```
✗ 数据源 ID 123 未找到
No mapping found for URL: jdbc:mysql://...
```

**解决方案：**
1. 更新 `open_metadata_url_service` 表
2. 检查 URL 格式是否正确
3. 确认服务名称在 OpenMetadata 中存在

---

## 最佳实践

### 1. 配置管理
- 使用 `config_example.py` 作为模板
- 敏感信息使用环境变量
- 分环境配置（dev, uat, prod）

### 2. 日志管理
- 使用日志文件记录执行历史
- 定期清理旧日志
- 关键操作添加详细日志

### 3. 错误处理
- 失败时继续处理下一个任务
- 记录失败任务以便重试
- 定期检查错误日志

### 4. 性能优化
- 合理设置批量大小
- 避免频繁的 API 调用
- 使用缓存减少重复查询

### 5. 测试验证
- 先在测试环境验证
- 使用测试脚本验证功能
- 定期检查血缘准确性

---

## 版本历史

### v2.0 (2024-12-01)
- ✅ 使用 OpenMetadata SDK 服务端解析
- ✅ 新增 StarRocks 专用处理器
- ✅ 优化 DolphinScheduler 集成
- ✅ 改进 DataX JSON 解析
- ✅ 增强错误处理和日志

### v1.0 (之前版本)
- 基础血缘提取功能
- 支持 SQL、DataX、FlinkSQL、Canal
- 本地 sqllineage 解析

---

## 参考资料

- [OpenMetadata Python SDK](https://docs.open-metadata.org/latest/sdk/python)
- [Lineage Mixin API](https://docs.open-metadata.org/latest/sdk/python/api-reference/lineage-mixin)
- [sqllineage 文档](https://github.com/reata/sqllineage)
- [StarRocks 文档](https://docs.starrocks.io/)
- [DolphinScheduler 文档](https://dolphinscheduler.apache.org/)

---

## 联系支持

如有问题或建议，请联系数据团队。


---

[← 返回文档目录](README.md) | [返回项目主页](../README.md)
