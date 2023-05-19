# coding:utf-8
"""
@date: 2023/2/23
@author: mawengang
"""
import traceback
from robot.api import logger
from DBUtils.PooledDB import PooledDB


class Config():
    # 数据库连接编码
    # DB_CHARSET = "utf-8"

    # mincached : 启动时开启的闲置连接数量(缺省值 0 开始时不创建连接)
    DB_MIN_CACHED = 10

    # maxcached : 连接池中允许的闲置的最多连接数量(缺省值 0 代表不闲置连接池大小)
    DB_MAX_CACHED = 10

    # maxshared : 共享连接数允许的最大数量(缺省值 0 代表所有连接都是专用的)如果达到了最大数量,被请求为共享的连接将会被共享使用
    DB_MAX_SHARED = 20

    # maxconnecyions : 创建连接池的最大数量(缺省值 0 代表不限制)
    DB_MAX_CONNECYIONS = 100

    # blocking : 设置在连接池达到最大数量时的行为(缺省值 0 或 False 代表返回一个错误<toMany......> 其他代表阻塞直到连接数减少,连接被分配)
    DB_BLOCKING = True

    # maxusage : 单个连接的最大允许复用次数(缺省值 0 或 False 代表不限制的复用).当达到最大数时,连接会自动重新连接(关闭和重新打开)
    DB_MAX_USAGE = 0

    # setsession : 一个可选的SQL命令列表用于准备每个会话，如["set datestyle to german", ...]
    DB_SET_SESSION = None


"""
@功能：创建数据库连接池
"""


class DbConnectionPool(object):
    __pool = None

    def __init__(self, creator, db_config):
        self.creator = creator
        self.db_config = db_config

    # 创建数据库连接conn和游标cursor
    def __enter__(self):
        self.conn = self.__get_conn()
        self.cursor = self.conn.cursor()

    # 创建数据库连接池
    def __get_conn(self):
        if self.__pool is None:
            self.__pool = PooledDB(
                creator=self.creator,
                mincached=Config.DB_MIN_CACHED,
                maxcached=Config.DB_MAX_CACHED,
                maxshared=Config.DB_MAX_SHARED,
                maxconnections=Config.DB_MAX_CONNECYIONS,
                blocking=Config.DB_BLOCKING,
                maxusage=Config.DB_MAX_USAGE,
                setsession=Config.DB_SET_SESSION,
                # use_unicode=False
                # charset=Config.DB_CHARSET
                **self.db_config
            )
        return self.__pool.connection()

    # 释放连接池资源
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        self.conn.close()

    # # 关闭连接归还给链接池
    # def close(self):
    #     self.cursor.close()
    #     self.conn.close()

    # 从连接池中取出一个连接
    def get_conn(self):
        conn = self.__get_conn()
        cursor = conn.cursor()
        return cursor, conn


"""执行语句查询有结果返回结果没有返回0；增/删/改返回变更数据条数，没有返回0"""


class SqLHelper(object):
    def __init__(self, creator, **db_config):
        """
        @param creator: 目标库Python库对象
        @param db_config: 数据库连接信息，根据Python库参数配置，示例如下：
        import psycopg2
        import psycopg2.extras
        creator = psycopg2
        db_conf = {
            "host": '10.66.241.19',
            "port": '5434',
            "user": 'postgres',
            "password": 'login@6123',
            "database": 'scanner',
            "cursor_factory": psycopg2.extras.RealDictCursor
        }
        """
        self.cursor_factory = db_config.get("cursor_factory", None)
        self.db = DbConnectionPool(creator, db_config)  # 从数据池中获取连接

    # def __new__(cls, *args, **kwargs):
    #     if not hasattr(cls, 'inst'):  # 单例
    #         cls.inst = super(SqLHelper, cls).__new__(cls, *args, **kwargs)
    #     return cls.inst

    # 封装执行命令
    def execute(self, sql, param=None, autoclose=False):
        """
        【主要判断是否有参数和是否执行完就释放连接】
        :param sql: 字符串类型，sql语句
        :param param: sql语句中要替换的参数"select %s from tab where id=%s" 其中的%s就是参数
        :param autoclose: 是否关闭连接
        :return: 返回连接conn和游标cursor
        """
        cursor, conn = self.db.get_conn()  # 从连接池获取连接
        count = 0
        logger.info(u"执行sql为： %s" % sql)
        logger.info(u"执行sql 参数为： %s" % param)
        try:
            # count : 为改变的数据条数
            if param:
                count = cursor.execute(sql, param)
            else:
                count = cursor.execute(sql)
            conn.commit()
            if autoclose:
                self.close(cursor, conn)
        except Exception as e:
            traceback.print_exc()
            # logger.warn(traceback.format_exc(e))
        return cursor, conn, count

    # 执行多条命令
    def executemany(self, lis):
        """
        :param lis: 是一个列表，里面放的是每个sql的字典'[{"sql":"xxx","param":"xx"}....]'
        :return:
        """
        cursor, conn = self.db.get_conn()

        try:
            for order in lis:
                sql = order['sql']
                param = order['param']
                logger.info(u"执行sql为： %s" % sql)
                logger.info(u"执行sql 参数为： %s" % param)
                if param:
                    cursor.execute(sql, param)
                else:
                    cursor.execute(sql)
            conn.commit()
            self.close(cursor, conn)
            return True
        except Exception as e:
            print(e)
            traceback.print_exc()
            conn.rollback()
            self.close(cursor, conn)
            return False

    # 释放连接
    def close(self, cursor, conn):
        """释放连接归还给连接池"""
        cursor.close()
        conn.close()

    # 查询所有， 应该是最常用的了
    def select_all(self, sql, param=None):
        cursor, conn, count = self.execute(sql, param)
        try:
            res = cursor.fetchall()
            print(res)
            if self.cursor_factory and res:
                res = [dict(i) for i in res]
            return [] if res == 0 else res
        except Exception as e:
            print(e)
            traceback.print_exc()
            self.close(cursor, conn)
            return [] if self.cursor_factory else count

    # 查询单条
    def select_one(self, sql, param=None):
        cursor, conn, count = self.execute(sql, param)
        try:
            res = cursor.fetchone()
            self.close(cursor, conn)
            if self.cursor_factory and res:
                return [dict(i) for i in res]
            return res
        except Exception as e:
            print("error_msg:", e.args)
            self.close(cursor, conn)
            return [] if self.cursor_factory else count

    # 增加
    def insert_one(self, sql, param):
        cursor, conn, count = self.execute(sql, param)
        try:
            # _id = cursor.lastrowid()  # 获取当前插入数据的主键id，该id应该为自动生成为好
            conn.commit()
            self.close(cursor, conn)
            return count
            # 防止表中没有id返回0
            # if _id == 0:
            #     return True
            # return _id
        except Exception as e:
            print(e)
            conn.rollback()
            self.close(cursor, conn)
            return count

    # 增加多行
    def insert_many(self, sql, param):
        """
        :param sql:
        :param param: 必须是元组或列表[(),()]或（（），（））
        :return:
        """
        cursor, conn, count = self.db.get_conn()
        try:
            cursor.executemany(sql, param)
            conn.commit()
            return count
        except Exception as e:
            print(e)
            conn.rollback()
            self.close(cursor, conn)
            return count

    # 删除
    def delete(self, sql, param=None):
        cursor, conn, count = self.execute(sql, param)
        try:
            self.close(cursor, conn)
            return count
        except Exception as e:
            print(e)
            conn.rollback()
            self.close(cursor, conn)
            return count

    # 更新
    def update(self, sql, param=None):
        cursor, conn, count = self.execute(sql, param)
        try:
            conn.commit()
            self.close(cursor, conn)
            return count
        except Exception as e:
            print(e)
            conn.rollback()
            self.close(cursor, conn)
            return count


if __name__ == '__main__':
    # pass
    import psycopg2
    import psycopg2.extras
    db_conf = {
        "host": '10.xx.xx.xx',
        "port": '',
        "user": '',
        "password": '',
        "database": '',
        "cursor_factory": psycopg2.extras.RealDictCursor
    }
    db = SqLHelper(creator=psycopg2, **db_conf)
    # 查询单条
    sql1 = 'SELECT x.* FROM public.rule_item x WHERE x.rule_type IN (5) AND x.match_type IN (0)'
    ret = db.select_all(sql=sql1)
    print(ret)
    # 增加单条
    # sql2 = 'insert into userinfo (name,password) VALUES (%s,%s)'
    # ret = db.insertone(sql2, ('old2','22222'))
    # print(ret)
    # 增加多条
    # sql3 = 'insert into userinfo (name,password) VALUES (%s,%s)'
    # li = li = [
    #     ('分省', '123'),
    #     ('到达','456')
    # ]
    # ret = db.insertmany(sql3,li)
    # print(ret)
    # 删除
    # sql4 = 'delete from  userinfo WHERE name=%s'
    # args = 'xxxx'
    # ret = db.delete(sql4, args)
    # print(ret)
    # 更新
    # sql5 = r'update userinfo set password=%s WHERE name LIKE %s'
    # args = ('993333993', '%old%')
    # ret = db.update(sql5, args)
    # print(ret)
