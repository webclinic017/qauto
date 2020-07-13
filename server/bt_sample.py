# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
# 入门: https://blog.csdn.net/ndhtou222/article/details/105236618?utm_medium=distribute.pc_relevant.none-task-blog-baidujs-2
# 入门: https://blog.csdn.net/halcyonbaby/article/details/104704079
# 入门: https://blog.csdn.net/m0_46603114/category_9820181.html
# 进阶: https://zhuanlan.zhihu.com/c_1189276087837011968
# 优化: https://blog.csdn.net/weixin_42232219/article/details/92115226?utm_medium=distribute.pc_relevant.none-task-blog-BlogCommendFromMachineLearnPai2-6.nonecase&depth_1-utm_source=distribute.pc_relevant.none-task-blog-BlogCommendFromMachineLearnPai2-6.nonecase

# https://zhuanlan.zhihu.com/p/64019862
# 画图: https://cloud.tencent.com/developer/article/1388001
# https://pyecharts.org/#/zh-cn/assets_host
# https://github.com/shidenggui/easytrader/blob/master/docs/usage.md
# https://zhuanlan.zhihu.com/c_1189276087837011968
import utils
import backtrader as bt
import pandas as pd
import time
from datetime import datetime, timedelta

from strategys import SchedStrategy, MomTestStrategy
from analyzers import AccountValue
import models


# %%


# %%


# def start():
start = '2017-05-13'
# start = None
# code = '159928'
code = '159941'
# code = '163407'
# code = '513050'
db = models.DB()
dbname = 'k_data'
wheres = [
    {'k': 'code', 'v': code},
    {'k': 'datetime', 'v': start, 'op': '>='},
]
orderby = 'timestamp asc'
df = db.select(dbname, wheres=wheres, orderby=orderby)
df.index = df['datetime']
df['code'] = df['code'].apply(lambda x: int(x))
sdt = df.index[0]
# 日期修正
start = '{0}-{1}-{2}'.format(sdt.year, sdt.month, sdt.day)
live = False
if live:
    dbname = 'k_1min_data'
    data = models.PGData(dbname)
else:
    data = models.PandasData(dataname=df)
cerebro = bt.Cerebro(
    live=live,  # 是否为实盘
    tradehistory=True,  # 记录交易开启
)
# 将数据传入回测系统
cerebro.adddata(data)
# 将交易策略加载到回测系统中
cerebro.addstrategy(
    SchedStrategy,
    minrise=-0.25,
    maxrise=3.25,
    buysize=100,
    sellsize=100,
    tradelog=True,
    orderlog=False,
    doprint=True,
    perrise=0.25,
)
# 设置初始资本为10,000
startcash = 20000
cerebro.broker.setcash(startcash)
# 设置交易手续费为0.01%
cerebro.broker.setcommission(commission=0.0001)
# 运行回测系统
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

if not live:
    # 添加收益分析指标
    cerebro.addanalyzer(AccountValue, _name='AccountValue')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='SharpeRatio',
                        riskfreerate=0.00, stddev_sample=True, annualize=True)
    cerebro.addanalyzer(bt.analyzers.Returns, _name="Returns")
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='AnnualReturn')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DW')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='TradeAnalyzer')
    # bt.analyzers.Order

strats = cerebro.run()
strat = strats[0]

if not live:
    # 获取指标数值
    # pyfolio: https://my.oschina.net/u/3949465/blog/3212451
    finalvalue = cerebro.broker.getvalue()
    totalreturn = finalvalue - startcash
    availablevalue = cerebro.broker.getcash()
    sharperatio = strat.analyzers.SharpeRatio.get_analysis()['sharperatio']
    maxdrowdown = strat.analyzers.DW.get_analysis()['max']['drawdown']
    maxdrowdownmoney = strat.analyzers.DW.get_analysis()['max']['moneydown']
    # tradeinfo = strat.analyzers.TradeAnalyzer.get_analysis()

    accountinfo = strat.analyzers.AccountValue.get_analysis()
    annualreturninfo = strat.analyzers.AnnualReturn.get_analysis()
    returnsinfo = strat.analyzers.Returns.get_analysis()
    returninfo = {'startcash': startcash, 'finalvalue': finalvalue, 'availablevalue': availablevalue, 'totalreturn': totalreturn,
                  'sharperatio': sharperatio, 'maxdrowdown': maxdrowdown, 'maxdrowdownmoney': maxdrowdownmoney,
                  'tradeinfo': ''}

    startclose = df.values[0][2]
    endclose = df.values[-1][2]
    riseper = (endclose - startclose) / startclose
    strategyriseper = (finalvalue - startcash) / startcash
    msg = '{0}, start:{3}, 涨幅:{1:.3f}, 策略涨幅:{2:.3f}'.format(
        code, riseper * 100, strategyriseper * 100, start)

    # print(returnsinfo)
    print(returninfo)
    print('end...')
    print(msg)

# cerebro.plot(iplot=False, dpi=300, width=32, height=18)


# %%
# %%

# data = utils.getstratdata(strat, accountinfo)
# utils.plot_strategy(
#     code,
#     start=start,
#     buy=data['buy'],
#     sell=data['sell'],
#     availablevalue=data['availablevalue'],
#     totalvalue=data['totalvalue'],
# )

# %%
# %%


def opt_strategy(code, start='', end='', startcash=20000, qts=500, com=0.001, retry=0):
    # 创建主控制器
    cerebro = bt.Cerebro(live=False)
    # 获取数据
    # df = utils.get_ts_data(code, start=start, end=end, freq='d')
    db = models.DB()
    dbname = 'k_data'
    wheres = [
        {'k': 'code', 'v': code, 'op': '='},
        {'k': 'datetime', 'v': start, 'op': '>='},
    ]
    orderby = 'timestamp asc'
    df = db.select(dbname, wheres=wheres, orderby=orderby)
    if df.empty:
        retry += 1
        if retry < 3:
            time.sleep(3)
            return opt_strategy(code, start, end, startcash, qts, com, retry)
    df.index = df['datetime']
    sdt = df.index[0]
    # 日期修正
    sdt = df['datetime'][0]
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
        # SchedStrategy,
        MomTestStrategy,
        # minrise=utils.gen_minrises(),
        # maxrise=utils.gen_maxrises(),
        maxrise=2.5,
        minrise=-0.75,
        # maxrise=[2.5, 2.75],
        buysize=200,
        sellsize=200,
        perrise=[0.25, 0.5, 0.75, 0.95],
        # mtmperiod=range(5, 11),
        # mamtmperiod=range(20, 31),
        # petype=['', 'pe', 'pe_ttm', 'pb'],
        # buysize=range(100, 400, 100),
        # sellsize=range(100, 400, 100),
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
# codes = ['159941', '159928', '513500', '513050',
#          '512760', '512170', '163407', '163402', '166001']

# codes = ['512170', '159928', '512760', '513050', '163407']
# codes = ['159928']

# codes = utils.get_all_etf()

# code = '512170'
# code = '166001'
# opt_strategy(code)


def get_dates():
    # 多周期,半年,一年,两年...
    dates = []
    now = datetime.now()
    half_date = utils.get_datetime_date(now + timedelta(days=-182))
    dates.append(half_date)
    for _ in range(7):
        now += timedelta(days=-365)
        date = utils.get_datetime_date(now)
        dates.append(date)
    return dates

# print(dates)


# for code in codes:
#     for date in dates:
#         try:
#             opt_strategy(code, start=date)
#         except Exception as ex:
#             time.sleep(60)
#             print(ex)

# %%


# %%


# def code_to_symbol(code):
#     return 'sh.%s' % code if code[:1] in ['5', '6', '9'] or code[:2] in ['11', '13'] else 'sz.%s' % code
