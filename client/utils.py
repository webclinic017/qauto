# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
from pyecharts.globals import CurrentConfig, OnlineHostType, SymbolType
import math
import datetime
import time
import os
from pyecharts import options as opts
from pyecharts.charts import Kline, Bar, Line, EffectScatter, Grid, Scatter
import talib as ta
import pandas as pd
import tushare as ts
from bs4 import BeautifulSoup as bs
import requests
import gevent
from gevent.pool import Pool
import gevent.monkey
from greenlet import greenlet
gevent.monkey.patch_all(select=False)


# %%
# 处理pyecharts在notebook显示空白
CurrentConfig.ONLINE_HOST = OnlineHostType.NOTEBOOK_HOST

htmlpath = 'html'
csvpath = 'csv'
dirs = [htmlpath, csvpath]
for fdir in dirs:
    if not os.path.exists(fdir):
        os.makedirs(fdir)


# %%
# 从tushare取数据,默认d,5min,60min
def get_data_ts(code, start=None, end=None, freq='d', retry=0):
    print(code)
    df = ts.bar(code, conn=ts.get_apis(), start_date=start,
                end_date=end, freq=freq)
    try:
        if df.empty:
            return pd.DataFrame()
    except Exception as ex:
        print(ex)
        return pd.DataFrame()
    # print(df.head())
    # df['datetime'] = df.index
    df.rename(columns={'vol': 'volume'}, inplace=True)
    df = df.sort_index()
    # df = df[['open', 'high', 'low', 'close', 'volume', 'openinterest']]
    return df


def get_code_cn(code):
    info = ts.get_fund_info(code)
    code_cn = info.values[0][1]
    return code_cn


def get_float(f, n=3):
    fstr = format(f, '.%sf' % n)
    return float(fstr)


# %%
# 获取所有场内基金
def get_all_etf():
    url = 'https://www.joinquant.com/help/api/getContent?name=fund'
    res = requests.get(url)
    data = res.json().get('data', '')
    soup = bs(data)
    items = soup.find_all('tbody')[4: 6]
    codes = []
    for x in items:
        for y in x.find_all('tr'):
            z = y.find_all('td')
            if len(z) == 0:
                continue
            item = z[0].get_text()
            code = item.split('.')[0]
            codes.append(code)
    return codes

# %%
# 获取策略回测数据


def getstratdata(strat, accountinfo):
    buy = []
    sell = []
    for order in strat.orders:
        date, tradetype = order.split(':')[0], order.split(':')[1]
        if tradetype == 'buy':
            buy.append(date)
        else:
            sell.append(date)
    for k, v in accountinfo.items():
        if k == 'totalvalue':
            totalvalue = v.values()
        else:
            availablevalue = v.values()

    return {
        'sell': sell,
        'buy': buy,
        'availablevalue': availablevalue,
        'totalvalue': totalvalue,
    }

# %%
# 检查优化策略结果


def check_opt_result():
    now = datetime.datetime.now()
    results = []
    for fn in os.listdir('.'):
        if fn.endswith('.csv'):
            y = fn.split('-')
            dt = datetime.datetime(int(y[1]), int(y[2]), int(y[3][:-4]))
            x = (now - dt).days / 365
            df = pd.DataFrame(pd.read_csv(fn))
            df = df.sort_values(by='value')
            totalvalue = df.values[-1][1] / x
            code = y[0]
            codecn = get_code_cn(code)
            msg = '{0},{3}, return:{2}, start:{1}, {4}'.format(
                y[0], str(dt), get_float(totalvalue, 3), codecn, df.values[-1].tolist())
            print(msg)
            results.append(msg)
    return results


def gen_minrises():
    rises = []
    for x in range(-500, 0, 25):
        rises.append(x / 100)
    return rises


def gen_maxrises():
    rises = []
    for x in range(75, 500, 25):
        rises.append(x / 100)
    return rises

# %%
# http://gallery.pyecharts.org/#/Candlestick/professional_kline_chart
# 画图


def plot_strategy(code, start=None, end=None, buy=None, sell=None, availablevalue=None, totalvalue=None):
    df = get_data_ts(code, start=start, end=end)
    title = get_code_cn(code)
    df['datetime'] = df.index
    date = df["datetime"].apply(lambda x: x.strftime('%Y-%m-%d')).tolist()
    # volume = df["volume"].apply(lambda x: int(x)).tolist()
    kvalue = df.apply(lambda record: [
        record['open'], record['close'], record['low'], record['high']], axis=1).tolist()
    close = df['close']
    slideroffset = 0
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
                    is_show=False,
                    type_="inside",
                    xaxis_index=[0, 1],
                    range_start=slideroffset,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=True,
                    xaxis_index=[0, 1],
                    type_="slider",
                    pos_top="80%",
                    range_start=slideroffset,
                    range_end=100,
                ),

            ],
            title_opts=opts.TitleOpts(title="{0}: 行情走势图".format(title)),
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                link=[{"xAxisIndex": "all"}],
                label=opts.LabelOpts(background_color="#777"),
                # label=opts.LabelOpts(formatter='{value}'),
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
    es.add_xaxis(date)
    if buy:
        buyy = []
        for x in buy:
            if x not in date:
                continue
            i = date.index(x)
            y = df['close'].iloc[i]
            buyy.append(y)
        es.add_xaxis(buy)
        es.add_yaxis('买入', buyy, symbol=SymbolType.TRIANGLE)
    if sell:
        selly = []
        for x in sell:
            if x not in date:
                continue
            i = date.index(x)
            y = df['close'].iloc[i]
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
            pos_left="10%", pos_right="8%", pos_top='25%', height="50%"),
    )
    accountgrph = Line()
    accountgrph.add_xaxis(date)
    if availablevalue:
        msg = '可用余额'
        (
            accountgrph
            .set_global_opts(title_opts='')
            .add_yaxis(msg, availablevalue, is_symbol_show=False, label_opts=opts.LabelOpts(is_show=False), is_smooth=True,
                       linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
                       is_hover_animation=True,)
            .set_global_opts(xaxis_opts=opts.AxisOpts(type_="category"))
        )
    if totalvalue:
        msg = '账户总额'
        (
            accountgrph
            .set_global_opts(title_opts='')
            .add_yaxis(msg, totalvalue, is_symbol_show=False, label_opts=opts.LabelOpts(is_show=False), is_smooth=True,
                       linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
                       is_hover_animation=True,)
            .set_global_opts(xaxis_opts=opts.AxisOpts(type_="category"))
        )
    if accountgrph:
        grid_chart.add(
            accountgrph,
            grid_opts=opts.GridOpts(
                pos_left="10%", pos_right="8%", height="12%"
            ),
        )
    print(grid_chart.render('{1}/{0}.html'.format(code, htmlpath)))
    # print(kline.render('{0}.html'.format(code)))


def update_daily_per_code(code, start='', con=None, db_name=''):
    print('start...{0},date...{1}'.format(code, start))
    data = get_data_ts(code, start=start)
    if data.empty:
        print('{0},未获得数据'.format(code))
        return
    con.update(data, db_name)


def update_daily(start=''):
    import models
    con = models.DB()
    db_name = 'k_data'
    now = datetime.datetime.now()
    if not start:
        start = '{0}-{1}-{2}'.format(now.year, now.month, now.day)
    codes = get_all_etf()
    print('开始...')
    async_tasks(update_daily_per_code, codes,
                start=start, con=con, db_name=db_name)
    print('end...')

# %%


def fetch(i, start=0):
    url = 'http://httpbin.org/get'
    resp = requests.get(url)
    print(len(resp.text), i, start)  # 返回结果长度，以及序号


def async_tasks(func, tasks, *args, **kw):
    pool = Pool(size=16)
    greenlets = []
    for task in tasks:
        greenlets.append(
            pool.spawn(func, task, *args, **kw)
        )
    gevent.joinall(greenlets)


# %%
if __name__ == "__main__":
    st = int(time.time())
    update_daily()
    end = int(time.time())
    print((end - st) / 60)

    # %%
