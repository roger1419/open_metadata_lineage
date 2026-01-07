import re


sql_script_file = 'D:/IdeaProjects/CD_demands/src/SQL/2025/12/idc_starrocks_all_databases.sql'

with open(sql_script_file, 'r', encoding='utf-8') as f:
    # 逐行读取文件
    for line in f:
        # 检查每行是否以 "USE" 开头（忽略大小写）
        if line.strip().upper().startswith('USE'):
            print(line.strip())