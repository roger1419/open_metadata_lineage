#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成StarRocks ALTER TABLE语句
为指定的表批量添加广告相关列
"""

# 配置
SCHEMA = "sharpengine_ads_global"

# 表名列表
TABLES = """
FbAdRoiInstallReferrerVideoHour
FbAdRoiInstallReferrerVideo
FbAdRoiInstallReferrerVideoByHour
FbAdRoiInstallReferrerV2
FbAdRoiInstallReferrerHourTimeZoneV3
FbAdRoiInstallReferrerDc
FbAdRoiInstallReferrerTimeZoneV3
FbAdRoiInstallReferrerDcCore2
FbAdRoiInstallReferrerPayAttrV3
FbAdRoiInstallReferrerV3
FbAdRoiInstallReferrerHour
FbAdRoiInstallReferrerHourTimeZone
FbAdRoiInstallReferrerTimeZone
FbAdRoiInstallReferrer
FbAdRoiInstallReferrerByHourTimeZoneV3
FbAdRoiInstallReferrerByHour
FbAdRoiInstallReferrerByHourTimeZone
""".strip()

# 列定义
COLUMNS = [
    ("D0RewardedVideoUserNum", "int", "0", "D0激励视频用户数"),
    ("D0InterstitialUserNum", "int", "0", "D0插屏用户数"),
    ("D0RewardedVideoShowCount", "bigint", "0", "D0激励视频展示数"),
    ("D0InterstitialShowCount", "bigint", "0", "D0插屏展示数"),
    ("D0TotalShowCount", "bigint", "0", "D0总展示数"),
    ("D0AdUserNum", "int", "0", "D0广告用户数(激励视频用户数+插屏用户数去重)"),
    ("D0AdPayNum", "int", "0", "D0产生广告价值用户数"),
]


def generate_alter_statements():
    """生成所有表的ALTER语句"""
    statements = []

    table_list = [t.strip() for t in TABLES.split('\n') if t.strip()]

    for table in table_list:
        statements.append(f"-- 为表 {table} 添加广告相关列")

        for col_name, col_type, default_val, comment in COLUMNS:
            sql = (
                f"ALTER TABLE {SCHEMA}.{table} "
                f"ADD COLUMN `{col_name}` {col_type} "
                f"DEFAULT '{default_val}' "
                f"COMMENT '{comment}';"
            )
            statements.append(sql)

        statements.append("")  # 空行分隔

    return statements


def save_to_file(statements, filename="alter_tables.sql"):
    """将SQL语句保存到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(statements))
    print(f"SQL语句已保存到: {filename}")
    print(f"共生成 {len([s for s in statements if s.startswith('ALTER')])} 条ALTER语句")


def main():
    print("开始生成ALTER TABLE语句...")
    print(f"Schema: {SCHEMA}")

    table_count = len([t for t in TABLES.split('\n') if t.strip()])
    print(f"表数量: {table_count}")
    print(f"列数量: {len(COLUMNS)}")
    print("-" * 60)

    statements = generate_alter_statements()

    # 输出到控制台
    for stmt in statements:
        print(stmt)

    print("-" * 60)

    # 保存到文件
    save_to_file(statements)


if __name__ == "__main__":
    main()