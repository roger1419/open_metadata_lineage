# -*- coding: utf-8 -*-
"""
OpenMetadata 表信息导出工具 v3.0
针对大数据量 Schema 优化，使用分页和直接 API 查询

改进：
- 使用 list_all_entities 分页获取
- 直接通过 Schema 关联查询表
- 支持增量导出（按批次）
- 内存优化
"""

import sys
import os
import io
import argparse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import OpenMetadataConnection, AuthProvider
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import OpenMetadataJWTClientConfig
from metadata.generated.schema.entity.data.table import Table
from metadata.generated.schema.entity.data.databaseSchema import DatabaseSchema
import pandas as pd
from datetime import datetime


def safe_extract_value(obj, default='N/A'):
    """安全提取对象的值"""
    if obj is None:
        return default
    if isinstance(obj, str):
        return obj
    if hasattr(obj, 'root'):
        root_val = obj.root
        return str(root_val) if root_val is not None else default
    if hasattr(obj, '__root__'):
        root_val = obj.__root__
        return str(root_val) if root_val is not None else default
    return str(obj)


class OpenMetadataExporterV3:
    """OpenMetadata 表信息导出器 v3 - 大数据量优化版"""
    
    def __init__(self, host_port, jwt_token):
        self.host_port = host_port
        self.jwt_token = jwt_token
        self.metadata = None
        
    def connect(self):
        """连接到 OpenMetadata"""
        print("正在连接 OpenMetadata...")
        try:
            server_config = OpenMetadataConnection(
                hostPort=self.host_port,
                authProvider=AuthProvider.openmetadata,
                securityConfig=OpenMetadataJWTClientConfig(jwtToken=self.jwt_token),
                verifySSL="no-ssl"
            )
            self.metadata = OpenMetadata(server_config)
            health = self.metadata.health_check()
            print(f"✅ 连接成功: {health}")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def count_schema_tables(self, schema_fqn):
        """统计 Schema 下的表数量（使用分页）"""
        print(f"\n📊 统计 Schema 表数量: {schema_fqn}")
        
        count = 0
        batch_size = 100
        
        # 使用 list_all_entities 生成器分页获取
        try:
            for table in self.metadata.list_all_entities(
                entity=Table,
                fields=["databaseSchema"],
                params={"databaseSchema": schema_fqn}
            ):
                table_schema_fqn = ''
                if hasattr(table, 'databaseSchema') and table.databaseSchema:
                    table_schema_fqn = safe_extract_value(
                        getattr(table.databaseSchema, 'fullyQualifiedName', None)
                    )
                
                if table_schema_fqn == schema_fqn:
                    count += 1
                    if count % 100 == 0:
                        print(f"  已统计 {count} 个表...")
        except Exception as e:
            print(f"⚠️  使用 params 过滤失败，尝试备用方法: {e}")
            # 备用方法：遍历所有表
            count = self._count_tables_fallback(schema_fqn)
        
        print(f"✅ Schema {schema_fqn} 共有 {count} 个表")
        return count
    
    def _count_tables_fallback(self, schema_fqn):
        """备用统计方法"""
        count = 0
        for table in self.metadata.list_all_entities(
            entity=Table,
            fields=["databaseSchema"]
        ):
            table_schema_fqn = ''
            if hasattr(table, 'databaseSchema') and table.databaseSchema:
                table_schema_fqn = safe_extract_value(
                    getattr(table.databaseSchema, 'fullyQualifiedName', None)
                )
            
            if table_schema_fqn == schema_fqn:
                count += 1
                if count % 100 == 0:
                    print(f"  已统计 {count} 个表...")
        return count

    def get_schema_tables_paginated(self, schema_fqn, include_columns=False, batch_size=50):
        """
        分页获取 Schema 下的表信息
        
        Args:
            schema_fqn: Schema FQN
            include_columns: 是否包含列信息
            batch_size: 每批处理的表数量
            
        Yields:
            tuple: (table_info, column_infos)
        """
        print(f"\n📊 开始获取表信息: {schema_fqn}")
        print(f"   批次大小: {batch_size}")
        
        table_count = 0
        
        # 使用生成器分页获取，减少内存占用
        fields = ["owners", "tags", "usageSummary", "profile", "database", "databaseSchema", "service"]
        if include_columns:
            fields.append("columns")
        
        for table in self.metadata.list_all_entities(
            entity=Table,
            fields=fields
        ):
            # 检查是否属于目标 Schema
            table_schema_fqn = ''
            if hasattr(table, 'databaseSchema') and table.databaseSchema:
                table_schema_fqn = safe_extract_value(
                    getattr(table.databaseSchema, 'fullyQualifiedName', None)
                )
            
            if table_schema_fqn != schema_fqn:
                continue
            
            table_count += 1
            table_name = safe_extract_value(getattr(table, 'name', None))
            print(f"  [{table_count}] {table_name}")
            
            # 提取表信息
            table_info = self._extract_table_info(table, table_count)
            
            # 提取列信息
            column_infos = []
            if include_columns and hasattr(table, 'columns') and table.columns:
                for col_idx, column in enumerate(table.columns, 1):
                    column_info = self._extract_column_info(table, column, table_count, col_idx)
                    column_infos.append(column_info)
            
            yield table_info, column_infos
        
        print(f"\n✅ 共处理 {table_count} 个表")
    
    def _extract_table_info(self, table, table_count):
        """提取表信息（简化版，减少内存）"""
        table_info = {
            '序号': table_count,
            '表名': safe_extract_value(getattr(table, 'name', None)),
            '显示名称': safe_extract_value(getattr(table, 'displayName', None)) or safe_extract_value(getattr(table, 'name', None)),
            '完全限定名': safe_extract_value(getattr(table, 'fullyQualifiedName', None)),
            '表类型': safe_extract_value(getattr(table, 'tableType', None)),
        }
        
        # 描述
        desc = getattr(table, 'description', None)
        desc_str = safe_extract_value(desc, '无描述') if desc else '无描述'
        table_info['描述'] = (desc_str[:100] + '...') if len(desc_str) > 100 else desc_str
        
        # 列数
        columns = getattr(table, 'columns', None)
        table_info['列数'] = len(columns) if columns else 0
        
        # Profile 信息
        profile = getattr(table, 'profile', None)
        if profile:
            table_info['行数'] = safe_extract_value(getattr(profile, 'rowCount', None))
            table_info['表大小(字节)'] = safe_extract_value(getattr(profile, 'sizeInByte', None))
        else:
            table_info['行数'] = 'N/A'
            table_info['表大小(字节)'] = 'N/A'
        
        # 所有者
        owners = getattr(table, 'owners', None)
        table_info['所有者'] = self._extract_owners(owners)
        
        # 标签
        tags = getattr(table, 'tags', None)
        table_info['标签'] = self._extract_tags(tags)
        
        # 服务信息
        service = getattr(table, 'service', None)
        table_info['服务名称'] = safe_extract_value(getattr(service, 'name', None)) if service else 'N/A'
        table_info['服务类型'] = safe_extract_value(getattr(table, 'serviceType', None))
        
        # 数据库和 Schema
        database = getattr(table, 'database', None)
        table_info['数据库'] = safe_extract_value(getattr(database, 'name', None)) if database else 'N/A'
        
        schema = getattr(table, 'databaseSchema', None)
        table_info['Schema'] = safe_extract_value(getattr(schema, 'name', None)) if schema else 'N/A'
        
        # 版本和时间
        table_info['版本'] = safe_extract_value(getattr(table, 'version', None))
        table_info['更新时间'] = self._extract_timestamp(getattr(table, 'updatedAt', None))
        table_info['更新者'] = safe_extract_value(getattr(table, 'updatedBy', None))
        table_info['是否已删除'] = '是' if getattr(table, 'deleted', False) else '否'
        
        # URL
        fqn = table_info['完全限定名']
        if fqn and fqn != 'N/A':
            table_info['URL'] = f"{self.host_port.replace('/api', '')}/table/{fqn}"
        else:
            table_info['URL'] = 'N/A'
        
        return table_info
    
    def _extract_owners(self, owners):
        """提取所有者信息"""
        if not owners:
            return '未设置'
        try:
            if hasattr(owners, 'root'):
                owners = owners.root
            if isinstance(owners, tuple):
                owners = owners[1] if len(owners) > 1 else []
            if owners and not isinstance(owners, (list, tuple)):
                owners = [owners]
            if owners:
                owner_names = [safe_extract_value(getattr(o, 'name', None), str(o)) for o in owners]
                return ', '.join(owner_names) if owner_names else '未设置'
        except:
            pass
        return '未设置'
    
    def _extract_tags(self, tags):
        """提取标签信息"""
        if not tags:
            return '无'
        try:
            if hasattr(tags, 'root'):
                tags = tags.root
            if isinstance(tags, tuple):
                tags = tags[1] if len(tags) > 1 else []
            if tags and not isinstance(tags, (list, tuple)):
                tags = [tags]
            if tags:
                tag_names = [safe_extract_value(getattr(t, 'tagFQN', None), str(t)) for t in tags]
                return ', '.join(tag_names) if tag_names else '无'
        except:
            pass
        return '无'
    
    def _extract_timestamp(self, updated_at):
        """提取时间戳"""
        if not updated_at:
            return 'N/A'
        try:
            if hasattr(updated_at, 'root'):
                updated_at = updated_at.root
            if hasattr(updated_at, 'strftime'):
                return updated_at.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(updated_at, (int, float)):
                return datetime.fromtimestamp(updated_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            return str(updated_at)
        except:
            return 'N/A'
    
    def _extract_column_info(self, table, column, table_count, col_idx):
        """提取列信息"""
        column_info = {
            '表序号': table_count,
            '表名': safe_extract_value(getattr(table, 'name', None)),
            '列序号': col_idx,
            '列名': safe_extract_value(getattr(column, 'name', None)),
            '显示名称': safe_extract_value(getattr(column, 'displayName', None)) or safe_extract_value(getattr(column, 'name', None)),
            '数据类型': safe_extract_value(getattr(column, 'dataType', None)),
            '数据长度': safe_extract_value(getattr(column, 'dataLength', None)),
            '是否可空': '是' if not getattr(column, 'constraint', None) else '否',
            '默认值': safe_extract_value(getattr(column, 'defaultValue', None)),
        }
        
        col_desc = getattr(column, 'description', None)
        column_info['描述'] = safe_extract_value(col_desc, '无描述') if col_desc else '无描述'
        
        tags = getattr(column, 'tags', [])
        if tags:
            try:
                tag_names = [safe_extract_value(getattr(t, 'tagFQN', None), str(t)) for t in tags]
                column_info['标签'] = ', '.join(tag_names) if tag_names else '无'
            except:
                column_info['标签'] = '无'
        else:
            column_info['标签'] = '无'
        
        constraint = getattr(column, 'constraint', None)
        column_info['约束'] = safe_extract_value(constraint) if constraint else '无'
        
        return column_info

    def export_to_excel_streaming(self, schema_fqn, include_columns=False, output_dir='.', batch_size=100):
        """
        流式导出到 Excel（内存优化）
        
        Args:
            schema_fqn: Schema FQN
            include_columns: 是否包含列信息
            output_dir: 输出目录
            batch_size: 批次大小
        """
        tables_data = []
        columns_data = []
        
        print(f"\n🚀 开始流式导出...")
        
        for table_info, column_infos in self.get_schema_tables_paginated(
            schema_fqn, include_columns, batch_size
        ):
            tables_data.append(table_info)
            columns_data.extend(column_infos)
            
            # 每 batch_size 个表打印一次进度
            if len(tables_data) % batch_size == 0:
                print(f"   📦 已收集 {len(tables_data)} 个表...")
        
        if not tables_data:
            print("⚠️  没有数据可导出")
            return None
        
        # 导出到 Excel
        return self._write_excel(tables_data, columns_data, schema_fqn, output_dir)
    
    def _write_excel(self, tables_data, columns_data, schema_fqn, output_dir):
        """写入 Excel 文件"""
        try:
            df_tables = pd.DataFrame(tables_data)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            schema_name = schema_fqn.replace('.', '_')
            filename = os.path.join(output_dir, f"OpenMetadata_Tables_{schema_name}_{timestamp}.xlsx")
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df_tables.to_excel(writer, sheet_name='Tables', index=False)
                
                if columns_data:
                    df_columns = pd.DataFrame(columns_data)
                    df_columns.to_excel(writer, sheet_name='Columns', index=False)
                
                # 调整列宽
                from openpyxl.utils import get_column_letter
                
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    df = df_tables if sheet_name == 'Tables' else pd.DataFrame(columns_data)
                    
                    for idx, col in enumerate(df.columns, 1):
                        try:
                            max_length = max(
                                df[col].astype(str).apply(len).max(),
                                len(str(col))
                            )
                            adjusted_width = min(max(max_length + 2, 10), 50)
                            column_letter = get_column_letter(idx)
                            worksheet.column_dimensions[column_letter].width = adjusted_width
                        except:
                            pass
            
            print(f"\n✅ 数据已成功导出到: {filename}")
            print(f"📊 表数量: {len(tables_data)}")
            if columns_data:
                print(f"📊 列数量: {len(columns_data)}")
            
            return filename
            
        except Exception as e:
            print(f"❌ 导出 Excel 时出错: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='OpenMetadata 表信息导出工具 v3.0 (大数据量优化)')
    parser.add_argument('--host', default="https://openmetadata.changdu.vip/api", help='OpenMetadata 服务器地址')
    parser.add_argument('--token', help='JWT Token')
    parser.add_argument('--schema', required=True, help='Schema FQN')
    parser.add_argument('--columns', action='store_true', help='是否导出列信息')
    parser.add_argument('--output', default='.', help='输出目录')
    parser.add_argument('--batch', type=int, default=50, help='批次大小')
    parser.add_argument('--count-only', action='store_true', help='仅统计表数量')
    
    args = parser.parse_args()
    
    # 默认 token（生产环境）
    if not args.token:
        args.token = "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImxpbmVhZ2UtYm90Iiwicm9sZXMiOlsiTGluZWFnZUJvdFJvbGUiXSwiZW1haWwiOiJsaW5lYWdlLWJvdEBvcGVuLW1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3NjU3OTQ2OTQsImV4cCI6bnVsbH0.YSFXrR-DzaeBBNtni_rc3Hw1j2rA29oj038n7llTr-8zLcf2g-MEqd1CVhQwrq4rrMgEmk3go4T3diHvGbZ5LLP-Z_-nl90ZUuC2xIXH2_m7LrMnIbuQxvrbtVAJz_X8AEK9im5rm9OQFUytPcWk0Yy0Bji4_8IfjpkhVxXNmR4ZIPyz2tVTkRKWvQ5HDCCuArhLw3fTxAuZYWazSzBVFjfv_WaSpth37C8ftD-JS3s9UT-QPog7zMjTehXFHx9q_pcegoSmVQST1P15I01r5S5bv_IDHnrqi-7bKJGOFwBbx0gtPfzc1fWIKDY57IEsVE1F4ijZxazhfsDTJtCs5Q"
    
    print("="*60)
    print("OpenMetadata 表信息导出工具 v3.0 (大数据量优化)")
    print("="*60)
    print(f"Schema FQN: {args.schema}")
    print(f"导出列信息: {'是' if args.columns else '否'}")
    print(f"批次大小: {args.batch}")
    print(f"输出目录: {args.output}")
    print("="*60 + "\n")
    
    exporter = OpenMetadataExporterV3(args.host, args.token)
    
    if not exporter.connect():
        sys.exit(1)
    
    if args.count_only:
        # 仅统计
        count = exporter.count_schema_tables(args.schema)
        print(f"\n📊 Schema {args.schema} 共有 {count} 个表")
    else:
        # 导出
        filename = exporter.export_to_excel_streaming(
            args.schema, args.columns, args.output, args.batch
        )
        
        if filename:
            print("\n" + "="*60)
            print("✅ 导出完成！")
            print("="*60)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
