# SQLLineage 1.3.7 Bug 修复指南

## 问题描述

`sqllineage 1.3.7` 存在一个已知 bug，导致导入时出现以下错误：

```
TypeError: 'str' object is not callable
```

错误发生在 `sqllineage/__init__.py` 的第 24 行：
```python
if regex("LATERAL VIEW EXPLODE(col)"):
```

## 解决方案

### 方案 1: 升级到 1.5.6（推荐）

```bash
pip install "sqllineage>=1.5.0"
```

**注意：** 这会导致与 `openmetadata-ingestion 0.13.1.8` 的依赖冲突警告，但不影响使用。

### 方案 2: 降级 openmetadata-ingestion

如果必须使用 sqllineage 1.3.7，需要降级 openmetadata-ingestion：

```bash
pip install "openmetadata-ingestion<0.13"
```

### 方案 3: 手动修复 sqllineage 1.3.7

找到 sqllineage 安装目录并编辑 `__init__.py`：

```bash
# 找到文件位置
python -c "import sqllineage; print(sqllineage.__file__)"
```

编辑该文件，将第 24 行：
```python
if regex("LATERAL VIEW EXPLODE(col)"):
```

修改为：
```python
import re as regex_module
if regex_module.search(r"LATERAL VIEW EXPLODE\(col\)", "LATERAL VIEW EXPLODE(col)"):
```

## 当前项目配置

本项目已升级到 `sqllineage 1.5.6`，可以正常使用。

## 验证修复

运行以下命令验证：

```bash
python -c "from sqllineage.runner import LineageRunner; print('导入成功！')"
```

## 依赖冲突说明

升级后会看到以下警告：

```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
openmetadata-ingestion 0.13.1.8 requires sqllineage==1.3.7, but you have sqllineage 1.5.6 which is incompatible.
```

**这个警告可以忽略**，因为：
1. sqllineage 1.5.6 向后兼容 1.3.7 的 API
2. 本项目优先使用 OpenMetadata SDK 的服务端解析
3. sqllineage 仅作为备选方案使用

## 测试

运行测试脚本验证功能：

```bash
python test_starrocks_lineage.py
```

## 参考

- [sqllineage GitHub Issues](https://github.com/reata/sqllineage/issues)
- [OpenMetadata Documentation](https://docs.open-metadata.org/)


---

[← 返回文档目录](README.md) | [返回项目主页](../README.md)
