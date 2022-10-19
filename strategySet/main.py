# -*- coding:UTF-8 -*-

import pandas as pd
import numpy as np
import json
import sys
import os
import asyncio
import time
import re

sys.path.append('..')
if re.search('/main/server', os.getcwd()):
    sys.path.append(
        '/Users/work/web/quantitative_investment_python/py/main/strategySet')
# from share.OsHandler import OsHandler
from sqlHandler import SqlHandler
from investment import Investment

# import pyecharts.options as opts
# from pyecharts.charts import Line


class DataBackTesting:
    def __init__(self):
        self.sqlHandler = SqlHandler(
            ip='127.0.0.1',
            userName='root',
            userPass='qass-utf-8',
            DBName='BTC-USDT_kline',
            charset='utf8',
        )

    # 根据列表id反查列表名；清空总表对应数据；删除对应表
    def delete_market_data(self, id):
        table_name = self.sqlHandler.select_table_id(id)['result'][0][1]
        res = self.sqlHandler.delete_table(table_name)
        if res['status']:
            return self.sqlHandler.delete_table_record('table_record', id)

    # 根据列表id反差列表名；根据列表名查询列表数据
    def search_market_data(self, id):
        res = self.sqlHandler.select_table_id(id)
        if res['status']:
            table_name = res['result'][0][1]
            table_data = self.sqlHandler.select_trade_marks_data(
                table_name)['result']
            df = pd.DataFrame(table_data)
            df.columns = self._get_table_column(table_name)
        return df.to_dict(orient='records')

    # 返回查询列表区块
    def get_record_list(self, table_name):
        # sql 获取列表数据
        list_res = self.sqlHandler.select_test_record_list(table_name)
        if len(list_res['result']) > 0:
            # sql 获取列名数据
            column = self._get_table_column(table_name)
            df = pd.DataFrame(list_res['result'])
            df.columns = column
            if list_res['status']:
                return df.to_dict('records')
        else:
            print('未查得')
            return []

    # 跑回测代码区块
    def _get_market_data(self, table_name, time=[]):
        res1 = self.search_table(table_name, time)

        if res1['status'] and res1['result']:
            self.klineMediumLevel = self._get_kline_data(
                res1['result'], table_name)

            # 获取样本数据
            self.medDF = self._get_MACD(self.klineMediumLevel['close_price'],
                                        self.klineMediumLevel['id_tamp'])
            return True
        else:
            print(res1, res2, '表不存在或为空')
            return False

    def _get_kline_data(self, data, table_name):
        df = pd.DataFrame(list(data))
        df.columns = self._get_table_column(table_name)
        #所有内容转化为数值型
        df = df.astype(float)
        return df

    def _get_MACD(self,
                  price,
                  timeTamps,
                  fastperiod=12,
                  slowperiod=26,
                  signalperiod=9):
        """
            入参：价格和基准等
            出参：dataFrame格式的数据结构
            """
        ewma12 = price.ewm(span=fastperiod).mean()
        ewma60 = price.ewm(span=slowperiod).mean()
        dif = ewma12 - ewma60
        dea = dif.ewm(span=signalperiod).mean()
        bar = (dif - dea
               )  #有些地方的bar = (dif-dea)*2，但是talib中MACD的计算是bar = (dif-dea)*1
        macd = dif - dea
        return pd.DataFrame({
            'macd': macd,
            'dif': dif,
            'dea': dea,
            'bar': bar,
            'id_tamp': timeTamps.values
        })

    def search_table(self, table_name, time=[]):
        if len(time) > 0:
            return self.sqlHandler.select_trade_marks_data(table_name, time)
        else:
            return self.sqlHandler.select_trade_marks_data(table_name)

    def run_test(self,
                 checkSurplus,
                 stopLoss,
                 principal,
                 mode,
                 odds,
                 _name,
                 time=[],
                 leverage=1):

        # 查询该表是否存在
        if len(time) > 0:
            table_name = '15m_60m_' + str(int(
                float(checkSurplus) * 100)) + '_' + str(
                    int(float(stopLoss) * 100)) + '_' + str(
                        time[0]) + '_' + str(time[1])
        else:
            table_name = '15m_60m_' + str(int(
                float(checkSurplus) * 100)) + '_' + str(
                    int(float(stopLoss) * 100))
        if _name != '':
            table_name = table_name + '_' + _name
        search_res = self.search_table(table_name)

        if search_res['status']:
            # 表存在 更新record表内容 可以去list查看历史记录
            # res = self.update_table_record(table_name)
            print('已有同名表')
        else:
            # 首先按照时间区段解析行情数据
            market_data_res = self._get_market_data('2020_kline_1H', time)
            if market_data_res:
                # 表不存在 创建表
                create_res = self.sqlHandler.create_trade_marks_table(
                    table_name)
                if create_res['status']:
                    # 创建表成功，执行回测
                    self._run_investment(checkSurplus, stopLoss, principal,
                                         table_name, self.klineMediumLevel,
                                         self.medDF, mode, odds, _name,
                                         leverage)

    # 查询指定表，返回表头列表
    def _get_table_column(self, table_name):
        res = self.sqlHandler.select_table_colimn_name(table_name)
        column_list = res['result']
        column = []
        # 编辑表头
        for item in column_list:
            if item[0] not in column:
                column.append(item[0])
        return column

    def _run_investment(self, checkSurplus, stopLoss, principal, table_name,
                        klineMediumLevel, medDF, mode, odds, _name, leverage):
        # 遍历并插入数据
        investment = Investment(checkSurplus, stopLoss, principal,
                                klineMediumLevel, medDF, table_name, mode,
                                odds, _name, leverage)
        # 返回要写入table_record表的内容
        investment.start()
        # 更新record表内容 table_name
        self.update_table_record(table_name)

    def update_table_record(self, table_name):
        # 更新record表内容 table_name
        res = self.sqlHandler.insert_table_record_data(
            str(round(time.time() * 1000)), table_name, True)
        return res['status']
