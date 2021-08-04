# -*- coding:UTF-8 -*-
from re import T
from numpy import result_type
import pymysql
from dbutils.pooled_db import PooledDB


class SqlHandler:
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

    # 删除表
    def delete_table(self, table_name):
        sql = "DROP TABLE " + table_name
        return self.sql_commit(sql)

    # 删除记录
    def delete_table_record(self, table_name, id):
        sql = "DELETE FROM " + table_name + " WHERE id='" + id + "'"
        return self.sql_commit(sql, sql)

    # 删除方法执行函数
    def sql_commit(self, sql, name=''):
        influence = 0
        text = ''
        status = ''
        result = ''
        cursor, conn = self._conn()
        try:
            # 执行sql语句
            influence = cursor.execute(sql)
            # 提交到数据库执行
            conn.commit()
            text = '删除表/内容: ' + str(influence) + ' 条。' + name
            status = True
        except Exception as e:
            # 如果发生错误则回滚
            conn.rollback()
            text = str(e) + str(influence) + name
            status = False
            print(text)
        self._close(cursor, conn)
        return {'status': status, "text": text, "result": result}

    # 查询表字段名
    def select_table_colimn_name(self, table_name):
        sql = "SELECT COLUMN_NAME from information_schema.COLUMNS where TABLE_NAME='" + table_name + "' ORDER BY ordinal_position"

        return self._run_select(sql)

    # 查询历史回测列表
    def select_test_record_list(self, table_name):
        sql = "SELECT * from " + table_name

        return self._run_select(sql)

    # 查询回测表数据
    def select_trade_marks_data(self, table, tamp=None):
        if tamp:
            if len(tamp) != 2:
                sql = "SELECT * FROM " + table + " WHERE id_tamp < " + tamp
            else:
                sql = "SELECT * FROM " + table + " WHERE id_tamp BETWEEN '" + tamp[
                    0] + "' AND '" + tamp[1] + "'"
        else:
            sql = "SELECT * FROM " + table
        return self._run_select(sql)

    # 根据id查询表名
    def select_table_id(self, id):
        sql = "SELECT * FROM table_record WHERE id=" + "'" + id + "'"
        return self._run_select(sql)

    # 查询语句的执行
    # @return tuple
    def _run_select(self, sql):
        influence = 0
        text = ''
        status = ''
        result = ''
        cursor, conn = self._conn()
        try:
            # 执行sql语句
            influence = cursor.execute(sql)
            # 获得查询内容
            result = cursor.fetchall()
            text = '数据查询: ' + str(influence) + ' 条。'
            status = True
        except Exception as e:
            # 如果发生错误则回滚
            conn.rollback()
            text = str(e) + str(influence) + ':' + sql
            status = False
            # print(text)

        self._close(cursor, conn)
        return {'status': status, "text": text, "result": list(result)}

    # 插入 行情数据 数据
    def insert_trade_marks_data(self, data, table_name):
        """
        入参 data dict 数据字典
        入参 table_name str 表名
        """
        sql = "INSERT INTO " + table_name
        _key = []
        _value = []
        for key in data:
            _key.append(key)
            _value.append("\'" + str(data[key]) + "\'")
        sql = sql + " (" + ','.join(_key) + ") VALUES (" + ','.join(
            _value) + ")"
        return self._insert_run(sql, table_name)

    def _insert_run(self, sql, name):
        influence = 0
        text = ''
        status = ''
        result = ''
        cursor, conn = self._conn()
        try:
            # 执行sql语句
            influence = cursor.execute(sql)
            # 提交到数据库执行
            conn.commit()
            text = '数据写入: ' + str(influence) + ' 条。' + name
            status = True
        except Exception as e:
            # 如果发生错误则回滚
            conn.rollback()
            text = str(e) + str(influence) + 'insert' + name
            status = False
            print(sql, '\n', text)
        self._close(cursor, conn)
        return {'status': status, "text": text, "result": result}

    #更新数据
    def update_buy_set(self, table_name, data):
        sql = "UPDATE {0} SET is_buy_set = '{1}' where id_tamp = {2}".format(
            table_name, data['is_buy_set'], data['date_key'])
        return self._update_run(sql, 'update')

    #更新数据操作 执行事务
    def _update_run(self, sql, name):
        influence = 0
        text = ''
        status = ''
        result = ''
        cursor, conn = self._conn()
        try:
            # 执行sql语句
            influence = cursor.execute(sql)
            # 提交到数据库执行
            conn.commit()
            text = '数据更新: ' + str(influence) + ' 条。' + name
            status = True
        except Exception as e:
            # 如果发生错误则回滚
            conn.rollback()
            text = str(e) + str(influence) + 'update' + name
            status = False
            print(sql, '\n', text)
        self._close(cursor, conn)
        return {'status': status, "text": text, "result": result}