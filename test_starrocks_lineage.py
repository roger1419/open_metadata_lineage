# -*- coding: utf-8 -*-
"""
StarRocks 血缘测试脚本
用于测试 StarRocks SQL 解析和血缘添加功能

注意：此测试需要连接到 OpenMetadata 服务器
如果无法连接，测试将失败
"""

import sys
import starrocks_lineage_handler
import open_metadata_lineage

# 检查 OpenMetadata 连接
print("检查 OpenMetadata 连接...")
try:
    metadata = open_metadata_lineage.get_metadata_client()
    health = metadata.health_check()
    print(f"✓ OpenMetadata 连接成功: {health}")
except Exception as e:
    print(f"✗ 无法连接到 OpenMetadata: {e}")
    print(f"\n请检查配置:")
    print(f"  - hostPort: {open_metadata_lineage.hostPort}")
    print(f"  - 确保 OpenMetadata 服务正在运行")
    print(f"  - 确保网络连接正常")
    print(f"\n跳过测试...")
    sys.exit(0)


def test_starrocks_insert_select():
    """测试 StarRocks INSERT SELECT 语句"""
    print("\n" + "="*60)
    print("测试 1: StarRocks INSERT SELECT")
    print("="*60)
    
    sql = """
----------------------------------------------------------------
-- 程序功能：分销机构用户统计报表
-- 程序名： P_ads_bi_dc_user_statistic_info_di
-- 目标表： ads.ads_bi_dc_user_statistic_info_di
-- 负责人： qhr
-- 开发日期： 2025-11-07
-- 版本号： v1.0.0
----------------------------------------------------------------

insert into ads.ads_bi_dc_user_statistic_info_di
with install_user_count as (
    select a1.dt
          ,a1.product_id
          ,a1.ad_id
          ,a2.inst_id
          ,a2.dc_acct
          ,a1.core
          ,a1.mt
          ,count(distinct a1.user_id)           as dev_unt
      from dwd.dwd_user_install_info_ed_view    as a1
      join dwd.dwd_advertisement_adext_view     as a2
        on a1.ad_id = a2.ad_id
       and a2.product_id = 6833
       and a2.inst_id > 0
     where a1.dt >= date_sub('${bf_1_dt}', interval 60 day)
       and a1.Product_Id = 6833
       and a1.IsDelete = 0
     group by 1,2,3,4,5,6,7
)
select a1.dt                                   as dt                  -- 统计日期
      ,md5(concat_ws( '_',a1.dt,a1.product_id,a1.user_type
                     ,a1.dc_code,a1.dc_account,a1.core,a1.mt
                    )
          )                                    as md5_key             -- 主键md5key
      ,a1.product_id                           as product_id          -- 产品id
      ,a1.dc_code                              as dc_code             -- 所属机构
      ,a1.dc_account                           as dc_account          -- 机构投放账号
      ,a1.core                                 as core                -- core
      ,a1.mt                                   as mt                  -- 终端
      ,a1.user_type                            as user_type           -- 用户类型
      ,coalesce(sum(a1.new_user_count), 0)     as new_user_count      -- 新增用户数
      ,coalesce(sum(a1.pay_user_count),0)      as pay_user_count      -- 新增用户数
      ,coalesce(sum(a1.pay_order_count),0)     as pay_order_count     -- 订单数
      ,coalesce(sum(a1.pay_order_amount),0)    as pay_order_amount    -- 订单金额
      ,now()                                   as etl_tm              -- 数据清洗时间
  from (select b1.dt                                                          as dt
              ,6833                                                           as product_id
              ,if(date(b1.AccountCreateTime)=date(b1.OrderCreateTime),1,0)    as user_type
              ,b1.dc                                                          as dc_code
              ,b1.DcAccount                                                   as dc_account
              ,b1.core                                                        as core
              ,b1.OsType                                                      as mt
              ,null                                                           as new_user_count
              ,count(distinct b1.UserId)                                      as pay_user_count
              ,count(b1.OrderSerialId)                                        as pay_order_count
              ,coalesce(sum(b1.Amount/100),0)                                 as pay_order_amount
          from dwd.dwd_pay_order_for_dc_view    as b1
         where b1.dt >= date_sub('${bf_1_dt}', interval 60 day)
         group by 1,2,3,4,5,6,7
         union all
         select b2.dt
               ,b2.product_id
               ,1                                                             as user_type
               ,b2.inst_id                                                    as dc_code
               ,b2.dc_acct                                                    as dc_account
               ,b2.core
               ,b2.mt
               ,b2.dev_unt                                                    as new_user_count
               ,0                                                             as pay_user_count
               ,0                                                             as pay_order_count
               ,0                                                             as pay_order_amount
           from install_user_count              as b2
       )                                        as a1
 group by 1,2,3,4,5,6,7,8
;
"""
    
    handler = starrocks_lineage_handler.StarRocksLineageHandler()
    success = handler.add_starrocks_lineage(
        service_name='StarRocks_test',
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
        service_name='starrocks_test',
        database_name='ads',
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
        service_name='starrocks_test',
        database_name='ads',
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
        service_name='starrocks_test',
        database_name='ads',
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
        service_name='starrocks_test',
        database_name='ads',
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
