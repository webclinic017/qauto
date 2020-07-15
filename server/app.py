from datetime import datetime, timedelta
import os
import json
import time

import requests
from bs4 import BeautifulSoup as bs
from flask import Flask, jsonify, request
import subprocess
import functools

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 支持中文

# 简单用户检查


def login_required(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        defaultu = 'august'
        user = request.args.get('user', '')
        user_ = request.form.get('user', '')
        if user != defaultu and user_ != defaultu:
            data = dict(msg='非法用户名', code=99)
            return jsonify(data)
        else:
            return func(*args, **kwargs)
    return inner


ave_volumes = {}
su_prefix = 'su -c '
am_prefix = 'am start -n org.my.jsbox/org.my.jsbox.external.open.RunIntentActivity '

task_file = '/data/data/com.termux/files/home/web/tasks.txt'


@app.route('/routing', methods=['POST'])
@login_required
def routing():
    args = request.form
    item = args.to_dict()
    item.pop('user', None)

    path = '/sdcard/JSBOX/main.js'
    extra_str = get_extras_str(item)
    cmd = '{}{} -d {} {}'.format(su_prefix, am_prefix, path, extra_str)
    print(cmd)
    raw_stat = get_stat(task_file)

    status, _ = subprocess.getstatusoutput(cmd)
    key = item['key']
    is_finished, extra = is_task_finished(key, raw_stat)
    data = dict(msg='success', code=0)
    if is_finished and status == 0:
        if item['action'] in ['buy', 'sell']:
            data['entrust_no'] = extra['entrust_no']
        return jsonify(data)
    else:
        data['msg'] = 'error'
        data['code'] = 1
        return jsonify(data)


def is_task_finished(key, raw_stat):
    stat = get_stat(task_file)
    is_finished = False
    seconds = 0
    while not is_finished and seconds < 90:
        if (stat.st_mtime != raw_stat.st_mtime):
            f = open(task_file)
            lines = f.readlines()
            data = json.loads(lines[-1])
            task_key = data.get('key', '')
            if key == task_key:
                return True, data
        seconds += 3
        time.sleep(3)
        stat = get_stat(task_file)
    return False, {}


def get_stat(file):
    stat = os.stat(task_file)
    return stat


def get_extras_str(item):
    extra_str = ''
    for x, y in item.items():
        extra_str += '-e {} {} '.format(x, y)
    return extra_str


@app.route('/unlock')
@login_required
def unlock():
    item = dict(d='/sdcard/JSBOX/unlock.js')
    cmd = '{}{}'.format(su_prefix, am_prefix)
    if item.get('d', ''):
        cmd += '-d {}'.format(item['d'])

    status, _ = subprocess.getstatusoutput(cmd)
    data = dict(msg='success', code=0)
    if status == 0:
        return jsonify(data)
    else:
        data['msg'] = 'error'
        data['code'] = 1
        return jsonify(data)


@app.route('/lock')
@login_required
def lock():
    item = dict(d='/sdcard/JSBOX/lock.js')
    cmd = '{}{}'.format(su_prefix, am_prefix)
    if item.get('d', ''):
        cmd += '-d {}'.format(item['d'])

    status, _ = subprocess.getstatusoutput(cmd)
    data = dict(msg='success', code=0)
    if status == 0:
        return jsonify(data)
    else:
        data['msg'] = 'error'
        data['code'] = 1
        return jsonify(data)


@app.route('/get_volume')
def get_volume():
    args = request.args
    code = args.get('code', '')
    if not code:
        data = dict(code=99)
        return jsonify(data)
    now = datetime.now()
    end = now.strftime('%Y-%m-%d')
    ave_key = '{0}:{1}'.format(end, code)
    ave_volume = ave_volumes.get(ave_key, 0)
    if ave_volume != 0:
        data = {'volume': ave_volume}
        print(ave_volume)
        return jsonify(data)
    start = (now + timedelta(days=-30)).strftime('%Y-%m-%d')

    url = 'http://quotes.money.163.com/fund/zyjl_{0}.html?start={1}&end={2}'.format(
        code, start, end)
    headers = {
        'User-Agent': 'Mozilla/5.0',
    }
    res = requests.get(url, headers=headers)
    if res.status_code == 404:
        return jsonify({'volume': 0})
    soup = bs(res.content, 'lxml')
    detail = soup.find('table', attrs={'class': 'fn_cm_table'}).find('tbody')
    items = detail.find_all('tr')
    volumes = []
    for item in items:
        tds = item.find_all('td')
        volume = tds[4].get_text()
        volume = volume.replace(',', '')
        volume_float = 0
        if u'亿' in volume:
            volume = volume.replace(u'亿', '')
            volume_float = float(volume)*10000*10000
        else:
            if u'万' in volume:
                volume = volume.replace(u'万', '')
                volume_float = float(volume)*10000*10000
            else:
                volume_float = float(volume)*10000
        volumes.append(volume_float)
    ave_volume = round((sum(volumes) / len(volumes)) / 10000, 3)
    ave_volumes[ave_key] = ave_volume
    data = dict(volume=ave_volume, code=0)
    print(ave_volume)
    return jsonify(data)


if __name__ == '__main__':
    import cron
    cron.start()
    print('cron start...')
    app.run(host='0.0.0.0', port=9000, debug=False)
