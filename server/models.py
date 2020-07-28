# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from functools import partial
from backtrader.feed import DataBase, CSVDataBase
from backtrader.feeds.pandafeed import PandasData as PD
from backtrader import date2num

from sqlalchemy import create_engine
import psycopg2

import pandas as pd
import utils
from datetime import datetime, timedelta
import time

# %%
# upsert: https://github.com/pandas-dev/pandas/pull/29636/files/c230d16619d507f7ba80063b5d25217dc65e2bd3#diff-b41f9fd042c423682f8e4c4d808dbe64
# TODO:添加索引


class DB(object):
    def __init__(self):
        self.max_overflow = 100
        self.engine = create_engine(
            'postgresql+psycopg2://postgres:123456@localhost:5432/postgres',
            # 'postgresql+psycopg2://postgres:123456@192.168.1.9:5432/postgres',
            pool_reset_on_return='commit',
            max_overflow=self.max_overflow,  # 不限制连接数
            pool_size=16,
            # echo=True,
            # echo_pool=True,
        )

    def execute(self, sql):
        cur = self.engine.execute(sql)
        if cur.returns_rows:
            ret = cur.fetchall()
            return ret
        return False

    def upsert(self, data, dbname, sets=None, wheres=None):
        if sets and wheres:
            df = self.select(dbname, wheres=wheres)
            if df.empty and data:
                self.insert(data, dbname)
            else:
                _set = self.get_where_or_set(sets)
                where = self.get_where_or_set(wheres)
                sql = 'UPDATE {0} set {1} where {2}'.format(
                    dbname, _set, where)
                ret = self.execute(sql)
                # print(ret)
        else:
            self.insert(data, dbname)

    def insert(self, data, dbname, pks=None):
        if pks:
            isempty = self.check_is_empty(data, dbname, pks)
            if isempty:
                return isempty
        if_exists = 'append'
        try:
            ret = data.to_sql(
                dbname,
                self.engine,
                index=False,
                # index_label=index_label,
                if_exists=if_exists
            )
            print(ret)
            return isempty
        except Exception as ex:
            print(ex)

    def check_is_empty(self, data, dbname, pks):
        labels = []
        for index, row in data.iterrows():
            wheres = []
            for pk in pks:
                where = {'k': pk, 'v': row[pk]}
                wheres.append(where)
            da = self.select(dbname, wheres=wheres)
            if not da.empty:
                labels.append(index)
        if labels:
            data.drop(labels=labels, axis=0, inplace=True)
        if data.empty:
            print('空数据')
            return True
        return False

    def select_count(self, dbname, wheres=None):
        sql = "SELECT count(1) FROM {}".format(dbname)
        if wheres:
            where = self.get_where_or_set(wheres)
            sql += ' WHERE {}'.format(where)
        ret = self.execute(sql)
        if ret:
            ret = [j[0] for j in ret]
            return ret[0]
        return 0

    def select_distinct(self, dbname, pk, wheres=None):
        sql = "SELECT distinct({}) FROM {}".format(pk, dbname)
        if wheres:
            where = self.get_where_or_set(wheres)
            sql += ' WHERE {}'.format(where)
        ret = self.execute(sql)
        if ret:
            ret = [j[0] for j in ret]
        return ret

    def select(self, dbname, fields=[], wheres=None, orderby=None):
        sql = 'SELECT * FROM {}'.format(dbname)
        if fields:
            sql = 'SELECT {} FROM {}'.format(','.join(fields), dbname)
        if wheres:
            where = self.get_where_or_set(wheres)
            sql += ' WHERE {}'.format(where)
        if orderby:
            sql += ' ORDER BY {}'.format(orderby)
        try:
            df = pd.read_sql(
                sql,
                self.engine,
            )
        except:
            df = pd.DataFrame()
        return df

    def delete(self, dbname, wheres=None):
        # 数据键变化需要drop方法
        sql = 'DELETE FROM {0} '.format(dbname)
        if wheres:
            where = self.get_where_or_set(wheres)
            sql += 'WHERE {0}'.format(where)
        ret = self.execute(sql)
        print(ret)

    def drop(self, dbname):
        sql = 'DROP TABLE {0} '.format(dbname)
        ret = self.execute(sql)
        print(ret)

    def has_table(self, dbname):
        sql = "SELECT table_name FROM information_schema.tables where table_name='{}';".format(
            dbname)
        ret = self.execute(sql)
        hastable = False
        if ret:
            hastable = True,
        return hastable

    def has_columns(self, dbname, columns):
        sql = "SELECT column_name FROM information_schema.columns WHERE table_name='{}' and column_name='{}';"
        hascolum = True
        for column in columns:
            ret = self.execute(sql.format(dbname, column))
            if not ret:
                hascolum = False
        return hascolum

    def stop(self, dbname):
        self.db_debug()
        self.engine.dispose()

    def set_index(self, dbname, indexes):
        for index in indexes:
            indexname = '{0}_{1}_idx'.format(dbname, index)
            sql = "SELECT * FROM pg_indexes WHERE tablename='{0}' and indexname='{1}';".format(
                dbname, indexname)
            ret = self.execute(sql)
            if ret:
                print('{0},索引已建立'.format(indexname))
                continue
            sql = 'CREATE INDEX {2} ON {0}({1});'.format(
                dbname, index, indexname)
            ret = self.execute(sql)
            print(ret)

    def get_where_or_set(self, wheres):
        where = ''
        for j in wheres:
            op = j.get('op', '')
            k = j.get('k', '')
            v = j.get('v', None)
            if v == None:
                print('未发现colums值')
                break
            flag = j.get('flag', 'and')
            if not op:
                op = '='
            if where:
                if type(v) == str:
                    where += " {3} {0}{1}'{2}'".format(k, op, v, flag)
                else:
                    where += " {3} {0}{1}{2}".format(k, op, v, flag)
            else:
                if type(v) == str:
                    where += " {0}{1}'{2}'".format(k, op, v)
                else:
                    where += " {0}{1}{2}".format(k, op, v)
        return where

    def db_debug(self):
        checkedout = self.engine.pool.checkedout()
        while checkedout <= self.max_overflow:
            logmsg = '闲置连接数:{0},占用连接数:{1}'.format(
                self.engine.pool.checkedin(), self.engine.pool.checkedout())
            print(logmsg)
            time.sleep(0.75)
            checkedout = self.engine.pool.checkedout()


class KDATA(DB):
    def select_data(self, dbname, fields=[], wheres=None, orderby=None, slg='', live=False):
        if live:
            code = wheres[0]['v']
            file = utils.get_csv_file(code, dbname)
            print('文件加载...', file)
            da = pd.read_csv(file)
            querystr = utils.get_query_str(wheres)
            df = da.query(querystr)
            if orderby:
                orderby = orderby.split()[0]
                df.sort_values(by=orderby, ascending=utils.true,
                               inplace=utils.true)

            df.datetime = df.datetime.astype('datetime64')
            date = utils.get_datetime_date(flag='-')
            # if dbname == 'k_5min_data':
            #     fund_today = utils.g_share['fund_today']
            #     t = fund_today.loc[fund_today.code == code]
            #     close = t.trade.astype(float).values[0]
            #     _time = t.ticktime.values[0]
            #     _dt = '{} {}'.format(date, _time)
            #     dt = datetime.strptime(_dt, '%Y-%m-%d %H:%M:%S')
            #     row = dict(
            #         code=code,
            #         datetime=dt,
            #         close=close,
            #     )
            #     row_series = pd.Series(row)
            #     df = df.append(row_series, ignore_index=True)
            #     df.fillna(0, inplace=True)

            # if dbname == 'k_data' and slg == 'sched':
            #     file = utils.get_csv_file(code, 'k_5min_data')
            #     print('文件加载...2', file)
            #     da5min = pd.read_csv(file)
            #     wheres[1]['v'] = date
            #     querystr = utils.get_query_str(wheres)
            #     import ipdb; ipdb.set_trace()
            #     df5min = da5min.query(querystr)
            #     todaydata = dict(
            #         code=df5min.code.values[0],
            #         open=df5min.open.values[0],
            #         close=df5min.close.values[-1],
            #         high=df5min.high.max(),
            #         low=df5min.low.min(),
            #         volume=df5min.volume.sum(),
            #         amount=df5min.amount.sum(),
            #         p_change=df.close.values[-1] - df5min.close.values[-1],
            #         datetime=pd.Timestamp(date),
            #         type='fund',
            #         createdtime=0,
            #         timestamp=0,
            #     )
            #     row = pd.Series(todaydata)
            #     df = df.append(row, ignore_index=True)

            return df
        else:
            print('数据库加载...', dbname)
            df = self.select(dbname, wheres=wheres, orderby=orderby)
        return df


class Order:
    def __init__(self):
        self.db = DB()
        self.dbname = 'live_order'

    def upsert_order(self, data, _set={}):
        pks = ['code', 'createdtime']
        self.db.insert(data, self.dbname, pks)

    def get_live_order(self):
        date = utils.get_datetime_date(flag='-')
        wheres = [
            {'k': 'status', 'v': 0},
            {'k': 'date', 'v': date, 'op': '<='},
        ]
        orderby = 'createdtime desc'
        orders = self.db.select(self.dbname, wheres=wheres, orderby=orderby)
        return orders


class PGData(DataBase):
    # 字段拓展
    # linesoverride = True
    lines = ('code', 'rt')
    params = (
        ('code', -1),
        ('rt', -1),
    )

    def __init__(self, dbname):
        self.dbname = dbname
        self.max_overflow = 100
        self.engine = create_engine(
            'postgresql+psycopg2://postgres:123456@localhost:5432/postgres',
            pool_reset_on_return='commit',
            max_overflow=self.max_overflow,  # 不限制连接数
            pool_size=16,
            echo=True,
            echo_pool=True,
        )

    def start(self):
        self.conn = self.engine.connect()
        now = int(time.time()) - 60
        print(now)
        sql = 'SELECT datetime,open,high,low,price,volume,code,name,rt FROM {0} WHERE timestamp >= {1}'.format(
            self.dbname, now
        )
        self.result = self.conn.execute(sql)

    def stop(self):
        self.engine.dispose()

    def _load(self):
        one_row = self.result.fetchone()
        if one_row is None:
            return False
        self.lines.datetime[0] = date2num(one_row[0])
        self.lines.open[0] = float(one_row[1])
        self.lines.high[0] = float(one_row[2])
        self.lines.low[0] = float(one_row[3])
        self.lines.close[0] = float(one_row[4])
        self.lines.volume[0] = int(one_row[5])
        self.lines.openinterest[0] = -1
        self.lines.code[0] = int(one_row[6])
        # self.lines.name[0] = one_row[7]
        return True


class PandasData(PD):
    # 字段拓展
    lines = ('code', 'rt')
    params = (
        ('code', -1),
        ('rt', -1),
    )


# %%
if __name__ == "__main__":
    db = DB()
    # code = '159928'
    dbname = 'ggt'
    indexes = ['code', 'name']
    db.set_index(dbname, indexes)

    # print(index, row)

# %%
