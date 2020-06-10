# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%

# https://zhuanlan.zhihu.com/p/64019862

from sqlalchemy import create_engine
import psycopg2
import pandas as pd
import utils
from datetime import datetime, timedelta

# %%


class DB(object):
    def __init__(self):
        self.engine = create_engine(
            'postgresql+psycopg2://postgres:123456@localhost:5432/postgres',
            pool_reset_on_return='commit',
            max_overflow=-1,  # 不限制连接数
            echo=True,
            echo_pool=True,
        )

    def exec(self, sql):
        df = self.engine.execute(sql)
        res = df.fetchall()
        print(df)
        return res

    def update(self, data, db_name):
        if_exists = 'append'
        try:
            ret = data.to_sql(
                db_name,
                self.engine,
                index=True,
                # index_label=index_label,
                if_exists=if_exists
            )
            print(ret)
        except Exception as ex:
            print(ex)

    def select(self, db_name, wheres={}):
        sql = 'SELECT * FROM {0} '.format(db_name)
        if wheres:
            where = self.get_where(wheres)
            sql += 'WHERE {0}'.format(where)
        df = pd.read_sql(
            sql,
            self.engine,
        )
        return df

    def delete(self, db_name, wheres={}):
        # 数据键变化需要drop方法
        sql = 'DELETE FROM {0} '.format(db_name)
        if wheres:
            where = self.get_where(wheres)
            sql += 'WHERE {0}'.format(where)
        df = pd.io.sql.execute(
            sql,
            self.engine,
        )
        print(df)

    def drop(self, db_name):
        sql = 'DROP TABLE {0} '.format(db_name)
        df = pd.io.sql.execute(
            sql,
            self.engine,
        )
        print(df)

    def get_where(self, wheres):
        where = ''
        for k, v in wheres.items():
            if type(v) in [str]:
                if where:
                    where += " and {0}='{1}'".format(k, v)
                else:
                    where += " {0}='{1}'".format(k, v)
            else:
                if where:
                    where += " and {0}={1}".format(k, v)
                else:
                    where += " {0}={1}".format(k, v)
        return where


# %%
if __name__ == "__main__":
    con = DB()
    code = '159928'
    db_name = 'opt_strategy'
    # data = utils.get_data_ts(code)
    # con.update(data, db_name)
    wheres = {'code': '163407', 'minrise': -1.5}
    # con.delete(db_name, wheres)
    # con.drop(db_name)
    df = con.select(db_name, wheres)
    if df.empty:
        print(df)


# %%
