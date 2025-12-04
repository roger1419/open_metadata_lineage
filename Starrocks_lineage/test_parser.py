#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 StarRocks SQL 解析器
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from starrocks_sql_parser import StarRocksSQLParser


def test_sql_cleaning():
    """测试 SQL 清理功能"""
    print("\n" + "="*60)
    print("测试 SQL 清理功能")
    print("="*60)
    
    parser = StarRocksSQLParser("", "", "test", "test")
    
    # 测试用例
    test_cases = [
        {
            "name": "移除注释",
            "input": "SELECT * FROM table1 -- 这是注释\nWHERE id = 1",
            "expected_contains": "SELECT * FROM table1"
        },
        {
            "name": "替换 INSERT OVERWRITE",
            "input": "INSERT OVERWRITE table1 SELECT * FROM table2",
            "expected_contains": "INSERT INTO table1"
        },
        {
            "name": "移除 DISTRIBUTED BY",
            "input": "CREATE TABLE t1 (id INT) DISTRIBUTED BY HASH(id) BUCKETS 10",
            "expected_not_contains": "DISTRIBUTED BY"
        },
    ]
    
    for test in test_cases:
        result = parser.clean_sql(test["input"])
        print(f"\n测试: {test['name']}")
        print(f"输入: {test['input'][:50]}...")
        print(f"输出: {result[:50]}...")
        
        if "expected_contains" in test:
            if test["expected_contains"] in result:
                print(f"✓ 通过")
            else:
                print(f"✗ 失败: 期望包含 '{test['expected_contains']}'")
        
        if "expected_not_contains" in test:
            if test["expected_not_contains"] not in result:
                print(f"✓ 通过")
            else:
                print(f"✗ 失败: 不应包含 '{test['expected_not_contains']}'")


def test_table_name_normalization():
    """测试表名规范化"""
    print("\n" + "="*60)
    print("测试表名规范化")
    print("="*60)
    
    parser = StarRocksSQLParser("", "", "StarRocks_test", "default")
    
    test_cases = [
        ("table1", "StarRocks_test.default.ads.table1"),
        ("ads.table1", "StarRocks_test.default.ads.table1"),
        ("ods.table2", "StarRocks_test.default.ods.table2"),
    ]
    
    for input_name, expected in test_cases:
        result = parser.normalize_table_name(input_name)
        status = "✓" if result == expected else "✗"
        print(f"{status} {input_name} -> {result} (期望: {expected})")


def test_sql_file_parsing():
    """测试 SQL 文件解析（不连接 OpenMetadata）"""
    print("\n" + "="*60)
    print("测试 SQL 文件解析（包含列级血缘）")
    print("="*60)
    
    parser = StarRocksSQLParser("", "", "StarRocks_test", "default")
    
    sql_file = "../sql/P_ads_bi_sv_user_recharge_expo_info_di.sql"
    
    target, sources, column_lineage = parser.parse_sql_file(sql_file, parse_columns=True)
    
    if target and sources:
        print(f"\n✅ 解析成功！")
        print(f"目标表: {target}")
        print(f"源表数量: {len(sources)}")
        print(f"源表列表:")
        for i, src in enumerate(sources, 1):
            print(f"  [{i}] {src}")
        
        if column_lineage:
            print(f"\n列级血缘数量: {len(column_lineage)}")
            print(f"列级血缘示例（前3个）:")
            for i, (target_col, source_cols) in enumerate(list(column_lineage.items())[:3], 1):
                print(f"  [{i}] {target_col} <- {len(source_cols)} 个源列")
                for src_col in source_cols[:2]:  # 只显示前2个源列
                    print(f"      - {src_col['table']}.{src_col['column']}")
    else:
        print(f"\n✗ 解析失败")


if __name__ == "__main__":
    print("="*60)
    print("StarRocks SQL 解析器测试")
    print("="*60)
    
    test_sql_cleaning()
    test_table_name_normalization()
    test_sql_file_parsing()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
