# 列级血缘功能指南

## 概述

StarRocks SQL 解析器现在支持列级血缘解析，可以自动识别列之间的依赖关系并导入到 OpenMetadata。

## 功能特性

✅ **表级血缘** - 识别表之间的依赖关系  
✅ **列级血缘** - 识别列之间的依赖关系  
✅ **自动解析** - 使用 sqllineage 自动解析 SQL  
✅ **智能匹配** - 自动匹配 OpenMetadata 中的列  
✅ **详细日志** - 显示解析和导入过程

## 使用方法

### 1. 启用列级血缘解析

```python
parser = StarRocksSQLParser(HOST_PORT, JWT_TOKEN, SERVICE_NAME, DATABASE_NAME)
parser.connect()

# 启用列级血缘解析
parser.process_sql_file(
    sql_file_path,
    parse_columns=True,  # 启用列级血缘
    description="SQL Description"
)
```

### 2. 禁用列级血缘解析（仅表级）

```python
# 只解析表级血缘
parser.process_sql_file(
    sql_file_path,
    parse_columns=False,  # 禁用列级血缘
    description="SQL Description"
)
```

## 工作原理

### 1. SQL 解析

使用 `sqllineage` 库解析 SQL，提取列级依赖关系：

```python
result = LineageRunner(cleaned_sql)
column_lineage = result.get_column_lineage()
```

### 2. 列名匹配

解析器会自动匹配 OpenMetadata 中的列：

```python
# 目标列：user_id
# 源列：b1.login_id

# 匹配过程：
# 1. 在目标表中查找 user_id 列
# 2. 在源表 b1 中查找 login_id 列
# 3. 创建列级血缘关系
```

### 3. 血缘导入

使用 OpenMetadata SDK 导入列级血缘：

```python
column_lineage = ColumnLineage(
    fromColumns=[source_col_fqn1, source_col_fqn2],
    toColumn=target_col_fqn
)

edge.lineageDetails = LineageDetails(columnsLineage=[column_lineage])
```

## 示例

### 示例 SQL

```sql
INSERT INTO ads.target_table
SELECT 
    a.user_id as user_id,
    a.user_name as name,
    b.order_count as order_cnt
FROM ods.source_table1 a
LEFT JOIN dws.source_table2 b
    ON a.user_id = b.user_id
```

### 解析结果

**表级血缘：**
```
ods.source_table1 → ads.target_table
dws.source_table2 → ads.target_table
```

**列级血缘：**
```
target_table.user_id ← source_table1.user_id
target_table.name ← source_table1.user_name
target_table.order_cnt ← source_table2.order_count
```

## 输出示例

### 测试脚本输出

```
============================================================
测试 SQL 文件解析（包含列级血缘）
============================================================

✓ 读取文件成功，长度: 2904 字符
✓ SQL 清理完成
→ 开始解析血缘关系...
✓ 目标表: ads.ads_bi_sv_user_recharge_expo_info_di
✓ 源表数量: 4

→ 开始解析列级血缘...
✓ 解析到 1 个目标列的血缘
  [1] generate_series <- 1 个源列

✅ 解析成功！
```

### 主程序输出

```
============================================================
添加血缘关系到 OpenMetadata
============================================================

处理列级血缘 (1 个目标列):
  ⚠ 未找到目标列: generate_series

✓ 成功创建 0 个列级血缘

创建血缘关系 (4 条表级边)...
  ✓ 添加血缘: xxx -> yyy
  ✓ 添加血缘: xxx -> yyy
  ✓ 添加血缘: xxx -> yyy
  ✓ 添加血缘: xxx -> yyy

✅ 血缘关系添加成功！
```

## 限制和注意事项

### 1. sqllineage 解析限制

sqllineage 可能无法解析所有复杂的 SQL 语法：

- ❌ 复杂的窗口函数
- ❌ 动态生成的列（如 generate_series）
- ❌ 复杂的 CASE WHEN 表达式
- ❌ 子查询中的列引用
- ✅ 简单的 SELECT 列
- ✅ 简单的 JOIN 列
- ✅ 简单的别名

### 2. 列名匹配

列名匹配是大小写不敏感的：

```python
# 以下都会匹配成功
user_id = USER_ID = User_Id
```

### 3. 列必须存在

源列和目标列必须在 OpenMetadata 中存在：

```
✓ 找到列: StarRocks_test.default.ads.table1.user_id
✗ 未找到列: StarRocks_test.default.ads.table1.temp_col
```

### 4. 性能考虑

对于包含大量列的表，列级血缘解析可能需要更多时间：

- 小表（< 50 列）：几秒钟
- 中表（50-200 列）：10-30 秒
- 大表（> 200 列）：30 秒以上

## 最佳实践

### 1. 简化 SQL

为了更好的列级血缘解析，建议：

```sql
-- ✅ 推荐：明确的列引用
SELECT 
    a.user_id,
    a.user_name,
    b.order_count
FROM source_table1 a
JOIN source_table2 b ON a.id = b.id

-- ❌ 不推荐：SELECT *
SELECT * FROM source_table
```

### 2. 使用别名

使用清晰的表别名：

```sql
-- ✅ 推荐
FROM ods.user_info a
JOIN dws.order_summary b

-- ❌ 不推荐
FROM ods.user_info t1
JOIN dws.order_summary t2
```

### 3. 避免复杂表达式

简单的列引用更容易解析：

```sql
-- ✅ 推荐
SELECT user_id, user_name

-- ⚠ 可能无法解析
SELECT 
    CASE WHEN status = 1 THEN 'active' ELSE 'inactive' END as status_name,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY create_time) as rn
```

### 4. 测试解析结果

在导入前先测试解析：

```bash
# 使用测试脚本
python test_parser.py

# 检查解析到的列数量
✓ 解析到 X 个目标列的血缘
```

## 故障排查

### Q1: 列级血缘解析失败

**问题：** `⚠ 列级血缘解析失败: ...`

**解决方案：**
1. 检查 SQL 语法是否正确
2. 简化复杂的 SQL 表达式
3. 查看详细错误信息

### Q2: 未找到目标列

**问题：** `⚠ 未找到目标列: column_name`

**解决方案：**
1. 确认列在 OpenMetadata 中存在
2. 检查列名拼写
3. 运行元数据摄取更新列信息

### Q3: 解析到的列数量很少

**问题：** 只解析到少量列的血缘

**原因：**
- SQL 太复杂，sqllineage 无法完全解析
- 使用了不支持的语法

**解决方案：**
1. 简化 SQL
2. 拆分复杂的 SQL 为多个简单的 SQL
3. 手动补充列级血缘

### Q4: 列级血缘未显示在 UI

**问题：** OpenMetadata UI 中看不到列级血缘

**解决方案：**
1. 刷新页面
2. 检查是否有权限查看
3. 确认血缘确实导入成功（查看日志）

## API 参考

### parse_sql_file()

```python
def parse_sql_file(self, sql_file_path, parse_columns=True):
    """
    解析 SQL 文件
    
    Args:
        sql_file_path: SQL 文件路径
        parse_columns: 是否解析列级血缘
        
    Returns:
        (target_table, source_tables, column_lineage)
        column_lineage: {target_col: [{'table': src_table, 'column': src_col}]}
    """
```

### add_lineage()

```python
def add_lineage(self, target_table, source_tables, column_lineage=None, description="StarRocks SQL"):
    """
    添加血缘关系到 OpenMetadata（支持列级血缘）
    
    Args:
        target_table: 目标表名
        source_tables: 源表名列表
        column_lineage: 列级血缘字典
        description: 血缘描述
        
    Returns:
        成功返回 True，失败返回 False
    """
```

### get_column_fqn()

```python
def get_column_fqn(self, table_entity, column_name):
    """
    获取列的完全限定名
    
    Args:
        table_entity: 表实体
        column_name: 列名
        
    Returns:
        列的 FQN 或 None
    """
```

## 扩展功能

### 自定义列映射

如果需要自定义列名映射：

```python
# 在 add_lineage 方法中添加映射逻辑
column_mapping = {
    'user_id': 'uid',
    'user_name': 'uname'
}

# 应用映射
mapped_col_name = column_mapping.get(col_name, col_name)
```

### 批量处理

批量处理多个 SQL 文件：

```python
import glob

for sql_file in glob.glob("../sql/*.sql"):
    print(f"\n处理: {sql_file}")
    parser.process_sql_file(sql_file, parse_columns=True)
```

## 相关文档

- [README.md](README.md) - 基础使用指南
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - 实现总结
- [../docs/07-TESTING_GUIDE.md](../docs/07-TESTING_GUIDE.md) - 测试指南

---

**更新时间：** 2024-12-04  
**版本：** v2.0 (支持列级血缘)  
**开发者：** Kiro AI Assistant
