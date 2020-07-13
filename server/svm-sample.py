# %%
import ipdb
from sklearn.metrics import accuracy_score, precision_score, \
    recall_score, f1_score, cohen_kappa_score, classification_report
import tushare as ts
import talib
from sklearn import svm
import pickle
from sklearn.model_selection import GridSearchCV

# %%


def save_model(model, fn):
    s = pickle.dumps(model)
    f = open(fn, "wb+")
    f.write(s)
    f.close()
    print("{} save Done\n".format(fn))


def open_model(fn):
    f = open(fn, 'rb')
    s = f.read()
    model = pickle.loads(s)
    return model


X = [[0, 0], [1, 1]]
y = [0, 1]
clf = svm.SVC(verbose=True)  # SVC,SVR,SVM调参
clf.fit(X, y)
fn = './model/svc.model'
save_model(clf, fn)
model = open_model(fn)
y_test = [2, 2]
predict = model.predict([y_test])
support_vectors_ = model.support_vectors_
support_ = model.support_
n_support_ = model.n_support_
msg = 'predict:{}, support_vectors_:{}, support_:{}, n_support_:{}'.format(
    predict, support_vectors_, support_, n_support_)
print(msg)

# %%
# 获取上证指数数据
df = ts.get_hist_data('159928', start='2017-05-09', end='2020-05-06')
# df = df.sort_index()
close = df['close']
close = close.sort_index(ascending=True)
print(df.head())
# 定义训练数据
x_train = []
y_train = []

# 至少要有一个交易日的时间差
# https://kiddie92.github.io/2019/05/19/SVM%E8%B0%83%E5%8F%82%E4%B9%8B%E8%82%A1%E7%A5%A8%E9%A2%84%E6%B5%8B/
# https://blog.csdn.net/howard789/article/details/105694706?utm_medium=distribute.pc_relevant.none-task-blog-BlogCommendFromMachineLearnPai2-3.nonecase&depth_1-utm_source=distribute.pc_relevant.none-task-blog-BlogCommendFromMachineLearnPai2-3.nonecase
# https://www.jiqizhixin.com/articles/2019-01-04-16
# https://www.joinquant.co  m/view/community/detail/3868e9ae199a486760192cecdf5590dc
# svm入门: https://www.joinquant.com/view/community/detail/6170c300d0aa8eb1aa3966a3b3d78d8e
# https://zhuanlan.zhihu.com/p/51257043
# https://www.jianshu.com/p/a9f9954355b3
# https://www.cnblogs.com/wj-1314/p/10422159.html
# https://www.jianshu.com/p/7701eab3bbc9
# https://sklearn.apachecn.org/?q=svm
# http://www.snailtoday.com/archives/category/qihuo/%e6%9c%ba%e5%99%a8%e5%ad%a6%e4%b9%a0/page/2

for index in range(2, len(close)):
    # 取数据[-2]表示使用的特征是由今天之前的数据计算得到的
    sma = talib.SMA(close[:index], timeperiod=5)[-2]
    wma = talib.WMA(close[:index], timeperiod=5)[-2]
    mom = talib.MOM(close[:index], timeperiod=5)[-2]

    features = []
    features.append(sma)
    features.append(wma)
    features.append(mom)
    x_train.append(features)

    # 对今天的交易进行打标签，涨则标记1，跌则标记-1
    if close[index-1] < close[index]:
        label = 1
    else:
        label = -1
    y_train.append(label)


# 去除前5天的数据，因为部分sma/wma/mom数值为nan
X_Train = x_train[5:]
Y_Train = y_train[5:]


# svm进行分类
# clf = svm.SVC(C=10, gamma=0.01, kernel='rbf', probability=True)
regressor = svm.SVC(verbose=False)
parameters = {'kernel': ['rbf'], 'C': [0.01, 0.03, 0.1, 0.3, 1, 3, 10],
              'gamma': [1e-4, 3e-4, 1e-3, 3e-3, 0.01, 0.03, 0.1, 0.3, 1]}

# 初始化配置并行网格搜索,n_jobs=-1代表使用该计算机全部的CPU,scoring:指定多个评估指标,cv: N折交叉验证
clf = GridSearchCV(regressor, parameters, cv=10, refit=True)
clf.fit(X_Train, Y_Train)

# 输出交叉验证的结果统计列表
print(clf.cv_results_)
# 输出最佳模型结果
print(clf.best_score_)
# 输出最佳模型参数
print(clf.best_params_)
means = clf.cv_results_['mean_test_score']
stds = clf.cv_results_['std_test_score']

# 看一下具体的参数间不同数值的组合后得到的分数是多少
for mean, std, params in zip(means, stds, clf.cv_results_['params']):
    print("%0.3f (+/-%0.03f) for %r"
          % (mean, std * 2, params))
# ipdb.set_trace()

cla = svm.SVC(C=10, gamma=0.3, kernel='rbf')
cla.fit(
    X_Train,
    Y_Train,
)

# SVM算法参数设计
# SVC(C=1.0, cache_size=200, class_weight=None, coef0=0.0,
#   decision_function_shape='ovr', degree=3, gamma='auto', kernel='rbf',
#   max_iter=-1, probability=False, random_state=None, shrinking=True,
#   tol=0.001, verbose=False)

# 2 关于cost和gamma
# SVM模型有两个非常重要的参数C与gamma。
# 其中 C是惩罚系数，即对误差的宽容度。c越高，说明越不能容忍出现误差,容易过拟合。
# C越小，容易欠拟合。C过大或过小，泛化能力变差
# gamma是选择RBF函数作为kernel后，该函数自带的一个参数。
# 隐含地决定了数据映射到新的特征空间后的分布，gamma越大，支持向量越少，gamma值越小，支持向量越多。
# 支持向量的个数影响训练与预测的速度。


# model = open_model(fn)


# 数据仅仅使用了2到len(close)，所以最后一个数据没有参与分类，拿来试试

def valid_train_data():
    right = 0
    closelen = len(close)
    for index in range(closelen-10, closelen):
        # 取数据[-2]表示使用的特征是由今天之前的数据计算得到的
        sma_test = talib.SMA(close[:index], timeperiod=5)[-3]
        wma_test = talib.WMA(close[:index], timeperiod=5)[-3]
        mom_test = talib.MOM(close[:index], timeperiod=5)[-3]

        x_test = [[sma_test, wma_test, mom_test]]

        # print(talib.SMA(close[:index], timeperiod=5)[-1])
        # print(talib.SMA(close[:index], timeperiod=5)[-2])
        # print(x_test)

        date = df.index[-(index-1)]
        change = df['p_change'][-index]
        y_test = -1
        if change > 0:
            y_test = 1
        prediction = clf.predict(x_test)[0]
        # import ipdb;ipdb.set_trace()
        msg = '{}, 涨跌幅:{}, 预测:{}'.format(
            date, change, prediction)
        print(msg)
        if prediction == y_test:
            right += 1
    print(right)


print('建立的SVM模型为：\n', cla)
print('\n\nScore: %.2f' % cla.score(X_Train, Y_Train))
print(msg)
# valid_train_data()


# print('使用SVM预测breast_cancer数据的准确率为：', accuracy_score(X_Train, Y_Train))
