# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%

from matplotlib.font_manager import _rebuild
import matplotlib
from datetime import datetime
import backtrader as bt
import matplotlib.pyplot as plt
import tushare as ts
import pandas as pd
import matplotlib as mpl
mpl.use('TkAgg')
# 正常显示画图时出现的中文和负号
mpl.rcParams['axes.unicode_minus'] = False

_rebuild()
plt.rcParams['font.sans-serif'] = ['songti sc']


# %%
# 回测策略
class TestStrategy(bt.Strategy):
    # 设置全局参数
    params = (
        ('maperiod', 20),
        ('printlog', False),
    )

    def __init__(self):
        # 指定价格序列
        self.dataclose = self.datas[0].close
        # 初始化交易指令、买卖价格和手续费
        self.order = None
        self.buyprice = None
        self.buycomm = None
        # 添加移动均线指标，内置了talib模块
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod)

    # 策略核心,根据条件执行买卖交易指令（必选）
    def next(self):
        # 检查是否有指令等待执行
        if self.order:
            return
        # 检查是否持仓
        if not self.position:
            # 执行买入条件判断:收盘价格上涨突破20日均线
            if self.dataclose[0] > self.sma[0]:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()
        else:
            # 执行卖出条件判断:收盘价格跌破20日均线
            if self.dataclose[0] < self.sma[0]:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()

#         self.log('Close, %.4f' % self.dataclose[0])

    # 记录交易执行情况（可省略，默认不输出结果）
    def notify_order(self, order):
        pass

    # 记录交易收益情况（可省略，默认不输出结果）
    def notify_trade(self, trade):
        pass

    # 交易记录日志（可省略，默认不输出结果）
    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            self.log(dt)

    # 回测结束后输出结果（可省略，默认输出结果）
    def stop(self):
        self.log('(MA均线:%2d日) 期末总资金:%.2f' %
                 (self.params.maperiod, self.broker.getvalue()), doprint=True)

# %%
# 优化参数


def opt_params(code, start='', end='', startcash=10000, qts=500, com=0.001):
    # 创建主控制器
    cerebro = bt.Cerebro()
    # 导入策略参数寻优
    cerebro.optstrategy(TestStrategy, maperiod=range(3, 31), printlog=True)
    # 获取数据
    df = ts.get_k_data(code, autype='qfq', start=start, end=end)
#     print(df.head())
    df.index = pd.to_datetime(df.date)
    df = df[['open', 'high', 'low', 'close', 'volume']]
    # 将数据加载至回测系统
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    # broker设置资金、手续费
    cerebro.broker.setcash(startcash)
    cerebro.broker.setcommission(commission=com)
    # 设置买入设置，策略，数量
    cerebro.addsizer(bt.sizers.FixedSize, stake=qts)
    print('期初总资金:%.2f' % cerebro.broker.getvalue())
    cerebro.run(maxcpus=1)
    print('期末总资金:%.2f' % cerebro.broker.getvalue())


# %%

code = '159928'
info = ts.get_fund_info(code)
# code = 'sh'
# start = '2017-01-01'
start = '2019-05-22'
end = '2020-05-22'
# title = '上证指数'
title = info.values[0][1]
opt_params(code, start, end, 1000000, 100)

# plot_stock('600000', '浦发银行', '2015-01-01', '2020-03-30')
# %%
