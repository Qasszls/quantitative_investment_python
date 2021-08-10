from MySqlHandler import MySqlHandler

import json
import re

# 取出任务队列 与 滤出队列
f = open(
    '/Users/work/web/quantitative_investment_python/py/main/crawler/config.json',
    'r')
config = json.load(f)
task_library = config['task_library']
task_filter = config['filter']
task_DBName = config['DBName']

# 实例化数据库对象
mySqlHandler = MySqlHandler(
    ip='127.0.0.1',
    userName='root',
    userPass='qass-utf-8',
    DBName=task_DBName,
    charset='utf8',
)

# 过滤任务列表，拿出预期数据 task_target
task_target = []
for item in task_library:
    for filter_item in task_filter:
        if filter_item == item['table'].split('_')[2]:
            task_target.append(item)

#清除所有表内容
for i in range(len(task_target)):
    status, msg = mySqlHandler.clear_table_record(task_target[i]['table'])
    print(msg)
