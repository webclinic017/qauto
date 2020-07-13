# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import backtrader as bt

import strategys
import models
from datetime import datetime, timedelta

import utils
import constant

# %%


# TODO: 检查数据正确性

def start_strategy(strategy, code, code_cn):
    # 开启实盘交易
    live = utils.true
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
            code, dbname=dbname, start=start)
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


def run_strategy(fund):
    # 消费特殊处理,cmi值一直偏高
    code = fund['code']
    code_cn = fund['code_cn']
    strategy = strategys.CMIStrategy
    if '消费' in code_cn:
        strategy = strategys.TWAPMultiStrategy
    else:
        strategy = strategys.CMIStrategy
    start_strategy(strategy, code, code_cn)


def async_run_strategy(fund, db=None, dbname=''):
    code = fund['code']
    isempty = utils.update_k_5min_data(
        code, db=db, dbname=dbname, init=utils.false)
    if not isempty:
        run_strategy(fund)


# %%
if __name__ == "__main__":
    funds = constant.live_trade_funds
    db = models.DB()
    dbname = 'k_5min_data'
    for fund in funds:
        # async_run_strategy(fund, db, dbname)
        run_strategy(fund)
    # utils.async_tasks(async_run_strategy, tasks=funds, db=db, dbname=dbname)
