from __future__ import print_function

from pyalgotrade import strategy
from pyalgotrade import plotter
from pyalgotrade.tools import quandl
from pyalgotrade.technical import vwap, ma
from pyalgotrade.stratanalyzer import sharpe

# https://blog.csdn.net/sdafhkjas/article/details/102802693


class VWAPMomentum(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, vwapWindowSize, threshold):
        super(VWAPMomentum, self).__init__(feed)
        self.__instrument = instrument
        self.__vwap = vwap.VWAP(feed[instrument], vwapWindowSize)
        self.__threshold = threshold
        self.__sma = ma.SMA(feed[instrument].getPriceDataSeries(), 5)

    def getVWAP(self):
        return self.__vwap

    def onBars(self, bars):
        print(self.__vwap[-1])
        vwap = self.__vwap[-1]
        if vwap is None:
            return

        shares = self.getBroker().getShares(self.__instrument)
        price = bars[self.__instrument].getClose()
        notional = shares * price

        if price > vwap * (1 + self.__threshold) and notional < 1000000:
            self.marketOrder(self.__instrument, 100)
        elif price < vwap * (1 - self.__threshold) and notional > 0:
            self.marketOrder(self.__instrument, -100)


def main(plot):
    vwapWindowSize = 10
    threshold = 0.01
    instrument = 'AAPL'

    # Download the bars.
    # https://blog.csdn.net/lawme/article/details/51495349
    # code = '159928'
    # instrument = code
    # from pyalgotrade_tushare import tools, barfeed
    # instruments = [code]
    # feed = tools.build_feed(instruments, 2016, 2018, "histdata")
    feed = quandl.build_feed("WIKI", [instrument], 2011, 2012, ".")
    # import ipdb
    # ipdb.set_trace()

    strat = VWAPMomentum(feed, instrument, vwapWindowSize, threshold)
    sharpeRatioAnalyzer = sharpe.SharpeRatio()
    strat.attachAnalyzer(sharpeRatioAnalyzer)

    if plot:
        plt = plotter.StrategyPlotter(strat, True, False, True)
        plt.getInstrumentSubplot(instrument).addDataSeries(
            "vwap", strat.getVWAP())

    strat.run()
    print("Sharpe ratio: %.2f" % sharpeRatioAnalyzer.getSharpeRatio(0.05))

    # if plot:
    #     plt.plot()


if __name__ == "__main__":
    main(True)
