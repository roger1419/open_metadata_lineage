# OpenMetadata 1.10.10 三大功能实现方案

## 总体架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      OpenMetadata 1.10.10                        │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ StarRocks    │  │  FineBI      │  │ DolphinSche- │          │
│  │ 血缘版本管理  │  │  Dashboard   │  │  duler       │          │
│  │              │  │  Connector   │  │  Connector   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                 │
│                            │                                     │
│              ┌─────────────▼─────────────┐                      │
│              │  Unified Lineage Engine   │                      │
│              │  - Version Control        │                      │
│              │  - Graph Management       │                      │
│              │  - Entity Relations       │                      │
│              └───────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 功能一：StarRocks 表血缘版本控制

### 1.1 需求分析

**目标**：
- 支持基于最新 SQL 代码解析的血缘版本管理
- 自动去除过期血缘关系
- 仅保留和显示最新版本的血缘
- 可选保留历史版本用于审计

**关键挑战**：
- OpenMetadata 原生不支持血缘版本概念
- 需要识别和删除过期的血缘边
- 需要处理并发更新的情况

### 1.2 技术方案

#### 方案 A：基于 ChangeVersion 的版本管理（推荐）

OpenMetadata 的实体自带版本控制（major.minor格式），我们利用这个机制实现血缘版本管理。

**实现步骤**：

**Step 1：扩展血缘元数据模型**

为每条血缘边添加版本标识：

```python
from metadata.generated.schema.api.lineage.addLineage import AddLineageRequest
from metadata.generated.schema.type.entityLineage import EntitiesEdge
from datetime import datetime

class LineageVersionManager:
    """血缘版本管理器"""
    
    def __init__(self, metadata_client):
        self.metadata = metadata_client
        self.version_tag_name = "lineage_version"
        self.created_at_tag = "lineage_created_at"
        
    def create_versioned_lineage(
        self,
        from_entity_fqn: str,
        to_entity_fqn: str,
        sql_query: str,
        version_id: str = None
    ):
        """
        创建带版本信息的血缘关系
        
        Args:
            from_entity_fqn: 源表FQN
            to_entity_fqn: 目标表FQN
            sql_query: SQL查询语句
            version_id: 版本标识（默认使用时间戳）
        """
        if not version_id:
            version_id = datetime.now().strftime("%Y%m%d%H%M%S")
            
        # 构建血缘请求
        lineage_request = AddLineageRequest(
            edge={
                "fromEntity": {
                    "id": self._get_entity_id(from_entity_fqn),
                    "type": "table"
                },
                "toEntity": {
                    "id": self._get_entity_id(to_entity_fqn),
                    "type": "table"
                },
                "lineageDetails": {
                    "sqlQuery": sql_query,
                    "source": "StarRocks",
                    "description": f"Version: {version_id}"
                }
            }
        )
        
        # 添加版本标签
        self._add_version_tags(from_entity_fqn, to_entity_fqn, version_id)
        
        return self.metadata.add_lineage(lineage_request)
```

**Step 2：实现过期血缘清理**

```python
from metadata.generated.schema.type.entityReference import EntityReference

class LineageVersionManager:
    
    def cleanup_outdated_lineage(
        self,
        target_table_fqn: str,
        keep_latest_only: bool = True,
        keep_history_count: int = 0
    ):
        """
        清理过期血缘关系
        
        Args:
            target_table_fqn: 目标表FQN
            keep_latest_only: 是否仅保留最新版本
            keep_history_count: 保留的历史版本数量（0表示不保留）
        """
        # 1. 获取目标表的所有上游血缘
        table_entity = self.metadata.get_by_name(
            entity=Table,
            fqn=target_table_fqn
        )
        
        lineage = self.metadata.get_lineage_by_id(
            entity=Table,
            entity_id=str(table_entity.id),
            up_depth=1,
            down_depth=0
        )
        
        # 2. 按版本分组血缘边
        version_groups = self._group_lineage_by_version(lineage)
        
        # 3. 确定要删除的血缘
        if keep_latest_only:
            versions_to_keep = self._get_latest_versions(
                version_groups, 
                count=1 + keep_history_count
            )
        else:
            versions_to_keep = list(version_groups.keys())
            
        # 4. 删除过期血缘
        for version, edges in version_groups.items():
            if version not in versions_to_keep:
                for edge in edges:
                    self._delete_lineage_edge(edge)
                    
        return {
            "total_versions": len(version_groups),
            "kept_versions": len(versions_to_keep),
            "deleted_count": sum(
                len(edges) 
                for v, edges in version_groups.items() 
                if v not in versions_to_keep
            )
        }
    
    def _delete_lineage_edge(self, edge: EntitiesEdge):
        """删除单条血缘边"""
        # OpenMetadata API 调用
        self.metadata.delete_lineage(
            from_entity=edge.fromEntity,
            to_entity=edge.toEntity
        )
```

**Step 3：完整的更新流程**

```python
class StarRocksLineageSync:
    """StarRocks 血缘同步服务"""
    
    def __init__(self, metadata_client, starrocks_conn):
        self.metadata = metadata_client
        self.starrocks = starrocks_conn
        self.version_manager = LineageVersionManager(metadata_client)
        
    def sync_table_lineage(self, table_fqn: str):
        """
        同步单个表的最新血缘
        
        完整流程：
        1. 从 StarRocks 解析最新 SQL
        2. 清理旧血缘
        3. 写入新血缘
        """
        # 1. 解析 StarRocks 表的 CREATE VIEW 或依赖关系
        lineage_data = self._parse_starrocks_lineage(table_fqn)
        
        if not lineage_data:
            return {"status": "no_lineage", "table": table_fqn}
        
        # 2. 生成新版本号
        new_version = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # 3. 清理旧版本（保留最新1个版本）
        cleanup_result = self.version_manager.cleanup_outdated_lineage(
            target_table_fqn=table_fqn,
            keep_latest_only=True,
            keep_history_count=0  # 改为1可以保留上一个版本
        )
        
        # 4. 写入新血缘
        new_edges = []
        for upstream_table, sql_query in lineage_data.items():
            edge = self.version_manager.create_versioned_lineage(
                from_entity_fqn=upstream_table,
                to_entity_fqn=table_fqn,
                sql_query=sql_query,
                version_id=new_version
            )
            new_edges.append(edge)
            
        return {
            "status": "success",
            "table": table_fqn,
            "version": new_version,
            "cleanup": cleanup_result,
            "new_edges_count": len(new_edges)
        }
```

#### 方案 B：基于自定义属性的版本标记（备选）

如果需要更灵活的版本管理，可以使用 OpenMetadata 的自定义属性功能。

```python
# 在 Table Entity 上添加自定义属性
custom_properties = {
    "lineage_version": "20250107120000",
    "lineage_last_updated": "2025-01-07T12:00:00Z",
    "lineage_sql_hash": "abc123..."  # SQL的哈希值，用于检测变化
}

# 通过 PATCH API 更新
self.metadata.patch_custom_property(
    entity=Table,
    entity_id=table_id,
    properties=custom_properties
)
```

### 1.3 部署配置

**Docker Compose 配置示例**：

```yaml
services:
  lineage-sync:
    image: python:3.10
    volumes:
      - ./lineage_sync:/app
    environment:
      - OPENMETADATA_URL=http://openmetadata:8585/api
      - STARROCKS_HOST=starrocks
      - STARROCKS_PORT=9030
    command: python /app/sync_service.py
    depends_on:
      - openmetadata
```

**定时任务配置**：

```python
# cron_config.py
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()

# 每天凌晨2点同步所有表血缘
@scheduler.scheduled_job('cron', hour=2, minute=0)
def daily_full_sync():
    sync_service = StarRocksLineageSync(metadata, starrocks)
    all_tables = get_all_starrocks_tables()
    
    for table_fqn in all_tables:
        sync_service.sync_table_lineage(table_fqn)

scheduler.start()
```

### 1.4 测试验证

```python
def test_lineage_version_control():
    # 1. 创建初始血缘
    sync_service.sync_table_lineage("starrocks.db.target_table")
    
    # 2. 验证血缘存在
    lineage = metadata.get_lineage_by_name(
        entity=Table,
        fqn="starrocks.db.target_table"
    )
    assert len(lineage.upstreamEdges) > 0
    
    # 3. 模拟 SQL 变更，再次同步
    # ... 修改 StarRocks 视图定义 ...
    
    sync_service.sync_table_lineage("starrocks.db.target_table")
    
    # 4. 验证旧血缘已删除，新血缘已创建
    new_lineage = metadata.get_lineage_by_name(
        entity=Table,
        fqn="starrocks.db.target_table"
    )
    
    # 应该只有新版本的血缘
    assert all(
        "20250107" in edge.description 
        for edge in new_lineage.upstreamEdges
    )
```

---

## 功能二：FineBI 报表元数据集成

### 2.1 需求分析

**目标**：
- 导入 FineBI 报表（Dashboard）元数据
- 解析 FineBI 使用的数据集定义
- 打通 FineBI Dashboard → Dataset → StarRocks Table 的完整血缘链路

**技术路线选择**：
- **优先方案**：基于 OpenMetadata Dashboard Services 开发自定义 FineBI Connector
- **备选方案**：使用 FineBI API + 自定义 Ingestion 脚本

### 2.2 技术方案

#### 方案 A：开发自定义 FineBI Dashboard Connector（推荐）

参考 OpenMetadata 官方的 Tableau、Superset 等 Dashboard Connector 实现方式。

**实现步骤**：

**Step 1：创建 FineBI Connector 项目结构**

```
finebi-connector/
├── connector/
│   ├── __init__.py
│   ├── finebi_connector.py          # 核心连接器
│   ├── finebi_client.py              # FineBI API 客户端
│   └── models.py                     # 数据模型
├── setup.py
├── requirements.txt
└── Dockerfile
```

**Step 2：实现 FineBI API 客户端**

```python
# connector/finebi_client.py
import requests
from typing import List, Dict, Any
import json

class FineBIClient:
    """FineBI REST API 客户端"""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self._authenticate(username, password)
        
    def _authenticate(self, username: str, password: str):
        """
        登录 FineBI 获取认证令牌
        基于 FineBI API 文档: /login/cross/domain
        """
        login_url = f"{self.base_url}/login/cross/domain"
        params = {
            "fine_username": username,
            "fine_password": password,
            "validity": -1
        }
        
        response = self.session.get(login_url, params=params)
        response.raise_for_status()
        
        # 从响应中提取 token
        # FineBI 使用 fine_auth_token 或 authorization 头
        self.token = response.cookies.get('fine_auth_token')
        if self.token:
            self.session.headers['fine_auth_token'] = self.token
            
    def get_dashboards(self) -> List[Dict[str, Any]]:
        """
        获取所有仪表板列表
        需要通过 FineBI 资源导出 API 或直接查询数据库
        """
        # 方法1: 使用资源导出 API
        # 根据 FineBI 文档，可能需要通过系统管理接口
        
        # 方法2: 直接查询 FineBI 的 MySQL/PostgreSQL 数据库
        # 表名通常为: fine_* 前缀
        dashboards = self._query_metadata_db(
            "SELECT * FROM fine_dashboard WHERE status = 'active'"
        )
        
        return dashboards
    
    def get_dashboard_datasets(self, dashboard_id: str) -> List[Dict[str, Any]]:
        """
        获取仪表板使用的数据集
        解析仪表板配置，提取数据集引用
        """
        dashboard = self._get_dashboard_detail(dashboard_id)
        
        datasets = []
        # 解析 dashboard JSON 配置
        config = json.loads(dashboard.get('config', '{}'))
        
        # FineBI 组件通常在 'components' 或 'widgets' 字段
        for component in config.get('components', []):
            dataset_ref = component.get('datasetId') or component.get('dataSource')
            if dataset_ref:
                dataset_info = self._get_dataset_info(dataset_ref)
                datasets.append(dataset_info)
                
        return datasets
    
    def _get_dataset_info(self, dataset_id: str) -> Dict[str, Any]:
        """
        获取数据集详细信息
        包括数据集使用的数据连接和表
        """
        # 查询 FineBI 数据集表
        dataset = self._query_metadata_db(
            f"SELECT * FROM fine_dataset WHERE id = '{dataset_id}'"
        )
        
        # 解析 SQL 数据集的查询语句
        if dataset.get('type') == 'SQL':
            sql_query = dataset.get('sql_statement')
            # 从 SQL 中提取表名
            tables = self._parse_tables_from_sql(sql_query)
            dataset['source_tables'] = tables
            
        return dataset
    
    def _query_metadata_db(self, sql: str) -> Any:
        """
        直接查询 FineBI 元数据数据库
        需要单独配置数据库连接
        """
        # 这里需要配置 FineBI 使用的数据库连接
        # 通常是 MySQL 或 PostgreSQL
        pass
```

**Step 3：实现 OpenMetadata Connector**

```python
# connector/finebi_connector.py
from metadata.ingestion.api.steps import Source
from metadata.ingestion.api.models import Either
from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.generated.schema.entity.services.dashboardService import (
    DashboardService,
    DashboardServiceType
)
from metadata.generated.schema.entity.data.dashboard import Dashboard
from metadata.generated.schema.entity.data.chart import Chart
from metadata.generated.schema.api.data.createDashboard import CreateDashboardRequest
from metadata.generated.schema.api.data.createChart import CreateChartRequest
from typing import Iterable, Optional

class FineBIConnector(Source):
    """FineBI Dashboard Service Connector for OpenMetadata"""
    
    def __init__(self, config, metadata: OpenMetadata):
        super().__init__()
        self.config = config
        self.metadata = metadata
        
        # 初始化 FineBI 客户端
        service_config = config.serviceConnection.config
        self.finebi_client = FineBIClient(
            base_url=service_config.hostPort,
            username=service_config.username,
            password=service_config.password
        )
        
    @classmethod
    def create(cls, config_dict, metadata, pipeline_name=None):
        config = WorkflowSource.parse_obj(config_dict)
        return cls(config, metadata)
    
    def prepare(self):
        """准备工作：验证连接"""
        pass
    
    def _iter(self) -> Iterable[Either]:
        """
        主要迭代逻辑：
        1. 创建 Dashboard Service
        2. 获取所有 Dashboards
        3. 为每个 Dashboard 创建 Charts
        4. 建立 Dashboard → Dataset → Table 的血缘
        """
        # 1. 创建 Dashboard Service
        yield from self.yield_create_request_dashboard_service()
        
        # 2. 获取并处理所有仪表板
        dashboards = self.finebi_client.get_dashboards()
        
        for dashboard_data in dashboards:
            # 创建 Dashboard Entity
            yield from self.yield_dashboard(dashboard_data)
            
            # 创建 Charts
            yield from self.yield_dashboard_charts(dashboard_data)
            
            # 建立血缘关系
            yield from self.yield_dashboard_lineage(dashboard_data)
    
    def yield_dashboard(self, dashboard_data: Dict) -> Iterable[Either]:
        """创建 Dashboard Entity"""
        dashboard_request = CreateDashboardRequest(
            name=dashboard_data['name'],
            displayName=dashboard_data.get('display_name'),
            description=dashboard_data.get('description'),
            dashboardUrl=f"{self.finebi_client.base_url}/dashboard/{dashboard_data['id']}",
            service=self.config.serviceName,
            charts=[],  # 稍后添加
            owner=self._get_owner_ref(dashboard_data.get('owner'))
        )
        
        yield Either(right=dashboard_request)
    
    def yield_dashboard_lineage(self, dashboard_data: Dict) -> Iterable[Either]:
        """
        建立血缘关系：Dashboard → Dataset → Table
        这是核心功能
        """
        dashboard_fqn = f"{self.config.serviceName}.{dashboard_data['name']}"
        
        # 获取 Dashboard 使用的数据集
        datasets = self.finebi_client.get_dashboard_datasets(dashboard_data['id'])
        
        for dataset in datasets:
            # 对于每个数据集，找到其对应的源表
            for source_table in dataset.get('source_tables', []):
                # 构建 Table FQN (需要匹配 StarRocks 表的 FQN)
                table_fqn = self._construct_table_fqn(source_table)
                
                # 创建血缘关系
                lineage_request = AddLineageRequest(
                    edge={
                        "fromEntity": {
                            "fqn": table_fqn,
                            "type": "table"
                        },
                        "toEntity": {
                            "fqn": dashboard_fqn,
                            "type": "dashboard"
                        },
                        "lineageDetails": {
                            "sqlQuery": dataset.get('sql_statement'),
                            "source": "FineBI"
                        }
                    }
                )
                
                yield Either(right=lineage_request)
    
    def _construct_table_fqn(self, table_ref: Dict) -> str:
        """
        构建表的 FQN，需要与 StarRocks 中的表匹配
        格式: service_name.database.schema.table
        """
        # 从 FineBI 数据连接信息中提取
        connection_name = table_ref.get('connection_name')
        database = table_ref.get('database')
        table = table_ref.get('table')
        
        # 需要映射到 OpenMetadata 中的 StarRocks Service
        return f"starrocks_service.{database}.{table}"
```

**Step 4：配置文件定义**

```json
{
  "source": {
    "type": "finebi",
    "serviceName": "finebi_production",
    "serviceConnection": {
      "config": {
        "type": "CustomDashboard",
        "hostPort": "http://finebi.company.com",
        "username": "admin",
        "password": "${FINEBI_PASSWORD}",
        "databaseServiceNames": ["starrocks_service"]
      }
    },
    "sourceConfig": {
      "config": {
        "type": "DashboardMetadata",
        "dashboardFilterPattern": {
          "includes": ["production_.*"]
        }
      }
    }
  },
  "sink": {
    "type": "metadata-rest",
    "config": {}
  },
  "workflowConfig": {
    "openMetadataServerConfig": {
      "hostPort": "http://localhost:8585/api",
      "authProvider": "openmetadata"
    }
  }
}
```

**Step 5：Docker 镜像构建**

```dockerfile
FROM openmetadata/ingestion:1.10.10

WORKDIR /app

# 安装 FineBI Connector
COPY connector connector/
COPY setup.py .
COPY requirements.txt .

RUN pip install --no-deps .

# 设置入口点
ENTRYPOINT ["metadata"]
```

#### 方案 B：FineBI 数据库直连方案（快速实现）

如果 FineBI API 不够完善，可以直接连接 FineBI 的元数据数据库。

```python
# 直接查询 FineBI 元数据库
import pymysql

class FineBIMetadataExtractor:
    def __init__(self, db_config):
        self.conn = pymysql.connect(**db_config)
        
    def extract_dashboard_metadata(self):
        """从 FineBI 数据库提取元数据"""
        with self.conn.cursor() as cursor:
            # 查询仪表板
            cursor.execute("""
                SELECT id, name, description, owner_id, create_time
                FROM fine_dashboard
                WHERE status = 1
            """)
            dashboards = cursor.fetchall()
            
            # 查询数据集
            cursor.execute("""
                SELECT d.id, d.name, d.sql_statement, d.connection_id
                FROM fine_dataset d
                JOIN fine_dashboard_dataset dd ON d.id = dd.dataset_id
                WHERE dd.dashboard_id IN (%s)
            """ % ','.join([str(d[0]) for d in dashboards]))
            datasets = cursor.fetchall()
            
        return dashboards, datasets
```

### 2.3 部署与运行

```bash
# 1. 构建镜像
docker build -t finebi-connector:latest .

# 2. 运行 ingestion
docker run --rm \
  -v $(pwd)/config.json:/config.json \
  finebi-connector:latest \
  ingest -c /config.json

# 3. 在 OpenMetadata UI 中查看
# Dashboard Services → FineBI → Dashboards
```

---

## 功能三：DolphinScheduler 工作流集成

### 3.1 需求分析

**目标**：
- 导入 DolphinScheduler 已上线工作流的元数据
- 解析工作流中的任务节点
- 建立 Workflow → Task → Table 的血缘关系

**技术选择**：
- **优先方案**：使用 DolphinScheduler REST API + OpenMetadata Pipeline Service
- **增强方案**：集成 OpenLineage 实现实时血缘捕获

### 3.2 技术方案

#### 方案 A：基于 REST API 的静态元数据导入

**Step 1：DolphinScheduler API 客户端**

```python
# dolphinscheduler_client.py
import requests
from typing import List, Dict, Any

class DolphinSchedulerClient:
    """DolphinScheduler REST API 客户端"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "token": token,
            "Content-Type": "application/json"
        }
        
    def get_projects(self) -> List[Dict]:
        """获取所有项目"""
        url = f"{self.base_url}/projects"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()['data']['totalList']
    
    def get_process_definitions(self, project_code: str) -> List[Dict]:
        """
        获取项目下的所有工作流定义
        API: /projects/{projectCode}/process-definition
        """
        url = f"{self.base_url}/projects/{project_code}/process-definition"
        params = {
            "pageSize": 1000,
            "pageNo": 1,
            "searchVal": ""
        }
        
        all_workflows = []
        while True:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()['data']
            
            all_workflows.extend(data['totalList'])
            
            if params['pageNo'] * params['pageSize'] >= data['total']:
                break
            params['pageNo'] += 1
            
        # 过滤仅返回已上线的工作流
        return [
            wf for wf in all_workflows 
            if wf.get('releaseState') == 'ONLINE'
        ]
    
    def get_process_definition_detail(
        self, 
        project_code: str, 
        workflow_code: str
    ) -> Dict:
        """
        获取工作流详细定义（包含任务节点）
        API: /projects/{projectCode}/process-definition/{code}
        """
        url = f"{self.base_url}/projects/{project_code}/process-definition/{workflow_code}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()['data']
    
    def get_task_definitions(
        self, 
        project_code: str, 
        workflow_code: str
    ) -> List[Dict]:
        """
        获取工作流的任务定义
        解析工作流 JSON，提取任务节点
        """
        workflow = self.get_process_definition_detail(project_code, workflow_code)
        
        # 解析任务定义（通常在 processDefinitionJson 字段）
        import json
        process_json = json.loads(workflow.get('processDefinitionJson', '{}'))
        
        tasks = []
        for task in process_json.get('tasks', []):
            task_info = {
                "code": task.get('code'),
                "name": task.get('name'),
                "type": task.get('type'),
                "params": task.get('params', {}),
                "preTasks": task.get('preTasks', [])  # 依赖关系
            }
            
            # 解析任务使用的数据源
            if task.get('type') in ['SQL', 'SPARK', 'PYTHON']:
                task_info['datasources'] = self._extract_datasources_from_task(task)
                task_info['sql_statements'] = self._extract_sql_from_task(task)
            
            tasks.append(task_info)
            
        return tasks
    
    def _extract_datasources_from_task(self, task: Dict) -> List[str]:
        """从任务参数中提取数据源信息"""
        datasources = []
        params = task.get('params', {})
        
        # SQL 类型任务
        if task.get('type') == 'SQL':
            datasource_id = params.get('datasource')
            if datasource_id:
                datasources.append(datasource_id)
        
        # Spark 任务
        elif task.get('type') == 'SPARK':
            # 从 Spark 配置中提取
            main_class = params.get('mainClass', '')
            main_args = params.get('mainArgs', '')
            # 解析参数中的表名
            
        return datasources
    
    def _extract_sql_from_task(self, task: Dict) -> List[str]:
        """提取任务中的 SQL 语句"""
        sqls = []
        params = task.get('params', {})
        
        if task.get('type') == 'SQL':
            sql = params.get('sql', '')
            if sql:
                sqls.append(sql)
        
        return sqls
```

**Step 2：OpenMetadata Pipeline Connector 实现**

```python
# dolphinscheduler_connector.py
from metadata.ingestion.api.steps import Source
from metadata.ingestion.api.models import Either
from metadata.generated.schema.entity.services.pipelineService import (
    PipelineService,
    PipelineServiceType
)
from metadata.generated.schema.entity.data.pipeline import Pipeline, Task
from metadata.generated.schema.api.data.createPipeline import CreatePipelineRequest
from metadata.generated.schema.type.entityLineage import EntitiesEdge
from typing import Iterable, List

class DolphinSchedulerConnector(Source):
    """DolphinScheduler Pipeline Connector for OpenMetadata"""
    
    def __init__(self, config, metadata):
        super().__init__()
        self.config = config
        self.metadata = metadata
        
        service_config = config.serviceConnection.config
        self.ds_client = DolphinSchedulerClient(
            base_url=service_config.hostPort,
            token=service_config.token
        )
        
    def _iter(self) -> Iterable[Either]:
        """
        主要迭代逻辑：
        1. 创建 Pipeline Service
        2. 获取所有项目
        3. 为每个项目获取已上线工作流
        4. 创建 Pipeline 和 Task Entities
        5. 建立血缘关系
        """
        # 1. 创建 Pipeline Service
        yield from self.yield_pipeline_service()
        
        # 2. 获取所有项目
        projects = self.ds_client.get_projects()
        
        for project in projects:
            # 3. 获取项目下的已上线工作流
            workflows = self.ds_client.get_process_definitions(
                project['code']
            )
            
            for workflow in workflows:
                # 4. 创建 Pipeline Entity
                yield from self.yield_pipeline(project, workflow)
                
                # 5. 建立血缘关系
                yield from self.yield_pipeline_lineage(project, workflow)
    
    def yield_pipeline(self, project: Dict, workflow: Dict) -> Iterable[Either]:
        """创建 Pipeline Entity"""
        # 获取工作流详细信息
        workflow_detail = self.ds_client.get_process_definition_detail(
            project['code'],
            workflow['code']
        )
        
        # 获取任务列表
        tasks = self.ds_client.get_task_definitions(
            project['code'],
            workflow['code']
        )
        
        # 构建 Task 对象
        task_entities = []
        for task in tasks:
            task_entity = Task(
                name=task['name'],
                displayName=task['name'],
                taskType=task['type'],
                taskUrl=self._construct_task_url(project['code'], workflow['code'], task['code']),
                downstreamTasks=[]  # 稍后填充
            )
            task_entities.append(task_entity)
        
        # 填充任务依赖关系
        for i, task in enumerate(tasks):
            downstream_tasks = [
                tasks[j]['name'] 
                for j, t in enumerate(tasks)
                if task['code'] in t.get('preTasks', [])
            ]
            task_entities[i].downstreamTasks = downstream_tasks
        
        # 创建 Pipeline Request
        pipeline_request = CreatePipelineRequest(
            name=workflow['name'],
            displayName=workflow['name'],
            description=workflow.get('description'),
            pipelineUrl=self._construct_pipeline_url(project['code'], workflow['code']),
            service=self.config.serviceName,
            tasks=task_entities,
            tags=self._extract_tags(workflow)
        )
        
        yield Either(right=pipeline_request)
    
    def yield_pipeline_lineage(self, project: Dict, workflow: Dict) -> Iterable[Either]:
        """
        建立血缘关系：Pipeline/Task → Table
        这是核心功能
        """
        tasks = self.ds_client.get_task_definitions(
            project['code'],
            workflow['code']
        )
        
        pipeline_fqn = f"{self.config.serviceName}.{workflow['name']}"
        
        for task in tasks:
            task_fqn = f"{pipeline_fqn}.{task['name']}"
            
            # 解析任务使用的 SQL，提取表依赖
            for sql in task.get('sql_statements', []):
                table_deps = self._parse_tables_from_sql(sql)
                
                for table_fqn in table_deps:
                    # 创建 Table → Task 的血缘
                    lineage_request = AddLineageRequest(
                        edge={
                            "fromEntity": {
                                "fqn": table_fqn,
                                "type": "table"
                            },
                            "toEntity": {
                                "fqn": task_fqn,
                                "type": "pipeline"
                            },
                            "lineageDetails": {
                                "sqlQuery": sql,
                                "source": "DolphinScheduler"
                            }
                        }
                    )
                    
                    yield Either(right=lineage_request)
    
    def _parse_tables_from_sql(self, sql: str) -> List[str]:
        """
        从 SQL 中解析表名
        使用 sqlparse 或 sqlglot
        """
        import sqlglot
        
        tables = []
        try:
            parsed = sqlglot.parse_one(sql, dialect='starrocks')
            for table in parsed.find_all(sqlglot.exp.Table):
                db = table.db or 'default'
                tbl = table.name
                # 构建 FQN: service.database.table
                table_fqn = f"starrocks_service.{db}.{tbl}"
                tables.append(table_fqn)
        except Exception as e:
            print(f"Failed to parse SQL: {e}")
            
        return tables
    
    def _construct_pipeline_url(self, project_code: str, workflow_code: str) -> str:
        """构建工作流 URL"""
        return f"{self.ds_client.base_url}/projects/{project_code}/workflow/definitions/{workflow_code}"
    
    def _construct_task_url(self, project_code: str, workflow_code: str, task_code: str) -> str:
        """构建任务 URL"""
        return f"{self.ds_client.base_url}/projects/{project_code}/workflow/definitions/{workflow_code}/tasks/{task_code}"
```

**Step 3：配置文件**

```json
{
  "source": {
    "type": "dolphinscheduler",
    "serviceName": "dolphinscheduler_production",
    "serviceConnection": {
      "config": {
        "type": "Pipeline",
        "hostPort": "http://dolphinscheduler.company.com:12345/dolphinscheduler",
        "token": "${DS_API_TOKEN}"
      }
    },
    "sourceConfig": {
      "config": {
        "type": "PipelineMetadata",
        "pipelineFilterPattern": {
          "includes": [".*"]
        },
        "includeLineage": true
      }
    }
  },
  "sink": {
    "type": "metadata-rest",
    "config": {}
  },
  "workflowConfig": {
    "openMetadataServerConfig": {
      "hostPort": "http://localhost:8585/api",
      "authProvider": "openmetadata",
      "securityConfig": {
        "jwtToken": "${OM_JWT_TOKEN}"
      }
    }
  }
}
```

#### 方案 B：基于 OpenLineage 的实时血缘捕获（增强方案）

DolphinScheduler 3.x+ 版本支持 OpenLineage 集成，可以实现实时血缘捕获。

**配置步骤**：

**Step 1：启用 DolphinScheduler OpenLineage 插件**

```yaml
# dolphinscheduler/conf/common.properties
# 启用 OpenLineage
lineage.enable=true

# OpenLineage 配置
openlineage.transport.type=http
openlineage.transport.url=http://openmetadata:8585/api/v1/lineage/openlineage
openlineage.namespace=dolphinscheduler_production
```

**Step 2：配置 OpenMetadata 接收 OpenLineage 事件**

OpenMetadata 原生支持 OpenLineage，只需确保相关服务已启用：

```yaml
# openmetadata.yaml
pipelineServiceClientConfiguration:
  enabled: true
  className: "org.openmetadata.service.clients.pipeline.OpenLineageClient"
  parameters:
    ingestionIpInfoEnabled: false
```

**Step 3：验证集成**

```python
# 运行一个 DolphinScheduler 工作流
# 自动发送 OpenLineage 事件到 OpenMetadata

# 在 OpenMetadata UI 中查看实时血缘
# Pipelines → DolphinScheduler → [Workflow Name] → Lineage Tab
```

### 3.3 完整血缘链路示例

整合所有三个功能后的血缘链路：

```
StarRocks Table (source_table)
       ↓ (版本化血缘)
StarRocks Table (target_table)
       ↓ (DolphinScheduler Task 使用)
DolphinScheduler Task (etl_task)
       ↓ (属于)
DolphinScheduler Workflow (daily_etl)
       ↓ (产出数据)
StarRocks Table (result_table)
       ↓ (FineBI 数据集使用)
FineBI Dataset (sales_dataset)
       ↓ (Dashboard 使用)
FineBI Dashboard (sales_report)
```

在 OpenMetadata UI 中，可以看到完整的端到端血缘图谱。

---

## 测试与验证计划

### 阶段 1：StarRocks 血缘版本控制测试

**测试用例**：

1. **基础功能测试**
   ```python
   def test_basic_versioning():
       # 创建初始血缘
       sync_service.sync_table_lineage("db.table_a")
       
       # 验证血缘存在
       lineage = get_lineage("db.table_a")
       assert len(lineage.upstreamEdges) > 0
       
       # 修改 SQL，再次同步
       # (模拟 StarRocks 视图定义变更)
       sync_service.sync_table_lineage("db.table_a")
       
       # 验证只有最新版本
       new_lineage = get_lineage("db.table_a")
       versions = extract_versions(new_lineage)
       assert len(versions) == 1
   ```

2. **并发更新测试**
   ```python
   def test_concurrent_updates():
       import threading
       
       def update_lineage():
           sync_service.sync_table_lineage("db.table_b")
       
       threads = [threading.Thread(target=update_lineage) for _ in range(5)]
       for t in threads:
           t.start()
       for t in threads:
           t.join()
       
       # 验证数据一致性
       lineage = get_lineage("db.table_b")
       assert is_consistent(lineage)
   ```

3. **历史版本保留测试**
   ```python
   def test_history_retention():
       # 配置保留 2 个历史版本
       sync_service.sync_with_history(
           "db.table_c",
           keep_history_count=2
       )
       
       # 触发 3 次更新
       for i in range(3):
           modify_sql()
           sync_service.sync_table_lineage("db.table_c")
       
       # 验证有 3 个版本（1个最新 + 2个历史）
       versions = get_all_versions("db.table_c")
       assert len(versions) == 3
   ```

**验收标准**：
- ✅ 新血缘能正确创建
- ✅ 旧血缘能正确删除
- ✅ 版本号正确递增
- ✅ 并发更新不产生脏数据
- ✅ 历史版本保留策略生效

---

### 阶段 2：FineBI 元数据导入测试

**测试用例**：

1. **Dashboard 创建测试**
   ```bash
   # 运行 ingestion
   metadata ingest -c finebi_config.json
   
   # 在 OpenMetadata UI 验证
   # Dashboard Services → FineBI → Dashboards
   # 应该能看到所有 FineBI 仪表板
   ```

2. **血缘关系测试**
   ```python
   def test_finebi_lineage():
       # 获取一个 Dashboard
       dashboard = metadata.get_by_name(
           entity=Dashboard,
           fqn="finebi_service.sales_dashboard"
       )
       
       # 获取其血缘
       lineage = metadata.get_lineage_by_id(
           entity=Dashboard,
           entity_id=dashboard.id,
           up_depth=2
       )
       
       # 验证能追溯到 StarRocks 表
       upstream_tables = extract_upstream_tables(lineage)
       assert "starrocks_service.db.sales_table" in upstream_tables
   ```

3. **数据集解析测试**
   ```python
   def test_dataset_parsing():
       # 验证 FineBI 数据集中的 SQL 被正确解析
       dashboard = get_dashboard("sales_dashboard")
       datasets = get_dashboard_datasets(dashboard)
       
       for dataset in datasets:
           assert dataset.sql_statement is not None
           assert len(dataset.source_tables) > 0
   ```

**验收标准**：
- ✅ Dashboard 元数据完整导入
- ✅ Chart 信息正确解析
- ✅ Dataset → Table 血缘正确建立
- ✅ SQL 语句正确存储
- ✅ 血缘图谱可视化正常

---

### 阶段 3：DolphinScheduler 工作流集成测试

**测试用例**：

1. **Pipeline 创建测试**
   ```bash
   # 运行 ingestion
   metadata ingest -c dolphinscheduler_config.json
   
   # 验证
   # Pipeline Services → DolphinScheduler → Pipelines
   # 应该只看到已上线的工作流
   ```

2. **Task 级别测试**
   ```python
   def test_pipeline_tasks():
       # 获取一个 Pipeline
       pipeline = metadata.get_by_name(
           entity=Pipeline,
           fqn="dolphinscheduler_service.daily_etl"
       )
       
       # 验证 Task 数量和类型
       assert len(pipeline.tasks) > 0
       assert any(t.taskType == 'SQL' for t in pipeline.tasks)
   ```

3. **完整血缘链路测试**
   ```python
   def test_end_to_end_lineage():
       """
       测试完整链路：
       StarRocks Table → DolphinScheduler Task → FineBI Dashboard
       """
       # 从源表开始
       source_table_fqn = "starrocks_service.db.source_table"
       
       # 获取完整下游血缘
       lineage = metadata.get_lineage_by_name(
           entity=Table,
           fqn=source_table_fqn,
           up_depth=0,
           down_depth=5  # 追溯 5 层
       )
       
       # 验证路径：Table → Task → Pipeline → Dataset → Dashboard
       path = extract_lineage_path(lineage)
       assert 'pipeline' in [e.type for e in path]
       assert 'dashboard' in [e.type for e in path]
   ```

**验收标准**：
- ✅ 仅上线工作流被导入
- ✅ Task 依赖关系正确
- ✅ SQL 任务的表依赖正确解析
- ✅ Pipeline → Table 血缘建立
- ✅ 完整血缘链路可追溯

---

## 实施时间线与里程碑

### Phase 1: StarRocks 血缘版本化（2-3 周）

**Week 1-2: 核心开发**
- [ ] 实现 `LineageVersionManager` 类
- [ ] 实现版本清理逻辑
- [ ] 编写单元测试

**Week 3: 集成测试**
- [ ] 部署到测试环境
- [ ] 运行集成测试
- [ ] 性能测试（处理 1000+ 表）

**Milestone 1**: StarRocks 血缘支持版本化，旧血缘自动清理

---

### Phase 2: FineBI 集成（3-4 周）

**Week 1-2: Connector 开发**
- [ ] 实现 `FineBIClient`
- [ ] 实现 `FineBIConnector`
- [ ] 测试 API 连接

**Week 3: 血缘解析**
- [ ] 实现数据集解析逻辑
- [ ] 实现 SQL 提取和表解析
- [ ] 血缘关系建立

**Week 4: 测试与优化**
- [ ] 集成测试
- [ ] UI 验证
- [ ] 性能优化

**Milestone 2**: FineBI Dashboard 元数据导入，血缘打通

---

### Phase 3: DolphinScheduler 集成（2-3 周）

**Week 1-2: Connector 开发**
- [ ] 实现 `DolphinSchedulerClient`
- [ ] 实现 `DolphinSchedulerConnector`
- [ ] 工作流过滤（仅已上线）

**Week 3: 血缘与测试**
- [ ] Task 级别血缘解析
- [ ] 集成测试
- [ ] OpenLineage 增强（可选）

**Milestone 3**: DolphinScheduler 工作流导入，完整血缘链路建立

---

## 总结与建议

### 技术栈总结

| 功能 | 核心技术 | 难度 | 预计工作量 |
|------|---------|------|-----------|
| StarRocks 血缘版本化 | Python + OpenMetadata API | 中 | 2-3周 |
| FineBI 集成 | Python + FineBI API + Connector Framework | 高 | 3-4周 |
| DolphinScheduler 集成 | Python + DS API + OpenLineage | 中 | 2-3周 |

### 实施优先级建议

**优先级 1 (P0): StarRocks 血缘版本化**
- 理由：这是现有功能的增强，风险最低，能立即提升数据质量
- 建议：先完成此功能，稳定运行后再进行其他集成

**优先级 2 (P1): DolphinScheduler 集成**
- 理由：DolphinScheduler API 相对标准，实施难度适中
- 建议：使用 REST API 方案，后期可考虑 OpenLineage 增强

**优先级 3 (P2): FineBI 集成**
- 理由：需要深入研究 FineBI API 或数据库结构，不确定性较高
- 建议：
  - 先调研 FineBI API 的可用性
  - 如果 API 不完善，考虑直连数据库方案
  - 可以先实现基础功能，逐步完善

### 风险与缓解措施

**风险 1: FineBI API 文档不完善**
- 缓解：准备数据库直连备选方案

**风险 2: 血缘解析 SQL 复杂度高**
- 缓解：使用成熟的 SQL 解析库（sqlglot, sqlparse）

**风险 3: 大规模数据同步性能问题**
- 缓解：实现增量同步、并行处理、分批次处理

**风险 4: OpenMetadata API 限制**
- 缓解：提前验证 API 能力，必要时直接操作数据库

### 长期优化建议

1. **建立统一的血缘管理框架**
   - 抽象通用的血缘解析、版本管理逻辑
   - 支持更多数据源的快速接入

2. **实现增量同步**
   - 基于变更检测（SQL Hash、文件修改时间）
   - 减少全量同步的性能开销

3. **监控与告警**
   - 血缘同步失败告警
   - 血缘断裂检测
   - 血缘质量评分

4. **考虑迁移到 Apache Gravitino**
   - 如果未来需要更强的异构数据源统一管理
   - 或需要支持 AI/ML 资产管理
   - Gravitino 的架构更适合长期扩展

---

## 附录

### 附录 A：关键代码仓库结构

```
openmetadata-extensions/
├── lineage-version-manager/
│   ├── src/
│   │   ├── version_manager.py
│   │   ├── starrocks_sync.py
│   │   └── utils.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── finebi-connector/
│   ├── connector/
│   │   ├── finebi_client.py
│   │   ├── finebi_connector.py
│   │   └── models.py
│   ├── tests/
│   ├── setup.py
│   └── Dockerfile
├── dolphinscheduler-connector/
│   ├── connector/
│   │   ├── ds_client.py
│   │   ├── ds_connector.py
│   │   └── models.py
│   ├── tests/
│   ├── setup.py
│   └── Dockerfile
└── docker-compose.yml
```

### 附录 B：部署架构图

```
┌─────────────────────────────────────────────────────────┐
│                  Docker Compose Stack                    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Lineage Sync │  │ FineBI Conn. │  │ DS Connector │  │
│  │  Container   │  │  Container   │  │  Container   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │          │
│         └──────────────────┴──────────────────┘          │
│                            │                             │
│                  ┌─────────▼─────────┐                  │
│                  │  OpenMetadata     │                  │
│                  │  - API Server     │                  │
│                  │  - MySQL          │                  │
│                  │  - Elasticsearch  │                  │
│                  └───────────────────┘                  │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌───▼────┐         ┌───▼──────┐
   │StarRocks│         │ FineBI │         │Dolphin   │
   │         │         │        │         │Scheduler │
   └─────────┘         └────────┘         └──────────┘
```

### 附录 C：参考资料

1. [OpenMetadata Ingestion Framework](https://docs.open-metadata.org/connectors/ingestion/framework)
2. [OpenMetadata Lineage API](https://docs.open-metadata.org/sdk/python/build-connector/lineage)
3. [DolphinScheduler REST API](https://dolphinscheduler.apache.org/en-us/docs/latest/user_doc/guide/api/api.html)
4. [OpenLineage Specification](https://openlineage.io/docs/spec/overview)
5. [sqlglot Documentation](https://sqlglot.com/)

---

**文档版本**: v1.0  
**最后更新**: 2025-01-07  
**作者**: Claude (Anthropic)  
**审阅状态**: 待技术评审 '