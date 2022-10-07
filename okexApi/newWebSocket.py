import requests.packages.urllib3.util.ssl_
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL'
import websocket
import json
try:
    import thread
except ImportError:
    import _thread as thread

import time

reconnect_count = 0


class Test(object):

    def __init__(self):
        super(Test, self).__init__()
        self.url = "wss://ws.okx.com:8443/ws/v5/public"
        self.ws = None

    def on_message(self, ws, data):
        print("####### on_message #######")
        print("message：", data)

    def on_error(self, ws, error):
        print('error', error)

        # global reconnect_count
        # if type(error) == ConnectionRefusedError or type(
        #         error
        # ) == websocket._exceptions.WebSocketConnectionClosedException:
        #     print("正在尝试第%d次重连" % reconnect_count)
        #     reconnect_count += 1
        #     if reconnect_count < 100:
        #         self.start()
        #         time.sleep(2)
        # else:
        #     print("其他error!")
        #     print(error)

    def on_close(self, ws, *args):
        print("####### on_close #######", args)
        global reconnect_count

        reconnect_count += 1
        time.sleep(2)
        print("正在尝试第%d次重连" % reconnect_count)
        self.start()

    def on_ping(self, message):
        print("####### on_ping #######")
        print("ping message：%s" % message)

    def on_pong(self, message):
        print("####### on_pong #######")
        print("pong message：%s" % message)

    def on_open(self, ws):
        print("####### on_open #######")
        thread.start_new_thread(self.run, (ws, ))

    def run(self, ws):
        ws.send(
            json.dumps({
                "op": "subscribe",
                "args": [{
                    "channel": "candle1D",
                    "instId": "BTC-USDT"
                }]
            }))

    def start(self):
        # websocket.enableTrace(True)  # 开启运行状态追踪。debug 的时候最好打开他，便于追踪定位问题。

        self.ws = websocket.WebSocketApp(self.url,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        # self.ws.on_open = self.on_open  # 也可以先创建对象再这样指定回调函数。run_forever 之前指定回调函数即可。

        self.ws.run_forever(ping_interval=20, ping_timeout=10)


if __name__ == '__main__':
    Test().start()
