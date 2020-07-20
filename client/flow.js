var common = require("./common");
var flow = {};

var init_param = {
    app_name: "",
    package_name: "",
    tip_ids: [],
    tip_texts: [],
    config: null,
    extras: {},
};

flow.init = function (param) {
    Object.assign(init_param, param);
};

flow.run = function (fun) {
    common.toastLog("flow start...");
    extras = flow.common.engineArgsGet();
    // 主循环
    common.engineCheckAndWait();
    flow.extras = extras;
    if (extras) {
        if (extras.action == "prepare") {
            flow.launch(fun);
        } else if (extras.action == "buy") {
            if (!fun.buy) {
                return;
            }
            fun.buy(fun, extras);
        } else if (extras.action == "apply") {
            if (!fun.apply) {
                return;
            }
            fun.apply(fun, extras);
        } else if (extras.action == "sell") {
            if (!fun.sell) {
                return;
            }
            fun.sell(fun, extras);
        } else if (extras.action == "auto_ipo") {
            flow.autoIpo(fun);
        } else if (extras.action == "checkrt") {
            fun.initJiSiLuFunds();
            flow.checkRT(fun);
        }

        if (extras.action != "prepare") {
            common.cleanAllApp();
        }
        flow.recordTasks(flow.extras);
    }
    // flow.main(fun);
};

flow.launch = function (fun) {
    common.toastLog("启动 ===> " + init_param.app_name);
    var current_package = currentPackage();
    if (current_package == init_param.package_name) {
        var msg = "处于{0}".format(init_param.app_name);
        common.toastLog(msg);
        return;
    }
    var msg = "打开{0}".format(init_param.app_name);
    common.toastLog(msg);
    common.launchApp(init_param.app_name);
    common.sleep(random(1, 3));

    flow.closeTips(fun);

    var current_package = currentPackage();
    var retry = 0;
    while (current_package != init_param.package_name && retry < 4) {
        retry += 1;
        common.toastLog(current_package);
        common.toastLog(init_param.package_name);
        var msg = "处于页面检查";
        common.toastLog(msg);
        common.sleep(3 * retry);
        flow.closeTips(fun);
        current_package = currentPackage();
    }
    if (retry >= 4) {
        flow.common.cleanAllApp();
        flow.sleep(3);
        flow.launch(fun);
    }
};

flow.checkRT = function (fun) {
    var is_in_rt_time = flow.checkInRTTime();
    if (1) {
        fun.checkPOSRT(fun);
        fun.getLOFFunds(fun);
    } else {
        var msg = "不在检查溢价率时间";
        common.toastLog(msg);
    }
};

flow.autoIpo = function (fun) {
    var storage_app = common.storageApp();
    var date = common.date();
    var user_nos = common.user_nos;
    for (var j = 0; j < 2; j++) {
        click("我的");
        common.sleep(1);
        click("程先生");
        common.sleep(3);
        var users = idEndsWith("recycler_view").findOnce();
        for (var i = 0; i < users.childCount(); i++) {
            var user = users.child(i);
            var user_ele = user.findOne(idEndsWith("tv_custom_no"));
            if (user_ele) {
                var user_no = user_ele.text().split("：")[1];
                if (user_no == user_nos[j]) {
                    var key = "{0}:{1}".format(user_no, date);
                    common.toastLog(user_no);
                    var hasipo = storage_app.get(key, false);
                    if (!hasipo) {
                        // user.click();
                        click(user_no);
                        common.sleep(5);
                        var num = fun.autoIpo(fun, user_no);
                        if (num == 0) {
                            // 没有可打新新债,设置已打新,直接返回
                            if (user_no == user_nos[0]) {
                                key = "{0}:{1}".format(user_nos[1], date);
                            } else {
                                key = "{0}:{1}".format(user_nos[0], date);
                            }
                            common.toastLog(key);
                            storage_app.put(key, true);
                            return;
                        }
                        storage_app.put(key, true);
                    } else {
                        var msg = "{0}:已打新".format(user_no);
                        common.toastLog(msg);
                        back();
                    }
                    break;
                }
            }
            common.sleep(1);
        }
    }
};

flow.jumpToTrade = function (fun, item) {
    common.sleep(1);
    flow.closeTips(fun);
    if (!item) {
        var msg = "未找到元素";
        common.toastLog(msg);
        var pass_ele = fun.getPassItem();
        flow.checkInputPassword(fun, pass_ele);
    } else {
        item.click();
        common.sleep(1);
        var pass_ele = fun.getPassItem();
        flow.checkInputPassword(fun, pass_ele);
        common.sleep(1);
    }
};

flow.checkInputPassword = function (fun, item) {
    var is_input = false;
    if (item) {
        common.sleep(1);
        item.click();
        common.sleep(1);
        fun.inputPassword();
        common.sleep(1);
        is_input = true;
    }
    return is_input;
};

flow.closeTips = function (fun) {
    var tip_ids = init_param.tip_ids;
    var isClose = true;
    if (tip_ids.length > 0) {
        for (i = 0; i < tip_ids.length; i++) {
            var tipId = tip_ids[i];
            var tip = idEndsWith(tipId).findOnce();
            if (tip) {
                var msg = "关闭提示 > {0}".format(tipId);
                common.toastLog(msg);
                common.sleep(1);
                tip.click();
                isClose = true;
                break;
            }
        }
    }
    var tip_texts = init_param.tip_texts;
    if (tip_texts.length > 0) {
        for (i = 0; i < tip_texts.length; i++) {
            var tipText = tip_texts[i];
            var tip = text(tipText).findOnce();
            if (tip) {
                var msg = "关闭提示 > {0}".format(tipText);
                common.toastLog(msg);
                common.sleep(1);
                click(tipText);
            }
        }
    }
};

flow.recordTasks = function (extras) {
    var engine = engines.myEngine();
    extras.id = engine.id;
    file = "/data/data/com.termux/files/home/qauto/server/log/tasks.txt";
    line = JSON.stringify(extras);
    ret = common.appendToFile(line, file);
    common.toastLog(ret);
};

flow.checkInRTTime = function () {
    var is_in_rt_time = false;
    var date_arr = new Date();
    var hour = parseInt(date_arr.getHours());
    var minute = parseInt(date_arr.getMinutes());
    // 14:49~59
    if (hour < 15 && hour > 13 && minute > 49 && minute < 59) {
        is_in_rt_time = true;
    }
    return is_in_rt_time;
};

flow.main = function (fun) {
    // common.toastLog("自动升级 ===> " + init_param.appName);
    // flow.autoUpdate(fun);
};

module.exports = flow;
// 导出init_param变量,子模块中访问
module.exports.init_param = init_param;
module.exports.common = common;
