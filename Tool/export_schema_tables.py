from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import OpenMetadataConnection, AuthProvider
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import OpenMetadataJWTClientConfig
from metadata.generated.schema.entity.data.table import Table
from metadata.generated.schema.entity.data.databaseSchema import DatabaseSchema
import pandas as pd
from datetime import datetime

# 1. 连接配置
hostPort = "http://192.168.100.214:4728/api"
jwtToken = "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImluZ2VzdGlvbi1ib3QiLCJyb2xlcyI6WyJJbmdlc3Rpb25Cb3RSb2xlIl0sImVtYWlsIjoiaW5nZXN0aW9uLWJvdEBvcGVuLW1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3NjQ1OTQzNzQsImV4cCI6bnVsbH0.DjdPZqRmTQyrZGqJ4iPO2RHstVggQHvIxZ8MdpjbcXEjFcqdhrsF0sbU471oMpoh2SyoZc7kMUiYIMjpqpFKRPPrlj0qJuGwdX1DHoKyGHUESf2ZDIky39HCSvMXv0-Hg-yqX8pN4xcmVEKlq8RETVdNgnE6jJzlEOYjkZ75tQUKiZ086XMEcycnyR3l3ooVvwIPAeJnPBVf4r_YQ_I19F-C2TOVyIt8K_EbfCecieovZkWDAKIppFTk_M2elAwWkJBeacJXTUf-Q9A2J2VntWe4-G5R1YOmUnkDNiXaam8OcBoWgMkkG8pyosyniGtMlEx6BI1sxLdDRyi5sul1xw"

# 2. 创建连接
def create_metadata_connection(hostPort: str, jwt_token: str):
    """创建 OpenMetadata 连接"""
    server_config = OpenMetadataConnection(
        hostPort=hostPort,
        authProvider=AuthProvider.openmetadata,
        securityConfig=OpenMetadataJWTClientConfig(jwtToken=jwt_token),
    )
    return OpenMetadata(server_config)

metadata = create_metadata_connection(hostPort, jwtToken)

# 3. 目标 Schema FQN
schema_fqn = "StarRocks_test.default.ads"

def safe_get_value(obj, max_length=None):
    """
    安全地获取对象的值，处理各种类型

    Args:
        obj: 要处理的对象
        max_length: 最大长度限制

    Returns:
        str: 处理后的字符串
    """
    if obj is None:
        return 'N/A'

    try:
        # 如果对象有 root 属性，优先使用
        if hasattr(obj, 'root'):
            value = str(obj.root)
        # 如果对象有 __root__ 属性
        elif hasattr(obj, '__root__'):
            value = str(obj.__root__)
        else:
            value = str(obj)

        # 处理长度限制
        if max_length and len(value) > max_length:
            return value[:max_length] + '...'
        return value
    except Exception as e:
        return f'Error: {str(e)[:50]}'

def get_schema_tables(metadata, schema_fqn):
    """
    获取指定 Schema 下的所有表信息

    Args:
        metadata: OpenMetadata 客户端实例
        schema_fqn: Schema 的完全限定名称

    Returns:
        list: 包含所有表信息的字典列表
    """
    try:
        # 获取 Schema 实体
        schema_entity = metadata.get_by_name(entity=DatabaseSchema, fqn=schema_fqn)

        if not schema_entity:
            print(f"❌ 未找到 Schema: {schema_fqn}")
            return []

        # 安全提取 Schema 名称
        schema_name = safe_get_value(schema_entity.name)
        print(f"✅ 找到 Schema: {schema_name}")
        print(f"📊 开始获取表信息...\n")

        # 存储所有表信息
        tables_data = []

        # 列出该 Schema 下的所有表
        # 使用 list_entities 方法
        tables_list = metadata.list_entities(
            entity=Table,
            fields=["owners", "tags", "usageSummary", "profile", "database", "databaseSchema", "service"],
            limit=1000  # 可根据实际情况调整
        )

        # 过滤出属于目标 Schema 的表
        table_count = 0
        for table in tables_list.entities:
            # 检查表是否属于目标 Schema
            if table.databaseSchema:
                # 安全提取 Schema FQN
                schema_fqn_value = safe_get_value(table.databaseSchema.fullyQualifiedName) if hasattr(table.databaseSchema, 'fullyQualifiedName') else None
                
                if schema_fqn_value == schema_fqn:
                    table_count += 1
                    # 安全提取表名用于显示
                    table_name = safe_get_value(table.name)
                    print(f"处理表 {table_count}: {table_name}")

                    # 提取表信息
                    table_info = {
                        '序号': table_count,
                        '表名': safe_get_value(table.name),
                        '显示名称': safe_get_value(table.displayName) if table.displayName else safe_get_value(table.name),
                        '完全限定名': safe_get_value(table.fullyQualifiedName),
                        '表类型': safe_get_value(table.tableType) if table.tableType else 'N/A',
                        '描述': safe_get_value(table.description, max_length=200) if table.description else '无描述',
                        '列数': len(table.columns) if table.columns else 0,
                        '行数': table.profile.rowCount if table.profile and hasattr(table.profile, 'rowCount') else 'N/A',
                        '表大小(字节)': table.profile.sizeInByte if table.profile and hasattr(table.profile, 'sizeInByte') else 'N/A',
                        '所有者': (', '.join([safe_get_value(owner.name) if hasattr(owner, 'name') else str(owner) for owner in (table.owners if not isinstance(table.owners, tuple) else table.owners[1] if len(table.owners) > 1 else [])]) if table.owners and (not isinstance(table.owners, tuple) or len(table.owners) > 1) else '未设置'),
                        '标签': (', '.join([safe_get_value(tag.tagFQN) if hasattr(tag, 'tagFQN') else str(tag) for tag in (table.tags if not isinstance(table.tags, tuple) else table.tags[1] if len(table.tags) > 1 else [])]) if table.tags and (not isinstance(table.tags, tuple) or len(table.tags) > 1) else '无'),
                        '服务名称': safe_get_value(table.service.name) if table.service else 'N/A',
                        '服务类型': safe_get_value(table.serviceType) if table.serviceType else 'N/A',
                        '数据库': safe_get_value(table.database.name) if table.database else 'N/A',
                        'Schema': safe_get_value(table.databaseSchema.name) if table.databaseSchema else 'N/A',
                        '版本': safe_get_value(table.version) if table.version else 'N/A',
                        '更新时间': table.updatedAt.strftime('%Y-%m-%d %H:%M:%S') if table.updatedAt and hasattr(table.updatedAt, 'strftime') else (datetime.fromtimestamp(table.updatedAt / 1000).strftime('%Y-%m-%d %H:%M:%S') if isinstance(table.updatedAt, (int, float)) else 'N/A'),
                        '更新者': safe_get_value(table.updatedBy) if table.updatedBy else 'N/A',
                        '是否已删除': '是' if table.deleted else '否',
                        'URL': f"{hostPort.replace('/api', '')}/table/{safe_get_value(table.fullyQualifiedName)}"
                    }

                    # 添加使用情况信息
                    if table.usageSummary:
                        table_info['日使用次数'] = table.usageSummary.dailyStats.count if hasattr(table.usageSummary, 'dailyStats') else 'N/A'
                        table_info['周使用次数'] = table.usageSummary.weeklyStats.count if hasattr(table.usageSummary, 'weeklyStats') else 'N/A'
                    else:
                        table_info['日使用次数'] = 'N/A'
                        table_info['周使用次数'] = 'N/A'

                    tables_data.append(table_info)

        print(f"\n✅ 共找到 {table_count} 个表")
        return tables_data

    except Exception as e:
        print(f"❌ 获取表信息时出错: {e}")
        import traceback
        traceback.print_exc()
        return []

def export_to_excel(tables_data, schema_fqn):
    """
    将表信息导出到 Excel

    Args:
        tables_data: 表信息列表
        schema_fqn: Schema 的完全限定名称
    """
    if not tables_data:
        print("⚠️  没有数据可导出")
        return

    try:
        # 创建 DataFrame
        df = pd.DataFrame(tables_data)

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        schema_name = schema_fqn.replace('.', '_')
        filename = f"OpenMetadata_Tables_{schema_name}_{timestamp}.xlsx"

        # 导出到 Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Tables', index=False)

            # 获取工作表
            worksheet = writer.sheets['Tables']

            # 调整列宽
            for idx, col in enumerate(df.columns, 1):
                # 根据列内容调整宽度
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                )
                # 设置最大宽度为50，最小为10
                adjusted_width = min(max(max_length + 2, 10), 50)
                worksheet.column_dimensions[chr(64 + idx)].width = adjusted_width

        print(f"\n✅ 数据已成功导出到: {filename}")
        print(f"📊 导出记录数: {len(tables_data)}")

    except Exception as e:
        print(f"❌ 导出 Excel 时出错: {e}")
        import traceback
        traceback.print_exc()

# 4. 主程序
if __name__ == "__main__":
    print("="*60)
    print("OpenMetadata 表信息导出工具")
    print("="*60)
    print(f"Schema FQN: {schema_fqn}")
    print("="*60 + "\n")

    # 获取表信息
    tables_data = get_schema_tables(metadata, schema_fqn)

    # 导出到 Excel
    if tables_data:
        export_to_excel(tables_data, schema_fqn)

        # 显示前5条数据预览
        print("\n" + "="*60)
        print("📋 数据预览 (前5条)")
        print("="*60)
        df_preview = pd.DataFrame(tables_data[:5])
        # 只显示部分关键列
        key_columns = ['序号', '表名', '表类型', '列数', '行数', '所有者', '更新时间']
        available_columns = [col for col in key_columns if col in df_preview.columns]
        print(df_preview[available_columns].to_string(index=False))
    else:
        print("\n⚠️  未找到任何表数据")