#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015-2020 Daniel Rodriguez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

# https://blog.csdn.net/m0_46603114/article/details/107140358

import argparse

import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.indicators as btind
from backtrader import ResamplerDaily, ResamplerWeekly, ResamplerMonthly, ResamplerMinutes
from backtrader import ReplayerDaily, ReplayerWeekly, ReplayerMonthly
from backtrader.utils import flushfile

# https://www.backtrader.com/docu/data-multitimeframe/data-multitimeframe/


class SMAStrategy(bt.Strategy):
    params = (
        ('period', 10),
        ('onlydaily', True),
    )

    def __init__(self):
        self.sma_small_tf = btind.SMA(self.data, period=self.p.period)
        bt.indicators.MACD(self.data0)

        if not self.p.onlydaily:
            self.sma_large_tf = btind.SMA(self.data1, period=self.p.period)
            bt.indicators.MACD(self.data1)

    def prenext(self):
        self.next()

    def nextstart(self):
        print('--------------------------------------------------')
        print('nextstart called with len', len(self))
        print('--------------------------------------------------')

        super(SMAStrategy, self).nextstart()

    def next(self):
        # print('Strategy:', len(self))
        print(len(self))

        txt = list()
        txt.append('Data0')
        txt.append('%04d' % len(self.data0))
        dtfmt = '%Y-%m-%d %H:%M:%S'
        txt.append('{:f}'.format(self.data.datetime[0]))
        txt.append('%s' % self.data.datetime.datetime(0).strftime(dtfmt))
        # txt.append('{:f}'.format(self.data.open[0]))
        # txt.append('{:f}'.format(self.data.high[0]))
        # txt.append('{:f}'.format(self.data.low[0]))
        txt.append('{:f}'.format(self.data.close[0]))
        # txt.append('{:6d}'.format(int(self.data.volume[0])))
        # txt.append('{:d}'.format(int(self.data.openinterest[0])))
        # txt.append('{:f}'.format(self.sma_small[0]))
        print(', '.join(txt))
        # import ipdb
        # ipdb.set_trace()

        if len(self.datas) > 1 and len(self.data1):
            txt = list()
            txt.append('Data1')
            txt.append('Data1len%s'%(len(self.datas)))
            txt.append('%04d' % len(self.data1))
            dtfmt = '%Y-%m-%d %H:%M:%S'
            txt.append('{:f}'.format(self.data1.datetime[0]))
            txt.append('%s' % self.data1.datetime.datetime(0).strftime(dtfmt))
            # txt.append('{}'.format(self.data1.open[0]))
            # txt.append('{}'.format(self.data1.high[0]))
            # txt.append('{}'.format(self.data1.low[0]))
            txt.append('{}'.format(self.data1.close[0]))
            # txt.append('{}'.format(self.data1.volume[0]))
            # txt.append('{}'.format(self.data1.openinterest[0]))
            # txt.append('{}'.format(float('NaN')))
            print(', '.join(txt))


def runstrat():

    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(
        SMAStrategy,

        # args for the strategy
        period=20,
    )

    # Load the Data
    import models
    import utils
    code = '159928'
    dbname = 'k_5min_data'
    start = '2020-05-22'
    end = '2020-06-22'

    df = utils.get_database_data(code, dbname=dbname, start=start, end=end)
    data = models.PandasData(dataname=df)
    cerebro.adddata(data)

    # dbname = 'k_data'
    # df = utils.get_database_data(code, dbname=dbname, start=start, end=end)
    # data2 = models.PandasData(dataname=df)

    # cerebro.adddata(data2)

    # Handy dictionary for the argument timeframe conversion

    # Resample the data
    data2 = bt.DataClone(dataname=data)
    data2.addfilter(ResamplerDaily)
    cerebro.adddata(data2)


    # cerebro.resampledata(
    #     data, timeframe=bt.TimeFrame.Days, compression=1)




    # First add the original data - smaller timeframe

    # And then the large timeframe

    # Run over everything
    fn = 'test.csv'
    cerebro.addwriter(bt.WriterFile, csv=True, out=fn, rounding=1)
    cerebro.run()

    # cerebro.plot(style='candle')


if __name__ == '__main__':
    runstrat()
