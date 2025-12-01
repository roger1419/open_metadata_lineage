# -*- coding: utf-8 -*-
"""
StarRocks 血缘测试脚本
用于测试 StarRocks SQL 解析和血缘添加功能
"""

import starrocks_lineage_handler
import open_metadata_lineage


def test_starrocks_insert_select():
    """测试 StarRocks INSERT SELECT 语句"""
    print("\n" + "="*60)
    print("测试 1: StarRocks INSERT SELECT")
    print("="*60)
    
    sql = """
    INSERT INTO dsj_dwd.dwd_user_behavior
    SELECT 
        user_id,
        event_time,
        event_type,
        page_id,
        item_id,
        CURRENT_TIMESTAMP() as etl_time
    FROM dsj_ods.ods_user_log
    WHERE dt = '2024-12-01'
    """
    
    handler = starrocks_lineage_handler.StarRocksLineageHandler()
    success = handler.add_starrocks_lineage(
        service_name='uat-starrocks',
        database_name='default',
        sql=sql,
        description='测试 StarRocks INSERT SELECT'
    )
    
    print(f"\n结果: {'✓ 成功' if success else '✗ 失败'}")
    return success


def test_starrocks_insert_overwrite():
    """测试 StarRocks INSERT OVERWRITE 语句"""
    print("\n" + "="*60)
    print("测试 2: StarRocks INSERT OVERWRITE")
    print("="*60)
    
    sql = """
    INSERT OVERWRITE dsj_dwd.dwd_order_summary
    SELECT 
        o.order_id,
        o.user_id,
        u.user_name,
        o.order_amount,
        o.order_status,
        o.create_time
    FROM dsj_ods.ods_orders o
    LEFT JOIN dsj_ods.ods_users u ON o.user_id = u.user_id
    WHERE o.dt = '2024-12-01'
    """
    
    handler = starrocks_lineage_handler.StarRocksLineageHandler()
    success = handler.add_starrocks_lineage(
        service_name='uat-starrocks',
        database_name='default',
        sql=sql,
        description='测试 StarRocks INSERT OVERWRITE'
    )
    
    print(f"\n结果: {'✓ 成功' if success else '✗ 失败'}")
    return success


def test_starrocks_with_dolphin_task():
    """测试 StarRocks 与 DolphinScheduler 任务关联"""
    print("\n" + "="*60)
    print("测试 3: StarRocks + DolphinScheduler 任务关联")
    print("="*60)
    
    sql = """
    INSERT INTO dsj_dwd.dwd_product_sales
    SELECT 
        p.product_id,
        p.product_name,
        s.sale_amount,
        s.sale_quantity,
        s.sale_date
    FROM dsj_ods.ods_products p
    INNER JOIN dsj_ods.ods_sales s ON p.product_id = s.product_id
    WHERE s.dt = '2024-12-01'
    """
    
    success = starrocks_lineage_handler.add_starrocks_lineage_from_dolphin(
        service_name='uat-starrocks',
        database_name='default',
        sql=sql,
        project_name='数据中台',
        workflow_name='DWD层数据处理',
        task_name='产品销售汇总',
        task_url='https://uatds.fixpng.com/dolphinscheduler/ui/projects/123/task/definitions'
    )
    
    print(f"\n结果: {'✓ 成功' if success else '✗ 失败'}")
    return success


def test_starrocks_complex_sql():
    """测试复杂的 StarRocks SQL"""
    print("\n" + "="*60)
    print("测试 4: 复杂 StarRocks SQL（多表 JOIN + 聚合）")
    print("="*60)
    
    sql = """
    INSERT INTO dsj_dwd.dwd_user_order_summary
    SELECT 
        u.user_id,
        u.user_name,
        u.user_level,
        COUNT(DISTINCT o.order_id) as order_count,
        SUM(o.order_amount) as total_amount,
        AVG(o.order_amount) as avg_amount,
        MAX(o.order_time) as last_order_time,
        CURRENT_TIMESTAMP() as etl_time
    FROM dsj_ods.ods_users u
    LEFT JOIN dsj_ods.ods_orders o ON u.user_id = o.user_id
    LEFT JOIN dsj_ods.ods_user_profile p ON u.user_id = p.user_id
    WHERE o.order_status = 'completed'
        AND o.dt >= '2024-11-01'
        AND o.dt <= '2024-11-30'
    GROUP BY u.user_id, u.user_name, u.user_level
    """
    
    handler = starrocks_lineage_handler.StarRocksLineageHandler()
    success = handler.add_starrocks_lineage(
        service_name='uat-starrocks',
        database_name='default',
        sql=sql,
        description='测试复杂 SQL 解析',
        task_info={
            'platform': 'DolphinScheduler',
            'project_name': '数据中台',
            'workflow_name': '用户分析',
            'task_name': '用户订单汇总'
        }
    )
    
    print(f"\n结果: {'✓ 成功' if success else '✗ 失败'}")
    return success


def test_starrocks_with_properties():
    """测试带 StarRocks 特有语法的 SQL"""
    print("\n" + "="*60)
    print("测试 5: StarRocks 特有语法（DISTRIBUTED BY）")
    print("="*60)
    
    sql = """
    INSERT INTO dsj_dwd.dwd_event_log
    PROPERTIES("timeout" = "3600")
    SELECT 
        event_id,
        user_id,
        event_type,
        event_time,
        event_data
    FROM dsj_ods.ods_event_raw
    WHERE dt = '2024-12-01'
    DISTRIBUTED BY HASH(user_id) BUCKETS 32
    """
    
    handler = starrocks_lineage_handler.StarRocksLineageHandler()
    
    # 测试 SQL 清理功能
    cleaned_sql = handler._clean_starrocks_sql(sql)
    print(f"\n清理后的 SQL:\n{cleaned_sql}\n")
    
    success = handler.add_starrocks_lineage(
        service_name='uat-starrocks',
        database_name='default',
        sql=sql,
        description='测试 StarRocks 特有语法'
    )
    
    print(f"\n结果: {'✓ 成功' if success else '✗ 失败'}")
    return success


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("StarRocks 血缘测试套件")
    print("="*60)
    
    tests = [
        ("基础 INSERT SELECT", test_starrocks_insert_select),
        ("INSERT OVERWRITE", test_starrocks_insert_overwrite),
        ("DolphinScheduler 任务关联", test_starrocks_with_dolphin_task),
        ("复杂 SQL 解析", test_starrocks_complex_sql),
        ("StarRocks 特有语法", test_starrocks_with_properties),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as exc:
            print(f"\n✗ 测试异常: {exc}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # 输出测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for test_name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{status} - {test_name}")
    
    print(f"\n总计: {success_count}/{total_count} 通过")
    print("="*60)


if __name__ == "__main__":
    # 运行所有测试
    run_all_tests()
    
    # 或者运行单个测试
    # test_starrocks_insert_select()
    # test_starrocks_with_dolphin_task()
