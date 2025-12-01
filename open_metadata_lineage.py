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
    'host': '192.168.31.130',
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

hostPort = "http://meta.fixpng.com/api"

jwtToken: str = (
"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)

# 延迟初始化 METADATA，避免导入时连接失败
METADATA = None

def get_metadata_client():
    """获取或初始化 OpenMetadata 客户端"""
    global METADATA
    if METADATA is None:
        METADATA = open_metadata(hostPort, jwtToken)
        try:
            print("Health check result:", METADATA.health_check())
        except Exception as e:
            print(f"Warning: OpenMetadata health check failed: {e}")
    return METADATA

# 为了向后兼容，在非导入时初始化
if __name__ != "__main__":
    try:
        METADATA = open_metadata(hostPort, jwtToken)
        print("Health check result:", METADATA.health_check())
    except Exception as e:
        print(f"Warning: Could not connect to OpenMetadata: {e}")
        print("METADATA client will be initialized on first use.")

# 数据库连接函数-mysql
def create_mysql_connection(host, port, database, user, password):
    return pymysql.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        connect_timeout=1
    )

# 使用正则表达式提取 SELECT 和 FROM 之间的字段
def extract_columns_from_sql(query_sql):
    match = re.search(r'select\s+(.*?)\s+from', query_sql, re.IGNORECASE)
    if match:
        columns_str = match.group(1)
        columns = [col.strip() for col in columns_str.split(',')]
        return columns
    return []


# 使用正则表达式匹配表名
def extract_table_name_from_sql(sql_query):
    # 匹配包含数据库名和表名的情况，处理反引号和非反引号
    pattern = r'from\s+`?(\w+)`?\.`?(\w+)`?'
    match = re.search(pattern, sql_query, re.IGNORECASE)

    if match:
        # 返回匹配到的数据库名和表名
        schema = match.group(1)
        table = match.group(2)
        return f"{schema}.{table}"
    else:
        return None

def load_url_service_mapping():
    conn = create_mysql_connection(**arch_config)
    cursor = conn.cursor()

    try:
        # 查询所有映射关系
        query = "SELECT url_pattern, service_name FROM open_metadata_url_service"
        cursor.execute(query)
        results = cursor.fetchall()
        
        # 将结果转换为字典
        mapping = {url_pattern: service_name for url_pattern, service_name in results}
        return mapping
    finally:
        cursor.close()
        conn.close()

# 加载映射关系到内存
url_service_mapping = load_url_service_mapping()
# print(url_service_mapping)

# 此处方法，后续增加url与实例名映射关系后再修改
# uat
def get_service_by_url(url):
    # 直接在映射关系中查找
    return_service = None
    for url_pattern, service_name in url_service_mapping.items():
        if url_pattern in url:
            return_service = f'{service_name}'
            break
    
    if return_service == None:
        print(f"No mapping found for URL: {url}")
        return 'uat-starrocks'
    if '.' in return_service:
        return f'"{return_service}"'
    else:
        return return_service
        


# 添加血缘基础方法
def add_lineage( fromTable: str, fromColumn: str, toTable: str, toColumn: str,
                description: str, sqlQuery: str, fromType_= "table", toType_= "table", metadata_ = METADATA, not_first_ = True):

    if  'kafka' in fromType_:
        fromEntity=Topic
        fromType="topic"
    else:
        fromEntity=Table
        fromType="table"

    if 'kafka' in toType_:
        toEntity=Topic
        toType="topic"
    else:
        toEntity=Table
        toType="table"
        
    metaFromTable = metadata_.get_by_name(entity=fromEntity, fqn=fromTable)
    if metaFromTable is None:
        return ('上游表不存在：' + fromTable)

    metaToTable = metadata_.get_by_name(entity=toEntity, fqn=toTable)
    if metaToTable is None:
        return ('下游表不存在：' + toTable)

    # 定义正则表达式模式，匹配任何被圆括号包围的内容
    pattern = r'\(.*?\)'
    # 检查 fromColumn 或 toColumn 是否包含函数
    if re.search(pattern, fromColumn) or re.search(pattern, toColumn):
        return f'字段存在函数, 跳过：{fromColumn},{toColumn}'

    # 获取现有血缘关系
    # existing_lineage = metadata.get_lineage_by_id(Table,metaFromTable.id.root)
    # print(existing_lineage)
    if '*' in fromColumn or '*' in toColumn or fromType=="topic" or toType=="topic":
        columnsLineage=[]
    else:
        columnsLineage=[ColumnLineage(fromColumns=[f"{fromTable}.{fromColumn}"],toColumn=f"{toTable}.{toColumn}")]

    new_edge = EntitiesEdge(
        fromEntity=EntityReference(id=metaFromTable.id, type=fromType),
        toEntity=EntityReference(id=metaToTable.id, type=toType),
        lineageDetails=LineageDetails(
            description=description,
            sqlQuery=sqlQuery,
            columnsLineage=columnsLineage,
            source="PipelineLineage"
        ),
    )
    
    try:
        add_lineage_request = AddLineageRequest(edge=new_edge)
        metadata_.add_lineage(data=add_lineage_request, check_patch= not_first_)  # check_patch 是否保留旧血缘？
    except Exception as exc:
        return (f"血缘添加失败,异常:{exc}")

    return '血缘添加成功'


# SQL 添加血缘 - 优化版本
def add_lineage_by_sql(database_service: str, database_name: str, sql: str, metadata_=None, description_="SQL", schema_name='default'):
    if metadata_ is None:
        metadata_ = get_metadata_client()
    """
    使用 OpenMetadata SDK 的 LineageMixin.add_lineage_by_query 方法添加血缘。
    该方法将 SQL 发送至 OpenMetadata 服务端进行解析和血缘构建，支持更准确的 SQL 方言解析。
    
    参数:
        database_service: 数据库服务名称（如 'Test-MySQL', 'uat-starrocks'）
        database_name: 数据库名称，如果为 None 则使用 'default'
        sql: SQL 查询语句
        metadata_: OpenMetadata 客户端实例
        description_: 血缘描述信息
        schema_name: Schema 名称，默认为 'default'
    
    参考: https://docs.open-metadata.org/latest/sdk/python/api-reference/lineage-mixin
    """
    print("=========SQL 血缘解析开始 (服务端解析)=============")
    print(f"Service: {database_service}, DB: {database_name}, Schema: {schema_name}")
    print(f"SQL: {sql[:200]}..." if len(sql) > 200 else f"SQL: {sql}")
    
    # 处理数据库名称
    if database_name is None or database_name == '':
        database_name = 'default'
    
    try:
        # 调用 SDK 的 add_lineage_by_query 方法
        # 该方法会自动：
        # 1. 解析 SQL 语句（支持多种方言）
        # 2. 提取表和字段级血缘关系
        # 3. 自动关联到 OpenMetadata 中的实体
        metadata_.add_lineage_by_query(
            service_name=database_service,
            query=sql,
            database_name=database_name,
            schema_name=schema_name,
            timeout_seconds=60  # 设置超时时间
        )
        print("✓ SQL 血缘已成功提交至 OpenMetadata 服务端解析")
        return True
        
    except Exception as exc:
        print(f"✗ 服务端血缘解析失败: {exc}")
        print("→ 尝试使用本地 sqllineage 解析作为备选方案...")
        return _add_lineage_by_sql_local_fallback(database_service, database_name, sql, metadata_, description_, schema_name)
    
    finally:
        print("=========SQL 血缘解析结束=============\n")


def _add_lineage_by_sql_local_fallback(database_service: str, database_name: str, sql: str, metadata_=METADATA, description_="SQL", schema_name='default'):
    """
    本地 SQL 解析备选方案，使用 sqllineage 库进行解析
    当服务端解析失败时使用
    """
    try:
        # 清理 SQL 语句
        cleaned_sql = sql.replace('`', '').strip()
        
        # 使用 sqllineage 解析
        result = LineageRunner(cleaned_sql, dialect="ansi")
        lineage = result.get_column_lineage()
        
        if database_name is None or database_name == '':
            database_name = 'default'
        
        # 遍历字段级血缘
        column_rank = 0
        success_count = 0
        fail_count = 0
        
        for columnTuples in lineage:
            column_rank += 1
            
            # 解析上下游字段和表
            for column in columnTuples:
                if columnTuples.index(column) == len(columnTuples) - 1:
                    # 下游字段
                    downStreamFieldName = str(column.raw_name)
                    downStreamTableName = str(column).replace(f'.{downStreamFieldName}', '').replace('<default>', database_name)
                    downStreamFullName = f"{database_service}.{schema_name}.{downStreamTableName}"
                else:
                    # 上游字段
                    upStreamFieldName = str(column.raw_name)
                    upStreamTableName = str(column).replace(f'.{upStreamFieldName}', '').replace('<default>', database_name)
                    upStreamFullName = f"{database_service}.{schema_name}.{upStreamTableName}"
            
            # 添加血缘关系
            result_msg = add_lineage(
                upStreamFullName, upStreamFieldName, 
                downStreamFullName, downStreamFieldName, 
                description_, cleaned_sql,
                metadata_=metadata_,
                not_first_=(column_rank != 1)
            )
            
            if '成功' in result_msg:
                success_count += 1
                print(f"  ✓ {upStreamTableName}.{upStreamFieldName} -> {downStreamTableName}.{downStreamFieldName}")
            else:
                fail_count += 1
                print(f"  ✗ {upStreamTableName}.{upStreamFieldName} -> {downStreamTableName}.{downStreamFieldName}: {result_msg}")
        
        print(f"本地解析完成: 成功 {success_count}, 失败 {fail_count}")
        return success_count > 0
        
    except Exception as exc:
        print(f"✗ 本地 SQL 解析也失败: {exc}")
        import traceback
        traceback.print_exc()
        return False


# DATAX JSON 添加血缘 - 优化版本
def add_lineage_by_datax_json(datax_json: json, metadata_=METADATA, description_='DolphinScheduler-DATAX'):
    """
    解析 DataX JSON 配置并添加血缘关系
    支持字段级血缘映射
    
    返回:
        bool: 是否成功添加血缘
    """
    print("=========DATAX 血缘解析开始=============")
    
    try:
        # 解析 DataX 配置
        content = datax_json['job']['content'][0]
        reader = content['reader']
        writer = content['writer']
        
        # 获取 Reader 配置
        reader_param = reader['parameter']
        reader_connection = reader_param['connection'][0]
        
        # 支持多种 Reader 配置格式
        if 'querySql' in reader_connection and reader_connection['querySql']:
            query_sql = reader_connection['querySql'][0]
            use_query_sql = True
        elif 'table' in reader_connection and reader_connection['table']:
            # 如果没有 querySql，使用 table 配置
            reader_table = reader_connection['table'][0] if isinstance(reader_connection['table'], list) else reader_connection['table']
            query_sql = f"SELECT * FROM {reader_table}"
            use_query_sql = False
        else:
            print("  ✗ 无法获取 Reader 表信息")
            return False
        
        # 获取上下游 URL
        from_url = reader_connection['jdbcUrl'][0] if isinstance(reader_connection['jdbcUrl'], list) else reader_connection['jdbcUrl']
        to_url = writer['parameter']['jdbcUrl']
        
        print(f"  上游 URL: {from_url}")
        print(f"  下游 URL: {to_url}")
        
        from_service = get_service_by_url(from_url)
        to_service = get_service_by_url(to_url)
        
        print(f"  上游 Service: {from_service}")
        print(f"  下游 Service: {to_service}")
        
        # 解析上游数据库和表名
        if use_query_sql:
            from_table_full = extract_table_name_from_sql(query_sql)
            if from_table_full and '.' in from_table_full:
                from_db, from_table = from_table_full.split('.', 1)
            else:
                from_db = 'default'
                from_table = from_table_full if from_table_full else 'unknown'
        else:
            from_db = 'default'
            from_table = reader_table
        
        # 解析下游数据库和表名
        to_db = writer['parameter'].get('database', 'default')
        to_table = writer['parameter']['table']
        
        # 构建完整表名（FQN）
        from_table_fqn = f"{from_service}.default.{from_db}.{from_table}"
        to_table_fqn = f"{to_service}.default.{to_db}.{to_table}"
        
        print(f"  上游表: {from_table_fqn}")
        print(f"  下游表: {to_table_fqn}")
        
        # 提取字段映射
        reader_columns = extract_columns_from_sql(query_sql) if use_query_sql else reader_param.get('column', ['*'])
        writer_columns = writer['parameter'].get('column', ['*'])
        
        # 处理通配符
        if writer_columns == ['*']:
            writer_columns = reader_columns
            print(f"  下游字段为 *，使用上游字段: {len(reader_columns)} 个")
        
        if reader_columns == ['*'] or writer_columns == ['*']:
            # 如果仍有通配符，只添加表级血缘
            print(f"  → 添加表级血缘（字段为通配符）")
            result = add_lineage(
                from_table_fqn, "*", 
                to_table_fqn, "*", 
                description_, query_sql, 
                metadata_=metadata_,
                not_first_=False
            )
            print(f"  表级血缘: {result}")
            return '成功' in result
        
        # 验证字段数量
        if len(reader_columns) != len(writer_columns):
            print(f"  ⚠ 上下游字段数量不一致: {len(reader_columns)} vs {len(writer_columns)}")
            print(f"  → 仅添加表级血缘")
            result = add_lineage(
                from_table_fqn, "*", 
                to_table_fqn, "*", 
                description_, query_sql, 
                metadata_=metadata_,
                not_first_=False
            )
            return '成功' in result
        
        # 添加字段级血缘
        print(f"  → 添加字段级血缘: {len(reader_columns)} 个字段映射")
        success_count = 0
        fail_count = 0
        
        for i in range(len(reader_columns)):
            from_column = reader_columns[i].strip()
            to_column = writer_columns[i].strip()
            
            result = add_lineage(
                from_table_fqn, from_column, 
                to_table_fqn, to_column, 
                description_, query_sql, 
                metadata_=metadata_,
                not_first_=(i != 0)
            )
            
            if '成功' in result:
                success_count += 1
                print(f"    ✓ {from_column} -> {to_column}")
            else:
                fail_count += 1
                print(f"    ✗ {from_column} -> {to_column}: {result}")
        
        print(f"  字段级血缘: 成功 {success_count}, 失败 {fail_count}")
        print("=========DATAX 血缘解析完成=============\n")
        
        return success_count > 0
        
    except KeyError as exc:
        print(f"  ✗ DataX JSON 格式错误，缺少必要字段: {exc}")
        return False
    except Exception as exc:
        print(f"  ✗ DATAX 血缘解析失败: {exc}")
        import traceback
        traceback.print_exc()
        return False


# 用于存储 FlinkSQL 内存表与实际表及其连接信息的映射


# Flink SQL 解析 CREATE TABLE 语句
def flinksql_extract_table_info(flink_sql_segment,flinksql_table_mapping):

    # 使用正则忽略大小写，并去掉不必要的空格，提取表名及配置信息
    source_pattern = r"create\s+table\s+`?([\w\-\.]+)`?\s*\(.*?\)\s*with\s*\((.*?)\)"
    source_match = re.search(source_pattern, flink_sql_segment, re.IGNORECASE | re.DOTALL)

    if source_match:
        flink_table_name = source_match.group(1).strip()  # 提取表名并去除空格
        # print(flink_table_name)

        # 提取连接信息，使用逗号分隔
        table_info_raw = source_match.group(2).split(',')
        table_info = {}

        for item in table_info_raw:
            # 移除多余的空格并拆分成键值对
            key_value = item.split('=', 1)
            if len(key_value) == 2:
                key = key_value[0].strip().strip("'")
                value = key_value[1].strip().strip("'")
                table_info[key] = value
        # print(source_match.group(2))
        # print(table_info)

        # 判断连接器类型，生成对应的 URL
        try:
            connector_type = table_info.get('connector')
            if connector_type == 'mysql-cdc':
                table_info[
                    'url'] = f"mysql://{table_info['hostname']}:{table_info['port']}/{table_info['database-name']}"
            elif connector_type == 'mongodb-cdc':
                table_info['url'] = f"mongodb://{table_info['hosts']}/{table_info['database']}"
                table_info['table-name'] = table_info.get('collection')
                table_info['database-name'] = table_info.get('database')
            elif connector_type == 'starrocks':
                table_info['url'] = f"starrocks://{table_info['load-url']}/{table_info['database-name']}"
            elif connector_type == 'jdbc':
                table_info['url'] = table_info['url']
                table_info['table-name'] = table_info['table-name']
            elif connector_type == 'kafka':
                table_info['url'] = table_info['properties.bootstrap.servers']
                table_info['table-name'] = table_info['topic']

            else:
                print(f"未支持解析的 FlinkCDC 类型: {table_info['connector']}")
                return None, None
        except Exception as exc:
            print(table_info)
            print(f"Flink SQL URL 解析失败,异常:{exc}")
            return None, None

        # 将表名和对应信息存储到table_mapping中，使用小写表名避免大小写问题
        flinksql_table_mapping[flink_table_name.lower()] = table_info

        # 返回内存表名称和表信息
        return flink_table_name, table_info
    return None, None


# Flink SQL 解析 INSERT ... SELECT 语句
def flinksql_parse_insert_select_sql(sql, flinksql_table_mapping, metadata_= METADATA, description_='FlinkSQL'):
    result = LineageRunner(sql.lower().replace('`', ''), dialect="ansi")  # 强制小写处理 SQL 语句
    try:
        lineage = result.get_column_lineage()
    except Exception as exc:
        print(f"Flink SQL 解析失败,异常:{exc}")
        return
    
    column_rank = 0
    for columnTuples in lineage:
        column_rank += 1
        for column in columnTuples:
            if columnTuples.index(column) == len(columnTuples) - 1:
                downStreamFieldName = column.raw_name.__str__()
                downStreamTableName = column.__str__().replace(f".{downStreamFieldName}", "")
            else:
                upStreamFieldName = column.raw_name.__str__()
                upStreamTableName = column.__str__().replace(f".{upStreamFieldName}", "")

        # 查找表名对应的连接信息
        upstream_info = flinksql_table_mapping.get(upStreamTableName.lower().replace('<default>.', ''), {})
        downstream_info = flinksql_table_mapping.get(downStreamTableName.lower().replace('<default>.', ''), {})

        up_database_name = upstream_info.get('database-name', upStreamTableName)
        up_table_name = upstream_info.get('table-name', upStreamTableName) #.replace('prod','test')
        up_service = get_service_by_url(upstream_info.get('url', '<unknown>'))
        up_type = upstream_info.get('connector', upStreamTableName)

        down_database_name = downstream_info.get('database-name', downStreamTableName)
        down_table_name = downstream_info.get('table-name', downStreamTableName)
        down_service = get_service_by_url(downstream_info.get('url', '<unknown>'))
        down_type = downstream_info.get('connector', downStreamTableName)

        if up_type=='kafka':
            fromTable = f"{up_service}.{up_table_name}"
        else:
            fromTable = f"{up_service}.default.{up_database_name}.{up_table_name}"
        
        if down_type =='kafka':
            toTable = f"{down_service}.{down_table_name}"
        else:
            toTable = f"{down_service}.default.{down_database_name}.{down_table_name}"

        result = add_lineage(fromTable, upStreamFieldName, toTable, downStreamFieldName, description_, sql, fromType_=up_type,toType_=down_type , metadata_=metadata_, not_first_= (column_rank!=1))
        print(f"{fromTable}.{upStreamFieldName} -> {toTable}.{downStreamFieldName} : {result}")


# 处理整个 Flink SQL
def add_lineage_by_flink_sql(raw_flink_sql,metadata_ = METADATA, description_='FlinkSQL'):
    # 使用正则表达式替换掉每行的注释、去掉多余的空行
    flink_sql = re.sub(r'--.*$', '', raw_flink_sql, flags=re.MULTILINE)
    flink_sql = re.sub(r'\n\s*\n', '\n\n', flink_sql)
    # 去掉每行末尾的多余空格
    flink_sql = re.sub(r'\s+$', '', flink_sql, flags=re.MULTILINE)

    print("=========FlinkSQL血缘解析开始=============")
    statements = flink_sql.strip().split(';\n')
    flinksql_table_mapping = {}
    for statement in statements:
        statement = statement.strip()
        # print(f"FlinkSQL: \n{statement}")
        # print("-------------------")
        if statement.lower().startswith('create table'):
            flink_table_name, table_info = flinksql_extract_table_info(statement,flinksql_table_mapping)
            if flink_table_name and table_info:
                print(f"Flink内存表名称: {flink_table_name}")
                print(f"实际表名称: {table_info.get('table-name', 'N/A')}")
                print(f"实际库名称: {table_info.get('database-name', 'N/A')}")
                print(f"连接地址: {table_info.get('url', 'N/A')}")
                print('----------------------')
        elif statement.lower().startswith('insert'):
            flinksql_parse_insert_select_sql(statement,flinksql_table_mapping, metadata_=metadata_,description_=description_)
    print("=========FlinkSQL血缘解析结束=============")


# 解析 canal 的 instance.propertios 获取血缘
def add_lineage_by_canal_propertios(propertios, metadata_= METADATA, description_='Canal'):
    match = re.search(r'canal\.instance\.master\.address=(.*)', propertios)
    if match:
        instance_url = match.group(1).strip()
        service = get_service_by_url(instance_url)
        print(service)
    else:
        print(f"数据源有误:{match}")
        return
    
    # Extract the dynamic topic section
    dynamic_topic_section = re.search(r'canal\.mq\.dynamicTopic=([\s\S]*?)(?:\n\n|\Z)', propertios)
    if not dynamic_topic_section:
        print(f"无 dynamicTopic")
        return

    # Parse the dynamic topic section
    pattern = re.compile(r'(\S+):(\S+)')
    matches = pattern.findall(dynamic_topic_section.group(1))
    
    for topic, table in matches:
        # Remove escape characters from the topic and table names
        topic = re.sub(r'\\[rn]', '', topic.strip())
        table = re.sub(r'\\[rn]', '', table.strip())
        
        fromTable = f"{service}.default.{table}".replace('\\','').replace(',','')
        
        kafka_service = get_service_by_url('kafka')
        toTable = f"{kafka_service}.{topic}".replace('\\','').replace(',','')#.replace('prod','test')
        result = add_lineage(fromTable, "*", toTable, "*", description_ , "", toType_="kafka" ,metadata_ = metadata_ ,not_first_= False)
        print(f"{fromTable} -> {toTable} : {result}")