# -*- coding:UTF-8 -*-

from events.event import EVENT_TICK, EVENT_LOGIN, EVENT_ERROR, EVENT_POSITION, EVENT_ACCOUNT
from events.engine import Event, EventEngine
from util.TimeStamp import TimeTamp
import base64
import hmac
import sys
import time
import websocket
import json
from threading import Thread
sys.path.append('okexApi')


PUB_URL = "wss://ws.okx.com:8443/ws/v5/public"
PRI_URL = "ws://ws.okx.com:8443/ws/v5/private"


class BaseSocketApi:
    def __init__(self, ws):
        self.ws = ws

    # 订阅频道 subscribe
    def add_channel(self, args):
        self._get_base('subscribe', args)

    # 推送信息
    def _get_base(self, op='subscribe', args=None):
        _a = []
        # 编辑args
        if isinstance(args, list):
            if len(args) == 0:
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
        self.ws.send(json.dumps(_s))


class PublicSocketApi(BaseSocketApi):
    def __init__(self, event_engine: EventEngine, user_info):
        self.thread: Thread = Thread(target=self.run)
        ws = websocket.WebSocketApp(PUB_URL,
                                    on_open=self.ON_OPEN,
                                    on_message=self.ON_MESSAGE,
                                    on_error=self.ON_ERROR,
                                    on_close=self.ON_CLOSED)
        BaseSocketApi.__init__(self, ws)

        self.ws = ws
        self.user_info = user_info
        self.event_engine = event_engine

    # 启动公有链接
    def run(self):
        self.ws.run_forever(http_proxy_host="127.0.0.1",
                            http_proxy_port=10000, proxy_type='socks5')

    # 打开常链接线程
    def start(self):
        self.thread.start()

    # 关闭长链接线程
    def close(self):
        self.ws.close()
        self.thread.join()

    # 生命周期函数 再包装
    def ON_OPEN(self, ws):
        # 订阅默认频道
        self.add_channel(
            {"channel": self.user_info['market_lv'], "instId": self.user_info['symbol']})

    def ON_MESSAGE(self, ws, *arg):
        # 如果有event字段，代表是服务器订阅回推内容，不予处理
        okx_data = json.loads(arg[0])
        if('event' not in okx_data):
            event = Event(EVENT_TICK, okx_data)
            self.event_engine.put(event)

    def ON_CLOSED(self, ws, *arg):
        print('ON_CLOSED')

    def ON_ERROR(self, ws, *error):
        global reconnect_count
        if type(error) == ConnectionRefusedError or type(
                error
        ) == websocket._exceptions.WebSocketConnectionClosedException:
            print("正在尝试第%d次重连" % reconnect_count)
            reconnect_count += 1
            if reconnect_count < 100:
                self.run()
                time.sleep(2)
        else:
            print("其他error!")
            print(error)


class PrivateSocketApi(BaseSocketApi):
    def __init__(self, event_engine: EventEngine, user_info):

        self.thread: Thread = Thread(target=self.run)

        BaseSocketApi.__init__(self)

        self.apiKey = user_info['access_key']
        self.market_lv = user_info['market_lv']
        self.passphrase = user_info['passphrase']
        self.SecretKey = user_info['secret_key']
        self.trading_type = user_info['trading_type']

        self.event_engine = event_engine
        self.ws = ''

    # 启动私有链接
    def run(self):
        self.ws = websocket.WebSocketApp(PRI_URL,
                                         on_open=self.ON_OPEN,
                                         on_message=self.ON_MESSAGE,
                                         on_error=self.ON_ERROR,
                                         on_close=self.ON_CLOSED)
        self.ws.run_forever(http_proxy_host="127.0.0.1",
                            http_proxy_port=10000, proxy_type='socks5')

    # 打开常链接线程
    def start(self):
        self.thread.start()

    # 关闭长链接线程
    def close(self):
        self.ws.close()
        self.thread.join()

    # 生命周期函数
    def ON_OPEN(self, ws):
        self.login(ws)

    def ON_MESSAGE(self, ws, *arg):
        recv_text = json.loads(arg[0])
        event_data = ''
        event_name = ''
        # 处理订阅返回的消息
        if 'event' in recv_text:
            if recv_text['event'] == 'error':
                event_data = '私有频道订阅出错，错误码为：' + recv_text['code']
                event_name = EVENT_ERROR
            elif recv_text['event'] == 'login':
                event_data = recv_text['code'] == 0
                event_name = EVENT_LOGIN
            elif 'event' not in recv_text:
                # 处理推送消息
                if recv_text['arg']['channel'] == 'account':
                    event_data = recv_text['data']
                    event_name = EVENT_ACCOUNT
                elif recv_text['arg']['channel'] == 'positions':
                    event_data = recv_text['data']
                    event_name = EVENT_POSITION

        event = Event(event_name, event_data)
        self.event_engine.put(event)

    def ON_CLOSED(self, ws, res):
        print('私有链接已经关闭')

    def ON_ERROR(self, ws, *error):
        global reconnect_count
        if type(error) == ConnectionRefusedError or type(
                error
        ) == websocket._exceptions.WebSocketConnectionClosedException:
            print("正在尝试第%d次重连" % reconnect_count)
            reconnect_count += 1
            if reconnect_count < 100:
                self.run()
                time.sleep(2)
        else:
            print("其他error!")
            print(error)

    # 订阅 登录
    def login(self, _w):
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

        self._get_base(_w, op='login', args=args)

    
    # 订阅持仓频道-私有
    async def _positions(self, _w):
        await self._get_base(_w,
                             args={
                                 "channel": "positions",
                                 "instType": "ANY"
                             })

    # 订阅持仓频道-私有
    async def _account(self, _w):
        await self._get_base(_w, args={
            "channel": "account",
        })
