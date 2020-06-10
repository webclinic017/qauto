# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%

import utils
import json
import backtrader as bt
import pandas as pd
import os
import math

# %%


# %%
# TODO
# 5分钟检查,未检查今日已购买
# 买入数量优化
# minrise,maxrise参数精细化

class FixedInvestStrategy(bt.Strategy):
    params = (
        ('printlog', False),
        ('doprint', False),
        ('minrise', -2.85),
        ('maxrise', 3.75),
        ('buysize', 200),
        ('sellsize', 200),
        ('perrise', 0.95),
        ('code', ''),
        ('start', ''),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.optpass = False
        self.orders = {}
        self.account = {}

    def log(self, txt, dt=None):
        ''' 策略的日志函数'''
        if self.params.printlog:
            dt = dt or self.get_datetime()
            print('%s, %s' % (dt.isoformat(), txt))

    def start(self):
        # 只在策略开始时执行一次
        if self.params.doprint:
            pass
            # fn = '{0}-{1}.csv'.format(self.params.code, self.params.start)
            # if os.path.exists(fn):
            #     da = pd.DataFrame(pd.read_csv(fn, engine="python"))
            #     record = da.values[-1]
            #     if record[0] >= self.params.minrise:
            #         if record[0] > self.params.minrise:
            #             self.updatestrat()
            #         else:
            #             if record[1] >= self.params.maxrise:
            #                 if record[1] > self.params.maxrise:
            #                     self.updatestrat()
            # else:
            #     if record[2] >= self.params.buysize:
            #         if record[2] > self.params.buysize:
            #             self.updatestrat()
            #         else:
            #             if record[3] >= self.params.sellsize:
            #                 self.updatestrat()

    def updatestrat(self):
        print('跳过本次')
        self.optpass = True
        self.stop()

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
            self.log(ex)
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

        # if (9 < dt.hour < 14) or (dt.hour >= 14 and dt.minute < 45):

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

        # elif (14 <= dt.hour < 15) and (45 < dt.minute < 55):
        #     # 盘尾加仓,类似定投,积累足够筹码
        #     if pricerise < -self.params.perrise:
        #         buykey = '{0}:{1}'.format(key, 'buy')
        #         buycount = self.orders.get(buykey, 0)
        #         if buycount < 2:
        #             tradesize = self.set_trade_size(pricerise)
        #             # buysize = self.params.buysize
        #             self.log('BUY CREATE, %s, 买入: %.1f股' % (msg, tradesize))
        #             self.order = self.buy(size=tradesize)
        #             buycount += 1
        #             self.orders[buykey] = buycount

    def set_trade_size(self, pricerise):
        buytimes = abs(pricerise / self.params.perrise)
        buysize = math.ceil(self.params.buysize * buytimes / 100) * 100
        return buysize

    def get_datetime(self):
        return self.datetime.datetime(0)

    def get_offset(self):
        # dt = self.get_datetime()
        # dtcompare = datetime.datetime(dt.year, dt.month, dt.day, 9, 30)
        # offsetseconds = (dt - dtcompare).total_seconds()
        # offset = int(offsetseconds / 60 / 5)
        offset = 1
        return offset
    # 回测结束后输出结果（可省略，默认输出结果）

    def stop(self):
        print(self._trades)
        if self.params.doprint:
            msg = 'minrise: %.2f, maxrise: %.2f, buysize: %s, sellsize: %s, 期末总资金: %.2f' % (
                self.params.minrise, self.params.maxrise, self.params.buysize, self.params.sellsize, self.broker.getvalue())
            if self.optpass:
                return
            finalvalue = self.broker.getvalue()
            availablevalue = self.broker.get_cash()
            totalreturn = finalvalue - self.broker.startingcash
            # print(dir(self))
            # print(self.cerebro.analyzers)
            # print(dir(self.cerebro.analyzers))
            # import ipdb; ipdb.set_trace()
            self.analyzers.SharpeRatio.stop()
            sharperatio = self.analyzers.SharpeRatio.rets['sharperatio']
            self.analyzers.DW.stop()
            maxdrowdown = self.analyzers.DW.get_analysis()['max']['drawdown']
            maxdrowdownmoney = self.analyzers.DW.get_analysis()[
                'max']['moneydown']
            self.analyzers.AnnualReturn.stop()
            annualreturninfo = dict(self.analyzers.AnnualReturn.get_analysis())

            optresult = {
                'totalreturn': utils.get_float(totalreturn, 3),
                'value': utils.get_float(finalvalue, 3),
                'availablevalue': utils.get_float(availablevalue, 3),
                'sharperatio': utils.get_float(sharperatio, 3),
                'maxdrowdown': utils.get_float(maxdrowdown, 3),
                'maxdrowdownmoney': utils.get_float(maxdrowdownmoney, 3),
                'minrise': self.params.minrise,
                'maxrise': self.params.maxrise,
                'buysize': self.params.buysize,
                'sellsize': self.params.sellsize,
                'annualreturninfo': json.dumps(annualreturninfo),
            }
            fn = '{0}-{1}.csv'.format(self.params.code, self.params.start)
            if not os.path.exists(fn):
                da = pd.DataFrame()
            else:
                da = pd.DataFrame(pd.read_csv(fn, engine="python"))
            dx = pd.DataFrame([optresult])
            da = pd.concat([da, dx], ignore_index=False)
            da.to_csv(fn, index=False)
            print(msg)


# %%


# %%
