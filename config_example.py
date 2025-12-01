# -*- coding: utf-8 -*-
"""
配置文件示例
请复制此文件为 config.py 并填入实际配置信息
"""

# ==================== OpenMetadata 配置 ====================
OPENMETADATA_CONFIG = {
    'host_port': 'http://meta.fixpng.com/api',
    'jwt_token': 'your_jwt_token_here',
}

# ==================== DolphinScheduler 配置 ====================
DOLPHINSCHEDULER_CONFIG = {
    'url': 'https://uatds.fixpng.com/dolphinscheduler',
    'username': 'admin',
    'password': 'your_password_here',
}

# ==================== StreamPark 配置 ====================
STREAMPARK_CONFIG = {
    'url': 'https://uatstreampark.fixpng.com',
    'username': 'admin',
    'password': 'your_password_here',
}

# ==================== Canal 配置 ====================
CANAL_CONFIG = {
    'url': 'https://uatcanal.fixpng.com',
    'username': 'admin',
    'password': 'your_password_here',
}

# ==================== Archery 数据库配置 ====================
# 用于获取数据库实例信息和 URL 映射
ARCHERY_DB_CONFIG = {
    'host': '192.168.31.130',
    'port': 3306,
    'database': 'archery',
    'user': 'archery',
    'password': 'your_password_here',
}

# ==================== URL 映射数据库配置 ====================
# 用于存储 URL 与服务名称的映射关系
URL_MAPPING_DB_CONFIG = {
    'host': '192.168.31.130',
    'port': 3306,
    'database': 'my_test',
    'user': 'root',
    'password': 'your_password_here',
}

# ==================== 血缘提取配置 ====================
LINEAGE_CONFIG = {
    # 是否启用各平台的血缘提取
    'enable_dolphinscheduler': True,
    'enable_streampark': True,
    'enable_canal': True,
    
    # 是否启用 StarRocks 专用处理器
    'enable_starrocks_handler': True,
    
    # SQL 解析超时时间（秒）
    'sql_parse_timeout': 60,
    
    # 是否在失败时使用本地解析备选方案
    'enable_local_fallback': True,
    
    # 日志级别: DEBUG, INFO, WARNING, ERROR
    'log_level': 'INFO',
}

# ==================== 数据库服务映射配置 ====================
# 用于将 JDBC URL 映射到 OpenMetadata 服务名称
# 格式: 'URL模式': 'OpenMetadata服务名称'
SERVICE_MAPPING = {
    # StarRocks
    'uatstarrocks.fixpng.com:9030': 'uat-starrocks',
    'uatstarrocks.fixpng.com:8030': 'uat-starrocks',
    
    # MySQL
    '192.168.31.133:6033': 'uat-mysql-01',
    '192.168.31.135:3306': 'uat-mysql-02',
    
    # MongoDB
    'mongo.fixpng.com:27017': 'uat-mongodb',
    
    # Kafka
    'hwuat-kafka01.fixpng.com:9092': 'uat-kafka',
    'hwuat-kafka02.fixpng.com:9092': 'uat-kafka',
    'hwuat-kafka03.fixpng.com:9092': 'uat-kafka',
}

# ==================== 任务过滤配置 ====================
TASK_FILTER = {
    # 排除的项目名称（支持正则表达式）
    'exclude_projects': [
        '.*测试.*',
        '.*test.*',
        '.*下线.*',
    ],
    
    # 排除的任务类型
    'exclude_task_types': [
        'SHELL',
        'PYTHON',
        'SPARK',
    ],
    
    # 只处理特定的任务类型（为空则处理所有支持的类型）
    'include_task_types': [
        'SQL',
        'DATAX',
    ],
}

# ==================== 重试配置 ====================
RETRY_CONFIG = {
    # 最大重试次数
    'max_retries': 3,
    
    # 重试间隔（秒）
    'retry_interval': 5,
    
    # 是否在失败时继续处理下一个任务
    'continue_on_error': True,
}

# ==================== 性能配置 ====================
PERFORMANCE_CONFIG = {
    # 批量处理大小
    'batch_size': 100,
    
    # 并发处理数（谨慎使用，可能导致 API 限流）
    'concurrent_workers': 1,
    
    # API 请求超时时间（秒）
    'api_timeout': 30,
}
