# 代码 6-17
# 加载所需的函数,
import ipdb
from sklearn import svm
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, \
    recall_score, f1_score, cohen_kappa_score, classification_report
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
cancer = load_breast_cancer()
cancer_data = cancer['data']
cancer_target = cancer['target']
cancer_names = cancer['feature_names']
# 将数据划分为训练集测试集
cancer_data_train, cancer_data_test, \
    cancer_target_train, cancer_target_test = \
    train_test_split(cancer_data, cancer_target,
                     test_size=0.2, random_state=2)
# 数据标准化
stdScaler = StandardScaler().fit(cancer_data_train)
cancer_trainStd = stdScaler.transform(cancer_data_train)
cancer_testStd = stdScaler.transform(cancer_data_test)
# 建立SVM模型
# svm = SVC().fit(cancer_trainStd,cancer_target_train)

regressor = svm.SVC(verbose=False)
parameters = {'kernel': ['rbf'], 'C': [0.01, 0.03, 0.1, 0.3, 1, 3, 10],
              'gamma': [1e-4, 3e-4, 1e-3, 3e-3, 0.01, 0.03, 0.1, 0.3, 1]}

# 初始化配置并行网格搜索,n_jobs=-1代表使用该计算机全部的CPU,scoring:指定多个评估指标,cv: N折交叉验证
cls = GridSearchCV(regressor, parameters, cv=10, refit=True, return_train_score=True)
cls.fit(cancer_trainStd, cancer_target_train)
# 输出最佳模型结果
print(cls.best_score_)
# 输出最佳模型参数
print(cls.best_params_)
print('建立的SVM模型为：\n', cls)

svm = SVC().fit(cancer_trainStd, cancer_target_train)
# import ipdb; ipdb.set_trace()
print(cls.get_params())
print(svm.get_params())


# 预测训练集结果
cancer_target_pred = svm.predict(cancer_testStd)
print('预测前20个结果为：\n', cancer_target_pred[:20])

# 求出预测和真实一样的数目
true = np.sum(cancer_target_pred == cancer_target_test)
print('预测对的结果数目为：', true)
print('预测错的的结果数目为：', cancer_target_test.shape[0]-true)
print('预测结果准确率为：', true/cancer_target_test.shape[0])

# 代码 6-19

print('使用SVM预测breast_cancer数据的准确率为：',
      accuracy_score(cancer_target_test, cancer_target_pred))
print('使用SVM预测breast_cancer数据的精确率为：',
      precision_score(cancer_target_test, cancer_target_pred))
print('使用SVM预测breast_cancer数据的召回率为：',
      recall_score(cancer_target_test, cancer_target_pred))
print('使用SVM预测breast_cancer数据的F1值为：',
      f1_score(cancer_target_test, cancer_target_pred))
print('使用SVM预测breast_cancer数据的Cohen’s Kappa系数为：',
      cohen_kappa_score(cancer_target_test, cancer_target_pred))

print('使用SVM预测iris数据的分类报告为：', '\n',
      classification_report(cancer_target_test,
                            cancer_target_pred))
