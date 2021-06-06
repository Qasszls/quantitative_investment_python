from MySqlHandler import MySqlHandler
from TimeStamp import TimeTamp

timeTamp = TimeTamp()
# 数据对象
task_library = [{
    'database':
    '2020_kline_3m',
    'times': [
        timeTamp.get_time_stamp('2020-12-31 23:59:59') * 1000,
        timeTamp.get_time_stamp('2019-12-31 23:59:59') * 1000
    ],
    'symbol':
    'BTC-USDT'
}, {
    'database':
    '2019_kline_3m',
    'times': [
        timeTamp.get_time_stamp('2019-12-31 23:59:59') * 1000,
        timeTamp.get_time_stamp('2018-12-31 23:59:59') * 1000
    ],
    'symbol':
    'BTC-USDT'
}, {
    'database':
    '2020_kline_5m',
    'times': [
        timeTamp.get_time_stamp('2020-12-31 23:59:59') * 1000,
        timeTamp.get_time_stamp('2019-12-31 23:59:59') * 1000
    ],
    'symbol':
    'BTC-USDT'
}, {
    'database':
    '2019_kline_5m',
    'times': [
        timeTamp.get_time_stamp('2019-12-31 23:59:59') * 1000,
        timeTamp.get_time_stamp('2018-12-31 23:59:59') * 1000
    ],
    'symbol':
    'BTC-USDT'
}, {
    'database':
    '2020_kline_15m',
    'times': [
        timeTamp.get_time_stamp('2020-12-31 23:59:59') * 1000,
        timeTamp.get_time_stamp('2019-12-31 23:59:59') * 1000
    ],
    'symbol':
    'BTC-USDT'
}, {
    'database':
    '2019_kline_15m',
    'times': [
        timeTamp.get_time_stamp('2019-12-31 23:59:59') * 1000,
        timeTamp.get_time_stamp('2018-12-31 23:59:59') * 1000
    ],
    'symbol':
    'BTC-USDT'
}, {
    'database':
    '2020_kline_30m',
    'times': [
        timeTamp.get_time_stamp('2020-12-31 23:59:59') * 1000,
        timeTamp.get_time_stamp('2019-12-31 23:59:59') * 1000
    ],
    'symbol':
    'BTC-USDT'
}, {
    'database':
    '2019_kline_30m',
    'times': [
        timeTamp.get_time_stamp('2019-12-31 23:59:59') * 1000,
        timeTamp.get_time_stamp('2018-12-31 23:59:59') * 1000
    ],
    'symbol':
    'BTC-USDT'
}]

# 实例化数据库对象
mySqlHandler = MySqlHandler(
    ip='127.0.0.1',
    userName='root',
    userPass='qass-utf-8',
    DBName='BTC-USDT_kline',
    charset='utf8',
)

#清楚所有表内容
for i in range(len(task_library)):
    status, msg = mySqlHandler.clear_table_record(task_library[i]['database'])
    print(msg)
