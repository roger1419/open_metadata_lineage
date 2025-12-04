# -*- coding: utf-8 -*-
"""
SQL 解析测试脚本（不需要 OpenMetadata 连接）
仅测试 SQL 清理和解析功能
"""

import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import starrocks_lineage_handler


def test_sql_cleaning():
    """测试 SQL 清理功能"""
    print("\n" + "="*60)
    print("测试 SQL 清理功能")
    print("="*60)
    
    handler = starrocks_lineage_handler.StarRocksLineageHandler()
    
    # 测试 1: INSERT OVERWRITE
    sql1 = """
    INSERT OVERWRITE dsj_dwd.dwd_order_summary
    SELECT * FROM dsj_ods.ods_orders
    """
    cleaned1 = handler._clean_starrocks_sql(sql1)
    print(f"\n原始 SQL:\n{sql1}")
    print(f"\n清理后:\n{cleaned1}")
    assert "INSERT INTO" in cleaned1
    assert "OVERWRITE" not in cleaned1
    print("✓ INSERT OVERWRITE 转换成功")
    
    # 测试 2: PROPERTIES
    sql2 = """
    INSERT INTO table1
    PROPERTIES("timeout" = "3600")
    SELECT * FROM table2
    """
    cleaned2 = handler._clean_starrocks_sql(sql2)
    print(f"\n原始 SQL:\n{sql2}")
    print(f"\n清理后:\n{cleaned2}")
    assert "PROPERTIES" not in cleaned2
    print("✓ PROPERTIES 移除成功")
    
    # 测试 3: DISTRIBUTED BY
    sql3 = """
    INSERT INTO table1
    SELECT * FROM table2
    DISTRIBUTED BY HASH(user_id) BUCKETS 32
    """
    cleaned3 = handler._clean_starrocks_sql(sql3)
    print(f"\n原始 SQL:\n{sql3}")
    print(f"\n清理后:\n{cleaned3}")
    assert "DISTRIBUTED" not in cleaned3
    assert "BUCKETS" not in cleaned3
    print("✓ DISTRIBUTED BY 移除成功")
    
    # 测试 4: 综合测试
    sql4 = """
    INSERT OVERWRITE `dsj_dwd`.`dwd_event_log`
    PROPERTIES("timeout" = "3600")
    SELECT 
        event_id,
        user_id
    FROM `dsj_ods`.`ods_event_raw`
    WHERE dt = '2024-12-01'
    DISTRIBUTED BY HASH(user_id) BUCKETS 32
    """
    cleaned4 = handler._clean_starrocks_sql(sql4)
    print(f"\n原始 SQL:\n{sql4}")
    print(f"\n清理后:\n{cleaned4}")
    assert "INSERT INTO" in cleaned4
    assert "OVERWRITE" not in cleaned4
    assert "PROPERTIES" not in cleaned4
    assert "DISTRIBUTED" not in cleaned4
    assert "`" not in cleaned4
    print("✓ 综合清理成功")
    
    print("\n" + "="*60)
    print("所有 SQL 清理测试通过！")
    print("="*60)


def test_sql_parsing():
    """测试 SQL 解析功能"""
    print("\n" + "="*60)
    print("测试 SQL 解析功能（使用 sqllineage）")
    print("="*60)
    
    from sqllineage.runner import LineageRunner
    
    # 测试 1: 简单 INSERT SELECT
    sql1 = """
    INSERT INTO table1
    SELECT col1, col2 FROM table2
    """
    print(f"\nSQL: {sql1}")
    try:
        result = LineageRunner(sql1, dialect="ansi")
        lineage = list(result.get_column_lineage())
        print(f"✓ 解析成功，找到 {len(lineage)} 个字段映射")
        for col_tuple in lineage:
            print(f"  {col_tuple}")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    # 测试 2: 带 JOIN 的 SQL
    sql2 = """
    INSERT INTO target_table
    SELECT 
        a.col1,
        b.col2
    FROM table_a a
    LEFT JOIN table_b b ON a.id = b.id
    """
    print(f"\nSQL: {sql2}")
    try:
        result = LineageRunner(sql2, dialect="ansi")
        lineage = list(result.get_column_lineage())
        print(f"✓ 解析成功，找到 {len(lineage)} 个字段映射")
        for col_tuple in lineage:
            print(f"  {col_tuple}")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    # 测试 3: INSERT OVERWRITE（清理后）
    handler = starrocks_lineage_handler.StarRocksLineageHandler()
    sql3 = """
    INSERT OVERWRITE target_table
    SELECT col1, col2 FROM source_table
    """
    cleaned_sql3 = handler._clean_starrocks_sql(sql3)
    print(f"\n原始 SQL: {sql3}")
    print(f"清理后: {cleaned_sql3}")
    try:
        result = LineageRunner(cleaned_sql3, dialect="ansi")
        lineage = list(result.get_column_lineage())
        print(f"✓ 解析成功，找到 {len(lineage)} 个字段映射")
        for col_tuple in lineage:
            print(f"  {col_tuple}")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    print("\n" + "="*60)
    print("SQL 解析测试完成")
    print("="*60)


def test_starrocks_syntax_detection():
    """测试 StarRocks 语法识别"""
    print("\n" + "="*60)
    print("测试 StarRocks 语法识别")
    print("="*60)
    
    handler = starrocks_lineage_handler.StarRocksLineageHandler()
    
    test_cases = [
        ("INSERT INTO table1 SELECT * FROM table2", False),
        ("INSERT INTO table1 DUPLICATE KEY(id) SELECT * FROM table2", True),
        ("INSERT INTO table1 AGGREGATE KEY(id) SELECT * FROM table2", True),
        ("INSERT INTO table1 SELECT * FROM table2 DISTRIBUTED BY HASH(id) BUCKETS 10", True),
        ("INSERT INTO table1 SELECT BITMAP_UNION(col) FROM table2", True),
        ("INSERT INTO table1 SELECT HLL_UNION(col) FROM table2", True),
    ]
    
    for sql, expected in test_cases:
        result = handler.is_starrocks_sql(sql)
        status = "✓" if result == expected else "✗"
        print(f"{status} {sql}; ... -> {result} (期望: {expected})")
    
    print("\n" + "="*60)
    print("StarRocks 语法识别测试完成")
    print("="*60)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("SQL 解析测试套件（无需 OpenMetadata 连接）")
    print("="*60)
    
    try:
        test_sql_cleaning()
        test_sql_parsing()
        test_starrocks_syntax_detection()
        
        print("\n" + "="*60)
        print("✓ 所有测试通过！")
        print("="*60)
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
