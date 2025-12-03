# 变更日志

## [2.0.0] - 2024-12-01

### 新增功能 ✨

- **StarRocks 专用血缘处理器** (`starrocks_lineage_handler.py`)
  - 支持 StarRocks 特有 SQL 语法识别和清理
  - 支持 INSERT INTO/OVERWRITE 语句解析
  - 自动关联 DolphinScheduler 任务元数据
  - 提供便捷函数 `add_starrocks_lineage_from_dolphin()`

- **优化版执行脚本** (`execute_lineage_v2.py`)
  - 改进的日志管理
  - 执行统计和时间跟踪
  - 支持选择性平台提取
  - 更好的错误处理

- **测试套件** (`test_starrocks_lineage.py`)
  - 5 个测试场景覆盖常见用例
  - 自动化测试报告
  - 便于验证功能正确性

- **配置管理** (`config_example.py`)
  - 集中化配置管理
  - 支持多环境配置
  - 敏感信息保护建议

- **文档完善**
  - `QUICKSTART.md` - 5 分钟快速上手指南
  - `OPTIMIZATION_GUIDE.md` - 详细优化说明和最佳实践
  - `CHANGELOG.md` - 版本变更记录

### 优化改进 🚀

#### open_metadata_lineage.py

- **使用 OpenMetadata SDK 服务端解析**
  - 调用 `add_lineage_by_query()` 方法
  - 支持更多 SQL 方言（MySQL, PostgreSQL, StarRocks, Hive 等）
  - 自动关联 OpenMetadata 实体
  - 失败时自动回退到本地解析

- **改进 SQL 血缘添加函数**
  - 新增 `schema_name` 参数支持
  - 新增 `timeout_seconds` 超时控制
  - 返回布尔值表示成功/失败
  - 详细的日志输出和错误追踪

- **优化 DataX JSON 解析**
  - 支持多种 Reader 配置格式（querySql, table）
  - 智能字段映射处理
  - 字段数量不一致时降级为表级血缘
  - 改进的错误处理和日志

- **统一日志格式**
  - ✓ 成功标记
  - ✗ 失败标记
  - ⊘ 跳过标记
  - → 提示信息标记

#### get_etl_add_lineage.py

- **DolphinScheduler 集成优化**
  - 自动识别 StarRocks 数据源
  - 使用专用处理器处理 StarRocks SQL
  - 提取完整的任务元数据
  - 统计信息输出（成功/跳过/失败）

- **改进任务处理方法**
  - 拆分 `_process_sql_task()` 和 `_process_datax_task()`
  - 返回明确的处理状态（success/skip/fail）
  - 更好的错误处理和日志
  - 支持 INSERT OVERWRITE 语句

- **增强错误处理**
  - 请求超时控制
  - 异常堆栈跟踪
  - 失败时继续处理下一个任务

### 技术改进 🔧

- **代码质量**
  - 添加详细的函数文档字符串
  - 改进变量命名和代码结构
  - 统一错误处理模式
  - 增加类型提示

- **性能优化**
  - 服务端解析减少本地计算
  - 缓存 URL 映射关系
  - 批量处理支持

- **可维护性**
  - 模块化设计
  - 配置与代码分离
  - 详细的日志和错误信息
  - 完善的文档

### 修复问题 🐛

- 修复 SQL 解析中的变量名错误（`url_service` -> `service`）
- 修复 DataX JSON 解析中的字段映射问题
- 修复 StarRocks 特有语法导致的解析失败
- 改进数据库名称解析逻辑

### 文档更新 📖

- 更新 README.md，添加版本更新说明
- 新增快速开始指南
- 新增优化详细说明文档
- 添加技术架构图
- 完善常见问题解答

### 向后兼容性 ⚠️

- ✅ 完全向后兼容，原有脚本仍可正常使用
- ✅ 新功能为可选，不影响现有流程
- ✅ 配置文件为新增，不影响现有配置

### 升级指南 📋

1. **无需修改现有代码**
   - 原有的 `execute_demo.py` 仍可正常使用
   - 所有优化都是增强，不破坏现有功能

2. **可选升级步骤**
   ```bash
   # 1. 使用新的执行脚本（推荐）
   python execute_lineage_v2.py
   
   # 2. 测试 StarRocks 功能
   python test_starrocks_lineage.py
   
   # 3. 创建配置文件（可选）
   cp config_example.py config.py
   # 编辑 config.py 填入配置
   ```

3. **建议的迁移路径**
   - 先在测试环境验证新功能
   - 逐步迁移到新的执行脚本
   - 根据需要启用 StarRocks 专用处理器

### 已知问题 ⚠️

- 服务端 SQL 解析依赖 OpenMetadata 版本（建议 1.2.0+）
- 复杂的 StarRocks SQL 可能需要手动调整
- 大批量任务处理可能触发 API 限流

### 下一步计划 🎯

- [ ] 支持更多 SQL 方言（ClickHouse, Doris）
- [ ] 添加血缘验证和质量检查
- [ ] 支持增量更新模式
- [ ] 添加 Web UI 管理界面
- [ ] 支持血缘影响分析
- [ ] 添加性能监控和告警

---

## [1.0.0] - 之前版本

### 功能特性

- 支持 DolphinScheduler SQL 和 DataX 血缘提取
- 支持 StreamPark FlinkSQL 血缘提取
- 支持 Canal 配置血缘提取
- 基于 sqllineage 的本地 SQL 解析
- 基础的错误处理和日志

---

## 版本说明

版本号格式：`主版本.次版本.修订版本`

- **主版本**：重大架构变更或不兼容更新
- **次版本**：新功能添加，向后兼容
- **修订版本**：Bug 修复和小改进

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

提交前请确保：
- [ ] 代码通过 pylint 检查
- [ ] 添加必要的测试
- [ ] 更新相关文档
- [ ] 遵循现有代码风格


---

[← 返回文档目录](README.md) | [返回项目主页](../README.md)
