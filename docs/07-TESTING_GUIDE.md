# 测试指南

## 测试脚本说明

项目提供了两个测试脚本：

### 1. test_sql_parsing.py ⭐ 推荐先运行

**无需 OpenMetadata 连接**

测试 SQL 解析和清理功能，不需要连接到 OpenMetadata 服务器。

```bash
python test_sql_parsing.py
```

**测试内容：**
- ✅ SQL 清理功能（移除 StarRocks 特有语法）
- ✅ INSERT OVERWRITE 转换为 INSERT INTO
- ✅ PROPERTIES 子句移除
- ✅ DISTRIBUTED BY 子句移除
- ✅ SQL 解析功能（使用 sqllineage）
- ✅ StarRocks 语法识别

**适用场景：**
- 验证 SQL 清理逻辑
- 测试 sqllineage 解析能力
- 开发和调试时快速验证

---

### 2. test_starrocks_lineage.py

**需要 OpenMetadata 连接**

完整的血缘测试，需要连接到 OpenMetadata 服务器。

```bash
python test_starrocks_lineage.py
```

**测试内容：**
- 基础 INSERT SELECT
- INSERT OVERWRITE
- DolphinScheduler 任务关联
- 复杂 SQL（多表 JOIN + 聚合）
- StarRocks 特有语法

**前置条件：**
1. OpenMetadata 服务器正在运行
2. 配置正确的连接信息（`open_metadata_lineage.py`）
3. 测试表已在 OpenMetadata 中注册

---

## 配置 OpenMetadata 连接

编辑 `open_metadata_lineage.py`：

```python
# 修改为实际的 OpenMetadata 服务器地址
hostPort = "http://192.168.100.214:8585/api"

# 修改为实际的 JWT Token
jwtToken = "your_jwt_token_here"
```

### 获取 JWT Token

1. 登录 OpenMetadata Web UI
2. 进入 Settings → Bots
3. 创建或选择一个 Bot
4. 复制 JWT Token

---

## 常见问题

### Q1: 连接 OpenMetadata 失败

**错误信息：**
```
HTTPConnectionPool(host='192.168.100.214', port=8585): Max retries exceeded
```

**解决方案：**
1. 检查 OpenMetadata 服务是否运行：
   ```bash
   curl http://192.168.100.214:8585/api/v1/version
   ```

2. 检查网络连接

3. 确认 URL 格式正确：
   ```python
   # 正确格式
   hostPort = "http://host:port/api"
   
   # 错误格式
   hostPort = "http://http://host/api"  # 重复 http://
   hostPort = "http://host/api"         # 缺少端口
   ```

### Q2: JWT Token 无效

**错误信息：**
```
401 Unauthorized
```

**解决方案：**
1. 重新生成 JWT Token
2. 确认 Token 没有过期
3. 确认 Bot 有足够的权限

### Q3: 表不存在

**错误信息：**
```
上游表不存在: service.database.table
```

**解决方案：**
1. 使用 `open_metadata_db_info.py` 注册数据库服务
2. 运行元数据摄取（Ingestion Pipeline）
3. 确认表名格式正确：`service.schema.database.table`

### Q4: INSERT OVERWRITE 解析失败

**说明：**
sqllineage 不支持 `INSERT OVERWRITE` 语法。

**解决方案：**
系统会自动将 `INSERT OVERWRITE` 转换为 `INSERT INTO`：

```python
# 原始 SQL
INSERT OVERWRITE table1 SELECT * FROM table2

# 自动转换为
INSERT INTO table1 SELECT * FROM table2
```

---

## 测试结果示例

### 成功的测试输出

```
============================================================
SQL 解析测试套件（无需 OpenMetadata 连接）
============================================================

============================================================
测试 SQL 清理功能
============================================================

✓ INSERT OVERWRITE 转换成功
✓ PROPERTIES 移除成功
✓ DISTRIBUTED BY 移除成功
✓ 综合清理成功

============================================================
所有 SQL 清理测试通过！
============================================================

============================================================
测试 SQL 解析功能（使用 sqllineage）
============================================================

✓ 解析成功，找到 2 个字段映射
✓ 解析成功，找到 2 个字段映射
✓ 解析成功，找到 2 个字段映射

============================================================
SQL 解析测试完成
============================================================

============================================================
✓ 所有测试通过！
============================================================
```

---

## 开发测试流程

### 1. 本地开发

```bash
# 1. 测试 SQL 解析（无需连接）
python test_sql_parsing.py

# 2. 修改代码

# 3. 再次测试
python test_sql_parsing.py
```

### 2. 集成测试

```bash
# 1. 确保 OpenMetadata 服务运行
curl http://192.168.100.214:8585/api/v1/version

# 2. 配置连接信息
# 编辑 open_metadata_lineage.py

# 3. 运行完整测试
python test_starrocks_lineage.py
```

### 3. 生产部署

```bash
# 1. 运行所有测试
python test_sql_parsing.py
python test_starrocks_lineage.py

# 2. 执行血缘提取
python execute_lineage_v2.py
```

---

## 自定义测试

### 添加新的 SQL 测试

编辑 `test_sql_parsing.py`：

```python
def test_my_sql():
    """测试自定义 SQL"""
    handler = starrocks_lineage_handler.StarRocksLineageHandler()
    
    sql = """
    INSERT INTO my_table
    SELECT col1, col2 FROM source_table
    """
    
    cleaned = handler._clean_starrocks_sql(sql)
    print(f"清理后: {cleaned}")
    
    # 测试解析
    from sqllineage.runner import LineageRunner
    result = LineageRunner(cleaned, dialect="ansi")
    lineage = list(result.get_column_lineage())
    print(f"找到 {len(lineage)} 个字段映射")

# 在 main 中调用
if __name__ == "__main__":
    test_my_sql()
```

---

## 性能测试

### 测试大量 SQL

```python
import time

sqls = [...]  # 大量 SQL 列表

start = time.time()
for sql in sqls:
    handler._clean_starrocks_sql(sql)
end = time.time()

print(f"处理 {len(sqls)} 个 SQL 耗时: {end - start:.2f} 秒")
```

---

## 相关文档

- [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md) - 故障排查
- [06-SQLLINEAGE_FIX.md](06-SQLLINEAGE_FIX.md) - SQLLineage 修复
- [01-QUICKSTART.md](01-QUICKSTART.md) - 快速开始

---

[← 返回文档目录](README.md) | [返回项目主页](../README.md)
