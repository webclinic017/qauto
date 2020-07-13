var flow = require("./flow");

flow.init({
    app_name: "e海通财",
    package_name: "com.android.haitong",
    tip_ids: ["iv_advertisement_layout"],
    tip_texts: ["关闭", "忽略"],
});

flow.run({
    getPassItem: function () {
        var pass_ele = idEndsWith("tradelogin_edt_tradepwd").findOnce();
        return pass_ele;
    },
    getItem: function () {
        var item = text("交易").findOnce();
        return item;
    },
    inputPassword: function () {
        var pass_ele = idEndsWith("tradelogin_edt_tradepwd").findOnce();
        if (pass_ele) {
            pass_ele.setText("200104");
            flow.common.sleep(1);
            click("登　录");
            flow.common.sleep(3);
            click("委托买入");
            flow.common.sleep(1);
        }
    },
    buy: function (fun, data) {
        var trade_text = "委托买入";
        return fun.trade(fun, data, trade_text);
    },
    sell: function (fun, data) {
        var trade_text = "委托卖出";
        return fun.trade(fun, data, trade_text);
    },
    trade: function (fun, data, trade_text) {
        var msg = "{0},{1}:{2},价格:{3}".format(
            data.code,
            trade_text,
            data.size,
            data.price
        );
        flow.common.toastLog(msg);
        flow.common.sleep(1);
        var item = text("交易").findOnce();
        flow.jumpToTrade(fun, item);
        flow.common.sleep(1);
        click(trade_text);
        flow.common.sleep(1);
        var pass_ele = fun.getPassItem();
        var is_input = flow.checkInputPassword(fun, pass_ele);
        if (is_input) {
            click(trade_text);
            flow.common.sleep(1);
        }
        flow.closeTips(fun);

        var code_ele_wait_text = "证券代码";
        text(code_ele_wait_text).waitFor();
        var price_ele = text("委托价格").findOnce();
        var sell_search_ele = text(code_ele_wait_text).findOnce();
        sell_search_ele.click();
        sell_search_ele.setText(data.code);
        flow.common.sleep(1);

        fun.checkChoice(data);

        flow.common.sleep(2);
        var trade_num_ele = text("委托数量").findOnce();
        trade_num_ele.setText(data.size);
        // 更新价格
        price_ele.setText(data.price);
        flow.common.sleep(1);

        fun.tradeComfirm(fun, data);
    },
    checkChoice: function (data) {
        flow.common.sleep(1);
        var has_choice = text("请选择证券").findOnce();
        if (has_choice) {
            click(data.code_cn);
            flow.common.sleep(1);
        }
    },
    tradeComfirm: function (fun, data) {
        if (data.action == "buy") {
            click("买入", 2);
        } else {
            click("卖出", 2);
        }
        flow.common.sleep(1);
        click("确定");
        flow.common.sleep(1);
        fun.getEntrustNo();
        click("确定");
        flow.common.sleep(1);
        back();
    },
    getEntrustNo: function () {
        entrust_no = "";
        var entrust_ele = idEndsWith("dlg_entrust_result_tv_msg").findOnce();
        if (entrust_ele) {
            var entrust_no = entrust_ele.text().split(":")[1];
            flow.extras.entrust_no = entrust_no
            flow.common.toastLog(entrust_no);
        }
    },
});
