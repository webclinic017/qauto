# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
from datetime import datetime
import backtrader as bt
import tushare as ts


# %%
import pandas as pd


# %%
import matplotlib.pyplot as plt


# %%
def get_data(code, start='2017-01-01', end='2020-03-31'):
    df = ts.get_k_data(code, autype='qfq', start=start, end=end)
    df.index = pd.to_datetime(df.date)
    df['openinterest'] = 0
    df = df[['open', 'high', 'low', 'close', 'volume', 'openinterest']]
    return df


# %%


# %%
# 回测期间
code = '159928'
start = datetime(2017, 3, 31)
end = datetime(2020, 3, 31)
dataframe = get_data(code)


# %%
data = bt.feeds.PandasData(dataname=dataframe, fromdate=start, todate=end)


# %%
class TestStrategy(bt.Strategy):

    # 设置全局参数
    params = (
        ('maperiod', 20),
    )

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.4f' % self.dataclose[0])


# %%
# 初始化cerebro回测系统设置
cerebro = bt.Cerebro()
# 将数据传入回测系统
cerebro.adddata(data)
# 将交易策略加载到回测系统中
cerebro.addstrategy(TestStrategy)
# 设置初始资本为10,000
startcash = 10000
cerebro.broker.setcash(startcash)
# 设置交易手续费为 0.2%
cerebro.broker.setcommission(commission=0.002)
# 运行回测系统
cerebro.run()


# %%
portvalue = cerebro.broker.getvalue()
pnl = portvalue - startcash


# %%
# print(f'初始资金: {startcash}\n回测期间：{d1}:{d2}')
print(f'净收益: {round(pnl,2)}')
print(f'总资金: {round(portvalue,2)}')


# %%

cerebro.plot(style='yahoo')


# %%



# %%
