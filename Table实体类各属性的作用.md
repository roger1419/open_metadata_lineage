基于官方文档,来详细分析 OpenMetadata 的 Table 实体类各属性的作用:
OpenMetadata Table 实体属性详解
🔑 基础标识属性
id: 表的唯一标识符 (UUID 格式)
name: 表名称,在数据库内应该是唯一的
displayName: 表的显示名称,可以是源服务的标题或标签
fullyQualifiedName (FQN): 完全限定名称,格式为 serviceName.databaseName.schemaName.tableName Open-metadata
description: 表的描述信息 (支持 Markdown 格式)
href: 指向该表资源的链接

📊 表结构属性
tableType: 表类型,可以是 Regular(常规表)、View(视图)、MaterializedView(物化视图)、External(外部表)、Iceberg、Partitioned(分区表)等
columns: 表的列信息数组,包含每列的详细元数据:

name: 列名
dataType: 数据类型 (如 INT, VARCHAR, TIMESTAMP 等)
dataLength: 数据长度(用于 char/varchar 类型)
precision/scale: 数值精度和小数位数
description: 列描述
tags: 列标签
constraint: 列约束 (NULL, NOT_NULL, UNIQUE, PRIMARY_KEY) Open-metadata

tableConstraints: 表级约束,包括主键、外键、唯一约束等
tablePartition: 分区配置信息,包括分区列和分区间隔类型 Open-metadata
schemaDefinition: DDL 语句 (用于表和视图的创建语句)

🔗 关系属性
databaseSchema: 包含此表的数据库 Schema 引用
database: 包含此表的数据库引用
service: 托管此表的数据库服务引用
serviceType: 服务类型 (如 MySQL, PostgreSQL, BigQuery 等)
location: 包含此表的位置引用
locationPath: 外部表和托管表的完整存储路径 Open-metadata

👥 治理属性
owners: 表的所有者列表
tags: 表的标签列表
domain: 资产所属的域
dataProducts: 此实体所属的数据产品列表
certification: 资产认证信息 Open-metadata
followers: 关注此表的用户列表
votes: 对实体的投票信息

📈 使用情况和分析
usageSummary: 表的最新使用情况信息
joins: 此表与其他表的连接详情,包括:

columnJoins: 列级别的连接信息
directTableJoins: 表级别的连接 (如 UNION 连接)

sampleData: 表的示例数据
profile: 最新的数据分析结果,包括:

rowCount: 行数
columnCount: 列数
sizeInByte: 表大小
customMetrics: 自定义指标 Open-metadata


🧪 质量和测试
testSuite: 与此表关联的可执行测试套件
customMetrics: 为表注册的自定义指标列表
tableProfilerConfig: 表分析器配置,用于包含或排除特定列的分析 Open-metadata

🏗️ 建模信息
dataModel: 表的建模信息 (目前支持 dbt 和 DDL 模型):

modelType: 模型类型 (dbt 或 DDL)
resourceType: 模型的资源类型
path: SQL 定义文件路径
rawSql: 原始 SQL
sql: 编译后的 SQL
upstream: 上游依赖的模型/表
columns: 建模期间定义的列 Open-metadata


🕐 版本和历史
version: 实体的元数据版本号
updatedAt: 最后更新时间 (Unix 时间戳毫秒)
updatedBy: 进行更新的用户
changeDescription: 导致当前版本的变更描述 Open-metadata
incrementalChangeDescription: 增量变更描述

🗃️ 存储和生命周期
fileFormat: 文件格式 (用于文件/数据湖表),如 csv, parquet, json 等
retentionPeriod: 数据保留期 (ISO 8601 格式),未设置时从父 Schema 继承
lifeCycle: 实体的生命周期属性 Open-metadata
deleted: 是否已软删除

🔧 扩展属性
extension: 添加到实体的自定义属性扩展数据
sourceUrl: 表的源 URL
sourceHash: 实体的源哈希值 Open-metadata

使用示例
python# 访问表的基本信息
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
这个实体类设计非常全面,涵盖了数据治理、质量管理、血缘追踪、使用分析等多个维度的元数据信息。