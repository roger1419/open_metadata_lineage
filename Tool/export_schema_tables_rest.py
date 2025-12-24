# -*- coding: utf-8 -*-
"""
OpenMetadata 表信息导出工具 - REST API 版本
使用直接 REST API 调用，支持大数据量 Schema 导出

特点：
- 使用 REST API 分页获取，避免 SDK 超时
- 支持 855+ 表的大数据量导出
- 进度显示
"""

import sys
import os
import io
import argparse
import requests
import urllib3
import pandas as pd
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class OpenMetadataRESTExporter:
    """使用 REST API 导出表信息"""
    
    def __init__(self, base_url, jwt_token):
        self.base_url = base_url.rstrip('/')
        self.jwt_token = jwt_token
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        })
    
    def get_schema_info(self, schema_fqn):
        """获取 Schema 信息"""
        url = f"{self.base_url}/v1/databaseSchemas/name/{schema_fqn}"
        resp = self.session.get(url)
        if resp.status_code == 200:
            return resp.json()
        return None
    
    def count_tables(self, schema_fqn):
        """统计表数量"""
        url = f"{self.base_url}/v1/tables"
        params = {"databaseSchema": schema_fqn, "limit": 1}
        resp = self.session.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get('paging', {}).get('total', 0)
        return 0
    
    def get_tables_page(self, schema_fqn, limit=100, after=None, fields=None):
        """获取一页表数据"""
        url = f"{self.base_url}/v1/tables"
        params = {
            "databaseSchema": schema_fqn,
            "limit": limit
        }
        if after:
            params["after"] = after
        if fields:
            params["fields"] = ",".join(fields)
        
        resp = self.session.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('data', []), data.get('paging', {})
        return [], {}
    
    def get_all_tables(self, schema_fqn, fields=None, batch_size=100):
        """获取所有表（分页）"""
        all_tables = []
        after = None
        page = 0
        
        total = self.count_tables(schema_fqn)
        print(f"📊 总共 {total} 个表，开始分页获取...")
        
        while True:
            page += 1
            tables, paging = self.get_tables_page(schema_fqn, batch_size, after, fields)
            
            if not tables:
                break
            
            all_tables.extend(tables)
            print(f"   第 {page} 页: 获取 {len(tables)} 个表，累计 {len(all_tables)}/{total}")
            
            after = paging.get('after')
            if not after:
                break
        
        print(f"✅ 共获取 {len(all_tables)} 个表")
        return all_tables
    
    def extract_table_info(self, table, idx):
        """提取表信息"""
        def safe_get(obj, *keys, default='N/A'):
            for key in keys:
                if obj is None:
                    return default
                if isinstance(obj, dict):
                    obj = obj.get(key)
                else:
                    obj = getattr(obj, key, None)
            return obj if obj is not None else default
        
        info = {
            '序号': idx,
            '表名': safe_get(table, 'name'),
            '显示名称': safe_get(table, 'displayName') or safe_get(table, 'name'),
            '完全限定名': safe_get(table, 'fullyQualifiedName'),
            '表类型': safe_get(table, 'tableType'),
            '描述': (safe_get(table, 'description', default='无描述')[:100] + '...') 
                    if len(safe_get(table, 'description', default='')) > 100 
                    else safe_get(table, 'description', default='无描述'),
        }
        
        # 列数
        columns = table.get('columns', [])
        info['列数'] = len(columns) if columns else 0
        
        # Profile
        profile = table.get('profile', {})
        info['行数'] = safe_get(profile, 'rowCount') if profile else 'N/A'
        info['表大小(字节)'] = safe_get(profile, 'sizeInByte') if profile else 'N/A'
        
        # 所有者
        owners = table.get('owners', [])
        if owners:
            owner_names = [o.get('name', str(o)) for o in owners if isinstance(o, dict)]
            info['所有者'] = ', '.join(owner_names) if owner_names else '未设置'
        else:
            info['所有者'] = '未设置'
        
        # 标签
        tags = table.get('tags', [])
        if tags:
            tag_names = [t.get('tagFQN', str(t)) for t in tags if isinstance(t, dict)]
            info['标签'] = ', '.join(tag_names) if tag_names else '无'
        else:
            info['标签'] = '无'
        
        # 服务信息
        service = table.get('service', {})
        info['服务名称'] = safe_get(service, 'name') if service else 'N/A'
        info['服务类型'] = safe_get(table, 'serviceType')
        
        # 数据库和 Schema
        database = table.get('database', {})
        info['数据库'] = safe_get(database, 'name') if database else 'N/A'
        
        schema = table.get('databaseSchema', {})
        info['Schema'] = safe_get(schema, 'name') if schema else 'N/A'
        
        # 版本和时间
        info['版本'] = safe_get(table, 'version')
        
        updated_at = table.get('updatedAt')
        if updated_at:
            try:
                if isinstance(updated_at, (int, float)):
                    info['更新时间'] = datetime.fromtimestamp(updated_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    info['更新时间'] = str(updated_at)
            except:
                info['更新时间'] = 'N/A'
        else:
            info['更新时间'] = 'N/A'
        
        info['更新者'] = safe_get(table, 'updatedBy')
        info['是否已删除'] = '是' if table.get('deleted', False) else '否'
        
        # URL
        fqn = info['完全限定名']
        if fqn and fqn != 'N/A':
            info['URL'] = f"{self.base_url.replace('/api', '')}/table/{fqn}"
        else:
            info['URL'] = 'N/A'
        
        return info

    def extract_column_info(self, table, column, table_idx, col_idx):
        """提取列信息"""
        def safe_get(obj, key, default='N/A'):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)
        
        info = {
            '表序号': table_idx,
            '表名': safe_get(table, 'name'),
            '列序号': col_idx,
            '列名': safe_get(column, 'name'),
            '显示名称': safe_get(column, 'displayName') or safe_get(column, 'name'),
            '数据类型': safe_get(column, 'dataType'),
            '数据长度': safe_get(column, 'dataLength'),
            '是否可空': '是' if not column.get('constraint') else '否',
            '默认值': safe_get(column, 'defaultValue'),
            '描述': safe_get(column, 'description', '无描述'),
        }
        
        tags = column.get('tags', [])
        if tags:
            tag_names = [t.get('tagFQN', str(t)) for t in tags if isinstance(t, dict)]
            info['标签'] = ', '.join(tag_names) if tag_names else '无'
        else:
            info['标签'] = '无'
        
        info['约束'] = safe_get(column, 'constraint', '无')
        
        return info
    
    def export_to_excel(self, schema_fqn, include_columns=False, output_dir='.', batch_size=100):
        """导出到 Excel"""
        print(f"\n🚀 开始导出 Schema: {schema_fqn}")
        
        # 获取 Schema 信息
        schema_info = self.get_schema_info(schema_fqn)
        if not schema_info:
            print(f"❌ 未找到 Schema: {schema_fqn}")
            return None
        
        print(f"✅ Schema: {schema_info.get('name')} (ID: {schema_info.get('id')})")
        
        # 确定需要的字段
        fields = ["owners", "tags", "usageSummary", "profile", "database", "databaseSchema", "service"]
        if include_columns:
            fields.append("columns")
        
        # 获取所有表
        tables = self.get_all_tables(schema_fqn, fields, batch_size)
        
        if not tables:
            print("⚠️  没有找到表")
            return None
        
        # 提取表信息
        print(f"\n📝 提取表信息...")
        tables_data = []
        columns_data = []
        
        for idx, table in enumerate(tables, 1):
            table_info = self.extract_table_info(table, idx)
            tables_data.append(table_info)
            
            if include_columns:
                columns = table.get('columns', [])
                for col_idx, column in enumerate(columns, 1):
                    column_info = self.extract_column_info(table, column, idx, col_idx)
                    columns_data.append(column_info)
            
            if idx % 100 == 0:
                print(f"   已处理 {idx} 个表...")
        
        # 导出到 Excel
        print(f"\n📊 导出到 Excel...")
        
        df_tables = pd.DataFrame(tables_data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        schema_name = schema_fqn.replace('.', '_')
        filename = os.path.join(output_dir, f"OpenMetadata_Tables_{schema_name}_{timestamp}.xlsx")
        
        try:
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
            
            print(f"\n✅ 导出成功: {filename}")
            print(f"📊 表数量: {len(tables_data)}")
            if columns_data:
                print(f"📊 列数量: {len(columns_data)}")
            
            return filename
            
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    parser = argparse.ArgumentParser(description='OpenMetadata 表信息导出工具 (REST API 版)')
    parser.add_argument('--host', default="https://openmetadata.changdu.vip/api", help='OpenMetadata API 地址')
    parser.add_argument('--token', help='JWT Token')
    parser.add_argument('--schema', required=True, help='Schema FQN')
    parser.add_argument('--columns', action='store_true', help='是否导出列信息')
    parser.add_argument('--output', default='.', help='输出目录')
    parser.add_argument('--batch', type=int, default=100, help='每页获取数量')
    
    args = parser.parse_args()
    
    # 默认 token
    if not args.token:
        args.token = "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImxpbmVhZ2UtYm90Iiwicm9sZXMiOlsiTGluZWFnZUJvdFJvbGUiXSwiZW1haWwiOiJsaW5lYWdlLWJvdEBvcGVuLW1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3NjU3OTQ2OTQsImV4cCI6bnVsbH0.YSFXrR-DzaeBBNtni_rc3Hw1j2rA29oj038n7llTr-8zLcf2g-MEqd1CVhQwrq4rrMgEmk3go4T3diHvGbZ5LLP-Z_-nl90ZUuC2xIXH2_m7LrMnIbuQxvrbtVAJz_X8AEK9im5rm9OQFUytPcWk0Yy0Bji4_8IfjpkhVxXNmR4ZIPyz2tVTkRKWvQ5HDCCuArhLw3fTxAuZYWazSzBVFjfv_WaSpth37C8ftD-JS3s9UT-QPog7zMjTehXFHx9q_pcegoSmVQST1P15I01r5S5bv_IDHnrqi-7bKJGOFwBbx0gtPfzc1fWIKDY57IEsVE1F4ijZxazhfsDTJtCs5Q"
    
    print("="*60)
    print("OpenMetadata 表信息导出工具 (REST API 版)")
    print("="*60)
    print(f"Schema: {args.schema}")
    print(f"导出列信息: {'是' if args.columns else '否'}")
    print(f"批次大小: {args.batch}")
    print("="*60)
    
    exporter = OpenMetadataRESTExporter(args.host, args.token)
    filename = exporter.export_to_excel(args.schema, args.columns, args.output, args.batch)
    
    if filename:
        print("\n" + "="*60)
        print("✅ 导出完成！")
        print("="*60)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
