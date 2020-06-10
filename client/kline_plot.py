# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%

# https://zhuanlan.zhihu.com/p/64019862
# 画图: https://cloud.tencent.com/developer/article/1388001
# https://pyecharts.org/#/zh-cn/assets_host
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from pyecharts.charts import Kline, Line, Bar, Grid
from typing import List, Union
import requests
from backtrader import Analyzer
from collections import OrderedDict
import backtrader as bt
import backtrader.analyzers as btanalyzers
import tushare as ts
import pandas as pd
import talib as ta

from pyecharts.charts import Kline, Bar, Line, EffectScatter, Grid, Scatter

from pyecharts import options as opts


import datetime
import time
import math

# %%
# 处理pyecharts在notebook显示空白
from pyecharts.globals import CurrentConfig, OnlineHostType, SymbolType
CurrentConfig.ONLINE_HOST = OnlineHostType.NOTEBOOK_HOST


# %%

# 从tushare取数据,默认d,5min,60min
def get_data_ts(code, start=None, end=None, freq='d'):
    df = ts.bar(code, conn=ts.get_apis(), start_date=start,
                end_date=end, freq=freq)
    try:
        df['openinterest'] = 0
    except TypeError as ex:
        print(ex)
        return get_data_ts(code, start, end, freq)
    print(df.head())
    df.rename(columns={'vol': 'volume'}, inplace=True)
    df = df.sort_index()
    df = df[['open', 'high', 'low', 'close', 'volume', 'openinterest']]
    return df


# %%


def draw_charts(code, start=None, end=None):
    df = get_data_ts(code, start=start, end=end)
    # info = ts.get_fund_info(code)
    # title = info.values[0][1]
    df['datetime'] = df.index
    date = df["datetime"].apply(lambda x: str(x)).tolist()
    # volume = df["volume"].apply(lambda x: int(x)).tolist()
    kvalue = df.apply(lambda record: [
        record['open'], record['close'], record['low'], record['high']], axis=1).tolist()
    # close = df['close']
    # slideroffset = 0
    print(date)
    print(11111111111111111)
    print(kvalue)
    # if len(date) > 150:
    #     slideroffset = math.ceil(100 - 100/(len(date)/150))
    kline = (
        Kline()
        .add_xaxis(xaxis_data=date)
        .add_yaxis(
            series_name="Dow-Jones index",
            y_axis=kvalue,
        )
        .set_global_opts(
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=True,
                    # xaxis_index=[0, 1],
                    type_="slider",
                    pos_top="85%",
                    range_start=98,
                    range_end=100,
                ),
            ],
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                link=[{"xAxisIndex": "all"}],
                label=opts.LabelOpts(background_color="#777"),
            ),
        )
    )

    print(kline.render("professional_kline_brush3.html"))


if __name__ == "__main__":
    code = '159928'
    start = '2020-03-22'
    draw_charts(code, start=start)


# %%

def plot_strategy(code, start=None, end=None, buy=None, sell=None, availablecash=None, totalvalue=None):
    df = get_data_ts(code, start=start, end=end)
    info = ts.get_fund_info(code)
    title = info.values[0][1]
    df['datetime'] = df.index
    date = df["datetime"].apply(lambda x: x.strftime('%Y-%m-%d')).tolist()
    volume = df["volume"].apply(lambda x: int(x)).tolist()
    kvalue = df.apply(lambda record: [
        record['open'], record['close'], record['low'], record['high']], axis=1).tolist()
    close = df['close']
    slideroffset = 0
    print(df)
    if len(date) > 150:
        slideroffset = math.ceil(100 - 100/(len(date)/150))

    kline = (
        Kline()
        .add_xaxis(xaxis_data=date)
        .add_yaxis(
            series_name="Dow-Jones index",
            y_axis=kvalue,
        )
        .set_global_opts(
            legend_opts=opts.LegendOpts(
                is_show=False, pos_bottom=10, pos_left="center"
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=False,
                    type_="inside",
                    xaxis_index=[0, 1],
                    range_start=98,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=True,
                    xaxis_index=[0, 1],
                    type_="slider",
                    pos_top="85%",
                    range_start=98,
                    range_end=100,
                ),
            ],
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitarea_opts=opts.SplitAreaOpts(
                    is_show=True, areastyle_opts=opts.AreaStyleOpts(opacity=1)
                ),
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000"),
            ),
            visualmap_opts=opts.VisualMapOpts(
                is_show=False,
                dimension=2,
                series_index=5,
                is_piecewise=True,
                pieces=[
                    {"value": 1, "color": "#00da3c"},
                    {"value": -1, "color": "#ec0000"},
                ],
            ),
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                link=[{"xAxisIndex": "all"}],
                label=opts.LabelOpts(background_color="#777"),
            ),
            brush_opts=opts.BrushOpts(
                x_axis_index="all",
                brush_link="all",
                out_of_brush={"colorAlpha": 0.1},
                brush_type="lineX",
            ),
        )
    )

    bar = (
        Bar()
        .add_xaxis(xaxis_data=date)
        .add_yaxis(
            series_name="Volume",
            yaxis_data=availablecash,
            xaxis_index=1,
            yaxis_index=1,
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                is_scale=True,
                grid_index=1,
                boundary_gap=False,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                axislabel_opts=opts.LabelOpts(is_show=False),
                split_number=20,
                min_="dataMin",
                max_="dataMax",
            ),
            yaxis_opts=opts.AxisOpts(
                grid_index=1,
                is_scale=True,
                split_number=2,
                axislabel_opts=opts.LabelOpts(is_show=False),
                axisline_opts=opts.AxisLineOpts(is_show=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
    )


    # overlap_kline_line = kline.overlap(line)

    # Grid Overlap + Bar
    grid_chart = Grid(
        init_opts=opts.InitOpts(
            width="1000px",
            height="800px",
            animation_opts=opts.AnimationOpts(animation=False),
        )
    )
    grid_chart.add(
        kline,
        grid_opts=opts.GridOpts(pos_left="10%", pos_right="8%", height="50%"),
    )

    grid_chart.add(
        bar,
        grid_opts=opts.GridOpts(
            pos_left="10%", pos_right="8%", pos_top="63%", height="16%"
        ),
    )

    print(grid_chart.render("{0}2.html".format(code)))


# code = '159928'
# start = '2020-02-22'
availablecash = strat.account.get('availablecash', {})
print(availablecash.items())
availablecash = list(availablecash.values())
plot_strategy(code, start=start, availablecash=availablecash)


# %%
# http://gallery.pyecharts.org/#/Candlestick/professional_kline_chart
# 画图
def kline_plot(code, start=None, end=None, buy=None, sell=None, availablecash=None, totalvalue=None):
    df = get_data_ts(code, start=start, end=end)
    info = ts.get_fund_info(code)
    title = info.values[0][1]
    df['datetime'] = df.index
    date = df["datetime"].apply(lambda x: x.strftime('%Y-%m-%d')).tolist()
    print(date.head(10))
    volume = df["volume"].apply(lambda x: int(x)).tolist()
    kvalue = df.apply(lambda record: [
        record['open'], record['close'], record['low'], record['high']], axis=1).tolist()
    close = df['close']
    slideroffset = 0
    print(len(date))
    if len(date) > 150:
        slideroffset = math.ceil(100 - 100/(len(date)/150))
    # k线
    kline = (
        Kline()
        .add_xaxis(date)
        .add_yaxis(
            code,
            kvalue,
            markline_opts=opts.MarkLineOpts(
                data=[opts.MarkLineItem(type_="max", value_dim="close")]
            ),
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(is_scale=True),
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitarea_opts=opts.SplitAreaOpts(
                    is_show=True,
                    areastyle_opts=opts.AreaStyleOpts(opacity=1)
                ),
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=True,
                    xaxis_index=[0, 1],
                    type_="slider",
                    pos_top="85%",
                    range_start=slideroffset,
                    range_end=100,
                ),
            ],
            title_opts=opts.TitleOpts(title="{0}: 行情走势图".format(title)),
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                link=[{"xAxisIndex": "all"}],
                label=opts.LabelOpts(background_color="#777"),
            ),
        )
    )

    # 均线
    # periods = [5, 10, 20]
    periods = [5]
    line = Line()
    line.add_xaxis(date)
    for period in periods:
        ma = ta.MA(close, timeperiod=period)
        ma = ma.apply(lambda x: '%.3f' % x).tolist()
        msg = 'MA{0}'.format(period)
        (line
         .set_global_opts(title_opts=msg)
         .add_yaxis(msg, ma, is_symbol_show=False, label_opts=opts.LabelOpts(is_show=False), is_smooth=True,
                    linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
                    is_hover_animation=True,)
         .set_global_opts(xaxis_opts=opts.AxisOpts(type_="category"))
         )
    # 买入,卖出信号
    es = EffectScatter()
    if buy:
        buyy = []
        for x in buy:
            i = date.index(x)
            y = df['close'].iloc[i]
            buyy.append(y)
        es.add_xaxis(buy)
        es.add_yaxis('买入', buyy, symbol=SymbolType.TRIANGLE)
    if sell:
        selly = []
        for x in sell:
            i = date.index(x)
            y = df['high'].iloc[i]
            selly.append(y)
        es.add_xaxis(sell)
        es.add_yaxis('卖出', selly)

    if buy or sell:
        kline.overlap(es)

    grid_chart = Grid(
        init_opts=opts.InitOpts(
            width="1250",
            height="750px",
            animation_opts=opts.AnimationOpts(animation=False),
        )
    )

    kline.overlap(line)
    grid_chart.add(
        kline,
        grid_opts=opts.GridOpts(
            pos_left="10%", pos_right="8%", height="50%"),
    )
    # if availablecash:
    #     msg = '可用余额'
    #     availablecashgrph = (
    #         Line()
    #         .add_xaxis(date)
    #         .add_yaxis(msg, availablecash, is_symbol_show=False, label_opts=opts.LabelOpts(is_show=False), is_smooth=True,
    #                    linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
    #                    is_hover_animation=True,)
    #         .set_global_opts(title_opts=msg, xaxis_opts=opts.AxisOpts(type_="category"))
    #     )
    #     grid_chart.add(
    #         availablecashgrph,
    #         grid_opts=opts.GridOpts(
    #             pos_left="10%", pos_right="8%", pos_top="60%", height="8%"
    #         ),
    #     )
    # if totalvalue:
    #     pos_top = '65%'
    #     if availablecash:
    #         pos_top = '70%'
    #     msg = '账户余额'
    #     totalvaluegrph = (
    #         Line()
    #         .add_xaxis(date)
    #         .add_yaxis(msg, totalvalue, is_symbol_show=False, label_opts=opts.LabelOpts(is_show=False), is_smooth=True,
    #                    linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
    #                    is_hover_animation=True,)
    #         .set_global_opts(title_opts=msg, xaxis_opts=opts.AxisOpts(type_="category"))
    #     )

    # grid_chart.add(
    #     totalvaluegrph,
    #     grid_opts=opts.GridOpts(
    #         pos_left="10%", pos_right="8%", pos_top=pos_top, height="8%"
    #     ),
    # )
    # print(grid_chart.render('{0}.html'.format(code)))
    print(kline.render('{0}.html'.format(code)))


# %%


class TotalValue(Analyzer):
    params = ()

    def start(self):
        super(TotalValue, self).start()
        self.rets = OrderedDict()

    def next(self):
        super(TotalValue, self).next()
        self.rets[self.datas[0].datetime.datetime(
        )] = self.strategy.broker.getvalue()

    def get_analysis(self):
        return self.rets


# %%
# TODO
# 5分钟检查,未检查今日已购买
# 买入数量优化
# minrise,maxrise参数精细化
a = 0


class FixedInvestStrategy(bt.Strategy):
    params = (
        ('printlog', False),
        ('doprint', False),
        ('minrise', -2.85),
        ('maxrise', 3.75),
        ('buysize', 300),
        ('sellsize', 300),
        ('perrise', 0.95),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.orders = {}
        self.account = {}

    def log(self, txt, dt=None):
        ''' 策略的日志函数'''
        if self.params.printlog:
            dt = dt or self.get_datetime()
            print('%s, %s' % (dt.isoformat(), txt))

    def next(self):
        offset = self.get_offset()
        try:
            predataclose = self.dataclose[-offset]
            predatetime = self.datetime.datetime(-offset)
            dt = self.get_datetime()
            if predatetime.day == dt.day:
                msg = '没有前一日收盘价,跳过'
                # self.log(msg)
                return
        except IndexError as ex:
            return
        except Exception as ex:
            self.log(ex)
            return
        pricerise = ((self.dataclose[0] -
                      predataclose) / self.dataclose[0]) * 100
        msg = '开盘价:%.3f, 收盘价:%.3f, 上一日收盘价:%.3f, 涨幅:%.3f' % (
            self.dataopen[0], self.dataclose[0], predataclose, pricerise)
        dt = self.get_datetime()
        key = dt.strftime('%Y-%m-%d')
        availablecash = self.account.get('availablecash', {})
        availablecash[key] = int(self.broker.get_cash())
        self.account['availablecash'] = availablecash
        totalvalue = self.account.get('totalvalue', {})
        totalvalue[key] = int(self.broker.getvalue())
        self.account['totalvalue'] = totalvalue
        if (9 < dt.hour < 14) or (dt.hour >= 14 and dt.minute < 45):
            # 盘中检查
            if pricerise < self.params.minrise:
                # 检查今日是否已购买
                buykey = '{0}:{1}'.format(key, 'buy')
                buycount = self.orders.get(buykey, 0)
                if buycount < 1:
                    tradesize = self.set_trade_size(pricerise)
                    # buysize = self.params.buysize
                    self.log('BUY CREATE, %s, 买入: %.1f股' % (msg, tradesize))
                    self.order = self.buy(size=tradesize)
                    buycount += 1
                    self.orders[buykey] = buycount
            elif pricerise > self.params.maxrise:
                sellkey = '{0}:{1}'.format(key, 'sell')
                sellcount = self.orders.get(sellkey, 0)
                if sellcount < 1:
                    tradesize = self.set_trade_size(pricerise)
                    self.log('SELL CREATE, %s, 卖出: %.1f股' % (msg, tradesize))
                    self.order = self.sell(size=tradesize)
                    sellcount += 1
                    self.orders[sellkey] = sellcount
        elif (14 <= dt.hour < 15) and (45 < dt.minute < 55):
            # 盘尾加仓,类似定投,积累足够筹码
            if pricerise < -self.params.perrise:
                buykey = '{0}:{1}'.format(key, 'buy')
                buycount = self.orders.get(buykey, 0)
                if buycount < 2:
                    tradesize = self.set_trade_size(pricerise)
                    # buysize = self.params.buysize
                    self.log('BUY CREATE, %s, 买入: %.1f股' % (msg, tradesize))
                    self.order = self.buy(size=tradesize)
                    buycount += 1
                    self.orders[buykey] = buycount

    def set_trade_size(self, pricerise):
        buytimes = abs(pricerise / self.params.perrise)
        buysize = math.ceil(self.params.buysize * buytimes / 100) * 100
        return buysize

    def get_datetime(self):
        return self.datetime.datetime(0)

    def get_offset(self):
        dt = self.get_datetime()
        dtcompare = datetime.datetime(dt.year, dt.month, dt.day, 9, 30)
        offsetseconds = (dt - dtcompare).total_seconds()
        offset = int(offsetseconds / 60 / 5)
        return offset
    # 回测结束后输出结果（可省略，默认输出结果）

    def stop(self):
        if self.params.doprint:
            print(self.broker.get_cash())
            msg = 'minrise: %.2f, maxrise: %.2f, buysize: %s, sellsize: %s, 期末总资金: %.2f' % (
                self.params.minrise, self.params.maxrise, self.params.buysize, self.params.sellsize, self.broker.getvalue())
            data = {
                'minrise': self.params.minrise,
                'maxrise': self.params.maxrise,
                'buysize': self.params.buysize,
                'sellsize': self.params.sellsize,
                'value': self.broker.getvalue(),
            }
            print(msg)

# %%


# def start():
start = '2019-06-04'
code = '159928'
# code = '512760'
# 获取5分钟K线图,获取不到全部数据,更换baostock
df = get_data_ts(code, start=start, freq='5min')
print(df.head())
print(df.tail())
data = bt.feeds.PandasData(dataname=df)
cerebro = bt.Cerebro()
# 将数据传入回测系统
cerebro.adddata(data)
# 将交易策略加载到回测系统中
cerebro.addstrategy(
    FixedInvestStrategy,
    minrise=-4,
    maxrise=4,
    buysize=400,
    sellsize=400,
    printlog=True,
)
# 设置初始资本为10,000
startcash = 100000
cerebro.broker.setcash(startcash)
# 设置交易手续费为0.3%
cerebro.broker.setcommission(commission=0.001)
# 运行回测系统
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

# 收益分析指标
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='SharpeRatio',
                    riskfreerate=0.00, stddev_sample=True, annualize=True)
cerebro.addanalyzer(bt.analyzers.Returns, _name="Returns")
cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='AnnualReturn')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DW')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='TradeAnalyzer')

strats = cerebro.run()
strat = strats[0]

finalvalue = cerebro.broker.getvalue()
totalreturn = startcash - finalvalue
sharperatio = strat.analyzers.SharpeRatio.get_analysis()['sharperatio']
maxdrowdown = strat.analyzers.DW.get_analysis()['max']['drawdown']
maxdrowdownmoney = strat.analyzers.DW.get_analysis()['max']['moneydown']
tradeinfo = strat.analyzers.TradeAnalyzer.get_analysis()
returninfo = {'startcash': startcash, 'finalvalue': finalvalue, 'totalreturn': totalreturn,
              'sharperatio': sharperatio, 'maxdrowdown': maxdrowdown, 'maxdrowdownmoney': maxdrowdownmoney,
              'tradeinfo': tradeinfo}

print(returninfo)

buy = []
sell = []
for order in strat.orders:
    date, tradetype = order.split(':')[0], order.split(':')[1]
    if tradetype == 'buy':
        buy.append(date)
    else:
        sell.append(date)

# code = '159928'
# code = '000725'
# %%


availablecash = strat.account.get('availablecash', {})
totalvalue = strat.account.get('totalvalue', {})
availablecash = list(availablecash.values())
totalvalue = list(totalvalue.values())
print(len(availablecash))
kline_plot(
    code,
    start=start,
    # buy=buy,
    # sell=sell,
    # availablecash=availablecash,
    # totalvalue=totalvalue,
)


# %%


# %%

def gen_rises():
    rises = []
    for x in range(-500, 0, 25):
        rises.append(x / 100)
    return rises


def opt_strategy(code, start='', end='', startcash=100000, qts=500, com=0.001):
    # 创建主控制器
    cerebro = bt.Cerebro()
    # 导入策略参数寻优
    cerebro.optstrategy(
        FixedInvestStrategy,
        minrise=range(-5, 0),
        maxrise=range(1, 5),
        # buysize=range(300, 500, 100),
        # sellsize=range(500, 700, 100),
        printlog=False,
        doprint=True
    )
    # 获取数据
    if 'df' not in locals():
        df = get_data_ts(code, start=start, end=end, freq='5min')
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


start = '2019-12-04'
code = '159928'
# code = '512170'
# code = '512760'

opt_strategy(code, start)

# %%


# %%


def code_to_symbol(code):
    return 'sh.%s' % code if code[:1] in ['5', '6', '9'] or code[:2] in ['11', '13'] else 'sz.%s' % code
