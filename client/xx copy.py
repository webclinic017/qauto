# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
# 入门: https://blog.csdn.net/ndhtou222/article/details/105236618?utm_medium=distribute.pc_relevant.none-task-blog-baidujs-2
# 入门: https://blog.csdn.net/halcyonbaby/article/details/104704079
# 入门: https://blog.csdn.net/m0_46603114/category_9820181.html
# 进阶: https://zhuanlan.zhihu.com/c_1189276087837011968
# 优化: https://blog.csdn.net/weixin_42232219/article/details/92115226?utm_medium=distribute.pc_relevant.none-task-blog-BlogCommendFromMachineLearnPai2-6.nonecase&depth_1-utm_source=distribute.pc_relevant.none-task-blog-BlogCommendFromMachineLearnPai2-6.nonecase

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
# 获取数据
def get_data(code, start='2017-01-01', end='2020-03-31'):
    df = ts.get_k_data(code, autype='qfq', start=start, end=end)
    df.index = pd.to_datetime(df.date)
    # df['openinterest'] = 0
    df = df[['open', 'high', 'low', 'close', 'volume']]
    return df


# %%
# 回测策略
class TestStrategy(bt.Strategy):
    # 设置全局参数
    params = (
        ('maperiod', 20),
        ('printlog', True),
        ('pricerise', 3),
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
        # offset = self.getOffSet()
        # try:
        #     predataclose = self.dataclose[offset]
        # except IndexError as ex:
        #     return
        # except Exception as ex:
        #     self.log(ex)
        #     return
        # pricerise = ((self.dataclose[0] -
        #               predataclose) / self.dataclose[0]) * 100
        # msg = '开盘价: %.3f, 收盘价: %.3f, 上一日收盘价: %.3f, 涨幅: %.3f' % (
        #     self.dataopen[0], self.dataclose[0], predataclose, pricerise)
        # self.log(msg)
        # 检查是否有指令等待执行
        if self.order:
            return
        # 检查是否持仓
        if not self.position:
            # 执行买入条件判断:收盘价格上涨突破20日均线
            # if self.dataclose[0] > self.sma[0]:
            if self.dataclose[0] > self.sma[0]:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()
        else:
            # 执行卖出条件判断:收盘价格跌破20日均线
            if self.dataclose[0] < self.sma[0]:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()

    # 交易记录日志（可省略，默认不输出结果）
    def log(self, txt, dt=None):
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()},{txt}')

    # 回测结束后输出结果（可省略，默认输出结果）
    def stop(self):
        self.log('(MA均线:%2d日) 期末总资金:%.2f' %
                 (self.params.maperiod, self.broker.getvalue()))

    def getOffSet(self):
        dt = self.datetime.datetime(0)
        msg = '{0}-{1}-{2}'.format(dt.year, dt.month, dt.day)
        dtcompare = datetime.datetime(dt.year, dt.month, dt.day, 9, 30)
        offsetseconds = (dt - dtcompare).total_seconds()
        offset = int(offsetseconds / 60 / 5)
        return offset


# %%
# 初始化cerebro回测系统设置

# %%
# 初始化cerebro回测系统设置
code = '159928'
df = get_data(code, start='2020-05-22')

data = bt.feeds.PandasData(dataname=df)

cerebro = bt.Cerebro()
# 将数据传入回测系统
cerebro.adddata(data)
# 将交易策略加载到回测系统中
cerebro.addstrategy(TestStrategy)
# 设置初始资本为10,000
startcash = 10000
cerebro.broker.setcash(startcash)
# 设置交易手续费为0.3%
cerebro.broker.setcommission(commission=0.003)
# 运行回测系统
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
cerebro.run()
print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
# print(f'初始资金: {startcash}\n回测期间：{d1}:{d2}')
# 获取回测结束后的总资金
portvalue = cerebro.broker.getvalue()
pnl = portvalue - startcash
print(f'净收益: {round(pnl,2)}')
print(f'总资金: {round(portvalue,2)}')

# cerebro.plot(style='yahoo')
# %matplotlib inline
# cerebro.plot()


# %%
# 优化参数
def opt_params(code, start='', end='', startcash=10000, qts=500, com=0.001):
    # 创建主控制器
    cerebro = bt.Cerebro()
    # 导入策略参数寻优
    cerebro.optstrategy(TestStrategy, maperiod=range(3, 31))
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


# %%
%matplotlib inline


def plot_stock(code, title, start, end):
    dd = ts.get_k_data(code, autype='qfq', start=start, end=end)
    dd.index = pd.to_datetime(dd.date)
    dd.close.plot(figsize=(14, 6), color='r')
    plt.title(title+'价格走势\n'+start+':'+end, size=15)
    plt.annotate(f'期间累计涨幅:{(dd.close[-1]/dd.close[0]-1)*100:.2f}%', xy=(dd.index[-150], dd.close.mean()), xytext=(dd.index[-500], dd.close.min()),
                 bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5), arrowprops=dict(facecolor='green', shrink=0.05), fontsize=12)
    plt.show()


# %%

code = '159928'
# code = 'sh'
# start = '2017-01-01'
start = '2020-01-01'
end = '2020-04-08'
title = '上证指数'
# plot_stock(code, title, start, end)
opt_params(code, start, end, 1000000, 100)

# plot_stock('600000', '浦发银行', '2015-01-01', '2020-03-30')


# %%
# 初始化cerebro回测系统设置
cerebro = bt.Cerebro()
# 获取数据
df = ts.get_k_data('600000', autype='qfq',
                   start='2015-01-01', end='2020-03-30')
df.index = pd.to_datetime(df.date)
df = df[['open', 'high', 'low', 'close', 'volume']]
data = bt.feeds.PandasData(dataname=df, fromdate=datetime(
    2010, 1, 1), todate=datetime(2020, 3, 30))
# 加载数据
cerebro.adddata(data)
# 将交易策略加载到回测系统中
# 设置printlog=True，表示打印交易日志log
cerebro.addstrategy(TestStrategy, maperiod=14, printlog=True)
# 设置初始资本为10,000
cerebro.broker.setcash(10000.0)
# 设置交易手续费为0.1%
cerebro.broker.setcommission(commission=0.001)
# 设置买入设置，策略，数量
cerebro.addsizer(bt.sizers.FixedSize, stake=1000)

cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DW')
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='SharpeRatio')
# 回测结果
results = cerebro.run()
strat = results[0]


# 获取最后总资金
portvalue = cerebro.broker.getvalue()
# Print out the final result
print(f'总资金: {portvalue:.2f}')
print('夏普比率:', strat.analyzers.SharpeRatio.get_analysis())
print('回撤指标:', strat.analyzers.DW.get_analysis())

%matplotlib inline
cerebro.plot()
# %%
