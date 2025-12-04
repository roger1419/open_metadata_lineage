from metadata.generated.schema.entity.data.table import Table



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


# FullyQualifiedEntityName 完全限定实体名称
# 格式: <service_name>.<database_name>.<schema_name>.<table_name>

# 获取表实体
table_fqn = "StarRocks_test.default.ads.ads_sv_user_element_exposure_info"
table_entity = metadata.get_by_name(entity=Table, fqn=table_fqn)

if table_entity:
    print("=" * 60)
    print("📋 基本信息")
    print("=" * 60)
    # 基本属性 - 直接访问,不需要 .root
    print(f"表名: {table_entity.name}")
    print(f"显示名称: {table_entity.displayName}")
    print(f"完全限定名: {table_entity.fullyQualifiedName}")
    print(f"表类型: {table_entity.tableType}")
    print(f"描述: {table_entity.description if table_entity.description else '无描述'}")
    print(f"ID: {table_entity.id}")

    print("\n" + "=" * 60)
    print("📊 列信息")
    print("=" * 60)
    # 访问列信息
    if table_entity.columns:
        for idx, col in enumerate(table_entity.columns, 1):
            print(f"\n列 {idx}:")
            print(f"  - 列名: {col.name.root}")
            print(f"  - 数据类型: {col.dataType}")
            print(f"  - 显示类型: {col.dataTypeDisplay if col.dataTypeDisplay else 'N/A'}")
            print(f"  - 描述: {col.description.root if col.description.root else '无描述'}")
            print(f"  - 约束: {col.constraint if col.constraint else '无约束'}")

            # 访问列的标签
            if col.tags:
                print(f"  - 标签: {[tag.tagFQN for tag in col.tags]}")
    else:
        print("无列信息")

    print("\n" + "=" * 60)
    print("👥 所有者信息")
    print("=" * 60)
    # 访问所有者信息
    if table_entity.owners:
        for owner in table_entity.owners:
            print(f"  - 所有者名称: {owner.name}")
            print(f"  - 所有者类型: {owner.type}")
            print(f"  - 所有者ID: {owner.id}")
    else:
        print("未设置所有者")

    print("\n" + "=" * 60)
    print("🏷️  标签信息")
    print("=" * 60)
    # 访问表级别标签
    if table_entity.tags:
        for tag in table_entity.tags:
            print(f"  - 标签: {tag.tagFQN}")
            print(f"    来源: {tag.source}")
    else:
        print("无标签")

    print("\n" + "=" * 60)
    print("📈 数据分析信息")
    print("=" * 60)
    # 访问数据分析信息
    if table_entity.profile:
        print(f"  - 行数: {table_entity.profile.rowCount}")
        print(f"  - 列数: {table_entity.profile.columnCount}")
        print(f"  - 大小(字节): {table_entity.profile.sizeInByte}")
        print(f"  - 创建时间: {table_entity.profile.createDateTime}")
        print(f"  - 分析时间戳: {table_entity.profile.timestamp}")
    else:
        print("无数据分析信息")

    print("\n" + "=" * 60)
    print("🔗 关系信息")
    print("=" * 60)
    # 访问数据库和服务信息
    if table_entity.database:
        print(f"  - 数据库: {table_entity.database.name}")
        print(f"  - 数据库FQN: {table_entity.database.fullyQualifiedName}")

    if table_entity.databaseSchema:
        print(f"  - Schema: {table_entity.databaseSchema.name}")
        print(f"  - Schema FQN: {table_entity.databaseSchema.fullyQualifiedName}")

    if table_entity.service:
        print(f"  - 服务: {table_entity.service.name}")
        print(f"  - 服务类型: {table_entity.serviceType}")

    print("\n" + "=" * 60)
    print("📊 使用情况")
    print("=" * 60)
    # 访问使用情况摘要
    if table_entity.usageSummary:
        print(f"  - 日期: {table_entity.usageSummary.date}")
        print(f"  - 日使用次数: {table_entity.usageSummary.dailyStats.count}")
        print(f"  - 周使用次数: {table_entity.usageSummary.weeklyStats.count}")
    else:
        print("无使用情况数据")

    print("\n" + "=" * 60)
    print("🔍 其他元数据")
    print("=" * 60)
    # 版本信息
    print(f"  - 版本: {table_entity.version}")
    print(f"  - 更新时间: {table_entity.updatedAt}")
    print(f"  - 更新者: {table_entity.updatedBy}")

    # Schema定义
    if table_entity.schemaDefinition:
        print(f"  - DDL语句: {table_entity.schemaDefinition[:100]}...")  # 只显示前100字符

    # 分区信息
    if table_entity.tablePartition:
        print(f"  - 分区列: {[col.columnName for col in table_entity.tablePartition.columns]}")

    # 约束信息
    if table_entity.tableConstraints:
        for constraint in table_entity.tableConstraints:
            print(f"  - 约束类型: {constraint.constraintType}")
            print(f"    约束列: {constraint.columns}")

    # 关注者
    if table_entity.followers:
        print(f"  - 关注者数量: {len(table_entity.followers)}")
        for follower in table_entity.followers:
            print(f"    - {follower.name}")

else:
    print(f"❌ 未找到表: {table_fqn}")