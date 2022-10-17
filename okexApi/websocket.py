from events.event import EVENT_TICK, EVENT_LOGIN, EVENT_ERROR, EVENT_INFO, EVENT_POSITION, EVENT_ACCOUNT
from events.engine import Event, EventEngine
from util.TimeStamp import TimeTamp
import base64
import hmac
import sys
import time
import websocket
import json
from queue import Empty, Queue
from threading import Thread
sys.path.append('okexApi')

"""
   BaseSocketApi:最底层socket，链接服务器，多线程执行，提供订阅和取消订阅的接口。
   DataHandle:区分订阅成功与失败的返回，区分订阅成功后推送的返回。指定on_tick等回调函数，继承者可以覆盖。
    我于鏊干嘛
    写蒙蔽了
    我想写个业务层包裹的websocket但是我的抽象和分层能力需要锻炼，不太懂什么放在什么层。
    业务层的内容可以放在Engine类中，比如发送事件；收集到的数据的处理；私有频道登录动作的监听。
"""

PUB_URL = "wss://ws.okx.com:8443/ws/v5/public"
PRI_URL = "ws://ws.okx.com:8443/ws/v5/private"


class Active:
    """类型定义
    """

    def __init__(self, active, *args):
        self.active = active
        self.args = args


class BaseSocketApi:
    """基础技术类
    """

    def __init__(self, url, message_callback):
        self.ws = None
        self.thread = None
        self.message_callback = message_callback  # 通讯函数
        self._queue: Queue = Queue()
        self.active = False
        self.url = url
        self.thread: Thread = Thread(target=self.run)

    # 链接服务器
    def run(self):
        self.ws = websocket.WebSocketApp(self.url,
                                         on_open=self.ON_OPEN,
                                         on_message=self.ON_MESSAGE,
                                         on_error=self.ON_ERROR,
                                         on_close=self.ON_CLOSED)
        self.ws.run_forever(http_proxy_host="127.0.0.1",
                            http_proxy_port=10000, proxy_type='socks5')

    # 监听长连接
    def connect_sever(self):
        # 本机代理链接
        self.thread.start()

    # 订阅频道
    def add_channel(self, args, op='subscribe'):
        if self.active:
            self._push(args=args, op=op)
        else:
            active: Active = Active(self.add_channel, args, op)
            self._queue.put(active)

    # 取消订阅频道
    def remove_channel(self, args, op='unsubscribe'):
        if self.active:
            self._push(args=args, op=op)
        else:
            active: Active = Active(self.remove_channel, args, op)
            self._queue.put(active)

    # 关闭长链接线程
    def close(self):
        self.ws.close()
        self.thread.join()

    # 推送信息
    def _push(self, op='subscribe', args=None):
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

    # 生命周期函数 再包装
    def ON_OPEN(self, ws):
        # 链接已经开启
        self.active = True
        # 再次调用这些方法
        while not self._queue.empty():
            active_item = self._queue.get(block=True, timeout=1)
            fn = active_item.active
            args = active_item.args
            fn(*args)

    # 服务端频道推送数据回调

    def ON_MESSAGE(self, ws, *arg):
        if self.message_callback:
            self.message_callback(ws, arg)

    # 长连接关闭的回调
    def ON_CLOSED(self, ws, *arg):
        self.active = False
        self.thread.join()

    # 遇到网络问题，自动重连
    def ON_ERROR(self, ws, *error):
        global reconnect_count
        self.active = False
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


class OkxExchange:
    """衍生业务类
    """

    def __init__(self, event_engine, user_info):
        self.event_engine = event_engine
        self.user_info = user_info
        self.private = BaseSocketApi(PRI_URL, self.ON_MESSAGE)
        self.public = BaseSocketApi(PUB_URL, self.ON_MESSAGE)

    def connect(self):
        # self.private.connect_sever()
        self.public.connect_sever()
        # 启动私有模块
        # self.private.add_channel(op='login', args=self._get_login_args())
        # 启动行情模块
        self.public.add_channel(
            args={"channel": self.user_info['market_lv'], "instId": self.user_info['symbol']})

    # 获得用户登录所需要的参数
    def _get_login_args(self):
        timestamp = (str(time.time()).split(".")[0])

        # 私有函数 获得签名
        def _get_sign():
            message = str(timestamp) + "GET" + '/users/self/verify'
            mac = hmac.new(
                bytes(self.user_info['SecretKey'].encode('utf-8')),
                bytes(message.encode('utf-8')),
                digestmod="sha256",
            )
            d = mac.digest()
            sign = base64.b64encode(d)
            return str(sign, 'utf-8')

        args = {'apiKey': '', 'passphrase': '', 'timestamp': '', 'sign': ''}

        args['apiKey'] = self.user_info['apiKey']
        args['passphrase'] = self.user_info['passphrase']
        args['timestamp'] = timestamp
        args['sign'] = _get_sign()

        return args

    def on_login(self):
        # 订阅用户持仓
        self.public.add_channel(args={
            "channel": "positions",
            "instType": "ANY"
        })
        # 订阅用户账户数据
        self.public.add_channel(args={
            "channel": "account",
        })

    def on_event(self, info) -> None:
        """
        Event event push.
        """
        self._put(EVENT_INFO, info)

    def on_tick(self, tick) -> None:
        """
        Tick event push.
        """
        self._put(EVENT_TICK, tick)

    def on_position(self, position) -> None:
        """
        Position event push.
        """
        self._put(EVENT_POSITION, position)

    def on_account(self, account) -> None:
        """
        Account event push.
        """
        self._put(EVENT_ACCOUNT, account)

    # 在和服务器接口交互时出现错误信息，调用该回调函数
    def on_error(self, error) -> None:
        """
        Account event push.
        """
        self._put(EVENT_ERROR, error)

    def _put(self, event):
        self.event_engine.put(event)

    def ON_MESSAGE(self, *args):
        # 判断数据内容逻辑
        print('on_message', args)

    def ON_LOGIN(self, ws):
        pass
