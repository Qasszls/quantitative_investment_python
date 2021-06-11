# -*- coding:UTF-8 -*-
import pymysql
from dbutils.pooled_db import PooledDB


class MySqlHandler:
    def __init__(self, ip, userName, userPass, DBName, charset='utf8'):
        self.ip = ip
        self.userName = userName
        self.userPass = userPass
        self.DBName = DBName
        self.charset = charset

    def _conn(self):
        try:
            self.POOL = PooledDB(
                pymysql,  # 使用链接数据库的模块
                maxconnections=0,  # 连接池允许的最大连接数，0和None表示不限制连接数
                # mincached=2,  # 初始化时，链接池中至少创建的空闲的链接，0表示不创建
                # maxcached=5,  # 链接池中最多闲置的链接，0和None不限制
                # # blocking=True,  # 连接池中如果没有可用连接后，是否阻塞等待。True，等待；False，不等待然后报错
                maxusage=None,  # 一个链接最多被重复使用的次数，None表示无限制
                # setsession=[],  # 开始会话前执行的命令列表。如：["set datestyle to ...", "set time zone ..."]
                # ping=0,
                # ping MySQL服务端，检查是否服务可用。# 如：0 = None = never, 1 = default = whenever it is requested, 2 = when a cursor is created, 4 = when a query is executed, 7 = always
                port=3306,
                host=self.ip,
                user=self.userName,
                passwd=self.userPass,
                db=self.DBName,
                charset=self.charset,
                use_unicode=True)
            conn = self.POOL.connection()
            cursor = conn.cursor()
            return cursor, conn
        except:
            return False

    def _close(self, cursor, conn):
        cursor.close()
        conn.close()

    def clear_table_record(self, database):
        cursor, conn = self._conn()
        sql = "TRUNCATE TABLE " + database
        try:
            # 执行sql语句
            influence = cursor.execute(sql)
            # 提交到数据库执行
            conn.commit()
            text = True, '删除影响:' + str(influence) + '条。 sql==>' + sql
        except Exception as e:
            # 如果发生错误则回滚
            conn.rollback()
            text = False, str(e) + str(influence) + sql
        self._close(cursor, conn)
        return text

    def insert_trade_marks_data(self, data, database):
        influence = 0
        text = ''
        cursor, conn = self._conn()
        for item in data:
            sql = "INSERT INTO "+database+"(id_tamp, open_price, high_price, lowest_price, close_price, vol, volCcy,checkSurplus,stopLoss,principal,property,tradingPrice,buyTraces,date) VALUES ('%s', '%s', '%s', '%s', '%s', '%s','%s', '%s', '%s','%s', '%s', '%s','%s','%s')"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      % \
                    (item[0], item[1],item[2],item[3],item[4],item[5],item[6])

            try:
                # 执行sql语句
                influence = cursor.execute(sql)
                # 提交到数据库执行
                conn.commit()
                text = True, '数据写入:' + str(influence) + '条。'
            except Exception as e:
                # 如果发生错误则回滚
                conn.rollback()
                text = False, str(e) + str(influence)

        self._close(cursor, conn)
        return text

    def insert_kline_data(self, data, database):
        influence = 0
        text = ''
        cursor, conn = self._conn()
        for item in data:
            sql = "INSERT INTO "+database+"(id_tamp, open_price, high_price, lowest_price, close_price, vol, volCcy) VALUES ('%s', '%s', '%s', '%s', '%s', '%s','%s')"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      % \
                    (item[0], item[1],item[2],item[3],item[4],item[5],item[6])

            try:
                # 执行sql语句
                influence = cursor.execute(sql)
                # 提交到数据库执行
                conn.commit()
                text = True, '数据写入:' + str(influence) + '条。'
            except Exception as e:
                # 如果发生错误则回滚
                conn.rollback()
                text = False, str(e) + str(influence)

        self._close(cursor, conn)
        return text
