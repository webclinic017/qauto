# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import json
import models
import math
from datetime import datetime, timedelta
import time
import os
import sys

import asyncio

from pprint import pprint
import pyecharts.options as opts
from pyecharts.globals import CurrentConfig, OnlineHostType, SymbolType
from pyecharts import options as opts
from pyecharts.charts import Kline, Bar, Line, EffectScatter, Grid, Scatter
# import talib as ta
import pandas as pd
import tushare as ts
# import akshare as ak
import backtrader as bt
from bs4 import BeautifulSoup as bs
import requests
# import gevent
# from gevent.pool import Pool
# import gevent.monkey
from sklearn import svm
import numpy as np
from analyzers import AccountValue

import constant
import remoteclient


# %%
# 处理pyecharts在notebook显示空白
CurrentConfig.ONLINE_HOST = OnlineHostType.NOTEBOOK_HOST

true = True
false = False

basedir = '/data/data/com.termux/files/home/qauto'
serverdir = '{}/server'.format(basedir)
clientdir = '{}/client'.format(basedir)
if sys.platform == 'linux':
    os.chdir(serverdir)

htmlpath = 'html'
csvpath = 'csv'
dirs = [htmlpath, csvpath]
for fdir in dirs:
    if not os.path.exists(fdir):
        os.makedirs(fdir)

global_config = {}

# gevent.monkey.patch_all(select=false)

# %%
# https://www.akshare.xyz/zh_CN/latest/data/futures/futures.html?highlight=%E6%9C%9F%E8%B4%A7#id35
# 股指期货: http://data.10jqka.com.cn/gzqh/index/instrumentId/IF2007/
# http://www.cffex.com.cn/


def get_all_futures():
    jyfm_exchange_symbol_dict = ak.jyfm_exchange_symbol_dict()
    pprint(jyfm_exchange_symbol_dict)


def get_ak_data(symbol, start='', end=''):
    # temp_url = ak.futures_global_commodity_name_url_map(sector="金属")
    if not end:
        end = get_datetime_date(flag='/')
    if not start:
        # start = '2000/06/22'
        start = '2017/06/22'
    df = ak.get_sector_futures(
        sector="金属", symbol=symbol, start_date=start, end_date=end)
    df['datetime'] = df.index
    columns = {
        '开盘': 'open',
        '收盘': 'close',
        '高': 'high',
        '低': 'low',
        '交易量': 'volume',
        '涨跌幅': 'p_change',
    }
    for k, v in columns.items():
        df.rename(columns={k: v}, inplace=true)
    return df


# 从tushare取数据,默认d,5min,60min
# http://tushare.org/trading.html#id2
# https://www.yisu.com/zixun/14379.html
def get_ts_data(code, start=None, end=None, freq='D', retry=0, _type='fund'):
    # ts.get_k_data
    # ts.get_hist_data
    # ts.bar
    # ts.get_h_data
    # pro = ts.pro_api()
    # pro.query
    # pro.fund_daily
    # ts.pro_bar
    df = ts.bar(code, conn=ts.get_apis(), start_date=start,
                end_date=end, freq=freq)
    try:
        if df.empty:
            return pd.DataFrame()
    except Exception as ex:
        print(ex)
        retry += 1
        if retry < 3:
            print('get_ts_data 重试 {0} 次'.format(retry))
            time.sleep(1.25)
            return get_ts_data(code, start, end, freq, retry)
        else:
            return pd.DataFrame()
    now = datetime.now()
    if len(df) > 0 and is_trade_day() and now.hour < 17 and freq == 'D':
        df.drop(df.index[0], inplace=true)
    # print(df)
    df['datetime'] = df.index
    df['type'] = _type
    df['createdtime'] = int(now.timestamp())
    df.rename(columns={'vol': 'volume'}, inplace=true)
    df = df.sort_index()
    return df


def get_database_data(code, start='', end='', dbname='k_data', live=false):
    db = models.KDATA()
    wheres = [
        {'k': 'code', 'v': code, 'op': '='},
    ]
    if start:
        where = {'k': 'datetime', 'v': start, 'op': '>='}
        wheres.append(where)
    if end:
        if dbname != 'k_data':
            end = get_datetime_date(datetime.strptime(
                end, '%Y-%m-%d') + timedelta(days=1), flag='-')
        where = {'k': 'datetime', 'v': end, 'op': '<='}
        wheres.append(where)
    orderby = 'timestamp asc'
    df = db.select_data(dbname, wheres=wheres, orderby=orderby, live=live)
    if df.empty:
        return pd.DataFrame()
    df.index = df['datetime']
    if dbname == 'k_data':
        df['code'] = df['code'].apply(lambda x: int(x)*10)
    else:
        df['code'] = df['code'].apply(lambda x: int(x))
    return df


def get_future_database_data(code, start='', end=''):
    db = models.DB()
    dbname = 'future'
    wheres = [
        {'k': 'code', 'v': code, 'op': '='},
    ]
    if start:
        where = {'k': 'datetime', 'v': start, 'op': '>='}
        wheres.append(where)
    if end:
        where = {'k': 'datetime', 'v': end, 'op': '<='}
        wheres.append(where)
    orderby = 'datetime asc'
    df = db.select(dbname, wheres=wheres, orderby=orderby)
    if df.empty:
        return pd.DataFrame()
    df.index = df['datetime']
    # df['code'] = df['code'].apply(lambda x: int(x))
    return df


def get_code_cn(code):
    info = ts.get_fund_info(code)
    code_cn = info.values[0][1]
    return code_cn


def get_float(f, n=3):
    if not f:
        return 0.0
    fstr = format(f, '.%sf' % n)
    return float(fstr)


def addanalyzer(cerebro):
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='SharpeRatio',
                        riskfreerate=0.00, stddev_sample=true, annualize=true)
    cerebro.addanalyzer(bt.analyzers.Returns, _name="Returns")
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='AnnualReturn')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DW')

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='TradeAnalyzer')
    cerebro.addanalyzer(AccountValue, _name='AccountValue')
    # order记录
    # analyzers.transactions.get_analysis()
    cerebro.addanalyzer(bt.analyzers.Transactions, _name="transactions")


# %%
# 获取所有场内基金


def get_all_etf():
    url = 'https://www.joinquant.com/help/api/getContent?name=fund'
    res = requests.get(url)
    data = res.json().get('data', '')
    soup = bs(data, 'lxml')
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


def get_my_etf():
    codes = ['161716', '512170', '161226', '513050', '161005', '159941',
             '163402', '513500', '159928', '163407', '166001', '512760']
    # codes = ['163402', '166001', '161005']
    return codes

# 获取沪深300股票


def get_hs300():
    df = ts.get_hs300s()
    codes = df.code.to_list()
    return codes


def get_db_etf():
    dbname = 'fund_info'
    pk = 'code'
    mcodes = get_distinct_codes(dbname, pk)
    jcodes = get_all_etf()
    codes = list(set(mcodes).difference(set(jcodes)))
    return codes


def get_distinct_codes(table, pk, wheres=None):
    db = models.DB()
    codes = db.select_distinct(table, pk, wheres)
    return codes


def get_difference_codes(table, table2, pk):
    ggtcodes = get_distinct_codes(table, pk)
    kcodes = get_distinct_codes(table2, pk)
    codes = list(set(kcodes).difference(set(ggtcodes)))
    return codes

# %%
# 获取策略回测数据


def getstratdata(strat, accountinfo):
    buy = []
    sell = []
    # import ipdb; ipdb.set_trace()
    for order in strat._orders:
        datetime = order.data.num2date(order.dteos)
        date = get_datetime_date(datetime, flag='-')
        tradetype = order.__class__.__name__
        if tradetype == 'BuyOrder':
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
    # df = get_ts_data(code, start=start, end=end)
    df = get_database_data(code, start, end)
    # title = get_code_cn(code)
    title = ''
    # df['datetime'] = df.index
    # date = df["datetime"].apply(lambda x: ('%Y-%m-%d')).tolist()
    date = df.datetime.apply(lambda x: x.strftime('%Y-%m-%d')).tolist()
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
            xaxis_opts=opts.AxisOpts(is_scale=true),
            yaxis_opts=opts.AxisOpts(
                is_scale=true,
                splitarea_opts=opts.SplitAreaOpts(
                    is_show=true,
                    areastyle_opts=opts.AreaStyleOpts(opacity=1)
                ),
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=false,
                    type_="inside",
                    xaxis_index=[0, 1],
                    range_start=slideroffset,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=true,
                    xaxis_index=[0, 1],
                    type_="slider",
                    pos_top="80%",
                    range_start=slideroffset,
                    range_end=100,
                ),

            ],
            title_opts=opts.TitleOpts(title="{0}: 行情走势图".format(title)),
            axispointer_opts=opts.AxisPointerOpts(
                is_show=true,
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
         .add_yaxis(msg, ma, is_symbol_show=false, label_opts=opts.LabelOpts(is_show=false), is_smooth=true,
                    linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
                    is_hover_animation=true,)
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
            animation_opts=opts.AnimationOpts(animation=false),
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
        msg = ''
        (
            accountgrph
            .set_global_opts(title_opts='')
            .add_yaxis(msg, availablevalue, is_symbol_show=false, label_opts=opts.LabelOpts(is_show=false), is_smooth=true,
                       linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
                       is_hover_animation=true,)
            .set_global_opts(xaxis_opts=opts.AxisOpts(type_="category"))
        )
    if totalvalue:
        msg = ''
        (
            accountgrph
            .set_global_opts(title_opts='')
            .add_yaxis(msg, totalvalue, is_symbol_show=false, label_opts=opts.LabelOpts(is_show=false), is_smooth=true,
                       linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
                       is_hover_animation=true,)
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


# %%
def plot_account_value(strat):
    accountinfo = strat.analyzers.AccountValue.get_analysis()
    info = {}
    for k in accountinfo.keys():
        datay = [y for _, y in accountinfo[k].items()]
        info[k] = datay
    info['datax'] = [x for x, _ in accountinfo[k].items()]
    line = (
        Line()
        .add_xaxis(xaxis_data=info['datax'])
        .add_yaxis(
            series_name="账户余额",
            stack="总量",
            y_axis=info['totalvalue'],
            is_smooth=true,
            label_opts=opts.LabelOpts(is_show=false),
            areastyle_opts=opts.AreaStyleOpts(opacity=0.5),
            linestyle_opts=opts.LineStyleOpts(width=2),
            is_symbol_show=false,
            # markpoint_opts=opts.MarkPointOpts(
            #     data=[opts.MarkPointItem(type_="max")]),
        )
        .set_global_opts(
            tooltip_opts=opts.TooltipOpts(
                trigger="none", axis_pointer_type="cross"),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                axistick_opts=opts.AxisTickOpts(is_align_with_label=true),
                axisline_opts=opts.AxisLineOpts(
                    is_on_zero=false, linestyle_opts=opts.LineStyleOpts(
                        color="#d14a61")
                ),
            ),
            yaxis_opts=opts.AxisOpts(
                type_="value",
                splitline_opts=opts.SplitLineOpts(
                    is_show=true, linestyle_opts=opts.LineStyleOpts(opacity=1)
                ),
            ),
        )
    )
    grid_chart = Grid(
        init_opts=opts.InitOpts(
            width="1300",
            height="600px",
            animation_opts=opts.AnimationOpts(animation=false),
        )
    )
    grid_chart.add(
        line,
        grid_opts=opts.GridOpts(
            # pos_left="10%", pos_right="8%", height="12%"
        ),
    )
    print(grid_chart.render())

# %%
# 北向资金,跟着北向资金买股
# 东方财富: https://emdatah5.eastmoney.com/dc/hsgtn/index
# https://emdatah5.eastmoney.com/dc/hsgtn/topten?date=2020-06-22
# 同花顺: http://data.10jqka.com.cn/hgt/hgtb/
# backtrader组合策略: https://blog.csdn.net/ndhtou222/article/details/106416802


def ggt_top10(date):
    print('start...', date)
    stys = {
        'SGT': 'MarketType%3D3',
        'HGT': 'MarketType%3D1',
    }
    dfs = []
    for k, v in stys.items():
        url = 'https://emdatah5.eastmoney.com/dc/HSGTN/GetTenTopData?sty={}&filter=(DetailDate%3D%5E{}%5E)({})'.format(
            k, date, v)
        res = requests.get(url)
        content = str(res.content, encoding='utf8')
        content = json.loads(content[23:-2])
        df = pd.DataFrame(content)
        dfs.append(df)
    df = contact_pandas(dfs)
    if df.empty:
        return
    df['datetime'] = df['DetailDate'].apply(
        lambda x: datetime.strptime(x[:10], '%Y-%m-%d'))
    for x in ['Rank1']:
        df[x] = df[x].apply(lambda x: x.replace('-', ''))
    df['timestamp'] = df['datetime'].apply(
        lambda x: int(x.timestamp() - 8*60*60))
    for x in df.columns:
        y = x.lower()
        df.rename(columns={x: y}, inplace=true)
    dbname = 'ggt'
    db = models.DB()
    print(date, df)
    pks = ['code', 'markettype', 'timestamp']
    db.insert(df, dbname, pks)


def contact_pandas(dfs):
    for df in dfs:
        df.reset_index(drop=true, inplace=true)
    newdfs = pd.concat(dfs, axis=0, ignore_index=true)
    return newdfs


def update_k_1min_data(codes, db, dbname):
    df = ts.get_realtime_quotes(codes)
    try:
        if df.empty:
            return pd.DataFrame()
    except Exception as ex:
        print(ex)
        return pd.DataFrame()
    if df.empty:
        print('空数据')
        return
    df['datetime'] = df[['date', 'time']].apply(
        lambda x: datetime.strptime('{0} {1}'.format(
            x['date'], x['time']), '%Y-%m-%d %H:%M:%S'),
        axis=1,
    )
    df['timestamp'] = df['datetime'].apply(
        lambda x: int(x.timestamp()) - 8*60*60,
    )
    df.rename(columns={'vol': 'volume'}, inplace=true)
    fits = ['code', 'name', 'timestamp', 'datetime', 'date', 'time', 'pre_close', 'open',
            'high', 'low', 'price', 'volume', 'amount']
    for fit in df.columns:
        if fit not in fits:
            df.drop([fit], axis=1, inplace=true)
    pks = ['name', 'date', 'time', 'code']
    db.insert(df, dbname, pks)


def get_code_string(code):
    code = "{0:06d}".format(int(code))
    return code


def get_query_str(querys):
    querystr = ''
    if isinstance(querys, dict):
        for k, v in querys.items():
            if not v:
                continue
            op = '=='
            querystr = _get_query_str(querystr, k, v, op)
    elif isinstance(querys, list):
        for x in querys:
            querystr = _get_query_str(querystr, x['k'], x['v'], x['op'])

    return querystr


def _get_query_str(querystr, k, v, op):
    if k == 'datetime':
        datearr = [int(x) for x in v.split('-')]
        dt = datetime(datearr[0], datearr[1], datearr[2])
        k = 'timestamp'
        v = int(dt.timestamp())

    if op == '=':
        op = '=='

    if querystr == '':
        querystr += '{}{}{}'.format(k, op, v)
    else:
        querystr += ' and {}{}{}'.format(k, op, v)
    return querystr


def update_one_code(code, start='', end='', db=None, dbname='', freq='D', _type='fund', live=false, init=false):
    print('start...{}, dbname...{}, date...{}'.format(code, dbname, start))
    code = get_code_string(code)
    df = get_ts_data(code, start=start, end=end, _type=_type, freq=freq)
    if df.empty:
        print('{0},未获得数据'.format(code))
        return true
    # 时区设置不一致
    df['timestamp'] = df['datetime'].apply(
        lambda x: int(x.timestamp()) - 8*60*60,
    )
    if live:
        file = get_csv_file(code, dbname)
        if init:
            df.code = df.code.apply(lambda x: str(x))
            pandas_save(df, file)
            return false

        isempty = true
        if not os.path.exists(file):
            update_one_code(code, start='', db=db, dbname=dbname,
                            _type=_type, freq=freq, live=live, init=true)
            isempty = false
        else:
            da = pd.read_csv(file)
            df.reset_index(drop=true, inplace=true)
            df.sort_values(by='datetime', ascending=false, inplace=true)

            for _, row in df.iterrows():
                querys = dict(
                    code=row.code,
                    timestamp=row.timestamp,
                )
                querystr = get_query_str(querys)
                dtmp = da.query(querystr)
                if len(dtmp) <= 0:
                    # print(row.to_dict())
                    da = da.append(row, ignore_index=True)
                    isempty = false
                else:
                    break
            if not isempty:
                pandas_save(da, file)
        return isempty

    wheres = [{'k': 'code', 'v': code}]
    if init:
        print('初始化 {} {}'.format(code, dbname))
        db.delete(dbname, wheres)
    count = db.select_count(dbname, wheres=wheres)
    if count > 0:
        pks = ['timestamp', 'code', 'type']
        isempty = db.insert(df, dbname, pks)
    else:
        isempty = db.insert(df, dbname)
    return isempty


def pandas_save(df, fn):
    df.reset_index(drop=true, inplace=true)
    df.to_csv(fn, index=False)
    print('save ', fn)


def update_k_5min_data(code, start='', db=None, dbname='k_5min_data', live=false, init=false):
    if not init:
        start = get_datetime_date(days=-7, flag='-')
    else:
        start = ''
    freq = '5min'
    isempty = update_one_code(code, start=start, db=db,
                              dbname=dbname, freq=freq, live=live, init=init)
    return isempty


def update_k_data(code, start='', db=None, dbname='k_data', live=false, init=false):
    if not init:
        start = get_datetime_date(
            datetime.now() + timedelta(days=-3), flag='-')
    else:
        start = ''
    freq = 'D'
    update_one_code(code, start=start, db=db,
                    dbname=dbname, freq=freq, live=live, init=init)


def update_future():
    symbols = {
        '黄金': 'gold',
        '白银': 'silver',
        # 'WTI原油': 'wit_oil'
    }
    dbname = 'future'
    db = models.DB()
    for k, v in symbols.items():
        df = get_ak_data(k)
        df['symbol'] = v
        pks = ['datetime', 'symbol']
        db.insert(df, dbname)


def update_daily(start=''):
    db = models.DB()
    dbnames = ['k_60min_data', 'k_data']
    # dbnames = ['k_5min_data']
    import constant
    for dbname in dbnames:
        now = datetime.now()
        # if not start:
        #     start = get_datetime_date(now + timedelta(days=-3), flag='-')
        start = None
        print('开始...')

        if dbname == 'k_5min_data':
            freq = '5min'
        else:
            freq = 'D'

        codes = [x for x in constant.trade_funds]
        for code in codes:
            update_one_code(code, start=start, db=db,
                            dbname=dbname, freq=freq)

        # async_tasks(update_one_code, codes,
        #             start=start, db=db, dbname=dbname, freq=freq)
        print('end...')


def back_up():
    types = ['fund', 'stock']
    for _type in types:
        dbname = 'k_data'
        pk = 'code'
        wheres = [
            {'k': 'type', 'v': _type}
        ]
        codes = get_distinct_codes(dbname, pk, wheres=wheres)
        async_tasks(update_one_code, codes,
                    start=start, db=db, dbname=dbname, _type=_type)

    codes = get_difference_codes('k_data', 'ggt', 'code')
    kcodes = get_distinct_codes('k_data', 'code')
    etfcodes = get_all_etf()
    codes = list(set(etfcodes).difference(set(kcodes)))


def get_trade_days():
    pro = ts.pro_api()
    tradedays = global_config.get('tradedays', [])
    if not tradedays:
        now = datetime.now()
        now = now + timedelta(days=-365*10)
        start_date = get_datetime_date(now)
        data = pro.query('trade_cal', start_date=start_date, is_open='1')
        # exchange默认为上交所,start_date和end_date不是必填,is_open不填是全部,is_open可以使用0和1,0为不交易的日期,1为交易日
        tradedays = data['cal_date'].to_list()
        global_config['tradedays'] = tradedays
    return tradedays


def get_last_trade_day(day=None, _type='timestamp'):
    if not day:
        now = datetime.now()
    else:
        now = day
    istradeday = is_trade_day(now)
    count = 0
    dt = now
    while not istradeday:
        count -= 1
        dt = now + timedelta(days=count)
        istradeday = is_trade_day(dt)
    dtstr = get_datetime_date(dt)
    tradedays = get_trade_days()
    for index, trade_day in enumerate(tradedays):
        if trade_day == dtstr:
            lastdaystr = tradedays[index-1]
    lastday = datetime.strptime(lastdaystr, '%Y%m%d')
    if _type == 'timestamp':
        return int(lastday.timestamp())
    elif _type == 'datetime':
        return lastday
    elif _type == 'date':
        return lastdaystr
    elif _type == 'date_ex':
        return get_datetime_date(lastday, flag='-')


def is_trade_day(day=None):
    # 参考地址:https://tushare.pro/document/2?doc_id=26
    if day:
        now = day
    else:
        now = datetime.now()
    dt = get_datetime_date(now)
    tradedays = get_trade_days()
    istradeday = false
    for trade_day in tradedays:
        if trade_day == dt:
            istradeday = true
            break
    return istradeday

# %%


def asyncgreelet_tasks(func, tasks, *args, **kw):
    pool = Pool(size=16)
    greenlets = []
    for task in tasks:
        greenlets.append(
            pool.spawn(func, task, *args, **kw)
        )
    gevent.joinall(greenlets)


def asyncio_tasks(func, tasks, *args, **kw):
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    # loop = asyncio.get_event_loop()
    coroutines = [func(task, *args, **kw) for task in tasks]
    wait_coroutines = asyncio.wait(coroutines)
    new_loop.run_until_complete(wait_coroutines)
    new_loop.close()


def get_morning_star(first=true, data={}):
    url = 'http://cn.morningstar.com/quickrank/default.aspx'
    headers = {
        'Content-Type': "application/x-www-form-urlencoded",
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    }
    if first:
        res = requests.get(url, headers=headers)
    else:
        # print(data)
        res = requests.post(url, headers=headers, data=data)
    soup = bs(res.content, 'lxml')
    viewstate = soup.find('input', attrs={'name': '__VIEWSTATE'})
    validation = soup.find('input', attrs={'name': '__EVENTVALIDATION'})
    pages = soup.find(
        'div', attrs={'id': 'qr_pager'})
    print(pages)
    info = pages.find_all('span')
    num_str = info[2]
    if num_str.get('style', '') != 'margin-right:5px;font-weight:Bold;color:red;':
        return
    record_num = info[1]
    n = int(num_str.get_text())
    data = {
        '__EVENTTARGET': 'ctl00$cphMain$AspNetPager1',
        # '__EVENTARGUMENT': 4,
        '__LASTFOCUS': '',
        '__VIEWSTATEGENERATOR': '302D9840',
        'ctl00$cphMain$cblStarRating$0': 'on',
        'ctl00$cphMain$cblStarRating5$0': 'on',
        'ctl00$cphMain$cblStarRating5$0': '',
        'ctl00$cphMain$ddlPortfolio': '',
        'ctl00$cphMain$ddlWatchList': '',
        'ctl00$cphMain$txtFund': '基金名称',
        'ctl00$cphMain$ddlPageSite': '25',
        'ctl00$cphMain$btnGo:': '查询',
    }
    if first:
        data['__EVENTARGUMENT'] = ''
        data['__VIEWSTATE'] = constant.viewstate
        data['__EVENTVALIDATION'] = constant.validation
    else:
        data['__EVENTARGUMENT'] = n + 1
        data['__VIEWSTATE'] = viewstate.get('value', '')
        data['__EVENTVALIDATION'] = validation.get('value', '')

        detail = soup.find('table', attrs={'id': 'ctl00_cphMain_gridResult'})
        db = models.DB()
        for x in detail.find_all('tr')[1:]:
            item = {}
            y = x.find_all('td')
            z = y[2]
            code = z.get_text()
            quick_take = z.a.get('href', '').split('/')[-1]
            code_cn = y[3].get_text()
            code_type = y[4].get_text()
            item = {
                'code': code,
                'quick_take': quick_take,
                'code_cn': code_cn,
                'code_type': code_type,
                'source': 'morningstar',
            }
            df = pd.DataFrame([item])
            db.insert(df, 'fund_info')
            print(item)

    print(record_num)
    print(num_str)
    get_morning_star(first=false, data=data)


def get_datetime_date(now=None, flag='', days=0):
    if not now:
        now = datetime.now()
    if days:
        now += timedelta(days=days)
    if not flag:
        return now.strftime('%Y%m%d')
    elif flag == '-':
        return now.strftime('%Y-%m-%d')
    elif flag == '/':
        return now.strftime('%Y/%m/%d')


def get_dt_date(dt, flag=''):
    datetime = bt.num2date(dt)
    return get_datetime_date(datetime, flag=flag)


def update_index_daily(init=false):
    # 官网市盈率: http://www.csindex.com.cn/zh-CN/downloads/industry-price-earnings-ratio?type=zy1
    # 获取综指历史行情
    pro = ts.pro_api()
    # names = ['上证综指', '深证成指', '上证50', '中证500', '中小板指', '创业板指']
    dbname = 'index_dailybasic'
    db = models.DB()
    now = datetime.now() + timedelta(days=-5)
    dt = get_datetime_date(now)
    df = pro.index_dailybasic(trade_date=dt)
    if not df.empty:
        codes = df['ts_code'].values
        pks = ['ts_code', 'trade_date']
        db.insert(df, dbname, pks)
        for code in codes:
            da = pro.index_daily(trade_date=dt, ts_code=code)
            dbname = 'index_daily'
            if not da.empty:
                db.insert(da, dbname, pks)
    if init:
        lastdaystr = get_last_trade_day()
        df = pro.index_dailybasic(trade_date=lastdaystr)
        codes = df['ts_code'].values
        for code in codes:
            da = pro.index_dailybasic(ts_code=code)
            db.insert(da, dbname)
            lastday = int(da['trade_date'].values[-1]) - 1
            # print(lastday)
            da = pro.index_dailybasic(ts_code=code, end_date=str(lastday))
            while not da.empty:
                db.insert(da, dbname)
                lastday = int(da['trade_date'].values[-1]) - 1
                da = pro.index_dailybasic(ts_code=code, end_date=str(lastday))
            print('{0},end'.format(code))


def get_filter_hs300():
    db = models.DB()
    dbname = 'k_data'
    codes = db.select_distinct(dbname, 'code')
    df = ts.get_stock_basics()
    filtercodes = []
    # df.groupby('industry').name.nunique()
    for code in codes:
        t = df.query('code=="{}"'.format(code))
        if t.empty:
            continue
        industry = t.industry[0]
        if industry not in ['证券', 'IT设备', '中成药']:
            filtercodes.append(code)
    print(filtercodes)
    return filtercodes


def check_and_delete_record():
    db = models.DB()
    dbname = 'k_data'
    pk = 'code'
    codes = db.select_distinct(dbname, pk)
    types = ['fund', 'stock']
    for code in codes:
        wheres = [
            {'k': 'code', 'v': code},
            {'k': 'type', 'v': types[0]}
        ]
        count = db.select_count(dbname, wheres)
        wheres2 = [
            {'k': 'code', 'v': code},
            {'k': 'type', 'v': types[1]}
        ]
        count_ = db.select_count(dbname, wheres2)
        if count and count_:
            print(code, '重复')
            codecn = get_code_cn(code)
            if type(codecn) == float:
                db.delete(dbname, wheres=wheres)
                continue
            db.delete(dbname, wheres=wheres2)


def bar_size(df, fromdate, todate):
    return len(df[(df['date'] >= fromdate.strftime('%Y-%m-%d'))
                  & (df['date'] <= todate.strftime('%Y-%m-%d'))])


def print_transaction(strat):
    transacions = strat.analyzers.transactions.get_analysis()
    for x, y in transacions.items():
        print(x, y)


def notify_to_wx(title, text):
    key = "SCU53613T74bdd3a5e5ff2eb57218f74f71d495965d0711a8483e7"
    wx_url = "https://sc.ftqq.com/{0}.send?text={1}&desp={2}".format(
        key, title, text)
    requests.get(wx_url)


def get_csv_file(code, dbname):
    file = '{}/{}_{}.csv'.format(csvpath, code, dbname)
    return file


def get_stat(file):
    stat = os.stat(file)
    return stat


def check_order():
    o = models.Order()
    df = o.get_live_order()
    for index, row in df.iterrows():
        tp = int(time.time())
        sets = [
            {'k': 'status', 'v': 1, 'flag': ','},
            {'k': 'updatedtime', 'v': tp, 'flag': ','},
        ]
        wheres = [
            {'k': 'date', 'v': row.date},
            {'k': 'createdtime', 'v': row.createdtime},
        ]
        # u = remoteclient.get_remote_client(row.broker)
        uc = remoteclient.get_remote_client('ht')
        ret = uc.trade(extras=row.to_dict(), action=row.action)
        if ret['code'] == 0:
            sets.append(
                {'k': 'entrust_no', 'v': ret['entrust_no'], 'flag': ','}
            )
        o.db.upsert(row, dbname=o.dbname, sets=sets, wheres=wheres)


# %%
if __name__ == "__main__":
    pass
    # get_all_futures()
    check_order()
