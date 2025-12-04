
from open_metadata_lineage import open_metadata
from metadata.generated.schema.entity.data.table import Table


# 1. 确保地址以 /api 结尾
hostPort = "http://192.168.100.214:4728/api"

# 2. 填入刚才复制的一长串 JWT Token
# jwtToken = "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImxpbmVhZ2UtYm90Iiwicm9sZXMiOlsiTGluZWFnZUJvdFJvbGUiXSwiZW1haWwiOiJsaW5lYWdlLWJvdEBvcGVuLW1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3NjQ1OTQzNzMsImV4cCI6bnVsbH0.11xQwfZG_zxpAyQ3FUvOAT3sERX1C6fd4DtTPo1Hk9Zi4CuV3da0h6Beazf5RdRupirL00_nsvwhdbYd5sbvkqhwCKAZOR4uY3muKkrqQ8b7T4MLPuK9bSr5oo3P13orJXkjYaX1kSfO-d33TgFDs3FMKT2_f3m3ZGXngK8KQw9p7CYHnmEKSYJaDGdcwKxUm06zr7sUozCFYgg967qRxORhZS9uSGfcONoomReqmtqShiTR0hXREa1cvAfzMVIKAgO-XoDtzwL2tLuEdjCnbOTrh359sHBDMDjgwm2GVyAjimr9sTcM_nsEBhZgwKKAlXotbNEZIuoRe7ixTtGIKQ"
jwtToken = "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImluZ2VzdGlvbi1ib3QiLCJyb2xlcyI6WyJJbmdlc3Rpb25Cb3RSb2xlIl0sImVtYWlsIjoiaW5nZXN0aW9uLWJvdEBvcGVuLW1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3NjQ1OTQzNzQsImV4cCI6bnVsbH0.DjdPZqRmTQyrZGqJ4iPO2RHstVggQHvIxZ8MdpjbcXEjFcqdhrsF0sbU471oMpoh2SyoZc7kMUiYIMjpqpFKRPPrlj0qJuGwdX1DHoKyGHUESf2ZDIky39HCSvMXv0-Hg-yqX8pN4xcmVEKlq8RETVdNgnE6jJzlEOYjkZ75tQUKiZ086XMEcycnyR3l3ooVvwIPAeJnPBVf4r_YQ_I19F-C2TOVyIt8K_EbfCecieovZkWDAKIppFTk_M2elAwWkJBeacJXTUf-Q9A2J2VntWe4-G5R1YOmUnkDNiXaam8OcBoWgMkkG8pyosyniGtMlEx6BI1sxLdDRyi5sul1xw"

# 调用函数
metadata = open_metadata(hostPort, jwtToken)

# 测试连接是否成功
try:
    print(f"Connected to OpenMetadata version: {metadata.get_server_version()}")
except Exception as e:
    print(f"Connection failed: {e}")



# [...](asc_slot://start-slot-19)获取一个表实体
# 参数: 实体类型 (Table), Fully Qualified Name (FQN)
# http://192.168.100.214:4728/table/StarRocks_test.default.ads.ads_sv_user_element_exposure_info

# FullyQualifiedEntityName 完全限定实体名称
# 格式: <service_name>.<database_name>.<schema_name>.<table_name>


# 表实体分析：
# https://docs.open-metadata.org/latest/main-concepts/metadata-standard/schemas/entity/data/table


table_fqn = "StarRocks_test.default.ads.ads_sv_user_element_exposure_info"
table_entity = metadata.get_by_name(entity=Table, fqn=table_fqn)

# if table_entity:
#     print(f"Found Table: {table_entity.name.root}")
#     # print(f"Found Table: {table_entity}")
#     print(f"columns : {table_entity.columns}")
#     print(f"Description: {table_entity.description.root if table_entity.description else 'No description'}")
#     print(f"ID: {table_entity.id.root}")

# if table_entity.columns:
#     for col in table_entity.columns.root: print(f"列名: {col.ColumnName.root}, 类型: {col.dataType}")
#
# else:
#     print(f"Table {table_fqn} not found.")


# 访问表的基本信息
print(f"表名: {table_entity.name.root}")
print(f"FQN: {table_entity.fullyQualifiedName.root}")
print(f"表类型: {table_entity.tableType}")

# 访问列信息
if table_entity.columns:
    for col in table_entity.columns.root:
        print(f"列名: {col.name.root}, 类型: {col.dataType}")

# 访问所有者信息
if table_entity.owners:
    for owner in table_entity.owners.root:
        print(f"所有者: {owner.name}")

# 访问数据分析信息
if table_entity.profile:
    print(f"行数: {table_entity.profile.rowCount}")
    print(f"列数: {table_entity.profile.columnCount}")

