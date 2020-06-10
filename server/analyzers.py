# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
from backtrader import Analyzer
from collections import OrderedDict
import utils

# %%


class AccountValue(Analyzer):
    params = ()

    def start(self):
        super(AccountValue, self).start()
        self.rets = OrderedDict()

    def next(self):
        super(AccountValue, self).next()
        totalvalue = self.rets.get('totalvalue', OrderedDict())
        dt = self.datas[0].datetime.datetime()
        key = '{0}-{1}-{2}'.format(dt.year, dt.month, dt.day)
        totalvalue[key] = utils.get_float(self.strategy.broker.getvalue(), 3)
        self.rets['totalvalue'] = totalvalue
        availablevalue = self.rets.get('availablevalue', OrderedDict())
        availablevalue[key] = utils.get_float(
            self.strategy.broker.get_cash(), 3)
        self.rets['availablevalue'] = availablevalue

    def get_analysis(self):
        return self.rets

# %%
