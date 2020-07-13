# %%
import utils
import json
import backtrader as bt
import pandas as pd
import os
import math
from datetime import timedelta
from pprint import pprint

import indicators as cinds
import talib

import models

# http://www.topquant.vip/?p=1703
# http://www.topquant.vip/?p=56

# %%
# multi strategy: https://community.backtrader.com/topic/2122/live-trading-multiple-strategies-each-one-on-a-separate-data-feed/101
# %%
true = True
false = False

# %%


class BaseStrategy(bt.Strategy):
    params = dict(
        printlog=false,
        doprint=false,
        tradelog=false,
        orderlog=false,
        tradestrats={},
        orderstrats={},

        pks='',  # 以下为优化参数使用
        db=None,
        dbname='',
        optpass=false,  # 是否跳过本次策略
        code=0,  # 检查是否执行过策略
        _type='',
        start='',  # 多周期参数优化
    )

    def __init__(self, inds=[]):
        if inds:
            self.set_inds(inds)

    def set_inds(self, inds):
        for ind in inds:
            setattr(self, ind, {})
        for data in self.datas:
            code = utils.get_code_string(data.code[0])
            for ind in inds:
                if ind == 'mom':
                    # 动量指标,与前N日价格比较*100
                    self.__dict__[ind][code] = cinds.MOM(
                        data=data, period=self.p.mperiod)
                elif ind == 'ad':
                    # Chaikin A/D Oscillator Chaikin震荡指标,将资金流动情况与价格行为相对比，检测市场中资金流入和流出的情况
                    self.__dict__[ind][code] = bt.talib.AD(
                        data.high, data.low, data.close, data.volume)
                elif ind == 'adosc':
                    # Chaikin A/D Oscillator Chaikin震荡指标,将资金流动情况与价格行为相对比，检测市场中资金流入和流出的情况
                    self.__dict__[ind][code] = bt.talib.ADOSC(
                        data.high, data.low, data.close, data.volume, fastperiod=3, slowperiod=10)
                elif ind == 'atr':
                    self.__dict__[ind][code] = cinds.ATR(data=data, period=14)
                elif ind == 'willr':
                    # 威廉指标 (%R) 可帮助识别超买位和超卖位,高于-20处于超买,低于-80为超卖
                    self.__dict__[ind][code] = cinds.WilliamsR()
                elif ind == 'kama':
                    # 自适应移动均线,可用于止损
                    self.__dict__[ind][code] = cinds.KAMA()
                elif ind == 'tsi':
                    # 指示超买,超卖,大于25处于超买,小于-25处于超卖,TSI可帮助判断市场趋势
                    self.__dict__[ind][code] = cinds.TSI()
                elif ind == 'mtm':
                    self.__dict__[ind][code] = bt.talib.MOM(
                        data, timeperiod=self.p.mtmperiod)
                elif ind == 'mamtm':
                    self.__dict__[ind][code] = bt.ind.SMA(
                        self.__dict__['mtm'][code], period=self.p.mamtmperiod)
                elif ind == 'D':
                    # KDJ,D值指示超买,超卖,大于80处于超买,小于20处于超卖
                    self.__dict__[ind][code] = self.get_d_value(data=data)
                elif ind == 'twap':
                    # TWAP,Time Weighted Average Price,时间加权平均价格算法
                    self.__dict__[ind][code] = cinds.TWAP(
                        data=data, period=self.p.period)
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
        # if self.cerebro.params.live:
        #     # 实盘下单,保存订单
        #     self.do_and_save_order(order)
        # import ipdb; ipdb.set_trace()

        msgdict = {
            '日期': utils.get_datetime_date(self.data.num2date(order.executed.dt), flag='-'),
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
                msgdict['买卖方向'] = '买入'
                if self.p.orderlog:
                    # 价格不一致???
                    print(msgdict)
            else:
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

    def do_and_save_order(self, order):
        msg = ''
        if self.position.size > 0:
            msg = '买入'
        else:
            msg = '卖出'
        print(msg, self.position.__dict__)
        import ipdb
        ipdb.set_trace()

    def get_weight(self, datas, add=false):
        weight = []
        datalen = len(datas)
        if not add:
            if datalen >= 3:
                weight = [0.5, 0.3, 0.15]
            elif datalen == 2:
                weight = [0.6, 0.35]
            else:
                weight = [0.95]
        else:
            if datalen >= 3:
                weight = [0.15, 0.1, 0.05]
            elif datalen == 2:
                weight = [0.2, 0.1]
            else:
                weight = [0.3]
        return weight

    def notify_trade(self, trade):
        pass
        # 成交收益,次数,胜率,金额,输出市值,手续费
        # if trade.isopen:
        #     count = self.p.tradestrats.get('total', 0) + 1
        #     self.p.tradestrats['total'] = count
        # if trade.isclosed:
        #     # 净收益(去除手续费)
        #     if self.p.tradelog:
        #         msg = 'NOTIFY TRADE, 日期:{}, 收益:{:.3f}, 净收益:{:.3f}, 手续费:{:.3f}'.format(
        #             utils.get_datetime_date(self.get_datetime()),
        #             trade.pnl, trade.pnlcomm, trade.commission)
        #         print(msg)
        #     if trade.pnlcomm > 0:
        #         count = self.p.tradestrats.get('win', 0) + 1
        #         self.p.tradestrats['win'] = count
        #         count = self.p.tradestrats.get('win_value', 0) + trade.pnlcomm
        #         self.p.tradestrats['win_value'] = count
        #     else:
        #         count = self.p.tradestrats.get('lose', 0) + 1
        #         self.p.tradestrats['lose'] = count
        #         count = self.p.tradestrats.get(
        #             'lose_value', 0) + trade.pnlcomm
        #         self.p.tradestrats['lose_value'] = count

    def get_postion(self, code):
        for data, pos in self.positions.items():
            poscode = utils.get_code_string(data.code[0])
            if poscode == code:
                return pos
        return None
        # value = self.broker.getvalue()
        # availablevalue = self.broker.getcash()
        # print('日期:{}, 账户余额:{:.3f}, 可用余额:{:.3f}'.format(
        #     self.data.datetime.date(), value, availablevalue))
        # if not datas:
        #     datas = self.datas
        # for data in datas:
        #     pos = self.getposition(data)
        #     if pos and pos.size > 0:
        #         msg = '{}, 持仓:{}, 成本价:{:.3f}, 当前价:{:.3f}, 盈亏:{:.3f}, 总市值:{:.3f}'.format(
        #             code,
        #             pos.size,
        #             pos.price,
        #             pos.adjbase,
        #             pos.size * (pos.adjbase - pos.price),
        #             pos.size * pos.adjbase,
        #         )
        #         print(msg)
        #         return pos

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

    def get_datetime(self):
        return self.datetime.datetime(0)

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
        self.p.optpass = true
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
        failrate = utils.get_float(fail/total)
        self.p.orderstrats = dict(total=total, fail=fail, failrate=failrate)

        tradestrats = []
        for i, j in self._trades.items():
            trades = j[0]
            code = utils.get_code_string(i.code[0])
            wincount = 0
            winvalue = 0.0
            losevalue = 0
            winrate = 0.0
            if trades:
                for trade in trades:
                    if trade.pnlcomm > 0:
                        wincount += 1
                        winvalue += trade.pnlcomm
                    else:
                        losevalue += trade.pnlcomm
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

        # 更新参数
        if self.p.tradelog:
            pprint(tradestrats)
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
        printlog=true,
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
        printlog=true,
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
        p_oneplot=false,      # 是否打印到同一张图
        pstake=1000,          # 单笔交易股票数
        printlog=false,          # 单笔交易股票数
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
        period=5,
    )

    def __init__(self):
        self.twap = cinds.TWAP(data=self.data, period=self.p.period)
        self.D = self.get_d_value(self.data)

    def next(self):
        if self.twap[0] <= self.data.close[0] and self.twap[-1] > self.data.close[-1]:
            target = 0.95
            if self.D[0] > 80:
                return
            if self.position.size > 0:
                return
            self.order_target_percent(
                data=self.data, target=target, price=self.data.close[0])

        if self.twap[0] >= self.data.close[0] and self.twap[-1] > self.data.close[-1]:
            if self.D[0] < 20:
                return
            if self.position.size <= 0:
                return
            target = 0
            self.order_target_percent(
                data=self.data, target=target, price=self.data.close[0])

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
    )

    def __init__(self, inds=[]):
        self.inds = ['mtm', 'D', 'mamtm']
        super(MtmStrategy, self).__init__(self.inds)

    def next(self):
        for data in self.datas:
            code = utils.get_code_string(data.code[0])
            mtm = self.mtm[code]
            mamtm = self.mamtm[code]
            D = self.D[code]
            # 动量指标大于平均动量指标,而且上一日小于平均动量指标
            if mtm[0] > mamtm[0] and mtm[-1] <= mamtm[-1]:
                target = 0.95
                # 但处于超买时,不买入
                if D[0] > 80:
                    continue
                self.order_target_percent(data, target=target)

            rise = (
                (data.close[0] - data.close[-1]) / data.close[0])*100
            if not mtm:
                # mtm值为0
                continue
            risemtm = ((mtm[0]-mtm[-1]) / mtm[0]) * 100
            # 价格上涨,mtm指标没有同步上涨,出现背离(根据百分比计算)
            if mtm[0] > mamtm[0]:
                # rise价格涨幅,mtm指标涨幅,价格涨幅高于mtm涨幅卖出
                if abs(rise) > abs(risemtm):
                    # 当处于超卖时,不卖出
                    if D[0] < 20:
                        continue
                    self.order_target_percent(data, target=0)

            if mtm[0] < mamtm[0] or mtm[0] < 0:
                if D[0] < 20:
                    continue
                self.order_target_percent(data, target=0)

# TODO: 闲置资金买入债券

# twap指标确认进场,出场,分批进场
# atr指标确认趋势,两次加仓机会
# D指标超买,超卖检查


class TWAPMultiStrategy(BaseStrategy):
    params = dict(
        period=3,
        mperiod=13,
        add=true,  # 是否分批加仓
    )

    def __init__(self, inds=[]):
        if inds:
            self.inds = inds
        else:
            self.inds = ['twap', 'D', 'mom', 'atr']
        super(TWAPMultiStrategy, self).__init__(self.inds)

    def next(self):
        tradelst = []
        # codes = self.get_ggt_top10(days=30)
        for data in self.datas:
            code = utils.get_code_string(data.code[0])
            twap = self.twap
            D = self.D
            atr = self.atr
            # if code not in codes:
            #     continue
            tradedict = dict(
                data=data,
                code=code,
                mom=self.mom[code][0],
            )
            pos = self.get_postion(code)
            haspos = false
            if pos and pos.size > 0:
                haspos = true

            if twap[code][0] <= data.close[0] and twap[code][-1] > data.close[-1] and not haspos:
                # 进场,未持仓
                if D[code][0] < 80:
                    tradedict['flag'] = 'buy'
                    tradelst.append(tradedict)

            if self.p.add:
                if atr[code][0] >= atr[code][-1] and haspos:
                    # 分批进仓时加仓,已持仓,本日真实价格波动均值大于昨日
                    # 效果不好???
                    if D[code][0] < 80:
                        tradedict['flag'] = 'buy'
                        tradelst.append(tradedict)

            if twap[code][0] >= data.close[0] and twap[code][-1] > data.close[-1] and haspos:
                # 出场,未持仓则跳过本次卖出
                if D[code][0] > 20:
                    tradedict['flag'] = 'sell'
                    tradelst.append(tradedict)

        # 动量指标确定权重
        tradelst = sorted(tradelst, key=lambda x: x['mom'], reverse=true)

        self.weight = self.get_weight(tradelst, add=self.p.add)
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

        # # 买入债券
        # if percent > 0.1 or not tradelst:
        #     data = self.datas[-1]
        #     size = self.get_target_size(data, percent)
        #     self.order = self.sell(data=data, size=size)

    def check_next(self, order):
        # 买入失败订单处理
        pass
        # if order.__class__.__name__ == 'BuyOrder' and order.status == 7:
        #     self.order = self.buy(data=order.data, size=order.size)

# 跟随北向资金 + 动量策略
# 效果不好,参数不对???


class FollowWestFundsStrategy(TWAPMultiStrategy):
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
        da.sort_values(ascending=false, inplace=true)
        codes = [i for i, j in da.items() if j > 2]
        return codes

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
        mperiod=17,
        holdperiod=3,
    )

    def __init__(self):
        self.holodays = 0

        # self.mom = [bt.ind.MomentumOscillator(
        #     i, period=self.p.mperiod) for i in self.datas]

        self.inds = ['mom']
        super(RoundStrategy, self).__init__(self.inds)

    def mom_weight(self):
        checkperiod = self.holodays % self.p.holdperiod
        self.holodays += 1
        if checkperiod != 0:
            return

        buyitems = [(i, j) for i, j in self.mom.items() if j > 100]
        buyitems = sorted(buyitems, key=lambda x: x[1][0], reverse=true)
        # 没有动量,买入债券
        if not buyitems:
            code = utils.get_code_string(self.datas[-1].code[0])
            buyitems.append((code, ))
        codes = [i[0] for i in buyitems[:2]]
        # 根据买入数量确认权重
        self.weight = self.get_weight(codes)
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
        needbuys.sort(key=lambda x: x[0], reverse=true)
        needbuys = needbuys[:2]
        # 动量不足,持有债券,根据权重1
        if not needbuys:
            needbuys.append(moms[-1])
        weight = self.get_weight(needbuys)
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


class VWAPStrategy(BaseStrategy):
    # 趋势跟踪
    # 动量策略 + 二八轮动
    # 指数基金+动量轮动+趋势跟踪+量化交易+机械执行+适当分散
    # 动量轮动: https://www.jisilu.cn/question/365575
    # https://www.jisilu.cn/question/370597
    # http://17fx.net/F2020/b_demo.aspx
    params = dict(
        period=3,
        # mperiod=21,
    )

    def __init__(self):
        self.vwap = cinds.VWAP(period=self.p.period)
        # self.mvwap = bt.ind.SMA(self.vwap, period=self.p.mperiod)
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
        printlog=true,
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
        printlog=true,
    )

    def __init__(self):
        # 真实强弱指数
        # self.inds = ['mtm', 'mom']
        # super(SmaStrategy, self).__init__(self.inds)
        bt.ind.AveragetrueRange()

        self.sma = bt.ind.SimpleMovingAverage(
            self.datas[0], period=self.p.period)

    def next(self):
        import ipdb
        ipdb.set_trace()
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
        printlog=false,
        petype='',  # 市盈率类型,pe,pe_ttm,pb,''
        perrise=0.75,
        minrise=-0.25,
        maxrise=2.5,
        buysize=100,
        sellsize=100,
    )

    def __init__(self):
        self.orders = {}
        self.bband = bt.ind.BBands(self.data.close)  # top,bot,mid 布林线上轨,下轨,中轨
        self.D = self.get_d_value()  # KDJ,D值,超买&超卖检查

    def next(self):
        if self.p.optpass:
            return
        dt = self.get_datetime()
        if (self.cerebro.params.live):
            # 实盘
            pretimestamp = utils.get_last_trade_day(_type='timestamp')
            if not pretimestamp:
                msg = '没有前一日交易日期,跳过'
                self.log(msg)
                return
            code = self.data.code[0]
            wheres = [
                {'k': 'code', 'v': utils.get_code_string(code), 'op': '='},
                {'k': 'timestamp', 'v': pretimestamp, 'op': '='},
            ]
            dbname = 'k_data'
            df = self.p.db.select(dbname, wheres=wheres)
            if df.empty:
                msg = '没有前一日交易信息,跳过'
                self.log(msg)
                return
            preclose = df['close'].values[0]
        else:
            offset = self.get_offset()
            try:
                preclose = self.data.close[-offset]
                predatetime = self.datetime.datetime(-offset)
                if predatetime.day == dt.day:
                    msg = '没有前一日收盘价,跳过'
                    self.log(msg)
                    return
            except Exception as ex:
                self.log(ex)
                return

        close = self.data.close[0]
        pricerise = ((close - preclose) / close) * 100
        msg = '开盘价{:.3f}, 收盘价:{:.3f}, 上一日收盘价:{:.3f}, 涨幅:{:.3f}'.format(
            self.data.open[0], close, preclose, pricerise)
        key = utils.get_datetime_date(dt, flag='-')

        # if (9 < dt.hour < 14) or (dt.hour >= 14 and dt.minute < 45):

        # 盘中检查
        if pricerise < self.p.minrise:
            # 检查今日是否已购买
            buykey = '{0}:{1}'.format(key, 'buy')
            buycount = self.orders.get(buykey, 0)
            if buycount < 1:
                tradesize = self.get_trade_size(pricerise, 'buy')
                self.order = self.buy(size=tradesize, price=close)
                buycount += 1
                self.orders[buykey] = buycount
        elif pricerise > self.p.maxrise:
            sellkey = '{0}:{1}'.format(key, 'sell')
            sellcount = self.orders.get(sellkey, 0)
            if sellcount < 1:
                tradesize = self.get_trade_size(pricerise, 'sell')
                self.order = self.sell(size=tradesize, price=close)
                sellcount += 1
                self.orders[sellkey] = sellcount

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

    def get_offset(self):
        # dt = self.get_datetime()
        # dtcompare = datetime.datetime(dt.year, dt.month, dt.day, 9, 30)
        # offsetseconds = (dt - dtcompare).total_seconds()
        # offset = int(offsetseconds / 60 / 5)
        offset = 1
        return offset

    def get_trade_size(self, pricerise, flag):
        # 根据大盘上证综指PETTM估值判断
        # PE估值近期对159928影响小
        petimes = self.get_pe_times(flag)
        # 大跌大买,小跌小买
        # 大涨大卖,小涨小卖
        dtimes = self.get_d_times(flag)
        postimes = self.get_pos_times(flag)
        tradetimes = abs(pricerise / self.p.perrise) * \
            petimes * dtimes * postimes
        tradesize = math.ceil(self.p.buysize * tradetimes / 100) * 100
        return tradesize

    def get_pos_times(self, flag):
        postimes = 1
        if flag == 'sell':
            pos = self.getposition()
            if pos:
                # 不止损
                if pos.price_orig < self.data.close[0]:
                    postimes = 0.3
        return postimes

    def get_d_times(self, flag):
        # 超买,超卖检查
        d_times = 1
        if flag == 'buy':
            if self.D[0] > 80:
                # d_times = 80 / self.D[0] / 1.5
                d_times = 80 / self.D[0]
            if self.D[0] < 20:
                d_times = 20 / self.D[0]
        elif flag == 'sell':
            if self.D[0] < 20:
                # d_times = self.D[0] / 20 / 1.5
                d_times = self.D[0] / 20
            if self.D[0] > 80:
                d_times = self.D[0] / 80
        return d_times

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
        printlog=true,
        orderlog=true,
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
            self.datahigh(-1), period=self.p.upperiod, subplot=false)
        # 唐奇安下支撑线 - 由过去M天的当日最低价的最小值形成，Min(最低价，M）
        self.DonchianLo = bt.ind.Lowest(
            self.datalow(-1), period=self.p.downperiod, subplot=false)
        # 真实波动幅度(TR), trueRange（TR）=Max(High−Low,High−PreClose,PreClose−Low)
        # self.atr = bt.ind.AveragetrueRange()
        self.tr = bt.ind.trueRange()

        self.TR = bt.ind.Max((self.datahigh(0) - self.datalow(0)), abs(
            self.dataclose(-1) - self.datahigh(0)), abs(self.dataclose(-1) - self.datalow(0)))
        # 真实波动幅度均值ATR(N值）,ATR=MA(TR,M)，即对真实波幅TR进行N日移动平均计算。
        # self.atr = cinds.ATR(self.data)
        self.ATR = bt.ind.SimpleMovingAverage(
            self.TR, period=self.p.maperiod, subplot=true)
        # 唐奇安通道上轨突破、唐奇安通道下轨突破
        self.CrossoverHi = bt.ind.CrossOver(self.dataclose(0), self.DonchianHi)
        self.CrossoverLo = bt.ind.CrossOver(self.dataclose(0), self.DonchianLo)

    def next(self):
        import ipdb
        ipdb.set_trace()
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


# %%


# %%


def backtest(cash, codes, periods):
    cerebro = bt.Cerebro()

    start = '2017-06-01'
    for code in codes:
        df = utils.get_database_data(code, start)
        if df.empty:
            print(code, 'missing')
            continue
        data = models.PandasData(dataname=df)
        cerebro.adddata(data)
    cerebro.addstrategy(
        RoundStrategy,
        period=periods,
        doprint=true,
        orderlog=false,
    )
    utils.addanalyzer(cerebro)
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(0.0001)

    cerebro.run(maxcpus=1)
    # cerebro.plot()

# %%


if __name__ == '__main__':
    # 上证50,沪深300,创业板,债券,白银
    # 沪深300ETF（510300）、创业板（159915）、银华日利（511880）
    # codes = ['510050', '163407', '159915', '161716', '161226']
    # codes = ['510300', '159915', '511880']
    # codes = ['510300']
    # 沪深300,创业板,主要消费,互联网50,纳指,白银,债券
    # codes = ['163407', '159915', '159928',
    #          '513050', '159941', '161226', '511880']
    # codes = ['163407', '159915', '512900', '161716']
    codes = ['163407', '159915', '161716']
    cash = 20000
    # periods = range(3, 50)
    periods = 13
    backtest(cash, codes, periods)
