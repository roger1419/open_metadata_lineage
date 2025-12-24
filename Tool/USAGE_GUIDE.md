# OpenMetadata 工具使用指南

## 概述

本工具集用于从 OpenMetadata 导出表信息和管理血缘关系。

## 工具列表

### 1. export_schema_tables_v2.py
从指定 Schema 导出所有表的元数据信息到 Excel。

### 2. test_production.py
测试生产环境连接。

## 环境配置

### 测试环境
- **地址：** `http://192.168.100.214:4728/api`
- **版本：** OpenMetadata 1.10.10

### 生产环境
- **地址：** `https://openmetadata.changdu.vip/api`
- **版本：** OpenMetadata 1.10.14

## 使用方法

### 测试环境导出

```bash
python Tool/export_schema_tables_v2.py --schema StarRocks_test.default.ads
```

### 生产环境导出

```bash
python Tool/export_schema_tables_v2.py \
  --host https://openmetadata.changdu.vip/api \
  --token YOUR_JWT_TOKEN \
  --schema data_starRocks.default.ads \
  --output D:\Downloads
```

### 测试生产环境连接

```bash
python Tool/test_production.py
```

## 参数说明

| 参数 | 说明 | 必需 | 默认值 |
|------|------|------|--------|
| --host | OpenMetadata 服务器地址 | 否 | http://192.168.100.214:4728/api |
| --token | JWT Token | 否 | 使用默认测试环境 Token |
| --schema | Schema FQN | 是 | - |
| --columns | 是否导出列信息 | 否 | False |
| --output | 输出目录 | 否 | 当前目录 |

## 修复的问题

### 1. root='' 显示问题 ✅

**问题：** 导出内容显示 `root='ads_ab_dbd_svsr_ad_cyc_rev'` 而不是 `ads_ab_dbd_svsr_ad_cyc_rev`

**原因：** OpenMetadata SDK 返回的是 Pydantic 模型对象，直接转字符串会显示 `root=''`

**修复：** 添加 `safe_extract_value()` 函数正确提取值

```python
def safe_extract_value(obj, default='N/A'):
    if obj is None:
        return default
    if isinstance(obj, str):
        return obj
    if hasattr(obj, 'root'):
        return str(obj.root)
    if hasattr(obj, '__root__'):
        return str(obj.__root__)
    return str(obj)
```

### 2. HTTPS 生产环境支持 ✅

**问题：** 生产环境使用 HTTPS，可能有 SSL 证书问题

**修复：** 
- 添加 `verifySSL="no-ssl"` 配置
- 禁用 SSL 警告

```python
server_config = OpenMetadataConnection(
    hostPort=self.host_port,
    authProvider=AuthProvider.openmetadata,
    securityConfig=OpenMetadataJWTClientConfig(jwtToken=self.jwt_token),
    verifySSL="no-ssl"
)
```

### 3. 直接使用 SDK 连接 ✅

**问题：** 之前依赖 `open_metadata_lineage.py` 模块

**修复：** 直接使用 OpenMetadata SDK 创建连接

```python
from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import OpenMetadataConnection, AuthProvider
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import OpenMetadataJWTClientConfig
```

## 测试结果

### 生产环境连接测试 ✅

```
============================================================
测试生产环境连接
============================================================
Host: https://openmetadata.changdu.vip/api
Schema: data_starRocks.default.ads
============================================================

1. 创建连接配置...
   ✓ 配置创建成功

2. 创建 OpenMetadata 客户端...
   ✓ 客户端创建成功

3. 执行健康检查...
   ✓ 健康检查成功: True

4. 获取 Schema: data_starRocks.default.ads...
   ✓ 找到 Schema: ads

============================================================
✅ 生产环境连接测试完成！
============================================================
```

## 注意事项

1. **JWT Token 安全**
   - 不要将 Token 提交到版本控制
   - 生产环境 Token 需要有相应权限

2. **SSL 证书**
   - 生产环境使用 `verifySSL="no-ssl"` 跳过证书验证
   - 如果需要验证证书，请配置正确的 CA 证书

3. **版本兼容性**
   - 测试环境：OpenMetadata 1.10.10
   - 生产环境：OpenMetadata 1.10.14
   - SDK 版本需要与服务器版本兼容

4. **网络连接**
   - 确保能够访问 OpenMetadata 服务器
   - 生产环境可能需要 VPN 或特定网络配置

## 常见问题

### Q1: 连接超时

**解决方案：**
1. 检查网络连接
2. 检查服务器地址是否正确
3. 检查防火墙设置

### Q2: 认证失败

**解决方案：**
1. 检查 JWT Token 是否有效
2. 检查 Token 是否有足够权限
3. 确认 Token 未过期

### Q3: Schema 未找到

**解决方案：**
1. 确认 Schema FQN 格式正确：`service.database.schema`
2. 在 OpenMetadata UI 中确认 Schema 存在
3. 检查 Token 是否有权限访问该 Schema

### Q4: 导出内容显示 root=''

**解决方案：**
已修复，使用 `safe_extract_value()` 函数正确提取值。

## 相关文档

- [OpenMetadata Python SDK](https://docs.open-metadata.org/latest/sdk/python)
- [项目主文档](../README.md)

---

**更新时间：** 2024-12-04  
**版本：** v2.1
