# -*- coding:UTF-8 -*-

from dingtalkchatbot.chatbot import DingtalkChatbot
import base64
import hmac
import sys
import asyncio
import time
import websockets
import json
import threading
import gc

sys.path.append('..')
from util.TimeStamp import TimeTamp


class SocketApi:
    def __init__(self, on_message, on_error, user_info=None):
        self.on_handle_message = on_message
        self.on_handle_error = on_error

        # 加载配置文件
        # user_info

        self.apiKey = user_info['access_key']
        self.market_lv = user_info['market_lv']
        self.passphrase = user_info['passphrase']
        self.SecretKey = user_info['secret_key']
        self.trading_type = user_info['trading_type']
        self.private_url = 'wss://ws.okex.com:8443/ws/v5/private'
        self.public_url = 'wss://ws.okex.com:8443/ws/v5/public'
        # 公有私有频道注册表
        self.subscribe = user_info['subscribe']
        # 心跳函数loop
        asyncio.run_coroutine_threadsafe(self.set_hearting(),
                                         self._get_thred_loop('    heart   '))
        # #获取线程锁
        self.threadLock = threading.RLock()
        self.timeTamp = TimeTamp()
        # 注册本---心跳函数
        self.subscribe_INFO = {}
        self.task_dict = {}
        # 各频道send方法
        self.subscribe_DICT = {
            'positions': self._positions,
            'account': self._account,
            'market': self._market
        }

    # 方法总入口
    def run(self, public_subscribe=None, private_subscribe=None):
        if public_subscribe:
            # 获取一个跑起异步协程的子线程
            new_loop = self._get_thred_loop('---public---' + public_subscribe +
                                            '---')
            # 扔到对应线程异步里去
            self.task_dict[
                public_subscribe] = asyncio.run_coroutine_threadsafe(
                    self.run_public(public_subscribe, self.public_url,
                                    new_loop), new_loop)

        if private_subscribe:
            # 获取一个跑起异步协程的子线程
            new_loop = self._get_thred_loop('---private---' +
                                            private_subscribe + '---')
            # 扔到对应线程异步里去
            self.task_dict[
                private_subscribe] = asyncio.run_coroutine_threadsafe(
                    self.run_private(private_subscribe, self.private_url,
                                     new_loop), new_loop)

        # 心跳函数
    async def set_hearting(self):
        # 如果 链接打开着
        while True:
            time.sleep(25)
            gc.collect()
            self.threadLock.acquire()
            dict = self.subscribe_INFO.copy()
            try:
                if dict and len(dict) > 0:
                    print('进入了心跳函数', dict)
                    for _k, _v in dict.items():
                        _w = _v['_w']
                        loop = _v['loop']
                        status = _v['status']
                        # pong 通了
                        if _w.state.name == "OPEN":
                            if status != None:  # 进入心跳循环流程
                                # 更新状态
                                dict[_k]['status'] = None
                                # 在心跳线程中塞入一个ping事件
                                await self._do_send(_w, 'ping')
                            elif status == None:  # 进入重启流程
                                self._restart_link(_w, _k, loop)
                        else:
                            if status == 'done':
                                self._restart_link(_w, _k, loop)

            except BaseException as err:
                print('心跳函数发生错误', str(err))
                self.threadLock.release()
            finally:
                del dict
                self.threadLock.release()

    # 启动私有链接
    async def run_private(self, subscribe, url, loop):
        try:
            async with websockets.connect(url) as _w:
                # 登录账户
                status = await self.login(_w)
                if not status:
                    print('登录失败')
                    return
                # 发起订阅请求
                await self.subscribe_DICT[subscribe](_w)

                # 注册心跳表 (websocket,频道名,事件循环对象,状态)
                # 清理对应频道的注册表
                self.threadLock.acquire()
                self.set_sub_info(_w=_w,
                                  subscribe=subscribe,
                                  loop=loop,
                                  status='start')
                self.threadLock.release()
                # 开启消息监听
                await self._get_recv(_w, subscribe)
        except BaseException as err:
            self.dingding_msg(subscribe + '出现问题,进行重启。' + str(err))
            print('出现问题,', subscribe, '重启', str(err))
        finally:
            if subscribe in self.subscribe_INFO:
                self.set_sub_info(subscribe=subscribe, status='done')

    # 启动公有链接
    async def run_public(self, subscribe, url, loop):
        try:
            # 开启socket
            async with websockets.connect(url) as _w:
                # 发起订阅请求
                await self.subscribe_DICT[subscribe](_w)
                # 注册心跳表 (websocket,频道名,事件循环对象,状态)
                self.threadLock.acquire()
                # 增加一条 频道信息
                self.set_sub_info(_w=_w,
                                  subscribe=subscribe,
                                  loop=loop,
                                  status='start')
                self.threadLock.release()
                # 开启消息监听
                await self._get_recv(_w, subscribe)
        except BaseException as err:
            self.dingding_msg(subscribe + '出现问题,进行重启。' + str(err))
            print('出现问题,', subscribe, '重启', str(err))
        finally:
            if subscribe in self.subscribe_INFO:
                self.set_sub_info(subscribe=subscribe, status='done')

    # 钉钉消息助手
    def dingding_msg(self, text, flag=False):
        webhook = 'https://oapi.dingtalk.com/robot/send?access_token=cb4b89ef41c8008bc4526bc33d2733a8c830f1c10dd6701a58c3ad149d35c8cc'
        ding = DingtalkChatbot(webhook)
        text = text + ' :525'
        ding.send_text(msg=text, is_at_all=flag)

    # 注册频道信息字典
    def set_sub_info(self,
                     _w=None,
                     subscribe=None,
                     loop=None,
                     status=None,
                     type="add"):
        if subscribe in self.subscribe_INFO:
            # 编辑
            if _w:
                self.subscribe_INFO[subscribe]['_w'] = _w
            elif loop:
                self.subscribe_INFO[subscribe]['loop'] = loop
            elif status:
                self.subscribe_INFO[subscribe]['status'] = status
        elif _w and subscribe and loop and status:
            # 新增
            self.subscribe_INFO[subscribe] = {}
            self.subscribe_INFO[subscribe]['_w'] = _w
            self.subscribe_INFO[subscribe]['loop'] = loop
            self.subscribe_INFO[subscribe]['status'] = status

    # 接收工具
    async def _get_recv(self, _w, subscribe):
        while True:
            await asyncio.sleep(1)
            recv_text = await _w.recv()
            # 消息处理阶段
            if recv_text != 'pong':
                recv_text = json.loads(recv_text)
                if 'event' in recv_text:
                    if recv_text['event'] == 'error':
                        print(
                            '订阅',
                            recv_text['msg'] + '失败，错误码为：' + recv_text['code'])
                        break
                    else:
                        self.dingding_msg('订阅' + recv_text['arg']['channel'] +
                                          '成功')
                        print('订阅', recv_text['arg']['channel'], '成功')
                else:
                    # print('连接中', recv_text, subscribe)
                    self.on_handle_message(recv_text)
            else:
                # 进程锁 更新频道信息
                self.threadLock.acquire()
                self.subscribe_INFO[subscribe]['status'] = recv_text
                self.threadLock.release()

    # 需要重启响应函数
    def _restart_link(self, _websocket, subscribe, loop):
        print('进入重启程序---关闭连接与loop,' + subscribe)
        try:
            # 关闭 websocket 停下 loop循环 run_coroutine_threadsafe
            if _websocket and _websocket.state.name == 'OPEN' and not _websocket.closed:
                asyncio.run_coroutine_threadsafe(_websocket.close(),
                                                 loop).result()
            # 停止task任务
            self.task_dict[subscribe].cancel()
            loop.call_soon_threadsafe(loop.stop)

            # 清理数据
            self.task_dict.pop(subscribe)
            self.subscribe_INFO.pop(subscribe)
            # 重启
            params = {'type': 'restart', "data": subscribe}
            self.on_handle_error(params)

        except BaseException as err:
            self.dingding_msg('重启程序出现问题: ' + str(err))
            print('重启程序出现问题')


# 获得一个在新线程里物阻塞的异步对象

    def _get_thred_loop(self, name):
        # 获取loop对象
        def get_loop():
            # 运行事件循环
            new_loop = asyncio.new_event_loop()  #在当前线程下创建时间循环，（未启用）
            return new_loop

        # 在一个新线程中启动loop
        def new_threading(new_loop):
            def _start_loop(loop):
                try:
                    asyncio.set_event_loop(loop)
                    loop.run_forever()
                finally:
                    loop.close()

            t = threading.Thread(target=_start_loop,
                                 name=name + "Thread",
                                 args=(new_loop, ))  #通过当前线程开启新的线程去启动事件循环
            t.start()

        new_loop = get_loop()  # 获取一个异步轮询对象
        new_threading(new_loop)  # 新起一个线程跑异步轮询
        return new_loop

    # 频道区
    # 订阅 登录

    async def login(self, _w):
        timestamp = (str(time.time()).split(".")[0])

        # 私有函数
        def _get_sign():

            message = str(timestamp) + "GET" + '/users/self/verify'
            mac = hmac.new(
                bytes(self.SecretKey.encode('utf-8')),
                bytes(message.encode('utf-8')),
                digestmod="sha256",
            )
            d = mac.digest()
            sign = base64.b64encode(d)
            return str(sign, 'utf-8')

        args = {'apiKey': '', 'passphrase': '', 'timestamp': '', 'sign': ''}

        args['apiKey'] = self.apiKey
        args['passphrase'] = self.passphrase
        args['timestamp'] = timestamp
        args['sign'] = _get_sign()

        await self._get_base(_w, op='login', args=args)

        recv_text = json.loads(await _w.recv())
        # 成功或失败推送处理
        if 'event' in recv_text:
            if recv_text['event'] == 'error':
                print('订阅', recv_text['msg'] + '失败，错误码为：' + recv_text['code'])
                return False
            else:
                if recv_text['code'] == '0':
                    return True

    # 订阅行情频道
    def _market(self, _w, channel='candle1m', symbol='BTC-USDT'):
        return self._get_base(_w,
                              args={
                                  "channel": self.market_lv,
                                  "instId": symbol
                              })

    # 订阅持仓频道-私有
    def _positions(self, _w):
        return self._get_base(_w,
                              args={
                                  "channel": "positions",
                                  "instType": "ANY"
                              })

    # 订阅持仓频道-私有
    def _account(self, _w):
        return self._get_base(_w, args={
            "channel": "account",
        })

    # 基础工具函数
    # 订阅函数
    def _get_base(self, _w, op='subscribe', args=None):
        _a = []
        # 编辑args
        if isinstance(args, list):
            if len(args) == 0:
                print('请输入订阅的频道')
                return
            for item in args:
                _a.append(item)
        elif isinstance(args, dict):
            _a.append(args)
        else:
            print('args类型错误', type(args))
            return
        # 发送订阅
        _s = {'op': op, 'args': _a}

        return self._do_send(_w, json.dumps(_s))

    # send操作函数-公共
    def _do_send(self, _w, statements):
        return _w.send(statements)
