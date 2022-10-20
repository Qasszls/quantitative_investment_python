# -*- coding:UTF-8 -*-
import json
import time
import emoji
from trading.engine import Trading
from share.TimeStamp import TimeTamp
from okexApi.websocket import OkxExchange
from okexApi._http import HttpApi
from events.engine import EventEngine

from dingtalkchatbot.chatbot import DingtalkChatbot


class Main:
    def __init__(self):
        self.user_info = self.get_user_info()

        self.event_engine = EventEngine()
        self.event_engine.start()

        self.okx_exchange = OkxExchange(self.event_engine,
                                        user_info=self.user_info)  # 初始化长连接
        self.http = HttpApi(user_info=self.user_info)  # 初始化短连接
        self.trading = Trading(
            self.event_engine, self.http, self.get_user_info())
        self.timeTamp = TimeTamp()  # 初始化时间操作对象
        webhook = 'https://oapi.dingtalk.com/robot/send?access_token=cb4b89ef41c8008bc4526bc33d2733a8c830f1c10dd6701a58c3ad149d35c8cc'
        self.ding = DingtalkChatbot(webhook)

    # 主函数

    def get_user_info(self):
        f = open('config.json', 'r', encoding='utf-8')
        _data = json.load(f)
        return _data['realPay']

    def start(self):
        try:
            self.okx_exchange.connect()
            self.trading.start()
            print('主程序已打开')
        except Exception as e:
            print('全局状态捕获', e)

    def dingding_msg(self, text, flag=False):

        text = text + '  作业时间：' + self.timeTamp.get_time_normal(
            time.time() * 1000) + ' :525'
        self.ding.send_text(msg=text, is_at_all=flag)

    # 获取服务器更新节点

    def get_systm_status(self):
        _ures, error = self.http.get_update_status()
        if not error and len(_ures) > 0:
            _utimes = 0
            for item in _ures:
                if item['state'] == 'ongoing':
                    self.dingding_msg(
                        '服务器正在更新中,更新开始时间: ' +
                        self.timeTamp.get_time_normal(item['begin']) +
                        '; 更新结束时间: ' +
                        self.timeTamp.get_time_normal(item['end']))
                    # 找出最长更新时间段
                    if _utimes < int(item['end']):
                        _utimes = int(item['end'])
                    # 服务器正在更新
                elif item['state'] == 'scheduled':
                    self.dingding_msg(
                        '服务器有更新计划,更新开始时间: ' +
                        self.timeTamp.get_time_normal(item['begin']) +
                        '; 更新结束时间: ' +
                        self.timeTamp.get_time_normal(item['end']))
                    print('服务器有更新计划,更新开始时间: ' +
                          self.timeTamp.get_time_normal(item['begin']) +
                          '; 更新结束时间: ' +
                          self.timeTamp.get_time_normal(item['end']))
            self.update_times = _utimes
        elif error:
            # 网络问题 轮询请求接口，等待网络恢复
            print('get_systm_status 出现问题')
            time.sleep(3)
            self.get_systm_status()
        else:
            self.update_times = 0
            self.dingding_msg('策略运行中，服务器没有更新计划')


if __name__ == "__main__":

    engine = Main()
    engine.start()
