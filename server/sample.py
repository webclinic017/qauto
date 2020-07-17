import constant
import backtrader as bt
import utils
import models
from backtrader_plotting import Bokeh, OptBrowser
from backtrader_plotting.schemes import Tradimo
from backtrader.analyzers import SQN

import strategys

from indicators import ssa_index_ind, VWAP, TWAP

# http://www.vincentsblog.com/post/backtrader-backtest-ashare
# multi strategy: https://community.backtrader.com/topic/2122/live-trading-multiple-strategies-each-one-on-a-separate-data-feed/6


ORDER_HISTORY = (
    ('2020-12-20', 9429, 2.014),
)

cerebro = bt.Cerebro(tradehistory=utils.true)

cerebro.add_order_history(ORDER_HISTORY, notify=utils.true)
# cerebro.addobserver(bt.observers.Trades)
# self.stats.trades[0] # 当前持仓盈亏

# 多周期回测
multiperiod = 'k_5min_data'
# multiperiod = ''

# 159928,单纯twap表现优秀,cmi表现不佳???,cmi取值有问题???
# 162703,twap表现远不如cmi,round长期持有???
# cerebro.addstrategy(strategys.TWAPMultiStrategy,
#                     _live=utils.true, multiperiod=multiperiod, orderlog=utils.false, tradelog=utils.true, doprint=utils.true)
cerebro.addstrategy(strategys.SchedStrategy,
                    multiperiod=multiperiod, doprint=utils.true, orderlog=utils.false, tradelog=utils.true)
start = '2019-06-22'
end = '2020-06-22'

# df = utils.get_database_data(code, start)
# print(df)
# data = models.PandasData(dataname=df)
# cerebro.adddata(data)


# dbname = 'ggt'
# pk = 'code'
# codes = utils.get_distinct_codes(dbname, pk)

funds = constant.trade_funds
# codes = ['002027', '000725']
# codes = utils.get_my_etf()

for fund in funds:
    code = fund['code']
    code_cn = fund['code_cn']
    dbnames = ['k_data']
    if multiperiod:
        dbnames.append(multiperiod)
        for dbname in dbnames:
            df = utils.get_database_data(
                code, dbname=dbname, start=start, end=end)
            # print(df)
            if df.empty:
                print(code, '未获取到数据')
                continue
            name = '{}:{}:{}'.format(code, code_cn, dbname)
            data = models.PandasData(dataname=df, name=name)
            cerebro.adddata(data)
    else:
        df = utils.get_database_data(
            code, dbname=dbnames[0], start=start, end=end)
        # print(df)
        data = models.PandasData(dataname=df, name='')
        cerebro.adddata(data)


utils.addanalyzer(cerebro)

# cerebro.addanalyzer(SQN)

# fn = 'test.csv'
# cerebro.addwriter(bt.WriterFile, csv=True, out=fn, rounding=2)

startcash = 20000  # 测试期货需调整
cerebro.broker.setcash(startcash)
cerebro.broker.setcommission(commission=0.00001)
print('Starting Portfolio Value: %.3f' % cerebro.broker.getvalue())
strats = cerebro.run(maxcpus=1, optreturn=utils.true)
strat = strats[0]
utils.print_transaction(strat)
# accountinfo = strat.analyzers.AccountValue.get_analysis()
# data = utils.getstratdata(strat, accountinfo)
# utils.plot_strategy(
#     code,
#     start=start,
#     buy=data['buy'],
#     sell=data['sell'],
#     availablevalue=data['availablevalue'],
#     totalvalue=data['totalvalue'],
# )

print('Final Portfolio Value: %.3f' % cerebro.broker.getvalue())
# cerebro.plot(style='candle')  # line,bar,candle
#  cerebro.plot(start=datetime.date(2018, 1, 1), end=datetime.date(2019, 12, 31),
# cerebro.plot(volume=False, style='candle',
#              barup='red', bardown='green')

# bo = Bokeh(style="bar", tabs="multi", scheme=Tradimo())
# cerebro.plot(bo)
