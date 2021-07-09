# -*- coding:UTF-8 -*-

import base64
import hmac
import sys
import asyncio
import time
import websockets
import json

sys.path.append('..')


class SocketApi:
    def __init__(self, callback, trading_type="virtualPay"):
        self.on_handle_message = callback

        # 加载配置文件
        f = open('../config.json', 'r')
        config = json.load(f)[trading_type]

        # 变量赋值
        self.apiKey = config['access_key']
        self.passphrase = config['passphrase']
        self.SecretKey = config['secret_key']
        self.subscribe_DICT = {
            'positions': self._positions,
            'account': self._account,
            'market': self._market
        }

    async def run(self, subscribe):
        private_url = 'wss://wspap.okex.com:8443/ws/v5/private?brokerId=9999'
        public_url = 'wss://wspap.okex.com:8443/ws/v5/public?brokerId=9999'
        private_subscribe = ['positions', 'account']
        public_subscribe = ['market']
        if subscribe in private_subscribe:
            await self.run_private(subscribe, private_url)
        elif subscribe in public_subscribe:
            await self.run_public(subscribe, public_url)

    async def run_private(self, subscribe, url):
        url = 'wss://wspap.okex.com:8443/ws/v5/private?brokerId=9999'
        async with websockets.connect(url) as _w:
            # 登录账户
            status = await self.login(_w)
            if not status:
                print('登录失败')
                return
            await self.subscribe_DICT[subscribe](_w)
            await self._get_recv(_w)

    # 并启动消息接收器
    async def run_public(self, subscribe, url):
        # 注册公共socket
        async with websockets.connect(url) as _w:

            await self.subscribe_DICT[subscribe](_w)
            await self._get_recv(_w)

    # 接收工具
    async def _get_recv(self, _w):
        while True:
            recv_text = json.loads(await _w.recv())
            # 成功或失败推送处理
            if 'event' in recv_text:
                if recv_text['event'] == 'error':
                    print('订阅',
                          recv_text['msg'] + '失败，错误码为：' + recv_text['code'])
                else:
                    print('订阅', recv_text['arg']['channel'], '成功')
            else:
                self.on_handle_message(recv_text)

    # 登录
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

    # 频道区

    # 订阅行情频道
    def _market(self, _w, channel='candle1m', symbol='BTC-USDT'):
        return self._get_base(_w, args={"channel": channel, "instId": symbol})

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

    # 工具函数
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
