# -*- coding:UTF-8 -*-
import time
import pymysql
from pymysql.cursors import SSCursor
from dbutils.pooled_db import PooledDB
import logging
from events.engine import Event
from logging import Logger, INFO, ERROR, DEBUG
from json import loads, dumps

# 业务和技术混杂在一起了，未来拆分开


class BaseSql:
    def __init__(self,  ip, user_name, user_pass, db_name, charset='utf8'):
        self.ip = ip
        self.user_name = user_name
        self.user_pass = user_pass
        self.db_name = db_name
        self.charset = charset
        self.logger: Logger = logging.getLogger()

        self.POOL = PooledDB(
            pymysql,  # 使用链接数据库的模块
            maxconnections=0,  # 连接池允许的最大连接数，0和None表示不限制连接数
            mincached=0,  # 初始化时，链接池中至少创建的空闲的链接，0表示不创建
            maxcached=1,  # 链接池中最多闲置的链接，0和None不限制
            blocking=True,  # 连接池中如果没有可用连接后，是否阻塞等待。True，等待；False，不等待然后报错
            maxusage=None,  # 一个链接最多被重复使用的次数，None表示无限制
            # setsession=[],  # 开始会话前执行的命令列表。如：["set datestyle to ...", "set time zone ..."]
            # ping=0,
            # ping MySQL服务端，检查是否服务可用。# 如：0 = None = never, 1 = default = whenever it is requested, 2 = when a cursor is created, 4 = when a query is executed, 7 = always
            port=3306,
            host=self.ip,
            user=self.user_name,
            passwd=self.user_pass,
            db=self.db_name,
            charset=self.charset,
            use_unicode=True)

    def connect(self, ss_cursor=False):
        cursor = ''
        conn = self.POOL.connection()
        if ss_cursor:
            cursor = conn.cursor(SSCursor)
        else:
            cursor = conn.cursor()
        return cursor, conn

    def _close(self, cursor, conn):
        cursor.close()
        conn.close()
    # 清空表内容

    def _commit(self, sql):
        cursor, conn = self.connect()
        text = ''
        try:
            # 执行sql语句
            cursor.execute(sql)
            # 提交到数据库执行
            conn.commit()
            text = cursor, 0
            self.logger.log(DEBUG, self.db_name+'sql操作成功')
        except Exception as e:
            # 如果发生错误则回滚
            conn.rollback()
            error = e.args
            code = error[0]
            text = False, code
            self.logger.log(ERROR, error)
        finally:
            self._close(cursor=cursor, conn=conn)
        return text

    # 批量插入
    def _batch_commit(self, sql, list):
        cursor, conn = self.connect()
        text = 0
        try:
            # 执行sql语句
            index = cursor.executemany(sql, list)
            # 提交到数据库执行
            conn.commit()
            text = index, 0
            self.logger.log(DEBUG, self.db_name+'sql操作成功')
        except Exception as e:
            # 如果发生错误则回滚
            conn.rollback()
            error = e.args
            code = error[0]
            text = False, code
            self.logger.log(DEBUG, error)

        return text


class Sql(BaseSql):
    def __init__(self, ip, user_name, user_pass, db_name, charset='utf8'):
        BaseSql.__init__(self, ip, user_name,
                         user_pass, db_name, charset)

    # 插入表内容
    def insert_kline_data(self, data, table):
        sql = "INSERT IGNORE INTO "+table + \
            "(id_tamp, open_price, high_price, lowest_price, close_price, vol, volCcy, volCcyQuote) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        params_list = []
        for item in data:
            params_list.append((item[0], item[1], item[2],
                                item[3], item[4], item[5], item[6], item[7]))
        return self._batch_commit(sql, params_list)

    # 创建表
    def create_table(self, table_name):
        sql = "CREATE TABLE "+table_name + \
            "(id_tamp BIGINT(50) PRIMARY KEY, open_price VARCHAR(100), high_price VARCHAR(100), lowest_price VARCHAR(100), close_price VARCHAR(100), vol VARCHAR(100), volCcy VARCHAR(100), volCcyQuote VARCHAR(100))"

        return self._commit(sql)

    # 查询表内容
    def search_table_content(self, table_name, start_timestamp, end_timestamp):
        sql = 'SELECT * FROM ' + table_name + \
            ' WHERE id_tamp BETWEEN {start_timestamp} AND {end_timestamp}'.format(
                start_timestamp=start_timestamp, end_timestamp=end_timestamp)

        ss_cursor, conn = self.connect(ss_cursor=True)
        # 执行sql语句
        ss_cursor.execute(sql)
        ss_cursor.fetchone()

    def is_table_exist(self, table_name):
        sql = "SELECT count(*) num FROM information_schema.TABLES WHERE table_schema = '{database_name}' AND table_name = '{table_name}' AND table_type = 'BASE TABLE'".format(
            database_name=self.db_name, table_name=table_name)

        cur, code = self._commit(sql)

        res = cur.fetchall()

        return res[0][0] == 1
