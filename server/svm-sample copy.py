import pandas as pd
import numpy as np
from sklearn import datasets
from sklearn import svm
# 使用交叉验证的方法，将数据集分为训练集与测试集
from sklearn.model_selection import train_test_split
from sklearn.model_selection import GridSearchCV

# 加载iris数据集


def load_data():
    iris = datasets.load_iris()
    """展示数据集的形状
       diabetes.data.shape, diabetes.target.shape
    """

    # 将数据集拆分为训练集和测试集
    import ipdb; ipdb.set_trace()
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.10, random_state=0)
    return X_train, X_test, y_train, y_test

# 使用LinearSVC考察线性分类SVM的预测能力


def test_LinearSVC(X_train, X_test, y_train, y_test):

    # 选择模型
    cls = svm.LinearSVC(verbose=True)
    # cls = svm.SVC(verbose=True)
    # cls = svm.SVR()

    # 利用训练数据训练模型
    cls.fit(X_train, y_train)
    # 训练好的参数
    # print('Coefficients:%s \n\nIntercept %s' % (cls.coef_, cls.intercept_))

    # 利用测试数据评判模型
    print('\n\nScore: %.2f' % cls.score(X_test, y_test))


if __name__ == "__main__":
    X_train, X_test, y_train, y_test = load_data()
    test_LinearSVC(X_train, X_test, y_train, y_test)
