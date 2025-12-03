# 快速开始指南

## 5 分钟快速上手

### 步骤 1: 安装依赖

```bash
pip install sqllineage openmetadata-ingestion pymysql requests django mirage-crypto
```

### 步骤 2: 配置连接信息

复制配置文件模板：
```bash
cp config_example.py config.py
```

编辑 `config.py`，填入实际配置：
```python
OPENMETADATA_CONFIG = {
    'host_port': 'http://your-openmetadata-server/api',
    'jwt_token': 'your_jwt_token',
}

DOLPHINSCHEDULER_CONFIG = {
    'url': 'https://your-dolphinscheduler-server',
    'username': 'admin',
    'password': 'your_password',
}
```

### 步骤 3: 配置 URL 映射

在数据库中创建映射表：
```sql
CREATE TABLE open_metadata_url_service (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url_pattern VARCHAR(255) NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    UNIQUE INDEX idx_url_pattern (url_pattern)
);

-- 添加映射关系
INSERT INTO open_metadata_url_service (url_pattern, service_name) VALUES
('uatstarrocks.fixpng.com:9030', 'uat-starrocks'),
('192.168.31.133:3306', 'uat-mysql-01');
```

### 步骤 4: 测试连接

```python
# 测试 OpenMetadata 连接
python -c "import open_metadata_lineage; print(open_metadata_lineage.METADATA.health_check())"
```

### 步骤 5: 运行血缘提取

```bash
# 运行完整提取
python execute_lineage_v2.py

# 或使用原始脚本
python execute_demo.py
```

---

## 测试 StarRocks 血缘

### 单个 SQL 测试

```python
from starrocks_lineage_handler import add_starrocks_lineage_from_dolphin

sql = """
INSERT INTO dsj_dwd.dwd_user_behavior
SELECT 
    user_id,
    event_time,
    event_type
FROM dsj_ods.ods_user_log
WHERE dt = '2024-12-01'
"""

success = add_starrocks_lineage_from_dolphin(
    service_name='uat-starrocks',
    database_name='default',
    sql=sql,
    project_name='数据中台',
    task_name='用户行为分析'
)

print(f"结果: {'成功' if success else '失败'}")
```

### 运行测试套件

```bash
python test_starrocks_lineage.py
```

---

## 常见场景

### 场景 1: 只提取 DolphinScheduler 血缘

```python
from execute_lineage_v2 import LineageExtractor

extractor = LineageExtractor()
extractor.run(platforms=['dolphinscheduler'])
```

### 场景 2: 处理单个 DolphinScheduler 项目

```python
import get_etl_add_lineage

ds = get_etl_add_lineage.GetDolphinSchedulerData()
projects = ds.get_projects_list()

# 只处理特定项目
for project in projects:
    if project['name'] == '数据中台':
        tasks = ds.get_app_list(project['code'])
        for task in tasks:
            ds.get_task(
                project_code=project['code'],
                task_code=task['taskCode'],
                description=f"项目: {project['name']}"
            )
```

### 场景 3: 批量注册数据库服务

```bash
python open_metadata_db_info.py
```

---

## 定时任务配置

### Linux Crontab

```bash
# 编辑 crontab
crontab -e

# 每天凌晨 2 点执行
0 2 * * * /usr/local/bin/python3 /path/to/execute_lineage_v2.py >> /path/to/lineage.log 2>&1

# 每 6 小时执行一次
0 */6 * * * /usr/local/bin/python3 /path/to/execute_lineage_v2.py >> /path/to/lineage.log 2>&1
```

### Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每天 02:00
4. 操作：启动程序
   - 程序：`python.exe`
   - 参数：`C:\path\to\execute_lineage_v2.py`
   - 起始于：`C:\path\to\`

---

## 验证血缘

### 在 OpenMetadata 中查看

1. 登录 OpenMetadata Web UI
2. 导航到 Tables
3. 选择目标表
4. 点击 "Lineage" 标签
5. 查看表级和字段级血缘关系

### 使用 API 查询

```python
from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.generated.schema.entity.data.table import Table

# 获取表的血缘
table = metadata.get_by_name(
    entity=Table, 
    fqn='uat-starrocks.default.dsj_dwd.dwd_user_behavior'
)

lineage = metadata.get_lineage_by_id(Table, table.id.root)
print(f"上游表数量: {len(lineage.upstreamEdges)}")
print(f"下游表数量: {len(lineage.downstreamEdges)}")
```

---

## 故障排查

### 问题：连接 OpenMetadata 失败

```bash
# 检查网络连接
curl http://your-openmetadata-server/api/v1/health-check

# 检查 JWT Token 是否有效
# 在 OpenMetadata UI 中重新生成 Token
```

### 问题：找不到数据源

```python
# 检查数据源映射
import open_metadata_lineage
print(open_metadata_lineage.url_service_mapping)

# 添加新的映射
# 在 open_metadata_url_service 表中插入记录
```

### 问题：SQL 解析失败

```python
# 使用 StarRocks 专用处理器
from starrocks_lineage_handler import StarRocksLineageHandler

handler = StarRocksLineageHandler()
cleaned_sql = handler._clean_starrocks_sql(your_sql)
print(f"清理后的 SQL:\n{cleaned_sql}")
```

---

## 下一步

- 📖 阅读 [02-OPTIMIZATION_GUIDE.md](02-OPTIMIZATION_GUIDE.md) 了解详细优化内容
- 📖 阅读 [../README.md](../README.md) 了解完整功能
- 🧪 运行 `test_starrocks_lineage.py` 测试各种场景
- 🔧 根据需要调整 `config.py` 配置
- 📊 在 OpenMetadata 中查看血缘关系

---

## 获取帮助

如遇到问题：
1. 查看日志文件 `lineage_extraction.log`
2. 运行测试脚本验证功能
3. 查看 [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md) 故障排查指南
4. 查看 [02-OPTIMIZATION_GUIDE.md](02-OPTIMIZATION_GUIDE.md) 详细说明
5. 联系数据团队获取支持

---

[← 返回文档目录](README.md) | [返回项目主页](../README.md)
