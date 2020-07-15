# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import time
import json
import itertools
from datetime import datetime, timedelta

import backtrader as bt
import pandas as pd
import numpy as np

import strategys

import models
import utils

# %%
globalparams = []
# %%


def get_one_params_ex(db, dbname, code, dates, strategy, optparams):
    oneparams = {}
    for optparam in optparams:
        k = optparam['k']
        # 每个参数去检查
        plist = []
        for date in dates:
            wheres = [
                {'k': 'code', 'v': code, 'op': '='},
                {'k': 'start', 'v': date, 'op': '='},
                # {'k': 'failrate', 'v': 0.2, 'op': '<'},
            ]
            orderby = 'value desc,maxdrowdown asc'
            df = db.select(dbname, wheres=wheres, orderby=orderby)
            if df.empty:
                continue
            # print(df[k], date)
            v = df[k][0]
            plist.append(v)
        pdict = {}
        for v in optparam['v']:
            count = plist.count(v)
            pdict[v] = count
        pdict = sorted(pdict.items(), key=lambda d: d[1], reverse=True)
        msg = '多周期,单参数历史最优'
        print(msg, pdict)
        if pdict:
            oneparams[k] = pdict[0][0]
        else:
            oneparams[k] = ''

    return oneparams


def valid_best_param(df, bestparams):
    df.sort_values(by='score', inplace=True, ascending=True)
    df.reset_index(drop=True, inplace=True)

    querystr = utils.get_query_str(bestparams)

    da = df.query(querystr)
    pos = da.index[-1]
    isbest = False
    if pos / len(df) > 0.55:
        isbest = True
    return isbest

# %%


def check_table(db, dbname, pks):
    # 检查表是否存在,表结构是否发生变化
    hastable = db.has_table(dbname)
    if hastable:
        hascolumns = db.has_columns(dbname, pks)
        if not hascolumns:
            db.drop(dbname)
        else:
            db.set_index(dbname, pks)


def run_strategy(code, start='', end='', strategy=None, params={}, isopt=True, comm=0.0001, startcash=20000):
    cerebro = bt.Cerebro()
    params['code'] = code
    if ',' in code:
        code = json.loads(code)
        for j in code:
            df = utils.get_database_data(j, start, end)
            if df.empty:
                continue
            data = models.PandasData(dataname=df)
            cerebro.adddata(data)
    else:
        params['code'] = code
        df = utils.get_database_data(code, start, end)
        if df.empty:
            print('未取到数据')
            return
        data = models.PandasData(dataname=df)
        cerebro.adddata(data)

        # dbnames = ['k_data', 'k_5min_data']
        # for dbname in dbnames:
        #     df = utils.get_database_data(
        #         code, dbname=dbname, start=start, end=end)
        #     if df.empty:
        #         print(code, '未获取到数据')
        #         continue
        #     name = '{}:{}'.format(code, dbname)
        #     data = models.PandasData(dataname=df, name=name)
        #     cerebro.adddata(data)

    cerebro.broker.setcash(startcash)
    cerebro.broker.setcommission(commission=comm)
    # 收益,风险指标
    utils.addanalyzer(cerebro)

    defaultparams = dict(
        printlog=False,
        orderlog=False,
        tradelog=False,
        doprint=True,
    )
    params['start'] = start
    params.update(defaultparams)

    if isopt:
        cerebro.optstrategy(
            strategy,
            **params
        )
    else:
        cerebro.addstrategy(
            strategy,
            **params
        )
    # 多进程,源码修改
    cerebro.run(maxcpus=1)
    if not isopt:
        cerebro.plot()


def get_sort_score(df, isweight=True):
    if isweight:
        df['score'] = df[['slgrate', 'sharpe', 'mddrate']].apply(
            # lambda x: x['slgrate'],
            lambda x: x['slgrate'] * 0.5 +
            x['sharpe'] * 0.2 + x['mddrate'] * 0.3,
            axis=1,
        )
    else:
        df['score'] = df['slgrate']
    # index改变,去除index
    df.sort_values(by='score', ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def get_dates(db, dbname, pk):
    # 多周期,半年,一年,一年半,两年...十年
    db = models.DB()
    hastable = db.has_table(dbname)
    if hastable:
        dates = db.select_distinct(dbname, pk)
        if dates:
            dates.sort(reverse=True)
            return dates

    dates = []
    now = datetime.now()
    for _ in range(21):
        now += timedelta(days=-182)
        date = utils.get_datetime_date(now)
        dates.append(date)
    return dates


def get_best_params(df, optkeys):
    if df.empty:
        return
    bestparams = {}
    for optkey in optkeys:
        da = df.groupby(by=optkey).size()
        da.sort_values(ascending=False, inplace=True)
        # 取出现次数多的值,稳定性最强
        print(da.to_dict())
        v = da.index[0]
        if isinstance(v, np.int64):
            v = int(v)
        elif isinstance(v, np.float):
            v = float(v)
        bestparams[optkey] = v
    return bestparams


def get_one_params(db, dbname, code, dates, strategy, optparams):
    # 长周期,参数最优
    oneparams = {}
    optkeys = [j['k'] for j in optparams]
    result = pd.DataFrame()
    for date in dates:
        wheres = [
            {'k': 'code', 'v': code, 'op': '='},
            {'k': 'start', 'v': date, 'op': '='},
            # {'k': 'failrate', 'v': 0.2, 'op': '<'}, # 不过滤失败次数,历史回撤大
        ]
        df = db.select(dbname, wheres=wheres)
        if df.empty:
            continue
        df = get_sort_score(df, isweight=False)
        # 取前三
        end = round(60*60 * 0.3)
        df = df[:end]
        # print(df, date)
        df.reset_index(drop=True, inplace=True)
        result.reset_index(drop=True, inplace=True)
        result = pd.concat([df, result], axis=0, ignore_index=True)

    oneparams = get_best_params(result, optkeys)
    msg = '长周期,多参数历史最优'
    print(msg, oneparams)
    return oneparams


def get_batch_params(db, dbname, code, dates, optparams):
    # 多周期,多参数历史最优
    optkeys = [j['k'] for j in optparams]
    result = pd.DataFrame()

    for date in dates:
        wheres = [
            {'k': 'code', 'v': code, 'op': '='},
            {'k': 'start', 'v': date, 'op': '='},
            # {'k': 'failrate', 'v': 0.2, 'op': '<'},
        ]
        df = db.select(dbname, wheres=wheres)
        # import ipdb; ipdb.set_trace()
        if df.empty:
            continue
        df = get_sort_score(df)
        # 取本周期前20%,各个周期多参数最优
        end = round(len(df) * 0.3)
        df = df[:end]
        # print(df, date)
        df.reset_index(drop=True, inplace=True)
        result.reset_index(drop=True, inplace=True)
        result = pd.concat([df, result], axis=0, ignore_index=True)

    globalparams.append(result)

    batchparams = get_best_params(result, optkeys)
    msg = '短周期,多参数历史最优'
    print(msg, batchparams)
    return batchparams

# 多周期??,以什么截止时间
# 多周期,单参数自动寻优:done
# 多周期,多参数最优:done
# 多品种参数寻优:TODO


def auto_run_strategy(code, dates, strategy, optparams, pks, _type='fund'):
    for date in dates:
        params = {}
        for optparam in optparams:
            params[optparam['k']] = optparam['v']
        params['pks'] = json.dumps(pks)
        params['_type'] = _type
        run_strategy(code, start=date, strategy=strategy, params=params)


def start_one(code, optparams, strategy, _type):
    if isinstance(code, list):
        code = json.dumps(code)

    db = models.DB()
    dbname = strategy.__name__.lower()
    pks = [j['k'] for j in optparams]
    field = 'start'
    pks.extend(['code', field, 'type'])
    check_table(db, dbname, pks)

    dates = get_dates(db, dbname, field)

    # auto_run_strategy(code, dates, strategy, optparams, pks, _type)

    oneparams = get_one_params(
        db, dbname, code, dates, strategy, optparams)
    # 两年历史最优
    batchparams = get_batch_params(
        db, dbname, code, dates[:4], optparams)
    msg = '{},\n'.format(code)
    if oneparams != batchparams:
        msg += '长周期,单参数最优与短周期多参数最优不一致\n'
    print(msg, oneparams, '\n', batchparams)

    # if oneparams:
    #     run_strategy(
    #         code, start=dates[-1], strategy=strategy, params=oneparams, isopt=False)
    # if batchparams:
    #     run_strategy(
    #         code, start=dates[0], strategy=strategy, params=batchparams, isopt=False)


def start(codes, optparams, strategy, _type='fund'):
    for code in codes:
        start_one(code, optparams, strategy, _type)

    results = pd.concat(globalparams, axis=0, ignore_index=True)
    optkeys = [j['k'] for j in optparams]
    targetparams = get_best_params(results, optkeys)
    return targetparams


def main():
    # optparams = [
    #     {'k': 'maxrise', 'v': [2.25, 2.5, 2.75, 3.25]},
    #     {'k': 'minrise', 'v': [-0.25, -0.75, -0.95]},
    #     {'k': 'perrise', 'v': [0.25, 0.75]},
    #     {'k': 'petype', 'v': ''},
    # ]
    # strategy = SchedStrategy

    optparams = [
        {'k': 'twapperiod', 'v': [3, 5]},
    ]
    strategy = strategys.TWAPMultiStrategy

    import constant
    codes = [i for i, _ in constant.trade_funds.items()]

    # allcodes = []
    # for y in itertools.combinations(codes, 4):
    #     x = list(y)
    #     x.append('161716')
    #     allcodes.append(x)

    # dbname = 'fund_info'
    # pk = 'code'
    # codes = utils.get_distinct_codes(dbname, pk)
    # optparams = [
    #     {'k': 'cmiperiod', 'v': 22},
    #     {'k': 'minperiod', 'v': 50},
    #     {'k': 'maxperiod', 'v': 150},
    # ]
    # strategy = strategys.CMIStrategy

    _type = 'fund'
    print(codes)

    targetparams = start(codes, optparams, strategy, _type)
    msg = '多品种,多参数,短周期(两年内)'
    print(msg, targetparams)


# %%

# 寻优: https://blog.csdn.net/luqiang_shi/category_8450377.html

# 策略参数自动寻优
# 策略稳定性(盈利)第一,不要过度优化,取前30%统计计算最优参数

# 多策略,CMI恒温器策略进行策略切换
# 多品种,done

# 优化要点:
# 1. 先小数据,小周期
# 2. 优化参数原则: 1.同类产品通用, 2.不同周期通用, 3.跨领域通用(基金,股票,期货)
# 3. 分组优化var变量参数, 每次最多2-3个参数(平均值)
# opt-pools


# select a.code, a.start, a.minperiod,a.maxperiod,b.twapperiod, a.rate, a.slgrate as cslgrate, b.slgrate as tslgrate, a.mddrate as cmddrate, b.mddrate as tmddrate from cmistrategy as a, twapmultistrategy as b where a.code=b.code and a.start=b.start and twapperiod=3 and minperiod=20 

if __name__ == "__main__":
    main()
