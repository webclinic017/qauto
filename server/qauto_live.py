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

def start_strategy(strategy, code, code_cn, slg='', live=utils.false):
    # 开启5分钟周期下单
    multiperiod = 'k_5min_data'

    cerebro = bt.Cerebro()

    cerebro.addstrategy(
        strategy,
        multiperiod=multiperiod,
        _live=live,
        orderlog=utils.false,
        tradelog=utils.false,
        doprint=utils.true,
    )
    # 获取3个月前数据,保证指标正常
    # if slg == 'sched':
    #     startdt = datetime.now() + timedelta(days=-30)
    # else:
    startdt = datetime.now() + timedelta(days=-22*3)
    start = utils.get_datetime_date(startdt, flag='-')

    dbnames = ['k_data']
    dbnames.append(multiperiod)
    for dbname in dbnames:
        df = utils.get_database_data(
            code, dbname=dbname, start=start, slg=slg, live=live)
        # 验证数据
        if df.empty:
            print(code, '未获取到数据')
            continue
        # print(df)
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


def run_one_strategy(fund, live):
    # 消费特殊处理,cmi值一直偏高
    if isinstance(fund, str):
        return
    code = fund['code']
    code_cn = fund['code_cn']
    slg = fund.get('slg', '')
    if not slg:
        return
    if slg == 'sched':
        strategy = strategys.SchedStrategy
    elif slg == 'twap':
        strategy = strategys.TWAPMultiStrategy
    elif slg == 'cmi':
        strategy = strategys.CMIStrategy
    else:
        raise Exception('未设置策略')

    start_strategy(strategy, code, code_cn, slg, live)

def run_strategy(funds, live=utils.true):
    print('开始回测,{}'.format(funds))
    for fund in funds:
        run_one_strategy(fund, live)

async def asyncio_update_k_5min_data(fund, db=None, dbname='', live=utils.true, init=False):
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
                # 获取近期溢价
                await utils.get_one_rt(code, init=utils.false)
        else:
            # 获取全部溢价
            await utils.get_one_rt(code, init=utils.true)
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
        run_one_strategy(fund, live)


async def asyncio_update_k_data(fund, db=None, dbname='', live=utils.true):
    code = fund['code']
    utils.update_k_data(
        code, db=db, dbname=dbname, live=live, init=utils.false
    )


# %%
if __name__ == "__main__":
    funds = constant.live_trade_funds
    db = models.DB()
    # wheres = [
    #     {'k': 'qtype', 'v': 'lof'}
    # ]
    # funds = utils.get_distinct_codes('fund_info', pk='code', wheres=wheres)
    live = utils.true
    dbname = 'k_5min_data'
    # dbname = 'k_data'
    # utils.load_fund_info()
    # fundinfo = utils.g_share['fund_info']
    # funds = [str(code) for code in fundinfo.code.values.tolist()]
    utils.asyncio_tasks(asyncio_update_k_5min_data, tasks=funds, db=db, dbname=dbname, live=utils.false, init=utils.true)

    # run_strategy(funds)
                    
