# -*- coding: utf-8 -*-
import re
import json
from sqllineage.runner import LineageRunner
from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.generated.schema.api.lineage.addLineage import AddLineageRequest
from metadata.generated.schema.type.entityLineage import EntitiesEdge
from metadata.generated.schema.type.entityReference import EntityReference
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import OpenMetadataConnection, AuthProvider
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import OpenMetadataJWTClientConfig
from metadata.generated.schema.entity.data.table import Table
from metadata.generated.schema.entity.data.topic import Topic
from metadata.generated.schema.type.entityLineage import ColumnLineage, LineageDetails
import pymysql
""" 
被 execute_demo.py, get_etl_add_lineage.py 调用的脚本，主要用于数据血缘提取
脚本功能：元数据平台 open_metadata_lineage 添加血缘

数据库表 open_metadata_url_service 用于存储 URL 与服务名称的映射关系
```
CREATE TABLE open_metadata_url_service (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url_pattern VARCHAR(255) NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    UNIQUE INDEX idx_url_pattern (url_pattern)
);
```
"""
arch_config = {
    'host': 'localhost',
    'port': 3306,
    'database': 'my_test',
    'user': 'root',
    'password': '123456'
}

def open_metadata(hostPort: str, jwt_token: str):
    server_config = OpenMetadataConnection(
        hostPort=hostPort,
        authProvider=AuthProvider.openmetadata,
        securityConfig=OpenMetadataJWTClientConfig(jwtToken=jwt_token),
    )
    metadata = OpenMetadata(server_config)
    return metadata

hostPort = "http://192.168.100.214:22173/api"

jwtToken: str = (
"eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImxpbmVhZ2UtYm90Iiwicm9sZXMiOlsiTGluZWFnZUJvdFJvbGUiXSwiZW1haWwiOiJsaW5lYWdlLWJvdEBvcGVuLW1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3NjQ1OTQzNzMsImV4cCI6bnVsbH0.11xQwfZG_zxpAyQ3FUvOAT3sERX1C6fd4DtTPo1Hk9Zi4CuV3da0h6Beazf5RdRupirL00_nsvwhdbYd5sbvkqhwCKAZOR4uY3muKkrqQ8b7T4MLPuK9bSr5oo3P13orJXkjYaX1kSfO-d33TgFDs3FMKT2_f3m3ZGXngK8KQw9p7CYHnmEKSYJaDGdcwKxUm06zr7sUozCFYgg967qRxORhZS9uSGfcONoomReqmtqShiTR0hXREa1cvAfzMVIKAgO-XoDtzwL2tLuEdjCnbOTrh359sHBDMDjgwm2GVyAjimr9sTcM_nsEBhZgwKKAlXotbNEZIuoRe7ixTtGIKQ"
)
