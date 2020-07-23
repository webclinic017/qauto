# %%
import utils
import json
import backtrader as bt
import pandas as pd
import numpy as np
import os
import math
from datetime import timedelta, datetime
import time
from pprint import pprint


import indicators as cinds
# import talib

import models
import constant

# http://www.topquant.vip/?p=1703
# http://www.topquant.vip/?p=56

# %%
# multi strategy: https://community.backtrader.com/topic/2122/live-trading-multiple-strategies-each-one-on-a-separate-data-feed/101
# %%

# %%


class BaseStrategy(bt.Strategy):
    params = dict(
        printlog=utils.false,
        doprint=utils.false,
        tradelog=utils.false,
        orderlog=utils.false,
        _live=utils.false,  # 开启实盘交易
        tradestrats={},
        orderstrats={},
        multiperiod='',  # 开启多周期回测
        weightflag='one',  # 默认不加仓,或平均分配,add,ave

        pks='',  # 以下为优化参数使用
        db=None,
        dbname='',
        optpass=utils.false,  # 是否跳过本次策略
        code=0,  # 检查是否执行过策略
        _type='',
        start='',  # 多周期参数优化
    )

    def __init__(self):
        if self.inds:
            self.init_inds()

    def init_inds(self):
        for ind in self.inds:
            setattr(self, ind, {})
        for data in self.datas:
            code = utils.get_code_string(data.code[0])
            if self.p.multiperiod and self.p.multiperiod in data._name:
                if 'sma' in self.inds:
                    self.__dict__['sma'][code] = bt.ind.SMA(
                        data.close, period=self.p.smaperiod)
            else:
                for ind in self.inds:
                    if ind == 'mom':
                        # 动量指标,与前N日价格比较*100
                        self.__dict__[ind][code] = cinds.MOM(
                            data=data, period=self.p.momperiod)
                    elif ind == 'momosc':
                        self.__dict__[ind][code] = cinds.MOMOSC(
                            data=data, period=self.p.momoscperiod)
                    elif ind == 'cmi':
                        # 市场波动指数CMI,如果CMI < 20,执行震荡策略,如果CMI ≥ 20，执行趋势策略
                        self.__dict__[ind][code] = cinds.CMI(
                            data, period=self.p.cmiperiod)
                    elif ind == 'bband':
                        self.__dict__[ind][code] = bt.ind.BBands(data.close)
                    elif ind == 'sma':
                        self.__dict__[ind][code] = bt.ind.SMA(data.close)
                    elif ind == 'maxvolume':
                        self.__dict__[ind][code] = bt.ind.Highest(
                            data.volume, period=5)
                    elif ind == 'atr':
                        self.__dict__[ind][code] = cinds.ATR(
                            data=data, period=14)
                    elif ind == 'highest':
                        self.__dict__[ind][code] = bt.ind.Highest(
                            data.high, period=20)
                    elif ind == 'lowest':
                        self.__dict__[ind][code] = bt.ind.Lowest(
                            data.low, period=10)
                    elif ind == 'willr':
                        # 威廉指标 (%R) 可帮助识别超买位和超卖位,高于-20处于超买,低于-80为超卖
                        self.__dict__[ind][code] = cinds.WilliamsR()
                    elif ind == 'kama':
                        # 自适应移动均线,可用于止损
                        self.__dict__[ind][code] = cinds.KAMA()
                    elif ind == 'tsi':
                        # 指示超买,超卖,大于25处于超买,小于-25处于超卖,
                        # TSI可帮助判断市场趋势,TSI 线上扬表示上升趋势。反之，TSI 线下挫表示下跌趋势
                        self.__dict__[ind][code] = cinds.TSI()
                    elif ind == 'mtm':
                        # self.__dict__[ind][code] = bt.talib.MOM(
                        #     data, timeperiod=self.p.mtmperiod)
                        self.__dict__[ind][code] = cinds.MTM(
                            data, period=self.p.mtmperiod)
                    elif ind == 'mamtm':
                        self.__dict__[ind][code] = bt.ind.SMA(
                            self.__dict__['mtm'][code], period=self.p.mamtmperiod)
                    elif ind == 'D':
                        # KDJ,D值指示超买,超卖,大于80处于超买,小于20处于超卖
                        self.__dict__[ind][code] = self.get_d_value(data=data)
                    elif ind == 'twap':
                        # TWAP,Time Weighted Average Price,时间加权平均价格算法
                        self.__dict__[ind][code] = cinds.TWAP(
                            data=data, period=self.p.twapperiod)
                    elif ind == 'vwap':
                        # VWAP,Volume Weighted Average Price,成交量加权平均价格算法
                        self.__dict__[ind][code] = cinds.VWAP(
                            data=data, period=self.p.period)
                    else:
                        raise Exception('指标未设置')

    def start(self):
        # 只在策略开始时执行一次
        if not self.p.db:
            self.p.dbname = self.__class__.__name__.lower()
            self.p.db = models.DB()
        self.p.__dict__['type'] = self.p.__dict__['_type']
        if self.p.doprint:
            # 参数寻优使用
            if self.p.pks:
                pks = json.loads(self.p.pks)
                wheres = []
                for pk in pks:
                    where = {'k': pk, 'v': self.p.__dict__[pk]}
                    wheres.append(where)
                print(wheres)
                df = self.p.db.select(self.p.dbname, wheres=wheres)
                if not df.empty:
                    msg = '策略已经执行'
                    print(msg)
                    self.prestop()

    def log(self, txt, dt=None):
        ''' 策略的日志函数'''
        if self.p.printlog:
            dt = dt or self.get_datetime()
            print('%s, %s' % (dt.isoformat(), txt))

    def notify_order(self, order):
        # 资金压力检查
        # if order.status in [order.Submitted, order.Accepted]:
        #     return

        msgdict = {
            '日期': self.data.num2date(order.executed.dt),
            '股票名称': order.data._name,
            '股票代码': utils.get_code_string(order.data.code[0]),
            '收盘价': order.data.close[0],
            '成交价格': order.executed.price,
            '成交金额': order.executed.value,
            '成交数量': order.executed.size,
            '手续费': order.executed.comm,
        }
        if order.status in [order.Completed]:
            if order.isbuy():
                if self.p._live:
                    # 实盘下单,保存订单
                    self.do_live_and_save_order(order)
                msgdict['买卖方向'] = '买入'
                if self.p.orderlog:
                    # 价格不一致???
                    print(msgdict)
            else:
                if self.p._live:
                    # 实盘下单,保存订单
                    self.do_live_and_save_order(order)
                msgdict['买卖方向'] = '卖出'
                if self.p.orderlog:
                    print(msgdict)
                self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.p.orderlog:
                print('订单失败', msgdict)

        self.check_next(order)
        self.order = None

    def check_next(self, order):
        pass

    def do_live_and_save_order(self, order):
        code = utils.get_code_string(order.data.code[0])
        code_cn = order.data._name.split(':')[1]
        size = order.executed.size
        price = utils.get_float(order.executed.price)
        if size > 0:
            action = 'buy'
            title = '买入提示'
        else:
            action = 'sell'
            title = '卖出提示'
        datadt = self.data.num2date(order.data.datetime[0])
        nowdate = datetime.now().date()
        datadate = datadt.date()
        text = '{}:{}:{}:{}:{}'.format(datadt, code, code_cn, size, price)
        # print(title, text)
        value = utils.get_float(price * size)
        tp = int(datadt.timestamp())
        data = dict(
            date=datadate,
            broker='hte',
            code=code,
            code_cn=code_cn,
            action=action,
            size=abs(size),
            price=price,
            value=value,
            status=0,
            entrust_no='',
            updatedtime=tp,
            createdtime=tp,
        )
        df = pd.DataFrame([data])
        o = models.Order()
        if not self.p._live:
            o.upsert_order(df)
        if nowdate == datadate:
            utils.notify_to_wx(title, text)

    def get_weight(self, datas, weightflag='one'):
        weight = []
        datalen = len(datas)
        if weightflag == 'one':
            if datalen >= 3:
                weight = [0.5, 0.3, 0.15]
            elif datalen == 2:
                weight = [0.6, 0.35]
            else:
                weight = [0.95]
        elif weightflag == 'add':
            if datalen >= 3:
                weight = [0.15, 0.1, 0.05]
            elif datalen == 2:
                weight = [0.1, 0.05]
            else:
                weight = [0.2]
        elif weightflag == 'ave':
            one = 0.95 / datalen
            weight = [one for x in range(datalen)]
        return weight

    def notify_trade(self, trade):
        pass

    def get_postion(self, code):
        code = self.adapt_code(code)
        for data, pos in self.positions.items():
            poscode = utils.get_code_string(data.code[0])
            if poscode == code:
                return pos
        return None

    def get_current_trade(self, code):
        code = self.adapt_code(code)
        for data, trades in self._trades.items():
            tradecode = utils.get_code_string(data.code[0])
            if code != tradecode:
                continue
            if not trades:
                continue
            for trade in trades[0][::-1]:
                return trade
        return None

    def adapt_code(self, code):
        if self.p.multiperiod:
            if len(code) != 6:
                code = code[:6]
        return code

    def get_current_order(self, code):
        code = self.adapt_code(code)
        for order in self._orders[::-1]:
            if order.__class__.__name__ != 'BuyOrder':
                continue
            if order.status != 4:
                continue
            ordercode = utils.get_code_string(order.data.code[0])
            if ordercode == code:
                return order
        return None

    def get_current_transaction(self, code, data):
        code = self.adapt_code(code)
        transaction = {}
        for x, y in self.analyzers.transactions.get_analysis().items():
            tcode = y[0][3].split(':')[0]
            if tcode != code:
                continue
            size = y[0][0]
            if size < 1000:
                continue
            transaction['dt'] = x
            transaction['data'] = y[0]
        if not transaction:
            transaction['dt'] = data.num2date(
                data.datetime[0]) + timedelta(days=-30)
        return transaction

    def is_trade_done(self, datadt, code):
        datadate = datadt.date()
        istradedone = utils.false
        for x, y in self.analyzers.transactions.get_analysis().items():
            tcode = y[0][3].split(':')[0]
            if tcode != code:
                continue
            xdate = x.date()
            if xdate == datadate:
                istradedone = utils.true
                break

        return istradedone

    def get_pre_trades(self):
        pretrades = {}
        tradelst = []
        # 处理昨日订单
        today = bt.num2date(self.data.datetime[0])
        for trade in self.pretrades:
            datetime = trade['datetime']
            if today.timestamp() - datetime.timestamp() > 60*60*24:
                continue
            tradelst.append(trade)

        self.weight = self.get_weight(tradelst, weightflag=self.p.weightflag)
        # 获取权重及次序
        tradelst = sorted(tradelst, key=lambda x: x['mom'], reverse=utils.true)
        for i, trade in enumerate(tradelst):
            code = trade['code'][:6]
            target = self.weight[i]
            trade['target'] = target
            pretrades.update({code: trade})
        return pretrades

    def get_d_value(self, data=None):
        # 9个交易日,3周加权平均值
        if not isinstance(data, models.PandasData):
            data = self.data
        high_nine = bt.ind.Highest(data.high, period=9)
        low_nine = bt.ind.Lowest(data.low, period=9)
        rsv = 100 * bt.DivByZero(
            data.close - low_nine, high_nine - low_nine, zero=None
        )
        K = bt.ind.EMA(rsv, period=3)
        D = bt.ind.EMA(K, period=3)
        return D

    def get_target_size(self, data, target):
        price = data.close[0]
        target *= self.broker.getvalue()
        value = self.broker.getvalue(datas=[data])
        comminfo = self.broker.getcommissioninfo(data)
        size = 0
        if target > value:
            size = comminfo.getsize(price, target - value)
        elif target < value:
            size = -comminfo.getsize(price, value - target)
        size = round(size / 100) * 100
        return size

    # 回测结束后输出结果（可省略，默认输出结果）

    def prestop(self):
        self.p.db.engine.dispose()
        self.p.optpass = utils.true
        self.stop()

    def get_strats(self):
        # 收益,最大回撤,夏普率
        finalvalue = self.broker.getvalue()
        availablevalue = self.broker.getcash()
        startingcash = self.broker.startingcash
        totalreturn = finalvalue - startingcash
        self.analyzers.SharpeRatio.stop()
        sharpe = self.analyzers.SharpeRatio.rets['sharperatio']
        self.analyzers.DW.stop()
        mddrate = self.analyzers.DW.get_analysis()['max']['drawdown']
        mddmoney = self.analyzers.DW.get_analysis()[
            'max']['moneydown']
        self.analyzers.AnnualReturn.stop()
        annualreturninfo = dict(self.analyzers.AnnualReturn.get_analysis())

        startclose = self.data.p.dataname.close[0]
        # code = self.data.p.dataname.code[0]
        start = self.data.p.dataname.datetime[0]
        endclose = self.data.p.dataname.close[-1]
        rate = (endclose - startclose) / startclose
        slgrate = (finalvalue - startingcash) / startingcash
        if totalreturn < 0:
            annualreturninfo = ''
        # self.p.code = code
        self.p.start = utils.get_datetime_date(start, flag='-')

        optresult = {
            'totalreturn': utils.get_float(totalreturn),
            'value': utils.get_float(finalvalue),
            'availablevalue': utils.get_float(availablevalue),
            'rate': utils.get_float(rate),
            'slgrate': utils.get_float(slgrate),
            'sharpe': utils.get_float(sharpe),
            'mddrate': utils.get_float(mddrate/100),
            'mddmoney': utils.get_float(mddmoney),
            'annualreturninfo': json.dumps(annualreturninfo),
        }
        return optresult

    def get_order_and_trade_strats(self):
        orderstatus = [j.status for j in self._orders]
        total = len(orderstatus)
        fail = orderstatus.count(7)
        if total:
            failrate = utils.get_float(fail/total)
        else:
            failrate = 0.0
        self.p.orderstrats = dict(total=total, fail=fail, failrate=failrate)

        tradestrats = []
        countkeys = ['roundst', 'twapst', 'mtmst']
        countinfo = {}
        for i, j in self._trades.items():
            trades = j[0]
            code = utils.get_code_string(i.code[0])
            wincount = 0
            winvalue = 0.0
            losevalue = 0
            winrate = 0.0
            if trades:
                for trade in trades:

                    date = utils.get_datetime_date(
                        bt.num2date(trade.dtopen) + timedelta(days=0), flag='-')
                    for key in countkeys:
                        datevalue = self.__dict__.get(key, [])
                        if date in datevalue:
                            break
                    info = countinfo.get(key, {})
                    if not info:
                        info['winvalue'] = 0
                        info['losevalue'] = 0
                        info['wincount'] = 0
                        info['tradecount'] = 0
                        info['winrate'] = 0

                    if self.p.tradelog:
                        if trade.history:
                            _size = trade.history[-1].event.size
                            _price = trade.history[-1].event.price
                        else:
                            _size = 0
                            _price = 0
                        trademsg = {
                            '买入时间': bt.num2date(trade.dtopen),
                            '买入价格': utils.get_float(trade.price),
                            '卖出数量': _size,
                            '卖出价格': _price,
                            '手续费': utils.get_float(trade.commission),
                            '市值': utils.get_float(_size * _price),
                        }
                        if trade.dtclose:
                            trademsg['卖出时间'] = utils.get_dt_date(
                                trade.dtclose, flag='-')
                        else:
                            trademsg['卖出时间'] = 0
                        trademsg['浮盈'] = utils.get_float(trade.pnlcomm)

                    if trade.pnlcomm > 0:
                        wincount += 1
                        winvalue += trade.pnlcomm
                        info['winvalue'] += trade.pnlcomm
                        info['wincount'] += 1
                    else:
                        losevalue += trade.pnlcomm
                        info['losevalue'] += trade.pnlcomm

                    if self.p.tradelog:
                        print(trademsg)

                    info['tradecount'] += 1
                    countinfo[key] = info

                tradecount = len(trades)
                winrate = wincount/tradecount
            tradedict = dict(
                code=code,
                winrate=utils.get_float(winrate),
                wincount=wincount,
                tradecount=tradecount,
                winvalue=utils.get_float(winvalue),
                losevalue=utils.get_float(losevalue),
            )
            tradestrats.append(tradedict)
        tradescount = sum([x['tradecount'] for x in tradestrats])
        winscount = sum([x['wincount'] for x in tradestrats])
        winrate = 0.0
        if tradescount:
            winrate = winscount/tradescount
        winsvalue = sum([x['winvalue'] for x in tradestrats])
        losesvalue = sum([x['losevalue'] for x in tradestrats])
        bref = dict(
            code='',
            wincount=winscount,
            winrate=utils.get_float(winrate),
            tradecount=tradescount,
            winvalue=utils.get_float(winsvalue),
            losevalue=utils.get_float(losesvalue),
        )
        tradestrats.insert(0, bref)
        # print(tradestrats)
        # self.get_postion()

        for key in countkeys:
            if not countinfo.get(key, ''):
                continue
            if not countinfo[key].get('tradecount', 0):
                continue
            countinfo[key]['winrate'] = countinfo[key]['wincount'] / \
                countinfo[key]['tradecount']

        # 更新参数
        if self.p.tradelog:
            pprint(tradestrats)
            pprint(countinfo)
            for data in self.datas:
                code = utils.get_code_string(data.code[0])
                pos = self.get_postion(code)
                if pos and pos.size > 0:
                    msg = '{}, 日期: {}, 持仓:{}, 成本价:{:.3f}, 当前价:{:.3f}, 盈亏:{:.3f}, 总市值:{:.3f}'.format(
                        code,
                        pos.datetime,
                        pos.size,
                        pos.price,
                        pos.adjbase,
                        pos.size * (pos.adjbase - pos.price),
                        pos.size * pos.adjbase,
                    )
                    print(msg)
        self.p.tradestrats = json.dumps(bref)
        self.p.orderstrats = json.dumps(self.p.orderstrats)

    def save_strats(self, optresult):
        self.get_order_and_trade_strats()

        optresult.update(self.p.__dict__)
        updatekeys = []
        if self.p.pks:
            self.p.pks = json.loads(self.p.pks)
            updatekeys.extend(self.p.pks)
        defaultkeys = ['code', 'type', 'start', 'rate', 'slgrate', 'sharpe', 'mddrate', 'totalreturn',
                       'value', 'availablevalue', 'annualreturninfo', 'tradestrats', 'orderstrats']
        updatekeys.extend(defaultkeys)
        updatedata = {}
        for key in updatekeys:
            updatedata[key] = optresult[key]

        print(optresult)
        df = pd.DataFrame([updatedata])
        if self.p.pks:
            self.p.db.insert(df, self.p.dbname, pks=self.p.pks)
        self.p.db.engine.dispose()
        self.p.db = None

    def stop(self):
        if self.p.doprint:
            if self.p.optpass:
                return
            optresult = self.get_strats()
            self.save_strats(optresult)
            # print(msg)

# %%

# %%
# TODO
# 5分钟检查,未检查今日已购买:done

# 在传统选股指标中，最真实的就是成交量，因为成交量都是“真金白银”，造不了假。
# 个股成交量的变化可以当做一个判断资金流向、市场情绪的标准。
# 至于其他指标，如MACD、KDJ、BBI等，严格来说，都具有滞后性，
# 是股票的量价走势决定了指标的走势，这个先后顺序是不能颠倒的。


# %%


class KdjStrategy(BaseStrategy):
    # KDJ策略,超买,超卖检查
    # 1.K与D值永远介于0到100之间。D大于80时，行情呈现超买现象。D小于20时，行情呈现超卖现象。
    # 2.上涨趋势中，K值小于D值，K线向上突破D线时，为买进信号。下跌趋势中，K值大于D值，K线向下跌破D线时，为卖出信号。
    # 3.KD指标不仅能反映出市场的超买超卖程度，还能通过交叉突破发出买卖信号。
    # 4.KD指标不适于发行量小、交易不活跃的股票，但是KD指标对大盘和热门大盘股有极高准确性。
    # 5.当随机指标与股价出现背离时，一般为转势的信号。
    # 6.K值和D值上升或者下跌的速度减弱，倾斜度趋于平缓是短期转势的预警信号。
    params = dict(
        printlog=utils.true,
    )

    def __init__(self):
        self.order = None
        self.buyprice = None
        self.buycomm = None
        # 9个交易日内最高价
        self.high_nine = bt.ind.Highest(self.data.high, period=9)
        # 9个交易日内最低价
        self.low_nine = bt.ind.Lowest(self.data.low, period=9)
        # 计算rsv值, RSV = （收盘价-N周期最低价）/（N周期最高价-N周期最低价）*100
        self.rsv = 100 * bt.DivByZero(
            self.data_close - self.low_nine, self.high_nine - self.low_nine, zero=None
        )
        # KDJ指标由3根曲线组成，移动速度最快的是J线，其次是K线，最慢的是D线
        # 计算rsv的3周期加权平均值，即K值, K值 = RSV的N周期加权移动平均值
        self.K = bt.ind.EMA(self.rsv, period=3)
        # D值=K值的3周期加权平均值, D值 = K值的N周期加权移动平均值
        self.D = bt.ind.EMA(self.K, period=3)
        # J=3*K-2*D
        self.J = 3 * self.K - 2 * self.D

    def next(self):
        condition1 = self.J[-1] - self.D[-1]
        condition2 = self.J[0] - self.D[0]
        if not self.position:
            # J - D 值
            if condition1 < 0 and condition2 > 0:
                self.log("BUY CREATE, %.2f" % self.data.close[0])
                self.order = self.buy()
        else:
            if condition1 > 0 or condition2 < 0:
                self.log("SELL CREATE, %.2f" % self.data.close[0])
                self.order = self.sell()


class MacdStrategy(BaseStrategy):
    params = dict(
        printlog=utils.true,
    )

    def __init__(self):
        me1 = bt.ind.EMA(self.data, period=12)
        me2 = bt.ind.EMA(self.data, period=26)
        # MACD=价格EMA(12) - 价格EMA(26).
        self.macd = me1 - me2
        # 信号线=MACD的EMA(9)
        self.signal = bt.ind.EMA(self.macd, period=9)
        # self.macd = bt.ind.MACD(
        #     self.data, period_me1=12, period_me2=26, period_signal=9)

    def next(self):
        if not self.position:
            # 如果没有持仓，若前一天MACD < Signal, 当天 Signal < MACD，则第二天买入
            condition1 = self.macd[-1] - self.signal[-1]
            condition2 = self.macd[0] - self.signal[0]
            if condition1 < 0 and condition2 > 0:
                self.log('BUY CREATE, %.2f' % self.data.close[0])
                self.order = self.buy()
        else:
            # 若已盈利10%，则卖出；若已亏损10%，则卖出。
            condition = (
                self.data.close[0] - self.bar_executed_close) / self.data.close[0]
            if condition > 0.1 or condition < -0.1:
                self.log('SELL CREATE, %.2f' % self.data.close[0])
                self.order = self.sell()


class BollStrategy(BaseStrategy):
    # 布林线策略,价值回归
    params = dict(
        p_period_volume=3,   # 前n日最大交易量
        p_sell_ma=3,          # 跌破该均线卖出
        p_oneplot=utils.false,      # 是否打印到同一张图
        pstake=1000,          # 单笔交易股票数
        printlog=utils.false,          # 单笔交易股票数
        # skiplen=1,
    )

    def __init__(self):
        self.bband = bt.ind.BBands(self.data.close)  # top,bot,mid 布林线上轨,下轨,中轨
        self.sma = bt.ind.SMA(self.data.close, period=self.p.p_sell_ma)
        self.maxvolume = bt.ind.Highest(
            self.data.volume, period=self.p.p_period_volume)

    def next(self):
        pos = self.getposition(self.data).size
        close = self.data.close[0]
        mid = self.bband.mid[0]
        if not pos:
            if self.data.open[0] < mid and close > mid and self.data.volume[0] == self.maxvolume[0]:
                # 开盘价小于布林线中轨,收盘价突破布林线中轨,放量
                self.log('BUY CREATE, %s, 买入:股' % (close))
                self.buy(data=self.data, size=self.p.pstake)
        elif close < self.sma[0] or close > self.bband.top[0]:
            # 跌破5日均线,或者收盘价>布林线上轨
            self.sell(data=self.data)
            self.log('BUY SELL, %s, 买入:股' % (close))


class TWAPStrategy(BaseStrategy):
    params = dict(
        twapperiod=3,
        momperiod=13,
        smaperiod=5,
    )

    def __init__(self):
        self.inds = ['twap', 'D', 'mom', 'atr']
        super(TWAPStrategy, self).__init__()

    def next(self):
        tradelst = []
        for data in self.datas:
            code = utils.get_code_string(data.code[0])

            twap = self.twap[code]
            D = self.D[code]
            mom = self.mom[code]
            atr = self.atr[code]

            datetime = bt.num2date(data.datetime[0])
            tradedict = dict(
                data=data,
                code=code,
                mom=mom[0],
                datetime=datetime,
            )
            pos = self.get_postion(code)
            haspos = utils.false
            if pos and pos.size > 0:
                haspos = utils.true

            # print(code, datetime, twap[0], twap[-1], data.close[0], data.close[-1])

            if (twap[0] <= data.close[0] and twap[-1] > data.close[-1]) and not haspos:
                # 进场,未持仓
                if D[0] < 80:
                    tradedict['flag'] = 'buy'
                    tradelst.append(tradedict)

            if (twap[0] >= data.close[0] and twap[-1] > data.close[-1]) and haspos:
                # 出场,未持仓则跳过本次卖出
                if D[0] > 20:
                    tradedict['flag'] = 'sell'
                    tradelst.append(tradedict)

        # 确定次序
        self.weight = self.get_weight(tradelst, weightflag='one')
        # 获取权重及次序
        tradelst = sorted(tradelst, key=lambda x: x['mom'], reverse=utils.true)
        for i, trade in enumerate(tradelst[:2]):
            data = trade['data']
            if trade['flag'] == 'buy':
                target = self.weight[i]
                size = self.get_target_size(data, target)
                self.order = self.buy(data=data, size=size)
            else:
                target = 0
                size = self.get_target_size(data, target)
                self.order = self.sell(data=data, size=size)

# Momentum Indictor, 动量指标,又称为MTM指标，是一种专门研究股价波动的中短期技术分析指标
# MTM=C−Cn, C:当日收盘价,n日前收盘价​
# MAMTM=MTM的移动平均线, 对于股市，N周期一般用6，移动平均线一般选用12周期。

# https://blog.csdn.net/The_Time_Runner/article/details/101512714
# https://blog.csdn.net/weixin_30354675/article/details/97290655?utm_medium=distribute.pc_relevant.none-task-blog-baidujs-2

# 使用方法
# MTM线由下向上突破零时为买进信号，相反，MTM由上向下跌破零时为卖出信号；
# MTM线由下向上突破MTMMA线为买入信号；当MTM线由上向下跌破MTMMA为卖出信号；
# 股价在上涨行情中创新高，而MTM未能配合上升，出现背离现象，意味着上涨动力减弱，谨防股价反转下跌；
# 股价在下跌行情中创新低，而MTM未能配合下降，出现背离现象，意味着下跌动力减弱，此时可以注意逢低吸纳；
# 如股价与MTM在低位同步上升，显示短期将有反弹行情；如股价与MTM在高位同步下降，显示短期可能出现回落走势；
# 动力指标也有以"振荡点"的方式计算，以10日动力指标为例，其10日动力指标值等于当日收盘价除以10日前收盘价乘上100。

# 动量轮动


class MtmStrategy(BaseStrategy):
    # 此动量策略比twap策略回撤小,收益也小
    # 适用于渣男类基金
    # twap策略比此策略更抓住上涨机会,回撤也大
    params = dict(
        mtmperiod=3,  # mtm选择短周期,3更灵敏, [3,6]
        mamtmperiod=21,  # mamtm指标选择长周期
        momperiod=13,  # mamtm指标选择长周期
        weightflag='add',  # 是否分批加仓
    )

    def __init__(self, inds=[]):
        self.inds = ['mtm', 'D', 'mamtm', 'mom', 'atr', 'ad', 'tsi']
        self.buytimes = {}  # 控制分批加仓次数
        super(MtmStrategy, self).__init__()

    def next(self):
        tradelst = []
        for data in self.datas:
            code = utils.get_code_string(data.code[0])
            mtm = self.mtm[code]
            mamtm = self.mamtm[code]
            D = self.D[code]
            atr = self.atr[code]
            ad = self.ad[code]
            tsi = self.tsi[code]
            tradedict = dict(
                data=data,
                code=code,
                mom=self.mom[code][0],
            )
            pos = self.get_postion(code)
            haspos = utils.false
            if pos and pos.size > 0:
                haspos = utils.true

            # 动量指标大于平均动量指标,而且上一日小于平均动量指标
            if (mtm[0] > mamtm[0] and mtm[-1] <= mamtm[-1]) and not haspos:
                # 但处于超买时,不买入
                if D[0] < 80:
                    tradedict['flag'] = 'buy'
                    tradelst.append(tradedict)
                    self.buytimes[code] = 1

            if self.p.weightflag == 'add':
                if (atr[0] >= atr[-1]) and haspos:
                    # 分批进仓时加仓,已持仓,本日真实价格波动均值大于昨日
                    # 效果不好???
                    if (D[0] < 80) and self.buytimes[code] < 3:
                        tradedict['flag'] = 'buy'
                        tradelst.append(tradedict)
                        self.buytimes[code] += 1

            rise = (
                (data.close[0] - data.close[-1]) / data.close[0])*100
            if not mtm:
                # mtm值为0
                continue
            risemtm = ((mtm[0]-mtm[-1]) / mtm[0]) * 100
            # 价格上涨,mtm指标没有同步上涨,出现背离(根据百分比计算)
            if (mtm[0] > mamtm[0]) and haspos:
                # rise价格涨幅,mtm指标涨幅,价格涨幅高于mtm涨幅卖出
                if abs(rise) > abs(risemtm):
                    # 当处于超卖时,不卖出
                    if D[0] > 20:
                        tradedict['flag'] = 'sell'
                        tradelst.append(tradedict)
                        self.buytimes[code] = 0
                        continue

            if (mtm[0] < mamtm[0] or mtm[0] < 0) and haspos:
                if D[0] > 20:
                    tradedict['flag'] = 'sell'
                    tradelst.append(tradedict)
                    self.buytimes[code] = 0

        tradelst = sorted(tradelst, key=lambda x: x['mom'], reverse=utils.true)
        self.weight = self.get_weight(tradelst, weightflag=self.p.weightflag)
        percent = 0.95
        for i, trade in enumerate(tradelst[:2]):
            code = trade['code']
            data = trade['data']
            price = data.close[0]
            if trade['flag'] == 'buy':
                target = self.weight[i]
                percent -= target
                size = self.get_target_size(data, target)
                self.order = self.buy(data=data, size=size, price=price)
            else:
                target = 0
                size = self.get_target_size(data, target)
                self.order = self.sell(data=data, size=size, price=price)


# https://blog.csdn.net/halcyonbaby/article/details/104704198
# 300、500、国债指数轮动，300和500的20天涨幅哪个大持有哪个，两个都为负数持有国债.
# http://17fx.net/F2020/c_create1.aspx

# 轮动策略不适合震荡市，更适合趋势明显的牛市和熊市

# 雪球蛋卷二八斗牛
# （1）每日收盘后对比当日收盘数据与20个交易日前的收盘数据，选择沪深300指数和中证500指数中涨幅较大的一个，于下一个交易日收盘时切换为持有该指数；
# （2）若两个指数均为下跌，则于下个交易日收盘时切换为持有国债指数。
# 且慢张翼轸的Earl二八轮动
# （1）每周五(或者本周的最后一个交易日)临近收盘时，将沪深300指数和中证500指数切换到周线状态，分别查看两者过去四周的累计涨幅。哪个过去四周涨幅大，那么就在收盘前买入对应的ETF持有一周，直至下一次的切换。
# （2）如果过去四周涨幅大的那个指数在四周中依然是亏损的，那么就选择空仓，直至下一次切换。
# 两者的区别是雪球的是20个交易日且慢的是4周，其实一般情况下4周等于20个交易日，论时间其实差不多。
# 但是雪球的看的是日线而且是每日计算进行调仓，且慢看的是周线而是每周计算进行调仓，所以雪球的更敏感一些交易可能会更频繁。
# 交易策略：每天收盘后将沪深300ETF（510300）和创业板（159915）按照最近20个交易日的涨幅排序，
# 排名第一并且20日涨幅大于2%则次日以开盘价买入；如果排名不是第一或者20日涨幅小于-2%则次日开盘价卖出；
# 如果以上两个条件都不满足则买入银华日利（511880）；

# https://blog.csdn.net/ndhtou222/article/details/106416802


class RoundStrategy(BaseStrategy):
    params = dict(
        momperiod=17,
        holdperiod=3,
    )

    def __init__(self):
        self.holddays = 0

        # self.mom = [bt.ind.MomentumOscillator(
        #     i, period=self.p.momperiod) for i in self.datas]

        self.inds = ['mom']
        super(RoundStrategy, self).__init__()

    def mom_weight(self):
        checkperiod = self.holddays % self.p.holdperiod
        self.holddays += 1
        if checkperiod != 0:
            return

        buyitems = [(i, j) for i, j in self.mom.items() if j > 100]
        buyitems = sorted(buyitems, key=lambda x: x[1][0], reverse=utils.true)
        # 没有动量,买入债券
        if not buyitems:
            code = utils.get_code_string(self.datas[-1].code[0])
            buyitems.append((code, ))
        codes = [i[0] for i in buyitems[:2]]
        # 根据买入数量确认权重
        self.weight = self.get_weight(codes, weightflag='ave')
        trades = {}
        # 设置权重
        for i, code in enumerate(codes):
            trades[code] = self.weight[i]

        for data in self.datas:
            code = utils.get_code_string(data.code[0])
            if code not in codes:
                target = 0
                size = self.get_target_size(data, target)
                self.order = self.sell(data=data, size=size)
                continue
            target = trades[code]
            size = self.get_target_size(data, target)
            if size > 0:
                self.order = self.buy(data=data, size=size)
            else:
                self.order = self.sell(data=data, size=size)

        return

        # 权重多只买入,分散风险

        moms = [i for i in self.mom]
        needbuys = [i for i in self.mom[:-1] if i[0] > 100]
        # 降序排列
        needbuys.sort(key=lambda x: x[0], reverse=utils.true)
        needbuys = needbuys[:2]
        # 动量不足,持有债券,根据权重1
        if not needbuys:
            needbuys.append(moms[-1])
        weight = self.get_weight(needbuys, weightflag='ave')
        # 检查卖出
        percent = 1
        for j in moms:
            v = j[0]
            if j not in needbuys:
                self.order_target_percent(data=j.data, target=0)
        # 根据权重买入,最多持有3只
        for i, j in enumerate(needbuys):
            v = j[0]
            if v > 100:
                target = weight[i]
                percent = percent - target
                self.order_target_percent(data=j.data, target=target)

    def mom_sample(self):
        # 选择动量最高的买入
        buy_id = 0
        c = [i[0] for i in self.mom]
        c[0] = 0
        index, value = c.index(max(c)), max(c)
        if value > 100:
            buy_id = index
        for i in range(0, len(c)):
            if i != buy_id:
                position_size = self.broker.getposition(
                    data=self.datas[i]).size
                if position_size != 0:
                    self.order_target_percent(data=self.datas[i], target=0)
        position_size = self.broker.getposition(data=self.datas[buy_id]).size
        if position_size == 0:
            self.order_target_percent(data=self.datas[buy_id], target=0.98)

    def next(self):
        self.mom_weight()
        # self.mom_sample()


# TODO: 闲置资金买入债券

# twap指标确认进场,出场,分批进场(进出场)
# 明日小周期K线突破均线买入
# 加仓策略,atr指标确认趋势,两次加仓机会(仓位控制)
# D指标超买,超卖检查


class TWAPMultiStrategy(BaseStrategy):
    params = dict(
        twapperiod=3,  # 3对于业绩好最优,5对于业绩较差最优,需动态调整
        momperiod=13,
        smaperiod=16,
        multiperiod='',
        weightflag='one',  # 是否分批加仓
    )

    def __init__(self, inds=[]):
        if inds:
            self.inds = inds
        else:
            self.inds = ['twap', 'D', 'mom', 'atr', 'sma']
        self.buytimes = {}  # 控制分批加仓次数
        self.hasdones = {}  # 加入不同周期,实盘接入,具体交易逻辑
        self.pretrades = []  # 记录长周期下单记录,用于第二天下单依据
        super(TWAPMultiStrategy, self).__init__()

    def next(self):
        # 获取昨日订单
        pretrades = self.get_pre_trades()

        tradelst = []
        for data in self.datas:
            code = utils.get_code_string(data.code[0])
            datadt = bt.num2date(data.datetime[0])

            # 过滤5分钟k线
            if self.p.multiperiod:
                if self.p.multiperiod in data._name:
                    trade = pretrades.get(code, {})
                    # 昨日没有订单,或者不是本基金
                    if not pretrades or not trade:
                        continue
                    sma = self.sma[code]
                    # 小周期突破均线入场,K线大于均线,上个K线小于均线
                    if data.close[0] >= sma[0] and data.close[-1] < sma[-1] and trade['flag'] == 'buy':
                        # 检查当天订单是否已完成
                        istradedone = self.is_trade_done(datadt, code)
                        if istradedone:
                            continue

                        target = trade['target']
                        size = self.get_target_size(data, target)
                        self.order = self.buy(data=data, size=size)
                        trade.pop(code, None)

                    # 小周期,K线小于均线,上个K线大于均线
                    if data.close[0] <= sma[0] and data.close[-1] > sma[-1] and trade['flag'] == 'sell':
                        target = 0
                        size = self.get_target_size(data, target)
                        self.order = self.sell(data=data, size=size)
                        trade.pop(code, None)

                    continue

                dones = self.hasdones.get(code, [])
                datalen = len(data)
                if datalen in dones:
                    continue
                dones.append(datalen)
                self.hasdones.update({code: dones})

            twap = self.twap[code]
            D = self.D[code]
            mom = self.mom[code]
            atr = self.atr[code]

            tradedict = dict(
                data=data,
                code=code,
                mom=mom[0],
                datetime=datadt,
            )
            pos = self.get_postion(code)
            haspos = utils.false
            if pos and pos.size > 0:
                haspos = utils.true

            # print(code, datetime, data._name, twap[0], twap[-1], data.close[0], data.close[-1])

            if (twap[0] <= data.close[0] and twap[-1] > data.close[-1]) and not haspos:
                # 进场,未持仓
                if D[0] < 80:
                    tradedict['flag'] = 'buy'
                    tradelst.append(tradedict)
                    self.buytimes[code] = 1

            if self.p.weightflag == 'add':
                if (atr[0] >= atr[-1]) and haspos:
                    # 分批进仓时加仓,已持仓,本日真实价格波动均值大于昨日
                    # 效果不好???
                    if (D[0] < 80) and self.buytimes[code] < 3:
                        # 加仓次数不超过2次,总共分三次入场
                        tradedict['flag'] = 'buy'
                        tradelst.append(tradedict)
                        self.buytimes[code] += 1

            if (twap[0] >= data.close[0] and twap[-1] > data.close[-1]) and haspos:
                # 出场,未持仓则跳过本次卖出
                if D[0] > 20:
                    tradedict['flag'] = 'sell'
                    tradelst.append(tradedict)
                    self.buytimes[code] = 0

        if not self.p.multiperiod:
            # 动量指标确定权重
            tradelst = sorted(
                tradelst, key=lambda x: x['mom'], reverse=utils.true)

            self.weight = self.get_weight(
                tradelst, weightflag=self.p.weightflag)
            percent = 0.95
            for i, trade in enumerate(tradelst[:2]):
                code = trade['code']
                data = trade['data']
                price = data.close[0]
                if trade['flag'] == 'buy':
                    if trade.get('size', 0) > 0:
                        size = trade['size']
                    else:
                        target = self.weight[i]
                        percent -= target
                        size = self.get_target_size(data, target)
                    self.order = self.buy(data=data, size=size, price=price)
                else:
                    target = 0
                    size = self.get_target_size(data, target)
                    self.order = self.sell(data=data, size=size, price=price)
        else:
            # 确定次序
            for trade in tradelst[:2]:
                trade['datetime'] = bt.num2date(self.data.datetime[0])
                self.pretrades.append(trade)

    def check_next(self, order):
        # 买入失败订单处理
        pass
        # if order.__class__.__name__ == 'BuyOrder' and order.status == 7:
        #     self.order = self.buy(data=order.data, size=order.size)


# 恒温器策略
# 根据cmi调节交易策略
# mtm作为震荡趋势进出场指标,两次加仓,使用atr真实波动幅度止损
# 海龟策略不理想
# 切换布林带策略,价值回归
# twap作为趋势明朗进出场指标,(核心)
# round牛市轮动策略
# D值判断超买超买

# 容易优化过度,太多参数,cmi判断依据有误???,cmi震荡市和趋势市cmi值难确定


class CMIStrategy(BaseStrategy):
    params = dict(
        cmiperiod=22,  # 恒温控制器参数, 22对业绩优秀最优,44对业绩不好最优
        minperiod=20,  # 20,50
        maxperiod=50,  # 50,150

        mtmperiod=3,  # mtm策略,短周期3,长周期21
        mamtmperiod=21,

        twapperiod=3,  # twap策略

        momperiod=13,  # 轮动策略,13个交易日
        holdperiod=3,  # 轮动策略持仓天数检查

        smaperiod=16,  # 小周期进场
        # multiperiod='k_5min_data',
        multiperiod='',

        orderholdperiod=7,  # 控制订单频率,不接受7天之内的订单
        weightflag='one',  # 是否分批加仓
    )

    def __init__(self, inds=[]):
        if inds:
            self.inds = inds
        else:
            self.inds = ['twap', 'D', 'mom', 'atr',
                         'cmi', 'mtm', 'mamtm', 'sma']
        self.holddays = 0  # 轮动策略持仓天数计算
        self.buytimes = {}  # 控制分批加仓次数
        self.hasdones = {}  # 过滤填充的大周期行
        self.pretrades = []  # 获取昨日订单,在5分钟小周期下单
        super(CMIStrategy, self).__init__()

    def next(self):
        # 获取昨日订单
        pretrades = {}
        if self.p.multiperiod:
            pretrades = self.get_pre_trades()

        tradelst = []
        for data in self.datas:
            code = utils.get_code_string(data.code[0])
            date = data.num2date(data.datetime[0])

            if self.p.multiperiod:
                # 过滤5分钟k线
                if self.p.multiperiod in data._name:
                    trade = pretrades.get(code, {})
                    # 昨日没有订单,或者不是本基金
                    if not pretrades or not trade:
                        continue

                    sma = self.sma[code]
                    if data.close[0] >= sma[0] and data.close[-1] < sma[-1] and trade['flag'] == 'buy':
                        # 检查当天订单是否已完成
                        istradedone = self.is_trade_done(date, code)
                        if istradedone:
                            continue

                        target = trade['target']
                        size = self.get_target_size(data, target)
                        self.order = self.buy(data=data, size=size)

                    if data.close[0] <= sma[0] and data.close[-1] > sma[-1] and trade['flag'] == 'sell':
                        target = 0
                        size = self.get_target_size(data, target)
                        self.order = self.sell(data=data, size=size)

                    continue

                dones = self.hasdones.get(code, [])
                datalen = len(data)
                if datalen in dones:
                    continue
                dones.append(datalen)
                self.hasdones.update({code: dones})

            cmi = self.cmi[code]

            # 评判当前趋势
            if cmi[0] <= self.p.minperiod:
                # 执行震荡策略
                # cmi值如何确定???
                # 趋势特征不明显分批建仓
                key = 'mtmst'
                # print(date, key)
                if not hasattr(self, key):
                    setattr(self, key, [])

                self.p.weightflag = 'add'
                tradedict = self.next_mtm(code, data)
                # tradedict = self.next_turtle(code, data)
                # tradedict = self.next_boll(code, data)
                if tradedict.get('flag', ''):
                    tradelst.append(tradedict)

                    date = utils.get_dt_date(
                        data.datetime[0], flag='-')
                    self.__dict__[key].append(date)
            elif self.p.maxperiod > cmi[0] > self.p.minperiod:
                # 执行趋势策略
                # 趋势特征明显不分批建仓
                key = 'twapst'
                # print(date, key)
                if not hasattr(self, key):
                    setattr(self, key, [])

                self.p.weightflag = 'one'
                tradedict = self.next_twap(code, data)
                if tradedict.get('flag', ''):
                    tradelst.append(tradedict)

                    date = utils.get_dt_date(
                        data.datetime[0], flag='-')
                    self.__dict__[key].append(date)
            elif cmi[0] >= self.p.maxperiod:
                # 牛市策略,长期持有,不使用加仓策略,价格相对便宜
                self.p.weightflag = 'one'
                key = 'roundst'
                # print(date, key)
                if not hasattr(self, key):
                    setattr(self, key, [])

                tradedict = self.next_round(code, data)
                if tradedict.get('flag', ''):
                    tradelst.append(tradedict)

                    date = utils.get_dt_date(
                        data.datetime[0], flag='-')
                    self.__dict__[key].append(date)

        if not self.p.multiperiod:
            # 动量指标确定权重
            tradelst = sorted(
                tradelst, key=lambda x: x['mom'], reverse=utils.true)

            self.weight = self.get_weight(
                tradelst, weightflag=self.p.weightflag)
            percent = 0.95
            for i, trade in enumerate(tradelst[:2]):
                code = trade['code']
                data = trade['data']
                price = data.close[0]
                if trade['flag'] == 'buy':
                    if trade.get('size', 0) > 0:
                        size = trade['size']
                    else:
                        target = self.weight[i]
                        percent -= target
                        size = self.get_target_size(data, target)
                    self.order = self.buy(data=data, size=size, price=price)
                else:
                    target = 0
                    size = self.get_target_size(data, target)
                    self.order = self.sell(data=data, size=size, price=price)
        else:
            # 确定次序
            for trade in tradelst[:2]:
                trade['datetime'] = bt.num2date(self.data.datetime[0])
                self.pretrades.append(trade)

    def next_twap(self, code, data):
        twap = self.twap[code]
        atr = self.atr[code]
        mom = self.mom[code]
        D = self.D[code]
        tradedict = dict(
            data=data,
            code=code,
            mom=mom[0],
        )
        pos = self.get_postion(code)
        haspos = utils.false
        if pos and pos.size > 0:
            haspos = utils.true

        # print(code, twap[0], twap[-1], data.close[0], data.close[-1], haspos)

        if (twap[0] <= data.close[0] and twap[-1] > data.close[-1]) and not haspos:
            # 进场,未持仓
            transaction = self.get_current_transaction(code, data)
            dtcp = data.num2date(data.datetime[0]) - transaction['dt']
            if (D[0] < 80) and (dtcp.days > self.p.orderholdperiod):
                # 未处于超买,上次订单7️天之前,控制订单频率
                tradedict['flag'] = 'buy'
                self.buytimes[code] = 1

        if self.p.weightflag == 'add':
            if (data.close[0] >= 0.5*atr[0]) and haspos:
                # if (atr[0] >= atr[-1]) and haspos:
                # 分批进仓时加仓,已持仓,本日真实价格波动均值大于昨日
                # 效果不好???
                if (D[0] < 80) and self.buytimes[code] < 5:
                    # 加仓次数不超过2次,总共分三次入场
                    tradedict['flag'] = 'buy'
                    self.buytimes[code] += 1

        if (twap[0] >= data.close[0] and twap[-1] > data.close[-1]) and haspos:
            # 出场,未持仓则跳过本次卖出
            if D[0] > 20:
                tradedict['flag'] = 'sell'
                self.buytimes[code] = 0
        return tradedict

    def next_mtm(self, code, data):
        mtm = self.mtm[code]
        mamtm = self.mamtm[code]
        D = self.D[code]
        atr = self.atr[code]
        mom = self.mom[code]
        tradedict = dict(
            data=data,
            code=code,
            mom=mom[0],
        )
        pos = self.get_postion(code)
        haspos = utils.false
        if pos and pos.size > 0:
            haspos = utils.true

        # 动量指标大于平均动量指标,而且上一日小于平均动量指标
        if (mtm[0] > mamtm[0] and mtm[-1] <= mamtm[-1]) and not haspos:
            # 但处于超买时,不买入
            transaction = self.get_current_transaction(code, data)
            dtcp = data.num2date(data.datetime[0]) - transaction['dt']
            if (D[0] < 80) and (dtcp.days > self.p.orderholdperiod):
                tradedict['flag'] = 'buy'
                self.buytimes[code] = 1

        if self.p.weightflag == 'add':
            if (data.close[0] >= 0.5*atr[0]) and haspos:
                # if (atr[0] >= atr[-1]) and haspos:
                # 分批进仓时加仓,已持仓,本日真实价格波动均值大于昨日
                # 效果不好???
                transaction = self.get_current_transaction(code, data)
                dtcp = data.num2date(data.datetime[0]) - transaction['dt']
                if (D[0] < 80) and self.buytimes[code] < 5 and self.buytimes[code] > 0 and dtcp.days > 1:
                    tradedict['flag'] = 'buy'
                    self.buytimes[code] += 1

        rise = (
            (data.close[0] - data.close[-1]) / data.close[0])*100
        if not mtm[0]:
            return tradedict
        risemtm = ((mtm[0]-mtm[-1]) / mtm[0]) * 100
        # 价格上涨,mtm指标没有同步上涨,出现背离(根据百分比计算)
        if (mtm[0] > mamtm[0]) and haspos:
            # rise价格涨幅,mtm指标涨幅,价格涨幅高于mtm涨幅卖出
            if abs(rise) > abs(risemtm):
                # 当处于超卖时,不卖出
                if D[0] > 20:
                    tradedict['flag'] = 'sell'
                    self.buytimes[code] = 0
                    return tradedict

        if (mtm[0] < mamtm[0] or mtm[0] < 0) and haspos:
            if D[0] > 20:
                tradedict['flag'] = 'sell'
                self.buytimes[code] = 0

        return tradedict

    def next_round(self, code, data):
        # 趋势明显,不进行超买,超卖检查
        mom = self.mom[code]
        tradedict = dict(
            data=data,
            code=code,
            mom=mom[0],
        )
        self.holddays += 1
        if self.holddays % self.p.holdperiod != 0:
            return tradedict

        if mom[0] > 0:
            tradedict['flag'] = 'buy'
            self.buytimes[code] = 1
        return tradedict

    def get_last_order_dt(self, code):
        order = self.get_current_order(code)
        if order:
            orderdt = round(order.dteos)
        else:
            orderdt = 0
        return orderdt

    def next_boll(self, code, data):
        mid = self.bband[code].mid
        top = self.bband[code].top
        maxvolume = self.maxvolume[code]

        mom = self.mom[code]
        sma = self.sma[code]
        D = self.D[code]
        tradedict = dict(
            data=data,
            code=code,
            mom=mom[0],
        )
        close = data.close[0]
        pos = self.get_postion(code)
        haspos = utils.false
        if pos and pos.size > 0:
            haspos = utils.true

        if not haspos:
            if data.open[0] < mid[0] and close > mid[0] and data.volume[0] == maxvolume[0]:
                datadt = round(data.datetime[0])
                orderdt = self.get_last_order_dt(code)
                if (D[0] < 80) and (datadt - self.p.orderholdperiod > orderdt):
                    # 未处于超买,上次订单7️天之前,控制订单频率
                    tradedict['flag'] = 'buy'
                    self.buytimes[code] = 1
                    # 开盘价小于布林线中轨,收盘价突破布林线中轨,放量
        elif close < sma[0] or close > top[0]:
            # 跌破5日均线,或者收盘价>布林线上轨
            if D[0] > 20:
                tradedict['flag'] = 'sell'
                self.buytimes[code] = 0
        return tradedict

    def next_turtle(self, code, data):
        atr = self.atr[code]
        D = self.D[code]
        mom = self.mom[code]
        highest = self.highest[code]
        lowest = self.lowest[code]
        tradedict = dict(
            data=data,
            code=code,
            mom=mom[0],
        )
        pos = self.get_postion(code)
        haspos = utils.false
        stake = 0
        buyprice = 0
        if pos and pos.size > 0:
            haspos = utils.true
            buyprice = pos.price

        if highest[-1] > 0 and not haspos:
            stake = self.broker.getvalue() * 0.01 / atr[0]
            size = int(stake / 100) * 100
            datadt = round(data.datetime[0])
            orderdt = self.get_last_order_dt(code)
            if (D[0] < 80) and (datadt - self.p.orderholdperiod > orderdt):
                tradedict['flag'] = 'buy'
                tradedict['size'] = size
                self.buytimes[code] = 1
        # 加仓,趋势确认,加仓次数不超过3次
        elif data.close[0] > buyprice+0.5*atr[0] and self.buytimes[code] > 0 and self.buytimes[code] < 5:
            stake = self.broker.getvalue() * 0.01 / atr[0]
            size = int(stake / 100) * 100
            if D[0] < 80:
                tradedict['flag'] = 'buy'
                tradedict['size'] = size
                self.buytimes[code] += 1
        # 出场,跌破唐奇安下轨,持仓
        elif lowest[-1] < 0 and self.buytimes[code] > 0:
            if D[0] > 20:
                tradedict['flag'] = 'sell'
                self.buytimes[code] = 0
        # 止损,趋势反转,持仓
        elif data.close[0] < (buyprice - 2*atr[0]):
            if D[0] > 20:
                tradedict['flag'] = 'sell'
                self.buytimes[code] = 0
        return tradedict


# 跟随北向资金 + 动量策略
# 效果不好,参数不对???

class FollowWestFundsStrategy(CMIStrategy):
    def get_ggt_top10(self, days=15):
        # 获取北向资金,十大成交股,前15天净买入
        today = self.get_datetime()
        lastday = utils.get_last_trade_day(today, _type='datetime')
        endtime = int(lastday.timestamp())
        starttime = endtime - days * 60 * 60 * 24
        dbname = 'ggt'
        ggtypes = ['sgtjme', 'hgtjme']
        dfs = []
        for ggtype in ggtypes:
            wheres = [
                {'k': 'timestamp', 'v': starttime, 'op': '>='},
                {'k': 'timestamp', 'v': endtime, 'op': '<='},
                {'k': ggtype, 'v': 0, 'op': '>'},
            ]
            df = self.p.db.select(dbname, wheres=wheres)
            dfs.append(df)
        df = utils.contact_pandas(dfs)
        if df.empty:
            return []
        da = df.groupby(by='code').size()
        da.sort_values(ascending=utils.false, inplace=utils.true)
        codes = [i for i, j in da.items() if j > 2]
        return codes


class VWAPStrategy(BaseStrategy):
    # 趋势跟踪
    # 动量策略 + 二八轮动
    # 指数基金+动量轮动+趋势跟踪+量化交易+机械执行+适当分散
    # 动量轮动: https://www.jisilu.cn/question/365575
    # https://www.jisilu.cn/question/370597
    # http://17fx.net/F2020/b_demo.aspx
    params = dict(
        period=3,
        # momperiod=21,
    )

    def __init__(self):
        self.vwap = cinds.VWAP(period=self.p.period)
        # self.mvwap = bt.ind.SMA(self.vwap, period=self.p.momperiod)
        self.D = self.get_d_value(self.data)

    def next(self):
        if self.vwap[0] <= self.data.close[0] and self.vwap[-1] > self.data.close[-1]:
            # if self.vwap[0] >= self.mvwap[0] and self.vwap[-1] < self.mvwap[-1]:
            target = 0.95
            if self.D[0] > 80:
                return
            self.order_target_percent(data=self.data, target=target)

        if self.vwap[0] > self.data.close[0] and self.vwap[-1] > self.data.close[-1]:
            # if self.vwap[0] < self.mvwap[0] and self.vwap[-1] >= self.mvwap[-1]:
            if self.D[0] < 20:
                return
            target = 0
            self.order_target_percent(data=self.data, target=target)


class SmaCrossStrategy(BaseStrategy):
    # 均线交叉策略
    params = dict(
        pfast=5,
        pslow=20,
        printlog=utils.true,
    )

    def __init__(self):
        self.sma1 = bt.ind.SMA(period=self.p.pfast)
        self.sma2 = bt.ind.SMA(period=self.p.pslow)
        self.crossover = bt.ind.CrossOver(self.sma1, self.sma2)

    def next(self):
        close = self.data.close[0]
        if not self.position:
            if self.crossover > 0:
                self.log('BUY CREATE, %s, 买入:股' % (self.data.close[0]))
                self.buy(size=200, price=close)
        elif self.crossover < 0:
            self.log('SELL CREATE, %s, 买入: 股' % (self.data.close[0]))
            self.sell(size=200, price=close)


class SmaStrategy(BaseStrategy):
    # 简单均线策略
    # 改进的均线择时: https://xueqiu.com/2401362725/63115081
    params = dict(
        period=5,
        printlog=utils.true,
    )

    def __init__(self):
        # 真实强弱指数
        # self.inds = ['mtm', 'mom']
        # super(SmaStrategy, self).__init__()
        bt.ind.Averageutils.trueRange()

        self.sma = bt.ind.SimpleMovingAverage(
            self.datas[0], period=self.p.period)

    def next(self):
        close = self.data.close[0]
        # print(close, self.sma[0])
        if close >= self.sma[0]:
            self.log('BUY CREATE, %.2f' % close)
            self.order = self.buy()
        if close < self.sma[0]:
            self.log('SELL CREATE, %.2f' % close)
            self.order = self.sell()


# %%

# 定投策略
class SchedStrategy(BaseStrategy):
    params = dict(
        printlog=utils.false,
        petype='',  # 市盈率类型,pe,pe_ttm,pb,''
        perrise=0.25,
        minrise=0.25,
        maxrise=2.5,
        buysize=100,
        sellsize=100,

        momoscperiod=1,
        smaperiod=16,
    )

    def __init__(self):
        self.inds = ['momosc', 'D']
        self.hasdones = {}
        self.pretrades = []
        super(SchedStrategy, self).__init__()

    def next(self):
        if self.p.optpass:
            return

        tradelst = []
        for data in self.datas:
            code = utils.get_code_string(data.code[0])
            datadt = self.data.num2date(data.datetime[0])

            if self.p.multiperiod:
                pretrades = self.get_pre_trades()
                trade = pretrades.get(code, {})
                intradetime = datadt.hour == 14 and datadt.minute == 45
                # 构造当天数据,14:45时,根据此时收盘价进行判断
                if intradetime and pretrades and trade:
                    tdatadt = trade['datetime']
                    if datadt.date() != tdatadt.date():
                        # 过滤不是当天订单
                        continue
                    now = datetime.now()
                    if datadt.date() == now.date() and self.p._live:
                        # 当天订单,且实盘,只处理14:45时间
                        df = self.getdatabyname(data._name)
                        last = df.p.dataname.timestamp[-1]
                        tp = int(datadt.timestamp())
                        if last != tp:
                            continue
                    flag = trade['flag']
                    size = trade['size']
                    # print(trade)
                    if flag == 'buy':
                        price = data.close[0]
                        print(datadt, price)
                        self.order = self.buy(data, size=size)
                        # self.order = self.buy(data, size=size, price=price, exectype=bt.Order.Limit)
                    else:
                        self.order = self.sell(data, size=size)
                    continue
                # 过滤5分钟k线
                if self.p.multiperiod in data._name:
                    continue

                dones = self.hasdones.get(code, [])
                datalen = len(data)
                if datalen in dones:
                    continue
                dones.append(datalen)
                self.hasdones.update({code: dones})

            momosc = self.momosc[code]
            pricerise = momosc[0]
            tradedict = dict(
                data=data,
                code=code,
                mom=pricerise,
                datetime=datadt,
            )

            # if (9 < dt.hour < 14) or (dt.hour >= 14 and dt.minute < 45):

            # 盘中检查
            if (pricerise < self.p.minrise or datadt.weekday() == 4):
                # 检查今日是否已购买
                tradesize = self.get_trade_size(pricerise, 'buy')
                tradedict['flag'] = 'buy'
                tradedict['size'] = tradesize
                tradelst.append(tradedict)
                # import ipdb; ipdb.set_trace()

            if pricerise > self.p.maxrise:
                tradesize = self.get_trade_size(pricerise, 'sell')
                tradedict['flag'] = 'sell'
                tradedict['size'] = tradesize
                tradelst.append(tradedict)

        if self.p.multiperiod:
            # 确定次序
            for trade in tradelst:
                self.pretrades.append(trade)
        else:
            for trade in tradelst:
                flag = trade['flag']
                size = trade['size']
                if flag == 'buy':
                    self.order = self.buy(data, size=size)
                else:
                    self.order = self.sell(data, size=size)

            # if self.bband.bot[0] > self.data.close[0]:
            #     tradesize = self.get_trade_size(pricerise, 'buy')
            #     self.order = self.buy(size=tradesize, price=close)

            # if self.bband.top[0] < self.data.close[0]:
            #     # 突破布林带上轨
            #     tradesize = self.get_trade_size(pricerise, 'sell')
            #     self.order = self.sell(size=tradesize, price=close)

            # elif (14 <= dt.hour < 15) and (45 < dt.minute < 55):
            #     # 盘尾加仓,类似定投,积累足够筹码
            #     if pricerise < -self.p.perrise:
            #         buykey = '{0}:{1}'.format(key, 'buy')
            #         buycount = self.orders.get(buykey, 0)
            #         if buycount < 2:
            #             tradesize = self.get_trade_size(pricerise)
            #             # buysize = self.p.buysize
            #             self.log('BUY CREATE, %s, 买入: %.1f股' % (msg, tradesize))
            #             self.order = self.buy(size=tradesize)
            #             buycount += 1
            #             self.orders[buykey] = buycount

    def get_d_times(self, flag):
        # 超买,超卖检查
        d_times = 1
        code = utils.get_code_string(self.data.code[0])
        drate = self.D[code][0]
        if flag == 'buy':
            if drate > 80:
                d_times = 80 / drate
            if drate < 20:
                d_times = 20 / drate
        elif flag == 'sell':
            if drate < 20:
                d_times = drate / 20
            if drate > 80:
                d_times = drate / 80
        return d_times

    def get_trade_size(self, pricerise, flag):
        # 根据大盘上证综指PETTM估值判断
        # PE估值近期对159928影响小
        if flag == 'buy' and pricerise > 0:
            return 100
        petimes = self.get_pe_times(flag)
        # 大跌大买,小跌小买
        # 大涨大卖,小涨小卖
        dtimes = self.get_d_times(flag)
        postimes = self.get_pos_times(flag)
        tradetimes = abs(pricerise / self.p.perrise) * \
            petimes * dtimes * postimes
        tradesize = math.ceil(self.p.buysize * tradetimes / 100) * 100
        return tradesize

    def get_offset(self):
        # dt = self.get_datetime()
        # dtcompare = datetime.datetime(dt.year, dt.month, dt.day, 9, 30)
        # offsetseconds = (dt - dtcompare).total_seconds()
        # offset = int(offsetseconds / 60 / 5)
        offset = 1
        return offset

    def get_pos_times(self, flag):
        # 不止损,持仓亏损,卖出0.3
        postimes = 1
        if flag == 'sell':
            pos = self.getposition()
            if pos:
                if pos.price_orig < self.data.close[0]:
                    postimes = 0.3
        return postimes

    def get_pe_times(self, flag):
        # 历史百分位计算: https://xueqiu.com/4579887327/142536174
        # https://zhuanlan.zhihu.com/p/53315314
        # https://eniu.com/gu/sh000001
        # https://www.jianshu.com/p/7d776567c473
        # http://www.sse.com.cn/market/stockdata/statistic/
        # http://www.csindex.com.cn/zh-CN/downloads/index-information
        # https://legulegu.com/stockdata/shanghaiPE
        # https://www.iguuu.com/market/board
        # https://androidinvest.com/chinaindicespe/sh000001/
        # https://danjuanapp.com/djmodule/value-center
        # 目前历史估值水平=(当前市盈率-历史最小)/(历史最高-历史最小)
        # 当前市盈率与平均市盈率比较,以上证指数为基准
        # 当前市盈率大于平均市盈率,买入少,卖出多
        # 小于平均市盈率,买入多,卖出少

        # 估值判断
        if self.p.petype == '':
            return 1
        dbname = 'index_dailybasic'
        dt = self.get_datetime()
        start = dt + timedelta(days=-365)
        start_date = utils.get_datetime_date(start)
        end_date = utils.get_datetime_date(dt)
        wheres = [
            {'k': 'ts_code', 'v': '000001.SH', 'op': '='},
            {'k': 'trade_date', 'v': start_date, 'op': '>='},
            {'k': 'trade_date', 'v': end_date, 'op': '<='},
        ]
        orderby = 'trade_date desc'
        df = self.p.db.select(dbname, wheres=wheres, orderby=orderby)
        pe = df[self.p.petype].values[0]
        avepe = sum(df[self.p.petype]) / len(df)
        petimes = 0
        if pe >= avepe:
            # 估值高,买的少,卖的多
            if flag == 'buy':
                petimes = avepe / pe * 0.75
                # petimes = 0.75
            else:
                petimes = pe / avepe * 1.25
                # petimes = 1.25
        else:
            # 估值低,买的多,买的少
            if flag == 'buy':
                petimes = pe / avepe * 1.25
                # petimes = 1.25
            else:
                petimes = avepe / pe * 0.75
                # petimes = 0.75
        return petimes

# %%


class TestSizer(bt.Sizer):
    params = (('stake', 1),)

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            return self.p.stake
        position = self.broker.getposition(data)
        if not position.size:
            return 0
        else:
            return position.size
        return self.p.stakeclass

# 海龟交易具体策略
# https://blog.csdn.net/trader_python/category_6470335.html
# https://zhuanlan.zhihu.com/p/114782214
# 入场：最新价格为20日价格高点，买入一单元股票
# 加仓：最新价格>上一次买入价格+0.5*ATR，买入一单元股票，最多3次加仓
# 出场：最新价格为10日价格低点，清空仓位
# 止损：最新价格<上一次买入价格-2*ATR，清空仓位

# 建仓单位：Unit=(1%∗账户总资金)/N
# 建仓单位的意义就是，让一个N值的波动与你总资金1%的波动对应，如果买入1unit单位的资产，当天震幅使得总资产的变化不超过1%。

# 海龟策略是一个高风险高收益的，基于投资组合的中低频趋势跟踪策略


class TurtleStrategy(BaseStrategy):
    params = dict(
        upperiod=20,
        downperiod=10,
        maperiod=14,
        printlog=utils.true,
        orderlog=utils.true,
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.D = self.get_d_value(self.data)

        self.order = None
        self.buyprice = 0
        self.buycomm = 0
        self.newstake = 0
        self.buytime = 0
        # 参数计算，唐奇安通道上轨、唐奇安通道下轨、ATR
        # 唐奇安上阻力线 - 由过去N天的当日最高价的最大值，Max(最高价，N)
        self.DonchianHi = bt.ind.Highest(
            self.datahigh(-1), period=self.p.upperiod, subplot=utils.false)
        # 唐奇安下支撑线 - 由过去M天的当日最低价的最小值形成，Min(最低价，M）
        self.DonchianLo = bt.ind.Lowest(
            self.datalow(-1), period=self.p.downperiod, subplot=utils.false)
        # 真实波动幅度(TR), utils.trueRange（TR）=Max(High−Low,High−PreClose,PreClose−Low)
        # self.atr = bt.ind.Averageutils.trueRange()
        # self.tr = bt.ind.TrueRange()

        self.TR = bt.ind.Max((self.datahigh(0) - self.datalow(0)), abs(
            self.dataclose(-1) - self.datahigh(0)), abs(self.dataclose(-1) - self.datalow(0)))
        # 真实波动幅度均值ATR(N值）,ATR=MA(TR,M)，即对真实波幅TR进行N日移动平均计算。
        # self.atr = cinds.ATR(self.data)
        self.ATR = bt.ind.SimpleMovingAverage(
            self.TR, period=self.p.maperiod, subplot=utils.true)
        # 唐奇安通道上轨突破、唐奇安通道下轨突破
        self.CrossoverHi = bt.ind.CrossOver(self.dataclose(0), self.DonchianHi)
        self.CrossoverLo = bt.ind.CrossOver(self.dataclose(0), self.DonchianLo)

    def next(self):
        # if self.order:
        #     return
        # 入场,突破唐奇安上轨,未持仓
        if self.CrossoverHi > 0 and self.buytime == 0:
            self.newstake = self.broker.getvalue() * 0.01 / self.ATR
            self.newstake = int(self.newstake / 100) * 100
            self.sizer.p.stake = self.newstake
            if self.D[0] > 80:
                return
            self.buytime = 1
            self.order = self.buy()
        # 加仓,趋势确认,加仓次数不超过3次
        elif self.datas[0].close > self.buyprice+0.5*self.ATR[0] and self.buytime > 0 and self.buytime < 5:
            self.newstake = self.broker.getvalue() * 0.01 / self.ATR
            self.newstake = int(self.newstake / 100) * 100
            self.sizer.p.stake = self.newstake
            if self.D[0] > 80:
                return
            self.order = self.buy()
            self.buytime = self.buytime + 1
        # 出场,跌破唐奇安下轨,持仓
        elif self.CrossoverLo < 0 and self.buytime > 0:
            if self.D[0] < 20:
                return
            self.order = self.sell()
            self.buytime = 0
        # 止损,趋势反转,持仓
        elif self.datas[0].close < (self.buyprice - 2*self.ATR[0]) and self.buytime > 0:
            if self.D[0] < 20:
                return
            self.order = self.sell()
            self.buytime = 0

# %%


if __name__ == '__main__':
    pass
