import pandas as pd
from sklearn import svm, preprocessing
import utils
import tushare as ts
# https://blog.csdn.net/howard789/article/details/105694706?utm_medium=distribute.pc_relevant.none-task-blog-BlogCommendFromMachineLearnPai2-3.nonecase&depth_1-utm_source=distribute.pc_relevant.none-task-blog-BlogCommendFromMachineLearnPai2-3.nonecase

# df=pd.read_csv("./MNIST_data/601012.csv")
columns = ['date', 'open', 'high', 'low', 'close', 'adjclose', 'vol']
df = ts.get_hist_data('159928', start='2017-05-09', end='2020-05-06')
df['date'] = df.index
df['adjclose'] = df['close']
df.rename(columns={'volume': 'vol'}, inplace=True)

df_original = df[columns]
# value = pd.Series((df['close']-df['close'].shift(1))/df['close'].shift(1),index=df.index)

# 第二天收盘买入,第三天开盘卖出
# value = pd.Series((df['open'].shift(-2)-df['close'].shift(-1))/df['close'].shift(-1),index=df.index)

# 第二天开盘买入,第三天开盘卖出
value = pd.Series((df['open'].shift(-2)-df['open'].shift(-1)
                   )/df['open'].shift(-1), index=df.index)

# 明日上涨
# value = pd.Series((df['close'].shift(-1)-df['close'])/df['close'],index=df.index)

df_original['后天开盘价'] = df['open'].shift(-2)
df_original['明天开盘价'] = df['open'].shift(-1)
df_original['涨幅'] = value
# df_original['close shift(1)']=df['close'].shift(1)

value = value.fillna(0)  # 第一笔数据是nan
value[value > 0.007] = 1  # 交易成本千分之7,至少要覆盖
value[value <= 0.007] = 0

df['value'] = value
df.set_index('date')
df.sort_index()
df.drop(columns='date', inplace=True)

# 删除无效数据
df = df.dropna(axis=0, how='any')
df = df.astype('float64')


df_x = df.drop(columns='value', axis=1)
df_x = preprocessing.scale(df_x)

correct = 0
totalNum = 0


df_original['结果'] = ""
trainNo = int(df_x.shape[0]*0.8)
trainOrigin = trainNo
profitTimes = 0  # 盈利次数
lossTimes = 0  # 亏损次数
miss_op = 0.
esc_risk = 0.

while trainNo < df_x.shape[0]:
    trainX = df_x[trainNo-trainOrigin:trainNo]
    trainY = value[trainNo-trainOrigin:trainNo]
    predictX = df_x[trainNo:trainNo+1]
    answer = value[trainNo:trainNo+1]

    classifier = svm.SVC(kernel='linear')
    # classifier = svm.SVC(C=1.0, kernel='poly')
    # classifier = svm.SVC(C=1.0, kernel='rbf')

    classifier.fit(trainX, trainY)
    value_predict = classifier.predict(predictX)
    anserC = answer.values[0]
    pre = value_predict[0]
    import ipdb; ipdb.set_trace()
    print("{} 实际:{},预测:{}".format(
        df_original.loc[trainNo, 'date'], anserC, pre))

    if(anserC == 1):
        if(pre == 1):
            df_original.loc[trainNo, '结果'] = "赚钱"
            profitTimes += 1
            correct += 1
        else:
            df_original.loc[trainNo, '结果'] = "错过机会"
            miss_op += 1

    else:
        if (pre == 1):
            df_original.loc[trainNo, '结果'] = "赔钱"
            lossTimes += 1
        else:
            df_original.loc[trainNo, '结果'] = "躲过风险"
            esc_risk += 1
            correct += 1

    trainNo = trainNo + 1
    totalNum += 1

print("总天数", profitTimes+lossTimes+miss_op+esc_risk)
print("盈利次数", profitTimes)
print("亏损次数", lossTimes)
print("错过机会", miss_op)
print("躲过风险", esc_risk)
print("正确率 {:.2%}".format(correct/totalNum))
print("END")
