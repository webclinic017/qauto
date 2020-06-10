# coding=utf8
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup as bs
from flask import Flask, jsonify, request

app = Flask(__name__)

ave_volumes = {}


@app.route('/get_ave_volume')
def getAveVolume():
    args = request.args
    code = args.get('code', '')
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
    data = {'volume': ave_volume}
    print(ave_volume)
    return jsonify(data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)
