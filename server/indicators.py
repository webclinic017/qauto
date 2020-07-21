# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import backtrader as bt
import numpy as np
import utils
import models

# %%

# 指标: http://fxcodebase.com/wiki/index.php/Category:%E6%8C%87%E6%A0%87
# https://cn.tradingview.com/scripts/truestrengthindicator/
# https://www.jianshu.com/p/bbee17ba168a

# 配对交易: https://www.cnblogs.com/ManWingloeng/p/12541244.html

# ACCDIST(df,n)：积累/分配（Accumulation/Distribution）。
# ADX(df,n,n_ADX)：定向运动平均指数（Average Directional Movement Index）。
# ATR(df,n)：平均真实范围（Average True Range）。
# BBANDS(df,n)：布林带（Bollinger Bands）。
# CCI(df,n)：商品通道指数（Commodity Channel Index）。
# COPP(df,n)：Coppock曲线（Coppock Curve）。
# Chaikin(df)：蔡金振荡器（Chaikin Oscillator）。
# DONCH(df,n)：奇安通道（Donchian Channel）。
# EMA(df,n)：指数移动平均（Exponential Moving Average）。
# EOM(df,n)：缓解运动（Ease of Movement）。
# FORCE(df,n)：力指数（Force Index）。
# KELCH(df,n)：Keltner通道（Keltner Channel）。
# KST(df,r1,r2,r3,r4,n1,n2,n3,n4)：KST振荡器（KST Oscillator）。
# MFI(df,n)：资金流量指标和比率（Money Flow Index and Ratio）。
# MassI(df)：质量指数（Mass Index）。
# OBV(df,n)：平衡量（On-balance Volume）。
# PPSR(df)：支点、支撑和阻力（Pivot Points,Supports and Resistances）。
# ROC(df,n)：变化率（Rate of Change）。
# STDDEV(df,n)：标准偏差（Standard Deviation）。
# STO(df,n)：随机指标D（Stochastic oscillator %D）。
# STOK(df)：随机指标K（Stochastic oscillator %K）。
# TRIX(df,n)：矩阵（Trix）。
# ULTOSC(df)：最终振荡器（Ultimate Oscillator）。
# Vortex(df,n)：涡指标（Vortex Indicator）。

# MA(df,n)：移动平均（Moving Average）。
# MACD(df,n_fast,n_slow)：MACD指标信号和MACD的区别（MACD Signal and MACD difference）。
# MOM(df,n)：动量（Momentum）。
# RSI(df,n)：相对强弱指标（Relative Strength Index）。
# TSI(df,r,s)：真实强度指数（True Strength Index）。

# 动量交易策略: http://reader.epubee.com/books/mobile/9f/9fddc3cb822d76d285508e57ab154769/text00007.html

# %%


class ssa_index_ind(bt.Indicator):
    lines = ('ssa',)

    def __init__(self, ssa_window):
        self.params.ssa_window = ssa_window
        # 这个很有用，会有 not maturity生成
        self.addminperiod(self.params.ssa_window * 2)

    def get_window_matrix(self, input_array, t, m):
        # 将时间序列变成矩阵
        temp = []
        n = t - m + 1
        for i in range(n):
            temp.append(input_array[i:i + m])
        window_matrix = np.array(temp)
        return window_matrix

    def svd_reduce(self, window_matrix):
        # svd分解
        u, s, v = np.linalg.svd(window_matrix)
        m1, n1 = u.shape
        m2, n2 = v.shape
        index = s.argmax()  # get the biggest index
        u1 = u[:, index]
        v1 = v[index]
        u1 = u1.reshape((m1, 1))
        v1 = v1.reshape((1, n2))
        value = s.max()
        new_matrix = value * (np.dot(u1, v1))
        return new_matrix

    def recreate_array(self, new_matrix, t, m):
        # 时间序列重构
        ret = []
        n = t - m + 1
        for p in range(1, t + 1):
            if p < m:
                alpha = p
            elif p > t - m + 1:
                alpha = t - p + 1
            else:
                alpha = m
            sigma = 0
            for j in range(1, m + 1):
                i = p - j + 1
                if i > 0 and i < n + 1:
                    sigma += new_matrix[i - 1][j - 1]
            ret.append(sigma / alpha)
        return ret

    def SSA(self, input_array, t, m):
        window_matrix = self.get_window_matrix(input_array, t, m)
        new_matrix = self.svd_reduce(window_matrix)
        new_array = self.recreate_array(new_matrix, t, m)
        return new_array

    def next(self):
        data_serial = self.data.get(size=self.params.ssa_window * 2)
        self.lines.ssa[0] = self.SSA(data_serial, len(
            data_serial), int(len(data_serial) / 2))[-1]


class TWAP(bt.Indicator):
    params = dict(
        period=5,
    )
    plotinfo = dict(subplot=False)
    lines = ('twap',)

    def __init__(self, data=None):
        if not isinstance(data, models.PandasData):
            data = self.data
        price = ((data.high + data.low +
                  data.close + data.open)/4)
        sumprice = bt.ind.SumN(price, period=self.p.period)
        self.l.twap = sumprice / self.p.period
        super(TWAP, self).__init__()


class VWAP(bt.Indicator):
    # 交易量加权
    # VWAP算法???
    # https://blog.csdn.net/u012234115/article/details/72822003
    plotinfo = dict(subplot=False)
    params = dict(
        period=22,
    )
    lines = ('vwap',)
    plotlines = dict(VWAP=dict(alpha=0.50, linestyle='-.', linewidth=2.0))

    def __init__(self, data=None):
        if not isinstance(data, models.PandasData):
            data = self.data
        sumvol = bt.ind.SumN(data.volume, period=self.p.period)
        # price = ((data.close + data.high + data.open +
        #           data.low)/4) * data.volume
        price = ((data.open + data.close)/2) * data.volume
        sumprice = bt.ind.SumN(price, period=self.p.period)
        # self.lines[0] = sumprice / sumvol
        self.l.vwap = sumprice / sumvol
        super(VWAP, self).__init__()


class MOM(bt.Indicator):
    lines = ('mom',)
    params = dict(
        period=13,
    )

    def __init__(self, data=None):
        if not isinstance(data, models.PandasData):
            data = self.data
        self.l.mom = 100.0 * (data / data(-self.p.period))
        super(MOM, self).__init__()


class MOMOSC(bt.Indicator):
    lines = ('momosc',)
    params = dict(
        period=13,
    )

    def __init__(self, data=None):
        if not isinstance(data, models.PandasData):
            data = self.data
        self.l.momosc = 100.0 * ((data - data(-self.p.period))/data)
        super(MOMOSC, self).__init__()


class MTM(bt.Indicator):
    lines = ('mtm',)
    params = dict(
        period=13,
    )

    def __init__(self, data=None):
        if not isinstance(data, models.PandasData):
            data = self.data
        self.l.mtm = data - data(-self.p.period)
        super(MTM, self).__init__()


class TSI(bt.Indicator):
    alias = ('TSI',)
    params = (
        ('period1', 25),
        ('period2', 13),
        ('pchange', 1),
        ('_movav', bt.ind.EMA),
    )
    lines = ('tsi',)

    def __init__(self, data=None):
        if not isinstance(data, models.PandasData):
            data = self.data
        pc = data - data(-self.p.pchange)
        sm1 = self.p._movav(pc, period=self.p.period1)
        sm12 = self.p._movav(sm1, period=self.p.period2)
        sm2 = self.p._movav(abs(pc), period=self.p.period1)
        sm22 = self.p._movav(sm2, period=self.p.period2)
        self.l.tsi = 100.0 * (sm12 / sm22)


class KAMA(bt.ind.MovingAverageBase):
    alias = ('KAMA', 'MovingAverageAdaptive',)
    lines = ('kama',)
    params = (('fast', 2), ('slow', 22))

    def __init__(self, data=None):
        if not isinstance(data, models.PandasData):
            data = self.data
        direction = data - data(-self.p.period)
        volatility = bt.ind.SumN(abs(data - data(-1)), period=self.p.period)
        er = abs(direction / volatility)  # efficiency ratio
        fast = 2.0 / (self.p.fast + 1.0)  # fast ema smoothing factor
        slow = 2.0 / (self.p.slow + 1.0)  # slow ema smoothing factor
        sc = pow((er * (fast - slow)) + slow, 2)  # scalable constant
        self.lines[0] = bt.ind.ExponentialSmoothingDynamic(data,
                                                           period=self.p.period,
                                                           alpha=sc)

        super(KAMA, self).__init__()


class WilliamsR(bt.Indicator):
    lines = ('percR',)
    params = (('period', 14),
              ('upperband', -20.0),
              ('lowerband', -80.0),)

    plotinfo = dict(plotname='Williams R%')
    plotlines = dict(percR=dict(_name='R%'))

    def _plotinif(self):
        self.plotinfo.plotyhlines = [self.p.upperband, self.p.lowerband]

    def __init__(self, data=None):
        if not isinstance(data, models.PandasData):
            data = self.data
        h = bt.ind.Highest(data.high, period=self.p.period)
        l = bt.ind.Lowest(data.low, period=self.p.period)
        c = data.close
        self.lines.percR = -100.0 * (h - c) / (h - l)

        super(WilliamsR, self).__init__()


class ATR(bt.Indicator):
    lines = ('atr', 'tr')
    params = dict(
        period=14,
        _movav=bt.ind.EMA,
    )

    def __init__(self, data=None):
        if not isinstance(data, models.PandasData):
            data = self.data

        self.tr = bt.ind.Max((data.high - data.low), abs(
            data.close[-1] - data.high), abs(data.close[-1] - data.low))

        self.l.tr = self.tr
        self.l.atr = self.p._movav(self.tr, period=self.p.period)


class CMI(bt.Indicator):
    # 恒温器策略
    # https://www.jianshu.com/p/f0816467bd6b
    # 可以定义多个lines,用于debug
    # 参数如何计算: https://www.backtrader.com/docu/concepts/
    lines = ('cmi', )
    params = dict(
        period=22,
    )

    def __init__(self, data=None):
        if not isinstance(data, models.PandasData):
            data = self.data

        # 当前价格,不可用data.close[0]表示,用data.close,否则取值有问题

        close22 = data.close[-self.p.period]  # 前22根K线的收盘价
        hh22 = bt.ind.Highest(data.high, period=self.p.period)  # 最近22根K线的最高价
        ll22 = bt.ind.Lowest(data.low, period=self.p.period)  # 最近22根K线的最低价
        self.l.cmi = abs((data.close - close22) /
                         (hh22 - ll22)) * 100  # 计算市场波动指数
