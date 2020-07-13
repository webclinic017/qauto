# SVM入门: https://www.joinquant.com/view/community/detail/6170c300d0aa8eb1aa3966a3b3d78d8e
import talib
from jqdata import *
import warnings
from sklearn import svm

warnings.filterwarnings("ignore")
test_stock = '399300.XSHE'
start_date = datetime.date(2013, 12, 11)
end_date = datetime.date(2020, 6, 3)

trading_days = get_all_trade_days()
start_date_index = trading_days.tolist().index(start_date)
end_date_index = trading_days.tolist().index(end_date)

x_all = []
y_all = []

for index in range(start_date_index, end_date_index):
    # 得到计算指标的所有数据
    start_day = trading_days[index - 30]
    end_day = trading_days[index]
    stock_data = get_price(test_stock, start_date=start_day,
                           end_date=end_day, frequency='daily', fields=['close'])
    close_prices = stock_data['close'].values

    # 通过数据计算指标
    # -2是保证获取的数据是昨天的，-1就是通过今天的数据计算出来的指标
    sma_data = talib.SMA(close_prices)[-2]
    wma_data = talib.WMA(close_prices)[-2]
    mom_data = talib.MOM(close_prices)[-2]

    features = []
    features.append(sma_data)
    features.append(wma_data)
    features.append(mom_data)

    label = False
    if close_prices[-1] > close_prices[-2]:
        label = True
    x_all.append(features)
    y_all.append(label)


# 准备算法需要用到的数据
x_train = x_all[: -1]
y_train = y_all[: -1]
x_test = x_all[-1]
y_test = y_all[-1]
print('data done')
# 开始利用机器学习算法计算
clf = svm.SVC()
# 训练的代码
clf.fit(x_train, y_train)
# 得到测试结果的代码
x_test = np.array(x_test).reshape(1, -1)
prediction = clf.predict(x_test)

# 看看预测对了没
print(prediction == y_test)
print('all done')
print('建立的SVM模型为：\n', clf)
print('\n\nScore: %.2f' % clf.score(x_train, y_train))
