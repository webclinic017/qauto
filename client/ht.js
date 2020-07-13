var flow = require("./flow");

flow.init({
    app_name: "涨乐财富通",
    package_name: "com.lphtsccft",
    tip_ids: ["iv_advertisement_layout", "dialog_iv_cancel"],
});

flow.run({
    getPassItem: function () {
        var pass_ele = idEndsWith("password_edit").findOnce();
        return pass_ele;
    },
    getItem: function () {
        var item = text("交易").findOnce();
        return item;
    },
    inputPassword: function () {
        var pass_ele = idEndsWith("password_edit").findOnce();
        var shield_pass_ele = idEndsWith("shield_password_edit").findOnce();
        if (pass_ele && shield_pass_ele) {
            pass_ele.setText("200104");
            flow.common.sleep(1);
            shield_pass_ele.setText("192706");
            click("登 录");
            flow.common.sleep(1);
        }
    },
    buy: function (fun, data) {
        var msg = "{0},买入:{1},价格:{2}".format(
            data.code,
            data.size,
            data.price
        );
        flow.common.toastLog(msg);

        fun.tradeBefore(fun);

        var code_ele_wait_text = "请输入股票代码";
        text(code_ele_wait_text).waitFor();
        var buy_search_ele = text(code_ele_wait_text).findOnce();
        buy_search_ele.click();
        buy_search_ele.setText(data.code);
        flow.common.sleep(1);

        fun.checkChoice(data);

        var buy_num_ele = text("买入数量").findOnce();
        buy_num_ele.setText(data.size);
        // 更新价格 TODO:
        var share_price_ele = idEndsWith("et_content").findOnce();
        share_price_ele.setText(data.price);
        flow.common.sleep(1);

        fun.tradeComfirm(fun, data);
    },
    sell: function (fun, data) {
        var msg = "{0},卖出:{1},价格:{2}".format(
            data.code,
            data.size,
            data.price
        );
        flow.common.toastLog(msg);

        fun.tradeBefore(fun);

        var code_ele_wait_text = "请输入股票代码";
        text(code_ele_wait_text).waitFor();
        var sell_search_ele = text(code_ele_wait_text).findOnce();
        sell_search_ele.click();
        flow.common.sleep(1);
        var sell_search_ele = text(code_ele_wait_text)
            .focused(false)
            .findOnce();
        sell_search_ele.setText(data.code);
        flow.common.sleep(1);
        click(data.code);
        flow.common.sleep(1);
        click("卖出价格");
        flow.common.sleep(1);

        fun.checkChoice(data);

        flow.common.sleep(2);
        var sell_num_ele = text("卖出数量").findOnce();
        sell_num_ele.setText(data.size);
        // 更新价格
        var share_price_ele = idEndsWith("et_content").findOnce(2);
        share_price_ele.setText(data.price);
        flow.common.sleep(1);

        fun.tradeComfirm(fun, data);
    },
    tradeBefore: function (fun) {
        flow.common.sleep(1);
        var item = fun.getItem();
        flow.jumpToTrade(fun, item);
        flow.common.sleep(1);
        var buy_ele = idEndsWith("trade_portal_normal_buy").findOnce();
        buy_ele.click();
        flow.common.sleep(1);
        var pass_ele = fun.getPassItem();
        flow.checkInputPassword(fun, pass_ele);
        flow.closeTips(fun);
    },
    checkChoice: function (data) {
        flow.common.sleep(1);
        var has_choice = text("请选择").findOnce();
        if (has_choice) {
            click(data.code_cn);
            flow.common.sleep(1);
        }
    },
    tradeComfirm: function (fun, data) {
        if (data.action == "buy") {
            click("买入");
        } else {
            click("卖出");
        }
        flow.common.sleep(1);
        click("确定");
        flow.common.sleep(1);
        fun.getEntrustNo();
        click("确定");
        flow.common.sleep(1);
        back();
        flow.common.sleep(1);
        back();
    },
    getEntrustNo: function () {
        entrust_no = "";
        var entrust_ele = idEndsWith("dialog_tv_message").findOnce();
        if (entrust_ele) {
            var entrust_no = entrust_ele.text().split(":")[1];
            flow.extras.entrust_no = entrust_no;
            flow.common.toastLog(entrust_no);
        }
    },
});
