# -*- coding:UTF-8 -*-

import base64
import hmac
import sys
import asyncio
import time
import websockets
import json
import threading

sys.path.append('..')


class SocketApi:
    def __init__(self, callback, user_info=None):
        self.on_handle_message = callback

        # 加载配置文件
        # user_info

        self.apiKey = user_info['access_key']
        self.market_lv = user_info['market_lv']
        self.passphrase = user_info['passphrase']
        self.SecretKey = user_info['secret_key']
        self.trading_type = user_info['trading_type']
        # loop对象
        self.new_loop_public = None
        self.new_loop_private = None
        # timer 线程对象
        self.pri_timer = None
        self.pub_timer = None
        # websocket对象
        self.private_w = None
        self.public_w = None
        # 获取进程锁
        self.subscribe_DICT = {
            'positions': self._positions,
            'account': self._account,
            'market': self._market
        }

    # 方法总入口
    def run(self, public_subscribe=None, private_subscribe=None):
        private_url = 'wss://ws.okex.com:8443/ws/v5/private'
        public_url = 'wss://ws.okex.com:8443/ws/v5/public'

        # 是否为模拟盘
        if self.trading_type == '0':
            private_url = 'wss://wspap.okex.com:8443/ws/v5/private?brokerId=9999'
            public_url = 'wss://wspap.okex.com:8443/ws/v5/public?brokerId=9999'
        if public_subscribe:
            # 获取一个跑起异步协程的子线程
            self.new_loop_public = self._get_thred_loop('public')
            # 扔到对应线程异步里去
            asyncio.run_coroutine_threadsafe(
                self.run_public(public_subscribe, public_url),
                self.new_loop_public)

        if private_subscribe:
            # 获取一个跑起异步协程的子线程
            self.new_loop_private = self._get_thred_loop('private')
            # 扔到对应线程异步里去
            asyncio.run_coroutine_threadsafe(
                self.run_private(private_subscribe, private_url),
                self.new_loop_private)

    # 启动私有链接
    async def run_private(self, subscribe, url):
        async with websockets.connect(url) as _w:
            # 登录账户
            status = await self.login(_w)
            if not status:
                print('登录失败')
                return
            for item in subscribe:
                # 发送send
                await self.subscribe_DICT[item](_w)
            self.private_w = _w
            await self._get_recv(_w, 'private')

    # 启动公有链接
    async def run_public(self, subscribe, url):
        # 注册公共socket
        async with websockets.connect(url) as _w:
            for item in subscribe:
                # 发送send
                await self.subscribe_DICT[item](_w)

            self.public_w = _w
            await self._get_recv(_w, 'public')

    # 获得一个在新线程里物阻塞的异步对象
    def _get_thred_loop(self, name):
        # 获取loop对象
        def to_start_loop():
            # 运行事件循环
            new_loop = asyncio.new_event_loop()  #在当前线程下创建时间循环，（未启用）
            return new_loop

        # 在一个新线程中启动loop
        def new_threading(new_loop):
            def _start_loop(loop):
                asyncio.set_event_loop(loop)
                loop.run_forever()

            t = threading.Thread(target=_start_loop,
                                 name=name + "Thread",
                                 args=(new_loop, ))  #通过当前线程开启新的线程去启动事件循环
            t.start()

        new_loop = to_start_loop()  # 获取一个异步轮询对象
        new_threading(new_loop)  # 新起一个线程跑异步轮询
        return new_loop

    async def set_hearting(self, _w, _wname, timer):

        # 心跳链接试验版
        if timer == None or (timer and not timer.is_alive()):
            await _w.send('ping')
            timer = threading.Timer(25, self._restart_link, (_wname, ))
            timer.start()
        return timer

    # 接收工具
    async def _get_recv(self, _w, _wname):
        timer = None
        while True:
            timer = await self.set_hearting(_w, _wname, timer)
            recv_text = await _w.recv()
            timer.cancel()
            if recv_text != 'pong':
                recv_text = json.loads(recv_text)
                if 'event' in recv_text:
                    if recv_text['event'] == 'error':
                        print(
                            '订阅',
                            recv_text['msg'] + '失败，错误码为：' + recv_text['code'])
                    else:
                        print('订阅', recv_text['arg']['channel'], '成功')
                else:
                    print('连接中', threading.activeCount())
                    self.on_handle_message(recv_text)

    # 需要重启响应函数
    def _restart_link(self, _wname):
        def async_close(_w, loop):
            future = asyncio.run_coroutine_threadsafe(_w.close(), loop)
            result = future.result()
            return result

        if _wname == "private":
            async_close(self.private_w, self.new_loop_private)
            self.private_w = None
            # print('private_w is close')
        else:
            async_close(self.public_w, self.new_loop_public)
            self.public_w = None
            # print('public_w is close')

        params = {'type': 'restart', "data": _wname}
        self.on_handle_message(params)

    # 关闭ws链接
    def websocket_close(self, subscribe, _w):
        _w.close()
        print(subscribe, '已经关闭', _w)

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
