# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import backtrader as bt

import strategys
import models
from datetime import datetime, timedelta
import asyncio
from tornado import ioloop, gen

import utils
import constant

# %%


# TODO: 检查数据正确性

def start_strategy(strategy, code, code_cn, live=utils.false):
    # 开启5分钟周期下单
    multiperiod = 'k_5min_data'

    cerebro = bt.Cerebro()

    cerebro.addstrategy(
        strategy,
        multiperiod=multiperiod,
        _live=live,
        twapperiod=3,
        orderlog=utils.false,
        tradelog=utils.true,
        doprint=utils.true,
    )
    # 获取3个月前数据,保证指标正常
    startdt = datetime.now() + timedelta(days=-30*3)
    start = utils.get_datetime_date(startdt, flag='-')

    dbnames = ['k_data']
    dbnames.append(multiperiod)
    for dbname in dbnames:
        df = utils.get_database_data(
            code, dbname=dbname, start=start, live=live)
        # 验证数据
        # print(df)
        if df.empty:
            print(code, '未获取到数据')
            continue
        name = '{}:{}:{}'.format(code, code_cn, dbname)
        data = models.PandasData(dataname=df, name=name)
        cerebro.adddata(data)

    utils.addanalyzer(cerebro)

    startcash = 20000
    cerebro.broker.setcash(startcash)
    cerebro.broker.setcommission(commission=0.0001)
    print('Starting Portfolio Value: %.3f' % cerebro.broker.getvalue())

    strats = cerebro.run(maxcpus=1)
    strat = strats[0]
    # 用于检查是否有误下单状况
    utils.print_transaction(strat)
    print('Final Portfolio Value: %.3f' % cerebro.broker.getvalue())


def run_strategy(fund, live):
    # 消费特殊处理,cmi值一直偏高
    if isinstance(fund, str):
        return
    code = fund['code']
    code_cn = fund['code_cn']
    strategy = strategys.CMIStrategy
    if '消费' in code_cn:
        strategy = strategys.TWAPMultiStrategy
    else:
        strategy = strategys.CMIStrategy
    start_strategy(strategy, code, code_cn, live)


def one_run_strategy(fund, db=None, dbname='', live=utils.true):
    if isinstance(fund, dict):
        code = fund['code']
    elif isinstance(fund, str):
        code = fund
    else:
        raise Exception('获取code失败')
    isempty = utils.true
    isempty = utils.update_k_5min_data(
        code, db=db, dbname=dbname, live=live, init=utils.false)
    _dbname = 'k_data'
    if live:
        # 检查k_data是否已更新
        file = utils.get_csv_file(code, _dbname)
        isupdate = utils.false
        if utils.os.path.exists(file):
            stat = utils.get_stat(file)
            if int(utils.time.time()) - stat.st_mtime > 60*60*12:
                isupdate = utils.true
        else:
            isupdate = utils.true
        if isupdate:
            utils.update_k_data(
                code, db=db, dbname=_dbname, live=live, init=utils.false
            )
    else:
        wheres = [
            {'k': 'code', 'v': code}
        ]
        count = db.select_count(_dbname, wheres)
        if count == 0:
            utils.update_k_data(
                code, db=db, dbname=_dbname, live=live, init=utils.true
            )

    if not isempty:
        run_strategy(fund, live)


@gen.coroutine
def tornado_run_strategy(fund, db=None, dbname='', live=utils.true):
    code = fund['code']
    isempty = utils.update_k_5min_data(
        code, db=db, dbname=dbname, live=live, init=utils.false)
    if live:
        # 检查k_data是否已更新
        _dbname = 'k_data'
        file = utils.get_csv_file(code, _dbname)
        isupdate = utils.false
        if utils.os.path.exists(file):
            stat = utils.get_stat(file)
            if int(utils.time.time()) - stat.st_mtime > 60*60*12:
                isupdate = utils.true
        else:
            isupdate = utils.true
        if isupdate:
            utils.update_k_data(
                code, db=db, dbname=_dbname, live=live, init=utils.false
            )
    if not isempty:
        run_strategy(fund, live)


@gen.coroutine
def tornado_update_k_data(fund, db=None, dbname='', live=utils.true):
    code = fund['code']
    utils.update_k_data(
        code, db=db, dbname=dbname, live=live, init=utils.false
    )


async def asyncio_run_strategy(fund, db=None, dbname='', live=utils.true, init=False):
    if isinstance(fund, dict):
        code = fund['code']
    elif isinstance(fund, str):
        code = fund
    else:
        raise Exception('获取code失败')
    isempty = utils.update_k_5min_data(
        code, db=db, dbname=dbname, live=live, init=init)
    _dbname = 'k_data'
    if live:
        # 检查k_data是否已更新
        file = utils.get_csv_file(code, _dbname)
        isupdate = utils.false
        if utils.os.path.exists(file):
            stat = utils.get_stat(file)
            if int(utils.time.time()) - stat.st_mtime > 60*60*12:
                isupdate = utils.true
        else:
            isupdate = utils.true
        if isupdate:
            utils.update_k_data(
                code, db=db, dbname=_dbname, live=live, init=utils.false
            )
    else:
        wheres = [
            {'k': 'code', 'v': code}
        ]
        count = db.select_count(_dbname, wheres)
        if count == 0 or init:
            utils.update_k_data(
                code, db=db, dbname=_dbname, live=live, init=utils.true
            )

    if not isempty:
        run_strategy(fund, live)


async def asyncio_update_k_data(fund, db=None, dbname='', live=utils.true):
    code = fund['code']
    utils.update_k_data(
        code, db=db, dbname=dbname, live=live, init=utils.false
    )


# %%
if __name__ == "__main__":
    # funds = constant.live_trade_funds
    db = models.DB()
    wheres = [
        {'k': 'qtype', 'v': 'lof'}
    ]
    funds = utils.get_distinct_codes('fund_info', pk='code', wheres=wheres)
    live = utils.true
    dbname = 'k_5min_data'
    # dbname = 'k_data'
    # for fund in funds:
    #     # tornado_run_strategy(fund, db, dbname, live)
    #     one_run_strategy(fund, db, dbname, utils.false)

    # utils.tornado_tasks(tornado_run_strategy, tasks=funds, db=db, dbname=dbname, live=live)

    utils.asyncio_tasks(asyncio_run_strategy, tasks=funds,
                        db=db, dbname=dbname, live=utils.false, init=utils.true)
