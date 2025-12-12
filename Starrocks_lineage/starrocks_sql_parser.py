#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
StarRocks SQL 解析器 - 独立版本
用于解析 StarRocks SQL 文件并将血缘信息导入到 OpenMetadata
"""

import sys
import os
import re
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import OpenMetadataConnection, AuthProvider
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import OpenMetadataJWTClientConfig
from metadata.generated.schema.api.lineage.addLineage import AddLineageRequest
from metadata.generated.schema.type.entityLineage import EntitiesEdge, ColumnLineage, LineageDetails
from metadata.generated.schema.type.entityReference import EntityReference
from metadata.generated.schema.entity.data.table import Table
from sqllineage.runner import LineageRunner
from sqllineage.core.models import Column


class StarRocksSQLParser:
    """StarRocks SQL 解析器"""
    
    def __init__(self, host_port, jwt_token, service_name, database_name):
        """
        初始化解析器
        
        Args:
            host_port: OpenMetadata 服务器地址
            jwt_token: JWT Token
            service_name: 服务名称
            database_name: 数据库名称
        """
        self.host_port = host_port
        self.jwt_token = jwt_token
        self.service_name = service_name
        self.database_name = database_name
        self.metadata = None
        
    def connect(self):
        """连接到 OpenMetadata"""
        print("正在连接 OpenMetadata...")
        try:
            server_config = OpenMetadataConnection(
                hostPort=self.host_port,
                authProvider=AuthProvider.openmetadata,
                securityConfig=OpenMetadataJWTClientConfig(jwtToken=self.jwt_token),
            )
            self.metadata = OpenMetadata(server_config)
            health = self.metadata.health_check()
            print(f"✅ 连接成功: {health}")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def clean_sql(self, sql):
        """
        清理 SQL，移除 StarRocks 特有语法
        
        Args:
            sql: 原始 SQL
            
        Returns:
            清理后的 SQL
        """
        # 移除注释
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # 替换 INSERT OVERWRITE 为 INSERT INTO
        sql = re.sub(r'\bINSERT\s+OVERWRITE\b', 'INSERT INTO', sql, flags=re.IGNORECASE)
        
        # 移除 PROPERTIES 子句
        sql = re.sub(r'\bPROPERTIES\s*\([^)]*\)', '', sql, flags=re.IGNORECASE)
        
        # 移除 DISTRIBUTED BY 子句
        sql = re.sub(r'\bDISTRIBUTED\s+BY\s+HASH\s*\([^)]*\)\s*BUCKETS\s+\d+', '', sql, flags=re.IGNORECASE)
        
        # 移除 DUPLICATE KEY / AGGREGATE KEY / UNIQUE KEY
        sql = re.sub(r'\b(DUPLICATE|AGGREGATE|UNIQUE)\s+KEY\s*\([^)]*\)', '', sql, flags=re.IGNORECASE)
        
        # 移除 PARTITION BY 子句（如果不是窗口函数的一部分）
        sql = re.sub(r'\bPARTITION\s+BY\s+\([^)]*\)', '', sql, flags=re.IGNORECASE)
        
        return sql.strip()
    
    def parse_sql_file(self, sql_file_path, parse_columns=True):
        """
        解析 SQL 文件
        
        Args:
            sql_file_path: SQL 文件路径
            parse_columns: 是否解析列级血缘
            
        Returns:
            (target_table, source_tables, column_lineage) 或 (None, None, None)
            column_lineage: {target_col: [source_cols]}
        """
        print(f"\n{'='*60}")
        print(f"解析 SQL 文件: {sql_file_path}")
        print(f"{'='*60}")
        
        try:
            # 读取 SQL 文件
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                raw_sql = f.read()
            
            print(f"✓ 读取文件成功，长度: {len(raw_sql)} 字符")
            
            # 清理 SQL
            cleaned_sql = self.clean_sql(raw_sql)
            print(f"✓ SQL 清理完成")
            
            # 使用 sqllineage 解析
            print(f"→ 开始解析血缘关系...")
            try:
                result = LineageRunner(cleaned_sql)
                
                # 获取目标表
                target_tables = list(result.target_tables)
                source_tables = list(result.source_tables)
                
                if not target_tables:
                    print(f"⚠ 未找到目标表")
                    return None, None, None
                
                target_table = str(target_tables[0])
                print(f"✓ 目标表: {target_table}")
                print(f"✓ 源表数量: {len(source_tables)}")
                
                for i, src in enumerate(source_tables, 1):
                    print(f"  [{i}] {src}")
                
                # 解析列级血缘
                column_lineage = {}
                if parse_columns:
                    print(f"\n→ 开始解析列级血缘...")
                    try:
                        # 获取列级血缘 - 使用 column_lineage 属性
                        col_lineage_list = result.get_column_lineage()
                        
                        if col_lineage_list:
                            for item in col_lineage_list:
                                # item 是一个元组 (target_col, source_cols_set)
                                if isinstance(item, tuple) and len(item) == 2:
                                    target_col, source_cols = item
                                    target_col_name = str(target_col).split('.')[-1]  # 获取列名
                                    source_col_list = []
                                    
                                    # source_cols 可能是单个 Column 或 set/list
                                    if isinstance(source_cols, (set, list)):
                                        cols_to_process = source_cols
                                    else:
                                        cols_to_process = [source_cols]
                                    
                                    for src_col in cols_to_process:
                                        # 解析源列：table.column
                                        src_col_str = str(src_col)
                                        if '.' in src_col_str:
                                            parts = src_col_str.rsplit('.', 1)
                                            table_name = parts[0]
                                            col_name = parts[1]
                                            source_col_list.append({
                                                'table': table_name,
                                                'column': col_name
                                            })
                                    
                                    if source_col_list:
                                        column_lineage[target_col_name] = source_col_list
                        
                        print(f"✓ 解析到 {len(column_lineage)} 个目标列的血缘")
                        
                        # 显示前5个列血缘
                        for i, (target_col, sources) in enumerate(list(column_lineage.items())[:5], 1):
                            print(f"  [{i}] {target_col} <- {len(sources)} 个源列")
                        
                        if len(column_lineage) > 5:
                            print(f"  ... 还有 {len(column_lineage) - 5} 个列")
                    
                    except Exception as e:
                        print(f"⚠ 列级血缘解析失败: {e}")
                        import traceback
                        traceback.print_exc()
                        column_lineage = {}
                
                return target_table, [str(s) for s in source_tables], column_lineage
                
            except Exception as e:
                print(f"✗ SQL 解析失败: {e}")
                return None, None, None
                
        except Exception as e:
            print(f"✗ 读取文件失败: {e}")
            return None, None, None
    
    def normalize_table_name(self, table_name, default_schema='ads'):
        """
        规范化表名为 FQN 格式
        
        Args:
            table_name: 表名（可能包含 schema）
            default_schema: 默认 schema
            
        Returns:
            完全限定名: service.database.schema.table
        """
        parts = table_name.split('.')
        
        if len(parts) == 1:
            # 只有表名
            schema = default_schema
            table = parts[0]
        elif len(parts) == 2:
            # schema.table
            schema = parts[0]
            table = parts[1]
        else:
            # 已经是完整格式
            return table_name
        
        fqn = f"{self.service_name}.{self.database_name}.{schema}.{table}"
        return fqn
    
    def get_table_entity(self, table_fqn):
        """
        获取表实体
        
        Args:
            table_fqn: 表的完全限定名
            
        Returns:
            Table 实体或 None
        """
        try:
            table = self.metadata.get_by_name(entity=Table, fqn=table_fqn)
            if table:
                print(f"  ✓ 找到表: {table_fqn}")
                return table
            else:
                print(f"  ✗ 未找到表: {table_fqn}")
                return None
        except Exception as e:
            print(f"  ✗ 获取表失败 {table_fqn}: {e}")
            return None
    
    def get_column_fqn(self, table_entity, column_name):
        """
        获取列的完全限定名
        
        Args:
            table_entity: 表实体
            column_name: 列名
            
        Returns:
            列的 FQN 或 None
        """
        if not table_entity or not table_entity.columns:
            return None
        
        # 在表的列中查找匹配的列
        for col in table_entity.columns:
            col_name = str(col.name.root) if hasattr(col.name, 'root') else str(col.name)
            if col_name.lower() == column_name.lower():
                col_fqn = str(col.fullyQualifiedName.root) if hasattr(col.fullyQualifiedName, 'root') else str(col.fullyQualifiedName)
                return col_fqn
        
        return None
    
    def add_lineage(self, target_table, source_tables, column_lineage=None, description="StarRocks SQL"):
        """
        添加血缘关系到 OpenMetadata（支持列级血缘）
        
        Args:
            target_table: 目标表名
            source_tables: 源表名列表
            column_lineage: 列级血缘 {target_col: [{'table': src_table, 'column': src_col}]}
            description: 血缘描述
            
        Returns:
            成功返回 True，失败返回 False
        """
        print(f"\n{'='*60}")
        print(f"添加血缘关系到 OpenMetadata")
        print(f"{'='*60}")
        
        # 规范化表名
        target_fqn = self.normalize_table_name(target_table)
        print(f"目标表 FQN: {target_fqn}")
        
        # 获取目标表实体
        target_entity = self.get_table_entity(target_fqn)
        if not target_entity:
            print(f"✗ 无法获取目标表实体")
            return False
        
        # 处理源表
        print(f"\n处理源表 ({len(source_tables)} 个):")
        edges = []
        source_entities = {}  # 保存源表实体，用于列级血缘
        
        for src_table in source_tables:
            src_fqn = self.normalize_table_name(src_table)
            src_entity = self.get_table_entity(src_fqn)
            
            if src_entity:
                source_entities[src_table] = src_entity
                edge = EntitiesEdge(
                    fromEntity=EntityReference(
                        id=src_entity.id,
                        type="table"
                    ),
                    toEntity=EntityReference(
                        id=target_entity.id,
                        type="table"
                    )
                )
                edges.append(edge)
        
        if not edges:
            print(f"\n✗ 没有有效的源表，无法创建血缘关系")
            return False
        
        # 处理列级血缘
        column_lineages = []
        if column_lineage and source_entities:
            print(f"\n处理列级血缘 ({len(column_lineage)} 个目标列):")
            
            for target_col, source_cols in column_lineage.items():
                # 获取目标列 FQN
                target_col_fqn = self.get_column_fqn(target_entity, target_col)
                if not target_col_fqn:
                    print(f"  ⚠ 未找到目标列: {target_col}")
                    continue
                
                # 处理源列
                source_col_fqns = []
                for src_col_info in source_cols:
                    src_table = src_col_info['table']
                    src_col = src_col_info['column']
                    
                    # 获取源表实体
                    src_entity = source_entities.get(src_table)
                    if not src_entity:
                        continue
                    
                    # 获取源列 FQN
                    src_col_fqn = self.get_column_fqn(src_entity, src_col)
                    if src_col_fqn:
                        source_col_fqns.append(src_col_fqn)
                
                if source_col_fqns:
                    col_lineage = ColumnLineage(
                        fromColumns=source_col_fqns,
                        toColumn=target_col_fqn
                    )
                    column_lineages.append(col_lineage)
                    print(f"  ✓ {target_col} <- {len(source_col_fqns)} 个源列")
            
            print(f"\n✓ 成功创建 {len(column_lineages)} 个列级血缘")
        
        # 创建血缘请求
        print(f"\n创建血缘关系 ({len(edges)} 条表级边)...")
        try:
            # 添加所有边（带列级血缘）
            for edge in edges:
                # 如果有列级血缘，添加到边中
                if column_lineages:
                    lineage_details = LineageDetails(columnsLineage=column_lineages)
                    edge.lineageDetails = lineage_details
                
                lineage_request = AddLineageRequest(edge=edge)
                self.metadata.add_lineage(lineage_request)
                print(f"  ✓ 添加血缘: {edge.fromEntity.id} -> {edge.toEntity.id}")
            
            print(f"\n✅ 血缘关系添加成功！")
            if column_lineages:
                print(f"   包含 {len(column_lineages)} 个列级血缘")
            return True
            
        except Exception as e:
            print(f"\n✗ 添加血缘失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_sql_file(self, sql_file_path, parse_columns=True, description="StarRocks SQL"):
        """
        处理 SQL 文件：解析并添加血缘
        
        Args:
            sql_file_path: SQL 文件路径
            parse_columns: 是否解析列级血缘
            description: 血缘描述
            
        Returns:
            成功返回 True，失败返回 False
        """
        # 解析 SQL
        target_table, source_tables, column_lineage = self.parse_sql_file(sql_file_path, parse_columns)
        
        if not target_table or not source_tables:
            print(f"\n✗ SQL 解析失败，无法添加血缘")
            return False
        
        # 添加血缘（包含列级血缘）
        return self.add_lineage(target_table, source_tables, column_lineage, description)


def main():
    """主函数"""
    # 配置
    HOST_PORT = "http://192.168.100.214:4728/api"
    JWT_TOKEN = "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImxpbmVhZ2UtYm90Iiwicm9sZXMiOlsiTGluZWFnZUJvdFJvbGUiXSwiZW1haWwiOiJsaW5lYWdlLWJvdEBvcGVuLW1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3NjQ1OTQzNzMsImV4cCI6bnVsbH0.11xQwfZG_zxpAyQ3FUvOAT3sERX1C6fd4DtTPo1Hk9Zi4CuV3da0h6Beazf5RdRupirL00_nsvwhdbYd5sbvkqhwCKAZOR4uY3muKkrqQ8b7T4MLPuK9bSr5oo3P13orJXkjYaX1kSfO-d33TgFDs3FMKT2_f3m3ZGXngK8KQw9p7CYHnmEKSYJaDGdcwKxUm06zr7sUozCFYgg967qRxORhZS9uSGfcONoomReqmtqShiTR0hXREa1cvAfzMVIKAgO-XoDtzwL2tLuEdjCnbOTrh359sHBDMDjgwm2GVyAjimr9sTcM_nsEBhZgwKKAlXotbNEZIuoRe7ixTtGIKQ"
    SERVICE_NAME = "StarRocks_test"
    DATABASE_NAME = "default"
    
    # SQL 文件路径
    # SQL_FILE = "../sql/P_ads_bi_sv_user_recharge_expo_info_di.sql"
    # SQL_FILE = "../sql/P_dws_user_short_video_wide_active_period_ed.sql"
    SQL_FILE = "../sql/P_ads_bi_sv_user_recharge_expo_info_di_copy.sql"


    print("="*60)
    print("StarRocks SQL 解析器 - 血缘导入工具")
    print("="*60)
    print(f"服务名称: {SERVICE_NAME}")
    print(f"数据库名称: {DATABASE_NAME}")
    print(f"SQL 文件: {SQL_FILE}")
    print("="*60)
    
    # 创建解析器
    parser = StarRocksSQLParser(HOST_PORT, JWT_TOKEN, SERVICE_NAME, DATABASE_NAME)
    
    # 连接 OpenMetadata
    if not parser.connect():
        print("\n✗ 无法连接到 OpenMetadata，退出")
        return
    
    # 处理 SQL 文件（启用列级血缘）
    success = parser.process_sql_file(
        SQL_FILE, 
        parse_columns=True,  # 启用列级血缘解析
        description="P_ads_bi_sv_user_recharge_expo_info_di"
    )
    
    if success:
        print("\n" + "="*60)
        print("✅ 处理完成！")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("✗ 处理失败")
        print("="*60)


if __name__ == "__main__":
    main()
