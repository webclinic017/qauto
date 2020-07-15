import sys
import time
import datetime
import base64
import json
import copy

import requests


def use(broker, host, port=9000, **kwargs):
    return RemoteClient(broker, host, port)


class RemoteClient:
    def __init__(self, broker, host, port=9000, **kwargs):
        self._s = requests.session()
        self._api = 'http://{}:{}'.format(host, port)
        self._broker = broker
        now = datetime.datetime.now()
        self._data = {
            'user': 'august',
            'date': now.strftime('%Y-%m-%d'),
            'broker': self._broker,
        }

    @property
    def unlock(self):
        args = self.gen_args()
        url = '{}/{}?{}'.format(self._api, 'unlock', args)
        res = self._s.get(url)
        return res.json()

    @property
    def lock(self):
        args = self.gen_args()
        url = '{}/{}?{}'.format(self._api, 'lock', args)
        res = self._s.get(url)
        return res.json()

    def gen_args(self):
        args = ''
        for k, v in self._data.items():
            if args:
                args += '&{}={}'.format(k, v)
            else:
                args += '{}={}'.format(k, v)
        return args

    def enc_args(self, data):
        data_str = json.dumps(data)
        data['key'] = base64.b64encode(bytes(data_str, encoding="utf8"))
        return data

    def dec_args(self, key):
        dec_key = base64.b64decode(key)
        return dec_key

    @property
    def prepare(self):
        action = sys._getframe().f_code.co_name
        return self.common_get(action)

    @property
    def balance(self):
        action = sys._getframe().f_code.co_name
        return self.common_get(action)

    @property
    def auto_ipo(self):
        action = sys._getframe().f_code.co_name
        return self.common_get(action)

    def common_get(self, action):
        data = copy.deepcopy(self._data)
        data.update(
            {
                'broker': self._broker,
                'action': action
            }
        )
        data = self.enc_args(data)

        res = self._s.post(self._api + '/routing', data=data)
        return res.json()

    def trade(self, extras={}, action=''):
        data = copy.deepcopy(self._data)
        extras.update(data)
        extras.update(
            dict(action=action),
        )
        extras = self.enc_args(extras)
        extras.pop('entrust_no', None)
        res = self._s.post(self._api + '/routing', data=extras)
        return res.json()

    @property
    def position(self):
        return self.common_get('position')

    @property
    def today_entrusts(self):
        return self.common_get('today_entrusts')

    @property
    def today_trades(self):
        return self.common_get('today_trades')

    # TODO:
    @property
    def cancel_entrusts(self):
        return self.common_get('cancel_entrusts')

    def exit(self):
        return self.common_get('exit')

    def cancel_entrust(self, entrust_no):
        data = locals().copy()
        data.pop('self')

        res = self._s.post(self._api + '/cancel_entrust', json=data)
        return res.json()


def get_user_client(broker):
    # host = '172.20.10.14'
    host = '192.168.1.9'
    port = 9000
    u = use(broker, host, port)
    ret = u.unlock
    print(ret)
    ret = u.prepare
    print(ret)
    return u


if __name__ == '__main__':
    broker = 'hb'
    u = get_user_client(broker)
    ret = u.auto_ipo
    print(ret)
    # extras = dict(
    #     code='159928',
    #     code_cn='消费ETF',
    #     price=4.012,
    #     size=100,
    #     money=1000,
    # )
    # # ret = u.trade(extras=extras, action='buy')
    # ret = u.trade(extras=extras, action='checkrt')
    # print(ret)
