# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import backtrader as bt

import strategys
import models
from datetime import datetime, timedelta
import asyncio

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
    code = fund['code']
    code_cn = fund['code_cn']
    strategy = strategys.CMIStrategy
    if '消费' in code_cn:
        strategy = strategys.TWAPMultiStrategy
    else:
        strategy = strategys.CMIStrategy
    start_strategy(strategy, code, code_cn, live)


def async_run_strategy2(fund, db=None, dbname='', live=utils.true):
    code = fund['code']
    isempty = utils.update_k_5min_data(
        code, db=db, dbname=dbname, live=live, init=utils.false)
    if live:
        # 检查k_data是否已更新
        _dbname = 'k_data'
        file = utils.get_csv_file(code, _dbname)
        stat = utils.get_stat(file)
        if int(utils.time.time()) - stat.st_mtime > 60*60*12:
            utils.update_k_data(
                code, db=db, dbname=_dbname, live=live, init=utils.false
            )
    if 1:
        run_strategy(fund, live)


async def async_run_strategy(fund, db=None, dbname='', live=utils.true):
    code = fund['code']
    isempty = utils.update_k_5min_data(
        code, db=db, dbname=dbname, live=live, init=utils.false)
    if live:
        # 检查k_data是否已更新
        _dbname = 'k_data'
        file = utils.get_csv_file(code, _dbname)
        stat = utils.get_stat(file)
        if int(utils.time.time()) - stat.st_mtime > 60*60*12:
            utils.update_k_data(
                code, db=db, dbname=_dbname, live=live, init=utils.false
            )
    if not isempty:
        run_strategy(fund, live)


async def async_update_live_k_data(fund, db=None, dbname='', live=utils.true):
    code = fund['code']
    utils.update_k_data(
        code, db=db, dbname=dbname, live=live, init=utils.false
    )


def async_update_live_k_data2(fund, db=None, dbname='', live=utils.true):
    code = fund['code']
    utils.update_k_data(
        code, db=db, dbname=dbname, live=live, init=utils.false
    )


# %%
if __name__ == "__main__":
    funds = constant.live_trade_funds
    db = models.DB()
    live = utils.true
    dbname = 'k_5min_data'
    # dbname = 'k_data'
    for fund in funds:
        # async_update_live_k_data2(fund, db, dbname)
        async_run_strategy2(fund, db, dbname, live)
        # run_strategy(fund)

    # utils.asyncio_tasks(async_run_strategy, tasks=funds, db=db, dbname=dbname, live=live)

    # utils.async_tasks(async_run_strategy2, tasks=funds, db=db, dbname=dbname)
