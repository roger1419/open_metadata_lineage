# -*- coding: utf-8 -*-
"""
StarRocks 血缘处理模块
专门处理 StarRocks 相关的 SQL 解析和血缘关系
支持与 DolphinScheduler 任务的关联
"""

import re
import json
from typing import Dict, List, Optional, Tuple
import open_metadata_lineage


class StarRocksLineageHandler:
    """
    StarRocks 血缘处理器
    支持 StarRocks 特有的 SQL 语法和功能
    """
    
    def __init__(self, metadata_client=None):
        """
        初始化 StarRocks 血缘处理器
        
        Args:
            metadata_client: OpenMetadata 客户端实例
        """
        self.metadata = metadata_client or open_metadata_lineage.METADATA
        
        # StarRocks 特有的 SQL 关键字和函数
        self.starrocks_keywords = [
            'DUPLICATE KEY', 'AGGREGATE KEY', 'UNIQUE KEY', 'PRIMARY KEY',
            'DISTRIBUTED BY HASH', 'BUCKETS', 'PROPERTIES',
            'BITMAP_UNION', 'HLL_UNION', 'PERCENTILE_UNION',
            'REPLACE_IF_NOT_NULL', 'REPLACE'
        ]
    
    def is_starrocks_sql(self, sql: str) -> bool:
        """
        判断是否为 StarRocks SQL
        
        Args:
            sql: SQL 语句
            
        Returns:
            bool: 是否为 StarRocks SQL
        """
        sql_upper = sql.upper()
        return any(keyword in sql_upper for keyword in self.starrocks_keywords)
    
    def parse_starrocks_insert(self, sql: str) -> Optional[Dict]:
        """
        解析 StarRocks INSERT 语句
        支持多种 INSERT 格式：
        - INSERT INTO ... SELECT
        - INSERT INTO ... VALUES
        - INSERT OVERWRITE
        
        Args:
            sql: SQL 语句
            
        Returns:
            Dict: 解析结果，包含 target_table, source_tables, columns 等
        """
        sql_cleaned = sql.strip().replace('`', '')
        
        # 匹配 INSERT INTO/OVERWRITE
        insert_pattern = r'INSERT\s+(INTO|OVERWRITE)\s+(\w+\.?\w*)\s*(?:\((.*?)\))?\s*SELECT'
        match = re.search(insert_pattern, sql_cleaned, re.IGNORECASE | re.DOTALL)
        
        if not match:
            return None
        
        insert_type = match.group(1).upper()
        target_table = match.group(2)
        target_columns = match.group(3)
        
        # 解析目标字段
        if target_columns:
            target_cols = [col.strip() for col in target_columns.split(',')]
        else:
            target_cols = []
        
        # 提取 FROM 子句中的表
        from_pattern = r'FROM\s+([\w\.]+)'
        from_matches = re.findall(from_pattern, sql_cleaned, re.IGNORECASE)
        
        # 提取 JOIN 子句中的表
        join_pattern = r'JOIN\s+([\w\.]+)'
        join_matches = re.findall(join_pattern, sql_cleaned, re.IGNORECASE)
        
        source_tables = list(set(from_matches + join_matches))
        
        return {
            'insert_type': insert_type,
            'target_table': target_table,
            'target_columns': target_cols,
            'source_tables': source_tables,
            'sql': sql_cleaned
        }
    
    def add_starrocks_lineage(
        self, 
        service_name: str,
        database_name: str,
        sql: str,
        description: str = "StarRocks SQL",
        task_info: Optional[Dict] = None
    ) -> bool:
        """
        添加 StarRocks SQL 血缘
        
        Args:
            service_name: StarRocks 服务名称
            database_name: 数据库名称
            sql: SQL 语句
            description: 血缘描述
            task_info: 关联的任务信息（DolphinScheduler 等）
            
        Returns:
            bool: 是否成功
        """
        print(f"\n{'='*60}")
        print(f"StarRocks 血缘解析")
        print(f"Service: {service_name}, Database: {database_name}")
        print(f"{'='*60}")
        
        # 如果有任务信息，添加到描述中
        if task_info:
            description = self._build_description_with_task(description, task_info)
        
        # 清理 SQL
        cleaned_sql = self._clean_starrocks_sql(sql)
        
        # 检查是否为 INSERT ... SELECT
        if not self._is_insert_select(cleaned_sql):
            print("  ⊘ 不是 INSERT ... SELECT 语句，跳过")
            return False
        
        # 优先使用 OpenMetadata 服务端解析
        try:
            print("  → 使用 OpenMetadata 服务端解析...")
            success = open_metadata_lineage.add_lineage_by_sql(
                database_service=service_name,
                database_name=database_name,
                sql=cleaned_sql,
                description_=description,
                schema_name='default'
            )
            
            if success:
                print("  ✓ StarRocks 血缘添加成功")
                return True
            else:
                print("  ⚠ 服务端解析未成功，尝试本地解析...")
                return self._add_lineage_local(service_name, database_name, cleaned_sql, description)
                
        except Exception as exc:
            print(f"  ✗ 服务端解析失败: {exc}")
            print("  → 尝试本地解析...")
            return self._add_lineage_local(service_name, database_name, cleaned_sql, description)
    
    def _clean_starrocks_sql(self, sql: str) -> str:
        """
        清理 StarRocks SQL
        移除 StarRocks 特有的语法，使其更容易被解析
        """
        cleaned = sql.strip()
        
        # 移除反引号
        cleaned = cleaned.replace('`', '')
        
        # 将 INSERT OVERWRITE 转换为 INSERT INTO（sqllineage 不支持 OVERWRITE）
        cleaned = re.sub(r'INSERT\s+OVERWRITE', 'INSERT INTO', cleaned, flags=re.IGNORECASE)
        
        # 移除 StarRocks 特有的 PROPERTIES 子句
        cleaned = re.sub(r'PROPERTIES\s*\([^)]*\)', '', cleaned, flags=re.IGNORECASE)
        
        # 移除 DISTRIBUTED BY 子句
        cleaned = re.sub(r'DISTRIBUTED\s+BY\s+HASH\s*\([^)]*\)\s*BUCKETS\s+\d+', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _is_insert_select(self, sql: str) -> bool:
        """检查是否为 INSERT ... SELECT 语句"""
        pattern = re.compile(r'INSERT\s+(INTO|OVERWRITE).*SELECT', re.IGNORECASE | re.DOTALL)
        return bool(pattern.search(sql))
    
    def _build_description_with_task(self, base_description: str, task_info: Dict) -> str:
        """
        构建包含任务信息的描述
        
        Args:
            base_description: 基础描述
            task_info: 任务信息字典
            
        Returns:
            str: 完整描述
        """
        task_desc_parts = [base_description]
        
        if task_info.get('platform'):
            task_desc_parts.append(f"\n平台: {task_info['platform']}")
        if task_info.get('project_name'):
            task_desc_parts.append(f"项目: {task_info['project_name']}")
        if task_info.get('workflow_name'):
            task_desc_parts.append(f"工作流: {task_info['workflow_name']}")
        if task_info.get('task_name'):
            task_desc_parts.append(f"任务: {task_info['task_name']}")
        if task_info.get('task_url'):
            task_desc_parts.append(f"链接: {task_info['task_url']}")
        
        return '\n'.join(task_desc_parts)
    
    def _add_lineage_local(self, service_name: str, database_name: str, sql: str, description: str) -> bool:
        """
        使用本地解析添加血缘（备选方案）
        """
        try:
            from sqllineage.runner import LineageRunner
            
            # 确保有 metadata 客户端
            if self.metadata is None:
                self.metadata = open_metadata_lineage.get_metadata_client()
            
            result = LineageRunner(sql, dialect="ansi")
            lineage = result.get_column_lineage()
            
            success_count = 0
            fail_count = 0
            
            for idx, columnTuples in enumerate(lineage):
                for column in columnTuples:
                    if columnTuples.index(column) == len(columnTuples) - 1:
                        # 下游
                        down_field = str(column.raw_name)
                        down_table = str(column).replace(f'.{down_field}', '').replace('<default>', database_name)
                        down_fqn = f"{service_name}.default.{down_table}"
                    else:
                        # 上游
                        up_field = str(column.raw_name)
                        up_table = str(column).replace(f'.{up_field}', '').replace('<default>', database_name)
                        up_fqn = f"{service_name}.default.{up_table}"
                
                result_msg = open_metadata_lineage.add_lineage(
                    up_fqn, up_field,
                    down_fqn, down_field,
                    description, sql,
                    metadata_=self.metadata,
                    not_first_=(idx != 0)
                )
                
                if '成功' in result_msg:
                    success_count += 1
                    print(f"    ✓ {up_table}.{up_field} -> {down_table}.{down_field}")
                else:
                    fail_count += 1
                    print(f"    ✗ {up_table}.{up_field} -> {down_table}.{down_field}: {result_msg}")
            
            print(f"  本地解析: 成功 {success_count}, 失败 {fail_count}")
            return success_count > 0
            
        except Exception as exc:
            print(f"  ✗ 本地解析失败: {exc}")
            # 不打印完整堆栈，避免输出过多
            return False


class DolphinSchedulerStarRocksIntegration:
    """
    DolphinScheduler 与 StarRocks 集成
    处理 DolphinScheduler 中的 StarRocks SQL 任务
    """
    
    def __init__(self, dolphin_client, metadata_client=None):
        """
        初始化集成处理器
        
        Args:
            dolphin_client: DolphinScheduler 客户端实例
            metadata_client: OpenMetadata 客户端实例
        """
        self.dolphin = dolphin_client
        self.starrocks_handler = StarRocksLineageHandler(metadata_client)
    
    def process_starrocks_task(
        self,
        project_code: str,
        task_code: str,
        task_data: Dict
    ) -> bool:
        """
        处理 StarRocks 任务
        
        Args:
            project_code: 项目代码
            task_code: 任务代码
            task_data: 任务数据
            
        Returns:
            bool: 是否成功
        """
        task_params = task_data.get('taskParams', {})
        sql = task_params.get('sql', '')
        
        if not sql:
            return False
        
        # 获取数据源信息
        datasource_id = task_params.get('datasource')
        if datasource_id not in self.dolphin.data_sources:
            print(f"  ✗ 数据源 {datasource_id} 未找到")
            return False
        
        raw_url = self.dolphin.data_sources[datasource_id]
        service_name = open_metadata_lineage.get_service_by_url(raw_url)
        
        # 解析数据库名
        url_parts = raw_url.split('/')
        if len(url_parts) > 3 and url_parts[-1]:
            db_name = url_parts[-1].split('?')[0]
        else:
            db_name = 'default'
        
        # 构建任务信息
        task_info = {
            'platform': 'DolphinScheduler',
            'project_name': task_data.get('projectName'),
            'workflow_name': task_data.get('processDefinitionName'),
            'task_name': task_data.get('taskName'),
            'task_code': task_code,
            'task_url': f"{self.dolphin.url}/ui/projects/{project_code}/task/definitions"
        }
        
        # 添加血缘
        return self.starrocks_handler.add_starrocks_lineage(
            service_name=service_name,
            database_name=db_name,
            sql=sql,
            description="DolphinScheduler-StarRocks",
            task_info=task_info
        )


# 便捷函数
def add_starrocks_lineage_from_dolphin(
    service_name: str,
    database_name: str,
    sql: str,
    project_name: str = None,
    workflow_name: str = None,
    task_name: str = None,
    task_url: str = None
) -> bool:
    """
    从 DolphinScheduler 添加 StarRocks 血缘的便捷函数
    
    Args:
        service_name: StarRocks 服务名
        database_name: 数据库名
        sql: SQL 语句
        project_name: 项目名称
        workflow_name: 工作流名称
        task_name: 任务名称
        task_url: 任务链接
        
    Returns:
        bool: 是否成功
    """
    handler = StarRocksLineageHandler()
    
    task_info = {
        'platform': 'DolphinScheduler',
        'project_name': project_name,
        'workflow_name': workflow_name,
        'task_name': task_name,
        'task_url': task_url
    }
    
    return handler.add_starrocks_lineage(
        service_name=service_name,
        database_name=database_name,
        sql=sql,
        description="DolphinScheduler-StarRocks",
        task_info=task_info
    )
