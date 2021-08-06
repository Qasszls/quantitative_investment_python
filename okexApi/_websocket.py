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


class BaseSocketApi:
    def __init__(self, name, url):
        self.timeTamp = TimeTamp()
        self._recv_pong = None
        self._task = None
        self.name = name
        self.url = url

    # 方法总入口
    def run(self, ON_CREATED, ON_MESSAGE, ON_CLOSED):
        # 获取一个跑起异步协程的子线程
        ws_loop = self._get_thred_loop('---' + self.name + '---')
        # 扔到对应线程异步里去
        self._task = asyncio.run_coroutine_threadsafe(
            self.link_websocket(ws_loop, ON_CREATED, ON_MESSAGE, ON_CLOSED),
            ws_loop)

    # 连接 websocket
    async def link_websocket(self, ws_loop, ON_CREATED, ON_MESSAGE, ON_CLOSED):
        url = self.url
        name = self.name
        try:
            async with websockets.connect(url) as websocket:
                # do_something 订阅频道 设置心跳函数
                await ON_CREATED(websocket)
                self.run_hearting(websocket, ws_loop)
                self._recv_pong = 'pong'
                # 开启消息监听
                await self._get_recv(websocket, ON_MESSAGE)
        except BaseException as err:
            self.dingding_msg(name + '连接出现问题,进行重启。' + str(err))
            print('出现问题,', name, '重启', str(err))
        finally:
            self._restart_link(ws_loop, ON_CLOSED)

    # 启动heart函数总入口
    def run_hearting(self, websocket, ws_loop):
        heart_loop = self._get_thred_loop('    heart   ')
        asyncio.run_coroutine_threadsafe(
            self._set_hearting(websocket, heart_loop, ws_loop), heart_loop)

    # 设置心跳函数
    async def _set_hearting(self, websocket, heart_loop, ws_loop):
        # 如果 链接打开着
        try:
            while True:
                time.sleep(20)
                gc.collect()
                if websocket.state.name == "OPEN":
                    if self._recv_pong == 'pong':
                        self._recv_pong = 'ping'  # 设置为None 并且期待下一次收到pong
                        await self._do_send(websocket, 'ping')
                    else:
                        raise Exception('ws服务器已经断开连接')
                else:
                    raise Exception('websocket已关闭')

        except BaseException as err:
            print('心跳函数抛出异常', str(err))
        finally:
            # 关闭 websocket 停下 loop循环 run_coroutine_threadsafe
            if websocket and websocket.state.name == 'OPEN' and not websocket.closed:
                asyncio.run_coroutine_threadsafe(websocket.close(),
                                                 ws_loop).result()
            heart_loop.call_soon_threadsafe(heart_loop.stop)

    # 接收工具
    async def _get_recv(self, websocket, ON_MESSAGE):
        while True:
            recv_text = await websocket.recv()
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
                    # print('连接中', recv_text)
                    ON_MESSAGE(recv_text)
            else:
                # print('pong :', recv_text)
                self._recv_pong = recv_text

    # 需要重启响应函数
    def _restart_link(self, ws_loop, ON_CLOSED):
        name = self.name
        print('进入重启程序---关闭连接与loop,' + name)
        try:
            if self._task and not self._task.cancelled():
                self._task.cancel()
                # 停止事件循环
                print('停止事件循环')
                if not ws_loop.is_closed():
                    ws_loop.call_soon_threadsafe(ws_loop.stop)

                # 清理数据
                print('清理数据')
                self._task = None
                print('重启')
                params = {'type': 'restart', "data": name}
                ON_CLOSED(params)
            else:
                print('_task已关闭,不进行重启')
        except BaseException as err:
            self.dingding_msg('重启程序出现问题: ' + str(err))
            print('重启程序出现问题' + str(err))

    # 钉钉消息助手
    def dingding_msg(self, text, flag=False):
        webhook = 'https://oapi.dingtalk.com/robot/send?access_token=cb4b89ef41c8008bc4526bc33d2733a8c830f1c10dd6701a58c3ad149d35c8cc'
        ding = DingtalkChatbot(webhook)
        text = text + ' :525'
        ding.send_text(msg=text, is_at_all=flag)

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
                    # 停止后自动关闭事件循环
                    loop.close()

            t = threading.Thread(target=_start_loop,
                                 name=name + "Thread",
                                 args=(new_loop, ))  #通过当前线程开启新的线程去启动事件循环
            t.start()

        new_loop = get_loop()  # 获取一个异步轮询对象
        new_threading(new_loop)  # 新起一个线程跑异步轮询
        return new_loop

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


class PublicSocketApi(BaseSocketApi):
    def __init__(self, on_created, on_message, on_closed, user_info):
        BaseSocketApi.__init__(
            self,
            name='public',
            url="wss://ws.okex.com:8443/ws/v5/public",
        )

        self.market_lv = user_info['market_lv']
        self.symbol = user_info['symbol']

        self.on_created = on_created
        self.on_message = on_message
        self.on_closed = on_closed

    # # 启动公有链接
    def subscription(self):
        self.run(self.ON_CREATED, self.ON_MESSAGE, self.ON_CLOSED)

    # 生命周期函数 再包装
    async def ON_CREATED(self, _w):
        await self._market(_w, channel=self.market_lv, symbol=self.symbol)
        if self.on_created:
            self.on_created()

    def ON_MESSAGE(self, res):
        self.on_message(res)

    def ON_CLOSED(self, res):
        self.on_closed(res)

    # 订阅行情频道
    def _market(self, _w, channel='candle1m', symbol='BTC-USDT'):
        return self._get_base(_w, args={"channel": channel, "instId": symbol})


class PrivateSocketApi(BaseSocketApi):
    def __init__(self, on_created, on_message, on_closed, user_info):
        BaseSocketApi.__init__(self,
                               name='private',
                               url='wss://ws.okex.com:8443/ws/v5/private')
        self.apiKey = user_info['access_key']
        self.market_lv = user_info['market_lv']
        self.passphrase = user_info['passphrase']
        self.SecretKey = user_info['secret_key']
        self.trading_type = user_info['trading_type']

        self.on_created = on_created
        self.on_message = on_message
        self.on_closed = on_closed

    # 启动私有链接
    def subscription(self):
        self.run(self.ON_CREATED, self.ON_MESSAGE, self.ON_CLOSED)

    # 生命周期函数
    async def ON_CREATED(self, _w):
        status = await self.login(_w)
        if not status:
            raise Exception('登录出错')
        await self._positions(_w)
        await self._account(_w)
        if self.on_created:
            self.on_created()

    def ON_MESSAGE(self, res):
        self.on_message(res)

    def ON_CLOSED(self, res):
        self.on_closed(res)

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
                print('登录出错，错误码为：' + recv_text['code'])
                return False
            else:
                if recv_text['code'] == '0':
                    return True

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
