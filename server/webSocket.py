# -*- coding -*-

import websockets
import socket
import asyncio
import os
import time


class WSserver:
    def __init__(self, ip='127.0.0.1', port="1874"):
        self.ip = ip
        self.port = port

    async def handler(self, websocket, path):
        recv_msg = await websocket.recv()
        print("i received %s" % recv_msg)
        while True:
            time.sleep(0.5)
            if recv_msg == 'need market':
                # 走发送心跳或发送行情的方法
                await websocket.send('server send ok')
            else:
                await websocket.send('no no no')

    def run(self):
        serve = websockets.serve(self.handle, self.ip, self.port)
        print('please request ws://' + self.ip + ':' + self.port)
        asyncio.get_event_loop().run_until_complete(serve)


if __name__ == "__main__":
    ws = WSserver()
    ws.run()
