# 故障排查指南

## 常见问题

### 1. SQLLineage 导入错误

**问题：**
```
TypeError: 'str' object is not callable
File "sqllineage/__init__.py", line 24, in _patch_updating_lateral_view_lexeme
    if regex("LATERAL VIEW EXPLODE(col)"):
```

**原因：** sqllineage 1.3.7 存在已知 bug

**解决方案：**
```bash
pip install "sqllineage>=1.5.0"
```

详细说明请参考 [06-SQLLINEAGE_FIX.md](06-SQLLINEAGE_FIX.md)

---

### 2. OpenMetadata 连接失败

**问题：**
```
ConnectionError: HTTPConnectionPool(host='meta.fixpng.com', port=80): Max retries exceeded
```

**原因：** 无法连接到 OpenMetadata 服务器

**解决方案：**
1. 检查网络连接
2. 确认 OpenMetadata 服务器地址正确
3. 更新 `open_metadata_lineage.py` 中的 `hostPort` 和 `jwtToken`

```python
hostPort = "http://your-openmetadata-server/api"
jwtToken = "your_jwt_token_here"
```

---

### 3. 数据源映射未找到

**问题：**
```
No mapping found for URL: jdbc:mysql://...
```

**原因：** URL 与服务名称的映射关系未配置

**解决方案：**
在数据库中添加映射关系：

```sql
INSERT INTO open_metadata_url_service (url_pattern, service_name) VALUES
('your-host:port', 'your-service-name');
```

---

### 4. SQL 解析失败

**问题：**
```
✗ 服务端血缘解析失败
✗ 本地 SQL 解析也失败
```

**可能原因：**
1. SQL 语法错误
2. 表在 OpenMetadata 中不存在
3. 数据库服务未注册

**解决方案：**
1. 检查 SQL 语法
2. 确认表已在 OpenMetadata 中注册
3. 使用 `open_metadata_db_info.py` 批量注册数据库服务

---

### 5. StarRocks SQL 解析失败

**问题：**
StarRocks 特有语法导致解析失败

**解决方案：**
使用 StarRocks 专用处理器：

```python
from starrocks_lineage_handler import StarRocksLineageHandler

handler = StarRocksLineageHandler()
success = handler.add_starrocks_lineage(
    service_name='uat-starrocks',
    database_name='dsj_ods',
    sql=your_sql
)
```

---

### 6. DolphinScheduler 认证失败

**问题：**
```
Login failed: ...
```

**解决方案：**
检查 `get_etl_add_lineage.py` 中的配置：

```python
self.userName = 'your_username'
self.userPassword = 'your_password'
self.url = 'https://your-dolphinscheduler-server'
```

---

### 7. 依赖冲突警告

**问题：**
```
ERROR: pip's dependency resolver does not currently take into account all the packages
openmetadata-ingestion 0.13.1.8 requires sqllineage==1.3.7, but you have sqllineage 1.5.6
```

**说明：** 这是预期的警告，可以安全忽略

**原因：**
- sqllineage 1.5.6 向后兼容 1.3.7
- 本项目优先使用 OpenMetadata SDK 服务端解析
- sqllineage 仅作为备选方案

---

### 8. 字段级血缘缺失

**问题：**
只有表级血缘，没有字段级血缘

**可能原因：**
1. SQL 使用了 `SELECT *`
2. 字段名包含函数或表达式
3. 服务端解析不支持该 SQL 方言

**解决方案：**
1. 避免使用 `SELECT *`，明确列出字段
2. 简化字段表达式
3. 检查日志查看具体原因

---

### 9. 任务处理失败

**问题：**
```
✗ SQL 任务处理失败
✗ DataX 任务处理失败
```

**解决方案：**
1. 查看详细错误日志
2. 检查数据源配置
3. 验证 SQL 或 DataX JSON 格式
4. 使用测试脚本单独测试

---

### 10. 性能问题

**问题：**
处理大量任务时速度慢

**解决方案：**
1. 调整批量处理大小
2. 使用过滤器排除不需要的任务
3. 分批次处理
4. 考虑使用并发（谨慎，避免 API 限流）

---

## 调试技巧

### 1. 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. 单独测试 SQL 解析

```python
from sqllineage.runner import LineageRunner

sql = "INSERT INTO table1 SELECT * FROM table2"
result = LineageRunner(sql)
print(result.get_column_lineage())
```

### 3. 测试 OpenMetadata 连接

```python
import open_metadata_lineage

metadata = open_metadata_lineage.get_metadata_client()
print(metadata.health_check())
```

### 4. 查看任务详情

```python
import get_etl_add_lineage

ds = get_etl_add_lineage.GetDolphinSchedulerData()
projects = ds.get_projects_list()
print(f"找到 {len(projects)} 个项目")
```

---

## 获取帮助

如果以上方法都无法解决问题：

1. 查看日志文件 `lineage_extraction.log`
2. 运行测试脚本 `test_starrocks_lineage.py`
3. 查看 [OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md) 故障排查部分
4. 联系数据团队获取支持

---

## 相关文档

- [06-SQLLINEAGE_FIX.md](06-SQLLINEAGE_FIX.md) - SQLLineage bug 修复
- [01-QUICKSTART.md](01-QUICKSTART.md) - 快速开始指南
- [02-OPTIMIZATION_GUIDE.md](02-OPTIMIZATION_GUIDE.md) - 优化详细说明
- [../README.md](../README.md) - 项目主文档

---

[← 返回文档目录](README.md) | [返回项目主页](../README.md)
