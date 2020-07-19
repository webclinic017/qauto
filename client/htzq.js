var commons = require("common.js");

// 条件单定投单,降低成本,类似定投
// 9:55~10:55,检查涨幅,涨幅超过5%,且持仓盈利卖出1/4
// 13:30~14:30,检查涨跌幅,跌幅超过3%买入,标记当日有买入
// 14:45,尾盘跌幅超过1%买入,当日有买入跌幅达4.25%以上,继续买入

// 检查持仓收益卖出

var config = {
    per_share_value: 500, // 每次买入金额
    main_activity: "com.lphtsccft.zhangle.main.MainActivity",
    key: "SCU53613T74bdd3a5e5ff2eb57218f74f71d495965d0711a8483e7",
    daily_funds: {
        "159928": "消费ETF",
        "512170": "医疗ETF",
        "512760": "半导体50",
        "513050": "中概互联",
    },
};

function main() {
    // commons.engineCheckAndWait();
    // startApp();
    // var code = "512760";
    // buy(code, config.per_share_value * 3);
    // sell(code, config.per_share_value * 3);
    check_market_funds();
}
main();

function check_market_funds_internal() {
    var funds = idEndsWith("user_stock_list_view").findOnce();
    if (!funds) {
        var msg = "未找到自选列表";
        commons.toastLog(msg);
        return;
    }
    var date_arr = new Date();
    var hour = parseInt(date_arr.getHours());
    var minute = parseInt(date_arr.getMinutes());
    var storage_app = commons.storageApp();
    var date = "{0}-{1}-{2}".format(
        date_arr.getFullYear(),
        date_arr.getMonth() + 1,
        date_arr.getDate()
    );
    var today_has_buy_key = "{0}:{1}".format(date, "buy");
    var today_has_sell_key = "{0}:{1}".format(date, "sell");
    var today_has_buy = storage_app.get(today_has_buy_key, false);
    var today_has_sell = storage_app.get(today_has_sell_key, false);
    var has_trade = false;
    for (var i = 0; i < funds.childCount(); i++) {
        if (has_trade) {
            jumpToMarket();
        }
        var fund = funds.child(i);
        var price_rise_ele = fund.findOne(idEndsWith("item_price_rise"));
        var price_rise = parseFloat(price_rise_ele.text());
        var last_price_ele = fund.findOne(idEndsWith("item_latest_price"));
        var last_price = parseFloat(last_price_ele.text());
        var code_ele = fund.findOne(idEndsWith("item_stock_code"));
        var code = code_ele.text();
        var msg = "{0},价格:{1},涨幅:{2}".format(code, last_price, price_rise);
        commons.toastLog(msg);
        var times = Math.abs(price_rise) / 0.95;
        if (price_rise > 4.75 && hour > 9 && !today_has_sell) {
            // 盘中,10:00~,涨幅大于4.75,今日未卖出,卖出
            has_trade = true;
            // 发送卖出提示到微信
            notifyToWX(code, code_cn, price_rise);
            // 取不到持仓收益
            // sell(code, config.per_share_value * times);
            storage_app.put(today_has_sell_key, true);
        } else if (price_rise < -2.85 && hour > 10 && !today_has_buy) {
            // 盘中,11:00~,今日未买入,跌幅大于2.85
            has_trade = true;
            buy(code, config.per_share_value * times);
            storage_app.put(today_has_buy_key, true);
        } else if (price_rise < -0.95 && hour > 13 && minute > 45) {
            // 盘尾,14:46~,跌幅小于0.95,买入
            has_trade = true;
            buy(code, config.per_share_value * times);
            storage_app.put(today_has_buy_key, true);
        }
    }
}

function check_market_funds() {
    var is_time = is_market_time();
    var current_activity = currentActivity();
    if (current_activity != config.main_activity) {
        startApp();
    }
    while (is_time) {
        jumpToMarket();
        check_market_funds_internal();
        var is_time = is_market_time();
        commons.sleep(60 * 3);
    }
    var msg = "不在程序检测时间";
    commons.toastLog(msg);
}

function is_market_time() {
    var is_time = false;
    var date_arr = new Date();
    var hour = parseInt(date_arr.getHours());
    if ((hour < 16 && hour > 12) || (hour > 10 && hour < 12)) {
        is_time = true;
    }
    return is_time;
}

function startApp() {
    var appName = "涨乐财富通";
    commons.launch(appName);
    commons.sleep(7);
    var close_ele = idEndsWith("dialog_iv_cancel").findOnce();
    if (close_ele) {
        back();
    }
}

function notifyToWX(code, code_cn, price_rise) {
    var msg = "{0},{1},涨幅:{2}".format(code, code_cn, price_rise);
    wx_url = "https://sc.ftqq.com/{0}.send?text={1}&desp={2}".format(
        config.key,
        "卖出提示",
        msg
    );
    commons.httpGet(wx_url);
}

function check_pos(code) {}

function buy(code, value) {
    var msg = "{0},买入:{1}".format(code, value);
    commons.toastLog(msg);
    jumpToTrade();
    var buy_ele = idEndsWith("trade_portal_normal_buy").findOnce();
    buy_ele.click();
    commons.sleep(1);
    checkInputPassword();
    var code_ele_wait_text = "请输入股票代码";
    text(code_ele_wait_text).waitFor();
    var buy_search_ele = text(code_ele_wait_text).findOnce();
    buy_search_ele.click();
    buy_search_ele.setText(code);
    commons.sleep(1);
    var has_choice = text("请选择").findOnce();
    if (has_choice) {
        var code_cn = config.daily_funds[code];
        var choice_ele = textEndsWith(code_cn).findOnce();
        choice_ele.click();
        commons.sleep(1);
    }
    var buy_num_ele = text("买入数量").findOnce();
    var data = calValueToNum(code);
    buy_num_ele.setText(data.share_num);
    // 更新价格
    var share_price_ele = idEndsWith("et_content").findOnce();
    share_price_ele.setText(data.price);
    commons.sleep(5);
    back();
    return;
    click("买入");
    commons.sleep(1);
    click("确定");
    commons.sleep(1);
    click("确定");
    commons.sleep(1);
    back();
}

function sell(code, value) {
    var msg = "{0},卖出:{1}".format(code, value);
    commons.toastLog(msg);
    jumpToTrade();
    var sell_ele = idEndsWith("trade_portal_normal_sell").findOnce();
    sell_ele.click();
    commons.sleep(1);
    checkInputPassword();
    var code_ele_wait_text = "请输入股票代码";
    commons.sleep(1);
    text(code_ele_wait_text).waitFor();
    var sell_search_ele = text(code_ele_wait_text).findOnce();
    sell_search_ele.click();
    commons.sleep(1);
    var sell_search_ele = text(code_ele_wait_text).focused(false).findOnce();
    sell_search_ele.setText(code);
    commons.sleep(1);
    click(code);
    commons.sleep(1);
    click("卖出价格");
    commons.sleep(1);
    var has_choice = text("请选择").findOnce();
    if (has_choice) {
        var code_cn = config.daily_funds[code];
        var choice_ele = textEndsWith(code_cn).findOnce();
        choice_ele.click();
        commons.sleep(1);
    }
    commons.sleep(2);
    var sell_num_ele = text("卖出数量").findOnce();
    var data = calValueToNum(value, 1);
    sell_num_ele.setText(data.share_num);
    // 更新价格
    var share_price_ele = idEndsWith("et_content").findOnce(2);
    share_price_ele.setText(data.price);
    commons.sleep(5);
    back();
    return;
    click("卖出");
    commons.sleep(1);
    click("确定");
    commons.sleep(1);
    click("确定");
    commons.sleep(1);
    back();
}

function calValueToNum(value, index) {
    // 计算买入/卖出金额转换成股数,越靠近买入金额,则取相应股数
    commons.sleep(1);
    if (!index) {
        index = 0;
    }
    var new_price = getNewPrice(index);
    var per_share_num = Math.trunc(value / new_price / 100);
    var per_share_predict = Math.abs(value - per_share_num * 100 * new_price);
    var per_share_predict_plus = Math.abs(
        value - (per_share_num + 1) * 100 * new_price
    );
    commons.toastLog(new_price);
    commons.toastLog(per_share_predict);
    commons.toastLog(per_share_predict_plus);

    if (per_share_predict > per_share_predict_plus) {
        per_share_num += 1;
    }
    var new_price = getNewPrice(index);
    var data = {
        price: new_price,
        share_num: per_share_num * 100,
    };
    return data;
}

function getNewPrice(index) {
    var new_price_ele = idEndsWith("tv_newest_price").findOnce(index);
    var new_price = parseFloat(new_price_ele.text());
    return new_price;
}

function jumpToTrade() {
    commons.sleep(1);
    var is_in_trade_ele = text("我的持仓").findOnce();
    if (is_in_trade_ele) {
        var msg = "当前处于交易页面";
        commons.toastLog(msg);
        return;
    }
    var tradeEle = text("交易").findOnce();
    tradeEle.click();
    commons.sleep(1);
}

function jumpToMarket() {
    commons.sleep(1);
    var is_in_market_ele = text("自选股").findOnce();
    if (is_in_market_ele) {
        var msg = "当前处于行情页面";
        commons.toastLog(msg);
        return;
    }
    var tradeEle = text("行情").findOnce();
    tradeEle.click();
    commons.sleep(1);
}

function checkInputPassword() {
    var pass_input_ele = idEndsWith("password_edit").findOnce();
    if (pass_input_ele) {
        pass_input_ele.setText("200104");
        click("登 录");
        commons.sleep(1);
    }
}
