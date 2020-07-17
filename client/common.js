var common = {};

// https://hyb1996.github.io/AutoJs-Docs/#/?id=%e7%bb%bc%e8%bf%b0

var w = device.width,
    h = device.height;

var key = "SCU53613T74bdd3a5e5ff2eb57218f74f71d495965d0711a8483e7";
// TODO: 检查是否为主账号,套利账号
common.user_nos = ["040020024337", "180000030960"];
common.file = "/data/data/com.termux/files/home/qauto/server/log/client.log";

common.DEBUG = false;

common.storageAppInit = function (app_name) {
    common.toastLog(app_name + " storageApp 集思录基金初始化");
    common.storageApp();
};
common.storageApp = function () {
    var storage = storages.create("app");
    return storage;
};
common.storageAppClear = function () {
    var storage = storages.create("app");
    storage.clear();
};
common.storageRT = function () {
    var storage = storages.create("rt");
    return storage;
};

common.checkAutoService = function () {
    common.toastLog("检查无障碍服务");
    var service = auto.service;
    if (service == null) {
        common.enableAccessibilityServiceByRoot();
    } else {
        common.toastLog("无障碍服务已开启");
    }
};

// 字符串格式化
if (!String.prototype.format) {
    String.prototype.format = function () {
        var args = arguments;
        return this.replace(/{(\d+)}/g, function (match, number) {
            return typeof args[number] != "undefined" ? args[number] : match;
        });
    };
}
// 日期格式化
Date.prototype.format = function (fmt) {
    var o = {
        "M+": this.getMonth() + 1, //月份
        "d+": this.getDate(), //日
        "h+": this.getHours(), //小时
        "m+": this.getMinutes(), //分
        "s+": this.getSeconds(), //秒
        "q+": Math.floor((this.getMonth() + 3) / 3), //季度
        S: this.getMilliseconds(), //毫秒
    };
    if (/(y+)/.test(fmt))
        fmt = fmt.replace(
            RegExp.$1,
            (this.getFullYear() + "").substr(4 - RegExp.$1.length)
        );
    for (var k in o)
        if (new RegExp("(" + k + ")").test(fmt))
            fmt = fmt.replace(
                RegExp.$1,
                RegExp.$1.length == 1
                    ? o[k]
                    : ("00" + o[k]).substr(("" + o[k]).length)
            );
    return fmt;
};

// 数组不同
Object.defineProperties(Array.prototype, {
    getDifference: {
        value: function (b) {
            var arr = [];
            for (var i = 0; i < this.length; i++) {
                var ele = this[i];
                if (b.indexOf(ele) == -1) {
                    arr.push(ele);
                }
            }
            return arr;
        },
    },
});

common.enableAccessibilityServiceByRoot = function () {
    // todo: 获取无障碍服务,再添加新增无障碍服务
    // settings get secure enabled_accessibility_services
    var accessibilityServices = [
        "net.dinglisch.android.taskerm/net.dinglisch.android.taskerm.MyAccessibilityService",
        "org.my.jsbox/com.stardust.autojs.core.accessibility.AccessibilityService",
    ];

    var appAccessibilityServices = accessibilityServices.join(":");
    var cmd = "settings put secure enabled_accessibility_services {0}".format(
        appAccessibilityServices
    );
    common.toastLog(cmd);
    var ret = shell(cmd, true);
    var cmd = "settings put secure accessibility_enabled 1";
    common.toastLog(cmd);
    var ret = shell(cmd, true);
    toastLog(ret);
};

common.netStatus = function () {
    common.toastLog("检查网络");
    importClass(android.content.BroadcastReceiver);
    importClass(android.content.ContextWrapper);
    importClass(android.content.IntentFilter);
    importClass(android.net.ConnectivityManager);
    var filter = new IntentFilter();
    filter.addAction(ConnectivityManager.CONNECTIVITY_ACTION);
    // 注册广播接收器
    new ContextWrapper(context).registerReceiver(
        (receiver = new BroadcastReceiver({
            onReceive: function (context, intent) {
                var action = intent.getAction();
                if (action.equals(ConnectivityManager.CONNECTIVITY_ACTION)) {
                    var mConnectivityManager = context.getSystemService(
                        context.CONNECTIVITY_SERVICE
                    );
                    netInfo = mConnectivityManager.getActiveNetworkInfo();
                    if (netInfo != null && netInfo.isAvailable()) {
                        // var name = netInfo.getTypeName();
                        // common.toastLog(name);
                        if (
                            netInfo.getType() == ConnectivityManager.TYPE_WIFI
                        ) {
                            common.toastLog("wifi网络");
                            return "wifi网络";
                        } else if (
                            netInfo.getType() ==
                            ConnectivityManager.TYPE_ETHERNET
                        ) {
                            common.toastLog("有线网络");
                            return "有线网络";
                        } else if (
                            netInfo.getType() == ConnectivityManager.TYPE_MOBILE
                        ) {
                            common.toastLog("3g网络");
                            return "3g网络";
                        }
                    } else {
                        common.toastLog("网络断开");
                        return "网络断开";
                    }
                }
            },
        })),
        filter
    );
    common.sleep(3);
    // 注销广播
    new ContextWrapper(context).unregisterReceiver(receiver);
    common.toastLog("检查网络结束");
};

common.cleanAllApp = function () {
    common.toastLog("清理后台");
    home();
    common.sleep(1);
    recents();
    common.sleep(3);
    var clean = id("clearAnimView").findOnce();
    if (clean) {
        clean.click();
        common.sleep(1);
    }
};

common.notifyToWX = function (title, text) {
    wx_url = "https://sc.ftqq.com/{0}.send?text={1}&desp={2}".format(
        key,
        title,
        text
    );
    common.toastLog(wx_url);
    common.httpGet(wx_url);
};

common.date = function () {
    var date = new Date().format("yyyy-MM-dd");
    return date;
};

common.datetime = function () {
    var datetime = new Date().format("yyyy-MM-dd hh:mm:ss");
    return datetime;
};

common.toastLog = function (msg) {
    runtime.toast(msg);
    global.log(msg);
    if (!common.DEBUG) {
        var datetime = common.datetime();
        var line = "{0},{1}".format(datetime, msg);
        common.appendToFile(line, common.file);
    }
};

common.sleep = function (second) {
    sleep(second * 1000);
};

common.appendToFile = function (line, file) {
    cmd = "echo '{0}' >> {1}".format(line, file);
    // toastLog(cmd);
    ret = shell(cmd, true);
    return ret;
};

common.engineCheckAndWait = function () {
    var engine_all = engines.all();
    var second = 1;
    while (engine_all.length > 1) {
        if (second == 1) {
            var current_id = engines.myEngine().id;
            var ids = [];
            for (var i = 0; i < engine_all.length; i++) {
                var engine = engine_all[i];
                ids.push(engine.id);
            }
            var min_id = Math.min.apply(null, ids);
            if (current_id == min_id) {
                // 先入栈,先运行
                break;
            }
        }
        if (second % 30 == 0) {
            var msg = "其他进程占用,休眠{0}秒".format(second);
            common.toastLog(msg);
        }
        common.sleep(1);
        second += 1;
        var engine_all = engines.all();
    }
};

common.engineArgsGet = function () {
    let intent = engines.myEngine().execArgv.intent;
    if (!intent) {
        return {};
    }
    extras = intent.extras;
    extrasdict = {};
    if (extras) {
        let iter = extras.keySet().iterator();
        while (iter.hasNext()) {
            let key = iter.next();
            let value = extras.get(key);
            extrasdict[key] = value;
        }
    }
    return extrasdict;
};

common.RunIntentActivity = function (data, extras) {
    app.startActivity({
        packageName: "org.my.jsbox",
        className: "org.my.jsbox.external.open.RunIntentActivity",
        data: data,
        type: "application/x-javascript",
        extras: extras,
    });
};

//唤醒主屏幕
common.wakeUp = function () {
    var isWakeUp = true;
    if (!device.isScreenOn()) {
        device.wakeUpIfNeeded();
        isWakeUp = false;
    }
    return isWakeUp;
};

common.unLockRetry = function () {
    let errorMessage = (msg) => {
        console.error(msg);
        device.isScreenOn() && KeyCode(26); //判断是否锁屏
        return true;
    };

    let max_try_times_wake_up = 10; //尝试解锁10次
    while (!device.isScreenOn() && max_try_times_wake_up--) {
        device.wakeUp();
        common.sleep(0.5);
    }
    if (max_try_times_wake_up < 0) errorMessage("点亮屏幕失败"); //尝试次数max，显示失败文本
    let keyguard_manager = context.getSystemService(context.KEYGUARD_SERVICE);
    let isUnlocked = () => !keyguard_manager.isKeyguardLocked();
    let swipe_time = 0;
    let swipe_time_increment = 80;
    let max_try_times_swipe = 20; //初始化时间，递增时间，最大解锁时间
    while (!isUnlocked() && max_try_times_swipe--) {
        swipe_time += swipe_time_increment;
        gesture(swipe_time, [w / 2, h * 0.95], [w / 2 - 15, h * 0.5]); //模拟手势
        common.sleep(1.2);
    } //循环函数
    if (max_try_times_swipe < 0) errorMessage("上滑屏幕失败"); //尝试失败，重新设置一下参数
    log("解锁成功");
    log("尝试得到最佳滑动时间: " + swipe_time + "(毫秒)"); //可到日志中查看最佳滑动时间
    return false;
};

common.unLock = function () {
    var tel_ele = text("电话").findOnce();
    common.toastLog(tel_ele);
    if (tel_ele) {
        common.toastLog("已解锁");
    }
    Home();
    var isLock = true;
    var isWakeUp = common.wakeUp();
    if (isWakeUp) {
        common.toastLog("已解锁");
        isLock = false;
        return isLock;
    }
    common.sleep(0.1);
    var lastTextArray = common.getAllText();
    isLock = common.unLockRetry();
    var textArray = common.getAllText();
    // common.toastLog(textArray)
    // common.toastLog(lastTextArray)
    var diff = textArray.getDifference(lastTextArray);
    // common.toastLog(diff)
    if (diff.length != 0) {
        // common.toastLog('解锁成功');
        isLock = false;
    }
    return isLock;
};

common.lock = function () {
    common.toastLog("锁屏");
    Power();
};

//打开APP
common.launchApp = function (app_name) {
    //打开应用
    app.launchApp(app_name);

    //如果存在提示，则点击允许
    var loop = 0;
    while (loop < 5) {
        loop++;
        common.sleep(0.35);
        common.textClick("允许");
    }

    //设置屏幕缩放
    setScreenMetrics(1080, 1920);
    common.sleep(3);
};

common.launch = function (package_name) {
    app.launch(package_name);
    var loop = 0;
    while (loop < 5) {
        loop++;
        common.sleep(0.35);
        common.textClick("允许");
    }

    setScreenMetrics(1080, 1920);
    common.sleep(3);
};

common.checkOpen = function () {
    var loop = 0;
    common.sleep(1);
    while (loop < 5) {
        loop++;
        common.sleep(0.35);
        common.textClick("允许");
    }
};

common.textClick = function (msgText) {
    var ele = text(msgText).findOnce();
    if (ele) {
        click(msgText);
    }
    common.sleep(1);
};
common.getClickItem = function (ele) {
    var clickAble = ele.clickable();
    var item = ele;
    while (!clickAble) {
        item = item.parent();
        clickAble = item.clickable();
        common.sleep(1);
    }
    return item;
};

//通过坐标点击 4.1.1版本可使用
common.boundsRandomClick = function (item) {
    var bounds = item.bounds();
    var x = random(bounds.left, bounds.right);
    var y = random(bounds.top, bounds.bottom);
    toastLog(bounds);
    toastLog(x);
    toastLog(y);
    common.sleep(3);
    var ret = click(x, y);
    common.toastLog(ret);
    common.sleep(1);
};

common.bezierCurves = function (cp, t) {
    cx = 3.0 * (cp[1].x - cp[0].x);
    bx = 3.0 * (cp[2].x - cp[1].x) - cx;
    ax = cp[3].x - cp[0].x - cx - bx;
    cy = 3.0 * (cp[1].y - cp[0].y);
    by = 3.0 * (cp[2].y - cp[1].y) - cy;
    ay = cp[3].y - cp[0].y - cy - by;

    tSquared = t * t;
    tCubed = tSquared * t;
    result = {
        x: 0,
        y: 0,
    };
    result.x = ax * tCubed + bx * tSquared + cx * t + cp[0].x;
    result.y = ay * tCubed + by * tSquared + cy * t + cp[0].y;
    return result;
};

// 仿真随机带曲线滑动
// qx, qy, zx, zy, time 代表起点x,起点y,终点x,终点y,过程耗时单位毫秒
common.smlMove = function (qx, qy, zx, zy, time) {
    var xxy = [time];
    var point = [];
    var dx0 = {
        x: qx,
        y: qy,
    };
    var dx1 = {
        x: random(qx - 100, qx + 100),
        y: random(qy, qy + 50),
    };
    var dx2 = {
        x: random(zx - 100, zx + 100),
        y: random(zy, zy + 50),
    };
    var dx3 = {
        x: zx,
        y: zy,
    };
    for (var i = 0; i < 4; i++) {
        eval("point.push(dx" + i + ")");
    }
    // log(point[3].x)
    for (let i = 0; i < 1; i += 0.08) {
        xxyy = [
            parseInt(common.bezierCurves(point, i).x),
            parseInt(common.bezierCurves(point, i).y),
        ];
        xxy.push(xxyy);
    }
    // log(xxy);
    gesture.apply(null, xxy);
};

common.scrollUpByHuman = function (long) {
    var ia = 50,
        ib = 60,
        ja = 30,
        jb = 40;
    if (long) {
        var ia = 60,
            ib = 70,
            ja = 20,
            jb = 30;
    }
    var ya = (h / 100) * random(ia, ib);
    var yb = (h / 100) * random(ja, jb);
    // toastLog(ya)
    // toastLog(yb)
    var xa = w / 2 + random(-w / 5, w / 5);
    var xb = xa + random(1, 5);
    var time = random(300, 600);
    try {
        common.smlMove(xa, ya, xb, yb, time);
    } catch (err) {
        toastLog(err);
        common.scrollUpByHuman(long);
    }
    common.sleep(0.5 * random(1, 2));
};

common.scrollDownByHuman = function () {
    var ya = random(h / 2 - 300, h / 2);
    var yb = ya + random(h / 2 - 300, h / 2);
    var xa = random(w / 2 - 300, w / 2 + 300);
    var xb = xa + random(1, 150);
    var time = random(600, 1200);
    common.smlMove(xa, ya, xb, yb, time);
    common.sleep(0.5 * random(1, 2));
};

common.scrollBackwardByHuman = function () {
    var xa = random(w / 2 - 300, w / 2);
    var xb = xa + random(w / 2 + 300, w / 2);

    var ya = random(h / 2 - 300, h / 2 + 300);
    var yb = ya + random(1, 10);

    var time = random(600, 900);
    common.smlMove(xa, ya, xb, yb, time);
    common.sleep(0.5 * random(1, 2));
};

common.scrollForwardByHuman = function () {
    var ia = 60,
        ib = 75,
        ja = 70,
        jb = 60;
    var ya = (h / 100) * random(ia, ib);
    var yb = ya + random(1, 3);
    var xa = (w / 100) * random(ja, jb);
    var xb = xa - random(500, 800);
    var time = random(600, 1000);
    try {
        common.smlMove(xa, ya, xb, yb, time);
    } catch (err) {
        toastLog(err);
    }
    common.sleep(0.5 * random(1, 2));
};

common.genArgsStr = function (args) {
    var argsStr = "";
    var argsArray = Object.keys(args);
    for (var i = 0; i < argsArray.length; i++) {
        var k = argsArray[i];
        var v = args[k];
        argsStr += "{0}={1}&".format(k, v);
    }
    return argsStr;
};

common.getAllText = function (setting) {
    var setting = setting || {};
    var defaultSetting = {
        getText: true,
        getDesc: true,
        getId: false,
        removeRepetitiveElements: true,
    };
    Object.assign(defaultSetting, setting);
    log(defaultSetting);
    var allStr = [];
    var getDescAndTextAndIdOfNode = function (node) {
        if (node) {
            if (defaultSetting.getText) {
                var text = node.text();
                if (!!text) {
                    allStr.push(text);
                }
            }
            if (defaultSetting.getDesc) {
                var desc = node.desc();
                if (!!desc) {
                    allStr.push(desc);
                }
            }
            if (defaultSetting.getId) {
                var id = node.id();
                if (!!id) {
                    allStr.push(id);
                }
            }
        }
        for (let i = 0; i < node.childCount(); i++) {
            getDescAndTextAndIdOfNode(node.child(i));
        }
    };
    var getFrameLayoutNode = function () {
        return className("FrameLayout").findOne(2000);
    };
    getDescAndTextAndIdOfNode(getFrameLayoutNode());

    function removeRepetitiveElements(arr) {
        var obj = {};
        for (let i = 0; i < arr.length; i++) {
            if (obj.hasOwnProperty(arr[i])) {
            } else {
                obj[arr[i]] = true;
            }
        }
        return Object.keys(obj);
    }
    if (defaultSetting.removeRepetitiveElements) {
        allStr = removeRepetitiveElements(allStr);
    }
    return allStr;
};

common.getSymbol = function (code) {
    var symbol = "";
    if (["5", "6", "9"].indexOf(code.slice(0, 1)) != -1) {
        symbol = "sh";
    } else if (["11", "13", "15", "16"].indexOf(code.slice(0, 2)) != -1) {
        symbol = "sz";
    }
    return symbol;
};

common.httpGet = function (uri, args, options, retry) {
    if (!retry) {
        retry = 0;
    }
    try {
        if (args && !retry) {
            var argsStr = common.genArgsStr(args);
            var uri = "{0}?{1}".format(uri, argsStr);
        }
        var res = http.get(uri, options);
        if (res.statusCode == 200) {
            return res;
        } else {
            retry++;
            if (retry > 3) {
                var msg = "{0} : {1} 多次获取信息失败".format(uri, args);
                common.toastLog(msg);
                return;
            }
            common.sleep(3 + retry * 3);
            return common.httpGet(uri, args, options, retry);
        }
    } catch (err) {
        common.toastLog(err);
        common.toastLog("网络出错了");
        common.sleep(3 + retry * 3);
        retry++;
        if (retry > 3) {
            common.toastLog("多次获取信息失败");
            return;
        }
    }
};

common.httpPost = function (uri, data, options, retry) {
    if (!retry) {
        retry = 0;
    }
    try {
        var res = http.post(uri, (data = data), (options = options));
        // common.toastLog(res.body.string());
        if ([200, 201].indexOf(res.statusCode) != -1) {
            return res;
        } else {
            retry++;
            if (retry > 3) {
                common.toastLog("多次获取信息失败");
                return;
            }
            common.sleep(3 + retry * 3);
            return common.httpPost(uri, data, options, retry);
        }
    } catch (err) {
        common.toastLog(err);
        common.toastLog("网络出错了");
        common.sleep(3 + retry * 3);
        retry++;
        if (retry > 3) {
            common.toastLog("多次获取信息失败");
            return;
        }
    }
};

module.exports = common;
