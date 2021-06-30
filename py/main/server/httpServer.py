from http.server import HTTPServer, BaseHTTPRequestHandler
import re
import os
import sys
import json
import time

sys.path.append('..')
from strategySet.main import DataBackTesting
from MySqlHandler import MySqlHandler

result_search = {'result': '查询成功，正在处理，请稍后', 'status': '200', 'msg': '成功'}
result_list = {'data': '', 'status': '200', 'msg': '成功'}

#host = ('localhost', 7777)
host = ('127.0.0.1', 2874)


class Resquest(BaseHTTPRequestHandler):
    def log_message(self, a, b, c, d):
        None

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        dataBackTesting = DataBackTesting()
        req_data = self.get_url_params(self.path)
        # 根据接口地址调用对应处理方法
        if (re.search('/strategySet/search', self.path) != None):
            checkSurplus = req_data['stop_profit']
            stopLoss = req_data['stop_loss']
            principal = req_data['cash']
            req_date = []
            if req_data['start_time'] != '' and req_data['end_time'] != '':
                req_date = [req_data['start_time'], req_data['end_time']]

            self.wfile.write(json.dumps(result_search).encode())
            dataBackTesting.run_test(checkSurplus, stopLoss, principal,
                                     req_date)
        if (re.search('/strategySet/list', self.path) != None):
            res_list = dataBackTesting.get_record_list('table_record')
            result_list['data'] = res_list
            self.wfile.write(json.dumps(result_list).encode())

        if (re.search('/strategySet/detail_delete', self.path) != None):
            id = req_data['id']
            dataBackTesting.delete_market_data(id)
            self.wfile.write(json.dumps(result_list).encode())

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        dataBackTesting = DataBackTesting()
        length = int(self.headers['Content-Length'])
        post_data = json.loads(self.rfile.read(length))['data']
        if (re.search('/strategySet/detail', self.path) != None):
            id = post_data['id']
            res_dict = dataBackTesting.search_market_data(id)
            result_list['data'] = res_dict[0:1000]
            self.wfile.write(json.dumps(result_list).encode())

    def connetSql(self):
        return MySqlHandler(
            ip='127.0.0.1',
            userName='root',
            userPass='qass-utf-8',
            DBName='BTC-USDT_kline',
            charset='utf8',
        )

    def get_url_params(self, url):
        if len(url.split('?')) > 1:
            _params_line = url.split('?')[1]
            _params_arr = _params_line.split('&')
            _params_dist = {}
            for item in _params_arr:
                key = item.split('=')[0]
                value = item.split('=')[1]
                _params_dist[key] = value
            return _params_dist
        else:
            return {}

    def strategySet_search(self, params):
        return 'trade_marks_macd_15m_60m_' + params[
            'stop_profit'] + '_' + params['checkSurplus']


if __name__ == '__main__':
    server = HTTPServer(host, Resquest)
    server.serve_forever()
