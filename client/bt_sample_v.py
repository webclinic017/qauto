# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%

# https://zhuanlan.zhihu.com/p/64019862
# 画图: https://cloud.tencent.com/developer/article/1388001
# https://pyecharts.org/#/zh-cn/assets_host
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import OrderedDict
import backtrader as bt
from backtrader import Analyzer
import backtrader.analyzers as btanalyzers
import tushare as ts
import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
import talib as ta

from strategys import FixedInvestStrategy

import os
import math
import time
import datetime
import json

import utils

# %%


class AccountValue(Analyzer):
    params = ()

    def start(self):
        super(AccountValue, self).start()
        self.rets = OrderedDict()

    def next(self):
        super(AccountValue, self).next()
        totalvalue = self.rets.get('totalvalue', OrderedDict())
        dt = self.datas[0].datetime.datetime()
        key = '{0}-{1}-{2}'.format(dt.year, dt.month, dt.day)
        totalvalue[key] = utils.get_float(self.strategy.broker.getvalue(), 3)
        self.rets['totalvalue'] = totalvalue
        availablevalue = self.rets.get('availablevalue', OrderedDict())
        availablevalue[key] = utils.get_float(
            self.strategy.broker.get_cash(), 3)
        self.rets['availablevalue'] = availablevalue

    def get_analysis(self):
        return self.rets

# %%


# %%


# def start():
start = '2017-06-22'
code = '159928'
# code = '512760'
# 获取5分钟K线图,获取不到全部数据,更换baostock
df = utils.get_data_ts(code, start=start, freq='d')
sdt = df.index[0]
# 日期修正
start = '{0}-{1}-{2}'.format(sdt.year, sdt.month, sdt.day)
print(df.head())
print(df.tail())
data = bt.feeds.PandasData(dataname=df)
cerebro = bt.Cerebro()
# 将数据传入回测系统
cerebro.adddata(data)
# 将交易策略加载到回测系统中
cerebro.addstrategy(
    FixedInvestStrategy,
    minrise=-1,
    maxrise=2.5,
    buysize=300,
    sellsize=300,
    printlog=True,
)
# 设置初始资本为10,000
startcash = 20000
cerebro.broker.setcash(startcash)
# 设置交易手续费为0.3%
cerebro.broker.setcommission(commission=0.001)
# 运行回测系统
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

# 收益分析指标
cerebro.addanalyzer(AccountValue, _name='AccountValue')

cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='SharpeRatio',
                    riskfreerate=0.00, stddev_sample=True, annualize=True)
cerebro.addanalyzer(bt.analyzers.Returns, _name="Returns")
cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='AnnualReturn')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DW')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='TradeAnalyzer')

strats = cerebro.run()
strat = strats[0]

finalvalue = cerebro.broker.getvalue()
totalreturn = finalvalue - startcash
sharperatio = strat.analyzers.SharpeRatio.get_analysis()['sharperatio']
maxdrowdown = strat.analyzers.DW.get_analysis()['max']['drawdown']
maxdrowdownmoney = strat.analyzers.DW.get_analysis()['max']['moneydown']
tradeinfo = strat.analyzers.TradeAnalyzer.get_analysis()

accountinfo = strat.analyzers.AccountValue.get_analysis()
annualreturninfo = strat.analyzers.AnnualReturn.get_analysis()
returnsinfo = strat.analyzers.Returns.get_analysis()
returninfo = {'startcash': startcash, 'finalvalue': finalvalue, 'totalreturn': totalreturn,
              'sharperatio': sharperatio, 'maxdrowdown': maxdrowdown, 'maxdrowdownmoney': maxdrowdownmoney,
              'tradeinfo': tradeinfo}

print(returninfo)
print(returnsinfo)


# %%


# code = '159928'
# code = '000725'
# %%

data = utils.getstratdata(strat, accountinfo)
utils.plot_strategy(
    code,
    start=start,
    buy=data['buy'],
    sell=data['sell'],
    availablevalue=data['availablevalue'],
    totalvalue=data['totalvalue'],
)

# %%


def opt_strategy(code, start='', end='', startcash=20000, qts=500, com=0.001):
    # 创建主控制器
    cerebro = bt.Cerebro()
    # 获取数据
    df = utils.get_data_ts(code, start=start, end=end, freq='d')
    sdt = df.index[0]
    # 日期修正
    start = '{0}-{1}-{2}'.format(sdt.year, sdt.month, sdt.day)
    print(start)
    # 将数据加载至回测系统
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    # broker设置资金、手续费
    cerebro.broker.setcash(startcash)
    cerebro.broker.setcommission(commission=com)
    # 设置买入设置，策略，数量
    cerebro.addsizer(bt.sizers.FixedSize, stake=qts)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='SharpeRatio',
                        riskfreerate=0.00, stddev_sample=True, annualize=True)
    cerebro.addanalyzer(bt.analyzers.Returns, _name="Returns")
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='AnnualReturn')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DW')
    # 导入策略参数寻优
    strats = cerebro.optstrategy(
        FixedInvestStrategy,
        minrise=utils.gen_minrises(),
        maxrise=utils.gen_maxrises(),
        buysize=range(100, 400, 100),
        sellsize=range(100, 400, 100),
        code=code,
        start=start,
        printlog=False,
        doprint=True,
    )
    print(strats)
    print('期初总资金:%.2f' % cerebro.broker.getvalue())
    cerebro.run(maxcpus=1)
    print('期末总资金:%.2f' % cerebro.broker.getvalue())


# start = '2013-06-04'
# code = '161005'
codes = ['159941', '159928', '513500', '513050',
         '512760', '512170', '163407', '163402', '166001']
# code = '512170'
# code = '166001'
# opt_strategy(code)
for code in codes:
    try:
        opt_strategy(code)
    except Exception as ex:
        time.sleep(60)
        print(ex)

# %%


# %%


def code_to_symbol(code):
    return 'sh.%s' % code if code[:1] in ['5', '6', '9'] or code[:2] in ['11', '13'] else 'sz.%s' % code
