# -*- coding:UTF-8 -*-
import emoji
import threading
import json
import re
import sys

sys.path.append('..')
from tqdm import tqdm

from util.TimeStamp import TimeTamp
from MarketCrawler import MarketCrawler
from MySqlHandler import MySqlHandler
from util.OsHandler import OsHandler


class Searchkline(threading.Thread):
    def __init__(
        self,
        threadID,
        marketCrawler,
        mySqlHandler,
        task=None,
        timeTamp=None,
    ):
        threading.Thread.__init__(self)
        self.task = task
        self.threadID = threadID
        self.marketCrawler = marketCrawler
        self.mySqlHandler = mySqlHandler
        self.timeTamp = timeTamp

        if not task:
            raise Exception('{}线程的任务不能为空'.format(threadID))
        self.instId = task['symbol']
        self.bar = int(task['bar'])
        self._bar_unit = task['_bar_unit']
        self.limit = str(task['limit'])

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
        _divide = self.get_divde(unit=_bar_unit, _ms=_ms, bar=int(bar))
        # 当剩余数据长度不足时，重新计算limit

        if _divide <= 1 or _divide < int(limit):
            return _divide, _divide
        else:
            return limit, _divide

    def crawler(self, tamp, limit, bar):
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
                # print('\n', '数据暂无或已到尽头，上一时间戳为', tamp, '返回数据', klineDatas, '\n')
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

        bar = self.bar  # 单次请求的时间长度
        _bar_unit = self._bar_unit  # 单次请求的时间粒度长单位 m:分 H:小时 D:天 W:周 M:月 Y:年
        limit = self.limit  # 单次请求的条数
        cumulative = 0  # 累计爬取了多少条
        total = self.get_divde(unit=_bar_unit,
                               _ms=int(start_tamp) - end_tamp,
                               bar=bar)  # 一共多少条
        pbar = tqdm(total=total)  #进度条 和 总条数
        # print('线程' + self.threadID + '开始下载数据  💾')
        # 打印 20到19年的行情数据
        while True:
            # 更新limit
            l, divide = self.get_residue_limit(_bar_unit,
                                               int(start_tamp) - end_tamp, bar,
                                               limit)
            limit = l
            status, last_tamp, listLength, data = self.crawler(
                str(start_tamp), bar=str(bar) + _bar_unit, limit=str(limit))

            # 更新累计下载条数
            cumulative = cumulative + listLength
            # 更新时间戳
            start_tamp = last_tamp

            if not status:
                # print(
                #     emoji.emojize('您本次共爬取了' + str(total) +
                #                   ' 条数据, 爬取被中断, 十分抱歉   🥺'))
                pbar.set_description(
                    emoji.emojize('表 ' + self.threadID + ' 无剩余数据:被中断   ' +
                                  self.timeTamp.get_time_normal(start_tamp) +
                                  '   📆'))
                pbar.update(total)
                break
            elif divide <= 0 or listLength == 0:
                # print(
                #     emoji.emojize('恭喜你爬取完成,   🥳   您本次共爬取了' + str(total) +
                #                   ' 条数据'))
                pbar.set_description(
                    emoji.emojize('表 ' + self.threadID + ' 无剩余数据:已完成   ' +
                                  self.timeTamp.get_time_normal(start_tamp) +
                                  '   📆'))
                pbar.update(total)
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
    # 取出任务队列 与 滤出队列
    f = open(
        '/Users/work/web/quantitative_investment_python/py/main/crawler/config.json',
        'r')
    config = json.load(f)
    task_library = config['task_library']
    task_filter = config['filter']

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

    # 过滤任务列表，拿出预期数据 task_target
    task_target = []
    for item in task_library:
        for filter_item in task_filter:
            if re.search(filter_item, item['database']):
                task_target.append(item)
    # 遍历预期数据
    for i in range(len(task_target)):
        data = task_target[i]
        # 实例化线程对象
        search.append(
            Searchkline(
                data['database'],
                marketCrawler,
                mySqlHandler,
                data,
                timeTamp=timeTamp,
            ))
        search[len(search) - 1].start()
    for item in search:
        item.join()

    # print("\n 全部结束 关机 \n")
    # osHandler.close_mac()
