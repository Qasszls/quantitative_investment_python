# -*- coding -*-
from http.server import HTTPServer, BaseHTTPRequestHandler
from webSocket import WSserver
from httpServer import Resquest
import socket


def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip


host = (get_host_ip(), 2874)

if __name__ == "__main__":
    # ws = WSserver('127.0.0.1','1874')
    # ws.run()

    hs = HTTPServer(host, Resquest)
    print("Starting Server.... ",
          'Network===> http://' + host[0] + ":" + str(host[1]))
    hs.serve_forever()
