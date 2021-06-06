# -*- coding:UTF-8 -*-
import emoji
import threading

from tqdm import tqdm

from MarketCrawler import MarketCrawler
from MySqlHandler import MySqlHandler
from TimeStamp import TimeTamp
from OsHandler import OsHandler


class Searchkline(threading.Thread):
    def __init__(self,
                 threadID,
                 marketCrawler,
                 mySqlHandler,
                 task=None,
                 timeTamp=None):
        threading.Thread.__init__(self)
        self.task = task
        self.threadID = threadID
        self.marketCrawler = marketCrawler
        self.mySqlHandler = mySqlHandler
        self.timeTamp = timeTamp
        if not task:
            raise Exception('{}线程的任务不能为空'.format(threadID))
        self.instId = task['symbol']

    def get_divde(self, unit, _ms, bar):
        divde = None
        if unit == 'm':
            divde = _ms / 1000 / 60 / bar
        if unit == 'H':
            divde = _ms / 1000 / 60 / 60 / bar
        if unit == 'D':
            divde = _ms / 1000 / 60 / 60 / 24 / bar
        if unit == 'W':
            divde = _ms / 1000 / 60 / 60 / 24 / 7 / bar
        if unit == 'M':
            divde = _ms / 1000 / 60 / 60 / 24 / 30 / bar
        if unit == 'Y':
            divde = _ms / 1000 / 60 / 60 / 24 / 30 / 12 / bar
        return int(round(divde))

    def get_residue_limit(self, _bar_unit, _ms, bar, limit):
        # 获取总条数
        _divide = self.get_divde(unit=_bar_unit, _ms=_ms, bar=bar)
        # 当剩余数据长度不足时，重新计算limit
        if _divide <= 1:
            return 1, _divide
        elif _divide < limit:
            return _divide, _divide
        else:
            return limit, _divide

    def crawler(self, tamp, limit='100', bar='15m'):
        """
        params1:爬虫程序
        params2:写入数据库
        return :时间戳痕迹
        """
        klineDatas = self.marketCrawler.fetch_history_candles(
            instId=self.instId, after=tamp, bar=bar, limit=limit)
        if not klineDatas:
            print(
                '\n', '参数错误, (code): ' + klineDatas['code'] + ', msg:' +
                klineDatas['msg'], '\n')
            return False, tamp, 0, []
        else:
            listLength = len(klineDatas[0]['data'])
            if listLength == 0:
                print('\n', '数据暂无或已到尽头，上一时间戳为', tamp, '返回数据', klineDatas, '\n')
                return True, tamp, listLength, []
            else:
                data = klineDatas[0]['data']
                last_t_tamp = klineDatas[0]['data'][listLength - 1][0]
                return True, last_t_tamp, listLength, data

    def run(self):
        database = self.task['database']
        times = self.task['times']
        # print(task, database)
        # 交易所 获取 相应k线
        # 2017-12-31 23:59:59 1514735999000
        # 2018-12-31 23:59:59 1546271999000
        # 2019-12-31 23:59:59 1577807999000
        # 2020-12-31 23:59:59 1609430399000
        # start_tamp = get_time_stamp('2019-12-31 23:59:59') * 1000
        start_tamp = times[0]
        # end_tamp = get_time_stamp('2018-12-31 23:59:59') * 1000
        end_tamp = times[1]

        bar = 3  # 单次请求的时间长度
        _bar_unit = 'm'  # 单次请求的时间粒度长单位 m:分 H:小时 D:天 W:周 M:月 Y:年
        limit = 100  # 单次请求的条数
        cumulative = 0  # 累计爬取了多少条
        total = self.get_divde(unit=_bar_unit,
                               _ms=int(start_tamp) - end_tamp,
                               bar=bar)  # 一共多少条
        pbar = tqdm(total=total)  #进度条 和 总条数
        # print('线程' + self.threadID + '开始下载数据  💾')
        # 打印 20到19年的行情数据
        while True:

            status, last_tamp, listLength, data = self.crawler(
                str(start_tamp), bar=str(bar) + _bar_unit, limit=str(limit))
            # 更新时间戳
            start_tamp = last_tamp
            # 更新累计下载条数
            cumulative = cumulative + listLength
            # 更新limit
            limit, divide = self.get_residue_limit(_bar_unit,
                                                   int(start_tamp) - end_tamp,
                                                   bar, limit)
            if not status:
                print(
                    emoji.emojize('您本次共爬取了' + str(total) +
                                  ' 条数据, 爬取被中断, 十分抱歉   🥺'))
                break
            elif divide <= 0:
                print(
                    emoji.emojize('恭喜你爬取完成,   🥳   您本次共爬取了' + str(total) +
                                  ' 条数据'))
                break
            elif listLength == 0:
                print(
                    emoji.emojize('您本次共爬取了' + str(total) +
                                  ' 条数据, 虽未爬取完成, 但继续爬取  🤔'))
                break
            else:
                # 操作数据库
                status, msg = self.mySqlHandler.insert_kline_data(
                    data, database)
                if not status:
                    print(msg)
                    break
                # 更新进度条
                pbar.set_description(
                    emoji.emojize('表 ' + self.threadID + ' 剩余   ' +
                                  str(divide) + '条   ' + '每次' + str(limit) +
                                  '条' +
                                  self.timeTamp.get_time_normal(start_tamp) +
                                  '   📆'))
                pbar.update(listLength)


if __name__ == "__main__":
    # 实例化时间模块
    timeTamp = TimeTamp()
    # 实例化命令行工具
    osHandler = OsHandler()
    # 编辑任务队列
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

    # 实例化交易所
    marketCrawler = MarketCrawler(
        access_key="7dbf6048-5661-4295-9298-d4e9da8b9609",
        secret_key="FB9D1024634A61F8F5F2E376CE10512F",
        passphrase="Zls2548120547",
        host='https://www.okex.com',
        simulated=True)
    # 实例化数据库对象
    mySqlHandler = MySqlHandler(
        ip='127.0.0.1',
        userName='root',
        userPass='qass-utf-8',
        DBName='BTC-USDT_kline',
        charset='utf8',
    )
    #清屏
    osHandler.clear_tem()

    #请求池
    search = []
    for i in range(len(task_library)):
        # if i > 4:
        #     break
        data = task_library[i]
        # 实例化线程对象
        search.append(
            Searchkline(data['database'] + '_task',
                        marketCrawler,
                        mySqlHandler,
                        data,
                        timeTamp=timeTamp))
        search[i].start()
    for item in search:
        item.join()

    print("\n 全部结束 关机 \n")
    osHandler.close_mac()
