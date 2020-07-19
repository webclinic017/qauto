var commons = require("common.js");

// map,跟踪同指数基金套利:done
// qdii判断是否卖出,1:根据期货指数(老虎指数获取失败:token失效,更换英为财情),2:根据当日涨跌幅(?)
// 白银基金为t+1,申购,特殊处理
// 黄金基金t+2,qdii都是t+2
// 溢价历史数据获取:done
// 交易额优化(剔除交易额小),历史交易:done(自己接口实现)
// http://quotes.money.163.com/fund/zyjl_501027.html
// 卖出优化:done

// 条件单定投单,降低成本
// 9:55~10:55,检查涨幅,涨幅超过5%,且持仓盈利卖出1/4
// 13:30~14:30,检查涨跌幅,跌幅超过3%买入,标记当日有买入
// 14:45,尾盘跌幅超过1%买入,当日有买入跌幅达4.25%以上,继续买入

var config = {
    white_funds: ["161716", "160618"], // 招商双债,鹏华丰泽
    app_name: "华宝智投",
    package_name: "com.hwabao.hbstockwarning",
    max_apply: 3, // 最高申购数量
    market_value: 1000, // 默认申购金额
    qdii_types: ["E", "C", "A"],
    alias_funds: {
        "513050": "164906", // 互联网50
        "159941": "161130", // 纳斯达克100
        "513500": "161125", // 标普500
    },
};

function main() {
    // code = "161716";
    // money = 1000;
    // applyForPurchase(code, money);
    // return;
    commons.engineCheckAndWait();
    initJiSiLuFunds();
    var has_start_app = false;
    var storage_app = commons.storageApp();
    var has_auto_ipo = storage_app.get("autoIpo", false);
    if (!has_auto_ipo) {
        startApp();
        has_start_app = true;
        autIPO();
    } else {
        var msg = "可转债已申购";
        commons.toastLog(msg);
    }
    var is_in_rt_time = checkInRTTime();
    if (is_in_rt_time) {
        if (!has_start_app) {
            startApp();
        }
        checkPOSRT();
        getLOFFunds();
    } else {
        var msg = "不在检查溢价率时间";
        commons.toastLog(msg);
    }
}
main();

function startApp() {
    var current_activity = currentActivity();
    if (current_activity.indexOf(config.package_name) != -1) {
        var msg = "处于{0}".format(config.app_name);
        commons.toastLog(msg);
        return;
    }
    var msg = "打开{0}".format(config.app_name);
    commons.toastLog(msg);
    commons.launch(config.app_name);
    commons.sleep(3);
    var is_input = checkInputPassword();
    if (is_input) {
        return;
    }
    commons.sleep(7);
    // text("输入股票代码/名称/简拼").waitFor();
}

function checkInRTTime() {
    var is_in_rt_time = false;
    var date_arr = new Date();
    var hour = parseInt(date_arr.getHours());
    var minute = parseInt(date_arr.getMinutes());
    // 14:49~59
    if (hour < 15 && hour > 13 && minute > 49 && minute < 59) {
        is_in_rt_time = true;
    }
    return is_in_rt_time;
}

function getLOFFunds() {
    var msg = "检查集思录LOF";
    commons.toastLog(msg);
    var args = {
        ___jsl: 0,
        rp: 300,
        page: 1,
    };
    var storage_app = commons.storageApp();
    var funds = storage_app.get("funds", []);
    commons.toastLog(funds.length);
    for (var i = 0; i < funds.length; i++) {
        var fundEle = funds[i];
        var uri = fundEle.uri;
        commons.toastLog(uri);
        var res = commons.httpGet(uri, args);
        var detail = res.body.json();
        for (var j = 0; j < detail.rows.length; j++) {
            var row = detail.rows[j];
            var discount_rt = parseFloat(row.cell.discount_rt);
            var volume = parseFloat(row.cell.volume);
            if (row.cell.apply_status == "暂停申购") {
                var msg = "{0},{1}:{2}: {3} 暂停申购".format(
                    row.cell.fund_id,
                    row.cell.fund_nm,
                    row.cell.issuer_nm,
                    discount_rt
                );
                commons.toastLog(msg);
                continue;
            }
            // 溢价率大于2.75,成交额大于5w
            if (discount_rt >= 2.75 && volume > 5) {
                var code = row.cell.fund_id;
                var data = getAllRT(code);
                if (!data) {
                    var msg = "交易额太小,跳过";
                    commons.toastLog(msg);
                    return;
                }
                dealWithRT(data, {});
            }
        }
    }
}

function initJiSiLuFunds() {
    var msg = "集思录初始化";
    commons.toastLog(msg);
    var appName = "jisilu";
    var storage_app = commons.storageApp();
    // storage_app.clear();
    var date_key = "{0}:{1}".format(appName, "date");
    var date_arr = new Date();
    var date = "{0}-{1}-{2}".format(
        date_arr.getFullYear(),
        date_arr.getMonth() + 1,
        date_arr.getDate()
    );
    var last_date = storage_app.get(date_key, "");
    if (date == last_date) {
        commons.toastLog("今日已经初始化");
        return;
    }
    storage_app.clear();
    commons.toastLog(date);
    commons.toastLog(last_date);
    var args = {
        ___jsl: 0,
        rp: 300,
        page: 1,
    };
    var funds = [];
    var code_types = ["E", "C", "A"];
    for (var i = 0; i < code_types.length; i++) {
        var code_type = code_types[i];
        commons.toastLog(code_type);
        var uri = "https://www.jisilu.cn/data/qdii/qdii_list/" + code_type;
        commons.toastLog(uri);
        var res = commons.httpGet(uri, args);
        var str = res.body.json();
        var sub_funds = [];
        for (var j = 0; j < str.rows.length; j++) {
            var row = str.rows[j];
            var fund_id = row.cell.fund_id;
            sub_funds.push(fund_id);
        }
        var detail_uri = "https://app.jisilu.cn/api_v2/qdii/detail/";
        var hist_uri =
            "https://www.jisilu.cn/data/qdii/detail_hists/?___jsl=LST___t=";
        var data = {
            qtype: code_type,
            funds: sub_funds,
            uri: uri,
            detail_uri: detail_uri,
            hist_uri: hist_uri,
        };
        funds.push(data);
    }
    var code_types = ["stock_lof_list", "index_lof_list"];
    for (var i = 0; i < code_types.length; i++) {
        var code_type = code_types[i];
        commons.toastLog(code_type);
        var uri = "https://www.jisilu.cn/data/lof/" + code_type + "/";
        commons.toastLog(uri);
        var res = commons.httpGet(uri, args);
        var detail = res.body.json();
        var sub_funds = [];
        for (var j = 0; j < detail.rows.length; j++) {
            var row = detail.rows[j];
            var fund_id = row.cell.fund_id;
            sub_funds.push(fund_id);
        }
        var detail_uri =
            "https://www.jisilu.cn/data/lof/detail_fund/?___jsl=LST___t=";
        var hist_uri =
            "https://www.jisilu.cn/data/lof/hist_list/{0}?___jsl=LST___t=";
        var data = {
            qtype: code_type,
            funds: sub_funds,
            uri: uri,
            detail_uri: detail_uri,
            hist_uri: hist_uri,
        };
        funds.push(data);
    }
    // commons.toastLog(typeof(date));
    storage_app.put(date_key, date);
    storage_app.put("funds", funds);
    storage_app.put("apply_funds", []);
    storage_app.put("autoIpo", false);
}

function getAllRT(code) {
    var msg = "{0},获取所有溢价率".format(code);
    commons.toastLog(msg);
    var ave_volume = getAveVolume(code);
    if (ave_volume < 10) {
        var msg = "{0},本月平均成交额:{1}".format(code, ave_volume);
        commons.toastLog(msg);
        return;
    }
    var req = getReq(code);
    var jisilu_rt = 0,
        tt_fund_rt = 0,
        tencent_rt = 0;
    if (Object.keys(req).length != 0) {
        jisilu_rt = getJiSiLuRT(code, req);
    } else {
        commons.toastLog("集思录未收录");
    }
    // commons.toastLog(req);
    var tt_fund_rt = getTTFundRT(code);
    var tencent_rt = getTencentRT(code, req);
    if (!jisilu_rt) {
        jisilu_rt = 0;
    }
    if (!tt_fund_rt) {
        tt_fund_rt = 0;
    }
    if (!tencent_rt) {
        tencent_rt = 0;
    }
    if (jisilu_rt == 0) {
        if (tt_fund_rt && tencent_rt) {
            jisilu_rt = (tt_fund_rt + tencent_rt) / 2;
        } else if (tt_fund_rt) {
            jisilu_rt = tt_fund_rt;
        } else if (tencent_rt) {
            jisilu_rt = tencent_rt;
        }
    }
    var msg = "{0}:溢价,集思录:{1},天天基金:{2},腾讯财经:{3}".format(
        code,
        jisilu_rt,
        tt_fund_rt,
        tencent_rt
    );
    var rts = {
        jisilu_rt: jisilu_rt,
        tt_fund_rt: tt_fund_rt,
        tencent_rt: tencent_rt,
        req: req,
        code: code,
    };
    commons.toastLog(msg);
    return rts;
}

function getAveVolume(code) {
    var msg = "{0},获取平均交易额".format(code);
    commons.toastLog(msg);
    var uri = "http://104.225.144.84:9000/get_ave_volume";
    var args = {
        code: code,
    };
    var res = commons.httpGet(uri, args);
    if (!res) {
        return;
    }
    var detail = res.body.json();
    var volume = detail.volume;
    return parseFloat(volume / 10000);
}

function getCurrentPrice(code) {
    var uri = "http://data.gtimg.cn/flashdata/hushen/minute/{0}{1}.js".format(
        "sz",
        code
    );
    var uri2 = "http://data.gtimg.cn/flashdata/hushen/minute/{0}{1}.js".format(
        "sh",
        code
    );
    var res = commons.httpGet(uri, {}, {}, uri2);
    if (!res) {
        var msg = "{0} : 腾讯价格获取失败".format(code);
        commons.toastLog(msg);
        return;
    }
    var flash_price_str = res.body.string();
    var flash_price_arr = flash_price_str.split("\n");
    var current_priceStr = flash_price_arr[flash_price_arr.length - 2];
    var current_priceArr = current_priceStr.split(" ");
    var current_price = current_priceArr[1];
    // commons.toastLog(current_price);
    return current_price;
}

function getReq(code) {
    var storage_app = commons.storageApp();
    var funds = storage_app.get("funds", []);
    var req = {};
    for (var i = 0; i < funds.length; i++) {
        var fundEle = funds[i];
        var sub_funds = fundEle.funds;
        for (var j = 0; j < sub_funds.length; j++) {
            var fund_id = sub_funds[j];
            if (fund_id == code) {
                req = fundEle;
                return req;
            }
        }
    }
    return req;
}

function getJiSiLuRT(code, req) {
    var uri = req.detail_uri;
    var hist_uri = req.hist_uri;
    var data = {
        is_search: 1,
        fund_id: code,
        fund_type: req.qtype.split("_")[0],
        rp: 5,
        page: 1,
    };
    if (config.qdii_types.indexOf(req.qtype) != -1) {
        uri = uri + code;
        var res = commons.httpGet(uri);
        if (!res) {
            commons.toastLog("集思录溢价获取失败");
            return;
        }
        var detail = res.body.json();
        if (detail.isError != 0) {
            commons.toastLog("集思录估值获取失败");
            commons.toastLog(uri);
            commons.toastLog(detail);
            return;
        }
        var jisilu_rt = parseFloat(detail.data.discount_rt);
        // commons.toastLog(detail.data);
        if (detail.data.apply_fee == "暂停") {
            var msg = "{0} : {1} : {2}: 溢价: {3} 暂停申购".format(
                detail.data.fund_id,
                detail.data.fund_nm,
                detail.data.issuer_nm,
                jisilu_rt
            );
            commons.toastLog(msg);
            return;
        }
        var res = commons.httpPost(hist_uri, data);
        var detail = res.body.json();
        var rows = detail.rows;
        var average_rt = calHistAveRT(rows);
        return jisilu_rt - average_rt;
    } else {
        var res = commons.httpPost(uri, data);
        var detail = res.body.json();
        var cell = detail.rows[0].cell;
        var jisilu_rt = parseFloat(cell.discount_rt);
        if (cell.apply_fee == "暂停") {
            var msg = "{0} : {1} : {2}: 溢价: {3} 暂停申购".format(
                cell.fund_id,
                cell.fund_nm,
                cell.issuer_nm,
                jisilu_rt
            );
            commons.toastLog(msg);
            return;
        }
        var rp = 22;
        var args = {
            ___jsl: 0,
            rp: rp,
            page: 1,
        };
        hist_uri = hist_uri.format(code);
        var res = commons.httpGet(hist_uri, args);
        var detail = res.body.json();
        var rows = detail.rows;
        var average_rt = calHistAveRT(rows);
        return jisilu_rt - average_rt;
    }
}
function getTTFundRT(code) {
    var uri = "https://fundmobapi.eastmoney.com/FundMApi/FundValuationDetail.ashx?callback=&FCODE={0}&deviceid=Wap&plat=Wap&product=EFund&version=2.0.0&Uid=&_=".format(
        code
    );
    var res = commons.httpGet(uri);
    if (!res) {
        commons.toastLog("天天基金估值获取失败");
        return;
    }
    var detail = res.body.json();
    if (detail.ErrCode != 0) {
        commons.toastLog("天天基金估值获取失败");
        commons.toastLog(uri);
        commons.toastLog(detail);
        return;
    }
    var current_price = getCurrentPrice(code);
    var tt_fund_gz = parseFloat(detail.Datas[0].gsz);
    // 实时溢价 = (现价 - 估值) / 估值
    var tt_fund_rt = ((current_price - tt_fund_gz) / tt_fund_gz) * 100;
    return tt_fund_rt;
}
function getTencentRT(code, req) {
    if (config.qdii_types.indexOf(req.qtype) != -1) {
        commons.toastLog("腾讯财经没有QDII估值");
        return;
    }
    var uri = "http://web.ifzq.gtimg.cn/fund/newfund/fundSsgz/getSsgz?app=web&symbol=jj{0}&_var=".format(
        code
    );
    var res = commons.httpGet(uri);
    if (!res) {
        commons.toastLog("腾讯财经估值获取失败");
        return;
    }
    var detail = res.body.json();
    if (detail.code != 0) {
        commons.toastLog("腾讯财经估值获取失败");
        commons.toastLog(uri);
        commons.toastLog(detail);
        return;
    }
    var data = detail.data.data;
    var last_data = data[data.length - 1];
    var tencent_gz = parseFloat(last_data[1]);
    var current_price = getCurrentPrice(code);
    // 实时溢价 = (现价 - 估值) / 估值
    var tencent_rt = ((current_price - tencent_gz) / tencent_gz) * 100;
    return tencent_rt;
}

function checkPOSRT() {
    var msg = "检查持仓溢价";
    commons.toastLog(msg);
    jumpToTrade();
    var pos_ele = text("资金持仓").idEndsWith("tv_menu_name").findOnce();
    pos_ele.parent().click();
    commons.sleep(3);
    var funds_ele = idEndsWith("listview")
        .className("android.widget.ListView")
        .findOnce();
    if (!funds_ele) {
        var msg = "未找到基金持仓";
        commons.toastLog(msg);
    }
    var funds = [];
    for (var i = 0; i < funds_ele.childCount(); i++) {
        var fund_ele = funds_ele.child(i);
        var txt_name_ele = fund_ele.findOne(idEndsWith("txt_name"));
        var txt_code_exchange_ele = fund_ele.findOne(
            idEndsWith("txt_code_exchange")
        );
        var txt_available_count_ele = fund_ele.findOne(
            idEndsWith("txt_available_account")
        );
        var txt_market_value_ele = fund_ele.findOne(
            idEndsWith("txt_market_value")
        );
        var fund = {
            code: txt_code_exchange_ele.text().split(".")[0],
            code_cn: txt_name_ele.text(),
            sell_available: txt_available_count_ele.text(),
            market_value: txt_market_value_ele.text(),
        };
        funds.push(fund);
    }
    back();
    commons.sleep(1);
    for (var i = 0; i < funds.length; i++) {
        var fund = funds[i];
        // commons.toastLog(fund);
        var fund_id = fund.code;
        var aliasFund = config.alias_funds[fund_id];
        var data = {};
        // 处理跨基金
        if (aliasFund) {
            data = getAllRT(aliasFund);
            data.raw_fund_id = fund_id;
        } else {
            data = getAllRT(fund_id);
        }
        if (!data) {
            var msg = "交易额太小,跳过";
            commons.toastLog(msg);
            continue;
        }
        dealWithRT(data, fund);
    }
}

function applyForPurchase(code, money) {
    var msg = "{0},申购 {1} 元".format(code, money);
    commons.toastLog(msg);
    var hasApply = false;
    jumpToTrade();
    click("场内基金");
    commons.sleep(1);
    click("场内申购");
    commons.sleep(3);
    click("输入基金代码");
    commons.sleep(1);
    var search_ele = idEndsWith("s_edittext").findOnce();
    search_ele.setText(code);
    commons.sleep(3);
    search_ele.click();
    commons.sleep(1);
    var retsult_eles = idEndsWith("s_listview").findOnce();
    if (!retsult_eles) {
        commons.toastLog("未找到相关code");
        return hasApply;
    }
    var code_ele = retsult_eles.findOne(textContains(code));
    if (!code_ele) {
        commons.toastLog("未找到相关code");
        return hasApply;
    }
    // commons.toastLog(code_ele);
    var code_x = code_ele.bounds().centerX(),
        code_y = code_ele.bounds().centerY();
    click(code_x, code_y);
    commons.sleep(1);
    var moneyEle = idEndsWith("et_right").findOnce(1);
    moneyEle.setText(money);
    commons.sleep(1);
    var btnOkEle = idEndsWith("btn_ok").findOnce();
    btnOkEle.click();
    commons.sleep(1);
    click("确定申购");
    commons.sleep(7);
    var btnEntrust = idEndsWith("btn_entrust_ok").findOnce();
    if (btnEntrust) {
        hasApply = true;
        btnEntrust.click();
        commons.sleep(1);
    }
    back();
    commons.sleep(1);
    back();
    commons.sleep(1);
    return hasApply;
}

function dealWithRTInternal(data, fund) {
    var is_open_apply = checkIsOpenApply(data.code);
    if (is_open_apply) {
        // 国内LOF溢价,直接卖出
        // 国外QDII溢价,1.根据期货指数,2.当日涨跌幅
        var needSell = false;
        // 判断QDII基金卖出
        if (data.req.qtype == "E") {
            // 纳斯达克期货,道琼斯期货,标普500涨幅
            var allAvePercent = getAveFut();
            // 平均值小于-0.75,晚上有可能跌,卖出
            if (allAvePercent < -0.75) {
                needSell = true;
            } else {
                needSell = false;
            }
        } else {
            needSell = true;
        }
        // 判断是否为持仓
        if (Object.keys(fund).length == 0) {
            needSell = false;
            // 默认申购1000
            fund.market_value = config.market_value;
            fund.sell_available = 0;
        }
        var msg = "{0},卖出:{1},买入:{2}".format(
            data.code,
            fund.sell_available,
            fund.market_value
        );
        var hasApply = applyForPurchase(data.code, fund.market_value);
        // 判断是否申购成功
        if (hasApply) {
            // 更新已申购基金
            var storage_app = commons.storageApp();
            var apply_funds = storage_app.get("apply_funds", []);
            apply_funds.push(data.code);
            storage_app.put("apply_funds", apply_funds);
            // 判断是否需要卖出
            if (needSell) {
                // 是否跨基金,跨基金则卖出相应基金raw_fund_id
                if (data.raw_fund_id) {
                    sell(data.raw_fund_id, fund.sell_available);
                } else {
                    sell(data.code, fund.sell_available);
                }
            }
        }
    } else {
        var msg = "{0},暂停申购".format(data.code);
        commons.toastLog(msg);
    }
}

function dealWithRT(data, fund) {
    var msg = "{0},处理溢价".format(JSON.stringify(data.code));
    commons.toastLog(msg);
    var storage_app = commons.storageApp();
    var apply_funds = storage_app.get("apply_funds", []);
    // 判断是否已申购
    if (apply_funds.indexOf(data.code) != -1) {
        var msg = "{0},今日已申购".format(JSON.stringify(data.code));
        commons.toastLog(msg);
        return;
    }
    // 判断是否为持仓
    // 有底仓情况
    // LOF底仓套利<QDII保守套利(持仓)<QDII风险套利(空仓)<LOF跨底仓套利<QDII跨基金保守套利<QDII跨基金风险套利
    // 0.3 < 0.75 < 1 < 1.25 < 1.5 < 2
    if (Object.keys(fund).length > 0) {
        // 持仓
        if (data.jisilu_rt > 0.2) {
            // 债券基金0.2
            if (config.white_funds.indexOf(data.code) != -1) {
                dealWithRTInternal(data, fund);
                return;
            }
            // 判断是否跨基金
            if (data.raw_fund_id) {
                // 跨基金
                if (config.qdii_types.indexOf(data.req.qtype) != -1) {
                    // QDII基金
                    if (data.jisilu_rt > 1.75) {
                        dealWithRTInternal(data, fund);
                    }
                } else {
                    // LOF
                    if (data.jisilu_rt > 1.25) {
                        dealWithRTInternal(data, fund);
                    }
                }
            } else {
                // 未跨基金
                if (config.qdii_types.indexOf(data.req.qtype) != -1) {
                    // QDII基金
                    if (data.jisilu_rt > 0.75) {
                        dealWithRTInternal(data, fund);
                    }
                } else {
                    // 国内LOF基金>0.3
                    if (data.jisilu_rt > 0.3) {
                        dealWithRTInternal(data, fund);
                    }
                }
            }
        }
    } else {
        // 未持仓,没有底仓,溢价率需高于2.75
        if (config.qdii_types.indexOf(data.req.qtype) != -1) {
            // QDII大于3
            if (data.jisilu_rt > 3) {
                dealWithRTInternal(data, fund);
            }
        } else {
            // LOF大于2.75
            dealWithRTInternal(data, fund);
        }
    }
}

function checkIsOpenApply(code) {
    var msg = "{0},检查是否开放申购".format(code);
    commons.toastLog(msg);
    var uri = "https://fundmobapi.eastmoney.com/FundMApi/FundVarietieValuationDetail.ashx?FCODE={0}&deviceid=2D&plat=Iphone&product=EFund&version=6.2.6&GTOKEN=".format(
        code
    );
    var is_open_apply = false;
    var res = commons.httpGet(uri);
    if (!res) {
        return is_open_apply;
    }
    var detail = res.body.json();
    is_open_apply = detail.Expansion.BUY;
    commons.toastLog(is_open_apply);
    return is_open_apply;
}

function sell(code, available, price) {
    var msg = "{0},卖出:{1},价格:{2}".format(code, available, price);
    commons.toastLog(msg);
    jumpToTrade();
    var search_ele_pre = className("android.widget.ImageView")
        .depth(11)
        .findOnce();
    search_ele_pre.click();
    commons.sleep(1);
    var search_ele = className("android.widget.EditText").depth(5).findOnce();
    search_ele.setText(code);
    commons.sleep(1);
    var retsult_eles = className("android.widget.ListView").depth(5).findOnce();
    if (!retsult_eles) {
        commons.toastLog("未找到相关code");
        return;
    }
    var code_ele = retsult_eles.findOne(textContains(code));
    if (!code_ele) {
        commons.toastLog("未找到相关code");
        return;
    }
    var code_x = code_ele.bounds().centerX(),
        code_y = code_ele.bounds().centerY();
    click(code_x, code_y);
    commons.sleep(1);
    sellInternal(available, price);
    commons.sleep(1);
    back();
}

function sellInternal(available, price) {
    click("交易");
    commons.sleep(1);
    click("普通卖出");
    commons.sleep(5);
    // 限价委托
    // var entrust_change = idEndsWith("tv_entrust").findOnce();
    // entrust_change.click();
    // commons.sleep(1);
    // click("对手方最优");
    // 限价修改
    var price_change_ele = idEndsWith("btn_plus").findOnce(2);
    var price_line_ele = price_change_ele.parent().child(1);
    var current_price = parseFloat(price_line_ele.text());
    commons.sleep(1);
    // 获取当前买入
    var buy_ele = idEndsWith("listview_buy").findOnce();
    var buy_one_ele = buy_ele.child(0);
    var buy_one_price = parseFloat(buy_one_ele.child(1).text());
    // 买盘数量判读
    // var buy_one_num_str = buy_one_ele.child(2).text();
    // var buy_one_num = parseFloat(buy_one_num_str);
    // if (buy_one_num_str.search("万") != -1) {
    //     buy_one_num *= 10000;
    // }
    // 仓位卖出修改
    commons.sleep(1);
    var amount_change_ele = idEndsWith("btn_plus").findOnce(3);
    var amount_line_ele = amount_change_ele.parent().child(1);
    if (current_price - buy_one_price > 0.003) {
        var msg = "当前无买盘";
        commons.toastLog(msg);
        back();
        commons.sleep(1);
        back();
        commons.sleep(1);
        return;
    }
    // 没有设定价格,为买盘价格
    if (!price) {
        price = buy_one_price;
    }
    price_line_ele.setText(price);
    commons.sleep(1);
    amount_line_ele.setText(available);
    click("卖出");
    commons.sleep(1);
    click("确认卖出");
    commons.sleep(1);
    click("我知道了");
    commons.sleep(1);
    back();
}

function autIPO() {
    var msg = "可转债申购";
    commons.toastLog(msg);
    commons.sleep(7);
    jumpToTrade();
    click("新股/新债申购");
    commons.sleep(3);
    var count_ele = textStartsWith("待预约").findOnce();
    var count_text = count_ele.text();
    var count = parseInt(count_text.slice(3, count_text.length - 3));
    if (count > 0) {
        click("一键预约");
        commons.sleep(1);
        click("一键预约");
        commons.sleep(1);
        var dismiss_ele = idEndsWith("dismiss").findOnce();
        dismiss_ele.click();
    }
    var storage_app = commons.storageApp();
    storage_app.put("autoIpo", true);
    back();
    commons.sleep(1);
    back();
    commons.sleep(1);
}

function checkInputPassword() {
    var input_text = "交易密码解锁";
    var need_input_word = textContains(input_text).findOnce();
    var is_input = false;
    if (need_input_word) {
        click(input_text);
        commons.sleep(1);
        inputPassword();
        commons.sleep(1);
        is_input = true;
    }
    return is_input;
}

function inputPassword() {
    var centerX = 535,
        centerY = 1520,
        moveX = 355,
        moveY = 150;

    // click(centerX + moveX + random(1, 10), centerY - moveY + random(1, 10));
    click(centerX - moveX + random(1, 10), centerY - moveY + random(1, 10)); // 1
    commons.sleep(1);
    click(centerX + moveX + random(1, 10), centerY + moveY + random(1, 10)); // 9
    commons.sleep(1);
    click(centerX + random(1, 10), centerY - moveY + random(1, 10)); // 2
    commons.sleep(1);
    click(centerX - moveX + random(1, 10), centerY + moveY + random(1, 10)); // 7
    commons.sleep(1);
    click(360 + random(1, 10), 1860 + random(1, 10)); // 0
    commons.sleep(1);
    click(centerX + moveX + random(1, 10), centerY + random(1, 10)); // 6
    commons.sleep(1);
}

function calHistAveRT(rows) {
    // if (row.length == 0) {
    //     return;
    // }
    var histRTs = [];
    for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        histRT = parseFloat(row.cell.est_error_rt);
        // 取绝对值相对保守
        // histRT = Math.abs(row.cell.est_error_rt);
        histRTs.push(histRT);
        if (i > 21) {
            break;
        }
    }
    // commons.toastLog(histRTs);
    var sum = 0;
    histRTs.map((item) => (sum += item));
    var average_rt = sum / histRTs.length;
    commons.toastLog(average_rt);
    return average_rt;
}

function jumpToTrade() {
    commons.sleep(1);
    var tradeEle = text("交易").findOnce();
    tradeEle.parent().parent().parent().click();
    commons.sleep(1);
    checkInputPassword();
    commons.sleep(1);
}

function getAveFut() {
    // "SImain", "YMmain", "NQmain", "CLmain", "GCmain", "VIXmain", "CNmain", 'ESmain"
    var msg = "获取期货涨幅";
    commons.toastLog(msg);
    var uri = "https://cnappapi.investing.com/get_screen.php";
    var options = {
        contentType: "application/json",
        headers: {
            "User-Agent": config.ua,
            "x-app-ver": 13,
        },
    };
    var args = {
        screen_ID: "29",
        skinID: "1",
        v2: "1",
        lang_ID: "6",
        time_utc_offset: "28800",
    };
    var res = commons.httpGet(uri, args, options);
    var data = {};
    if (!res) {
        return data;
    }
    var detail = res.body.json();
    var items = detail.data[0].screen_data.pairs_data;
    var data = {};
    var allAvePercent = 0;
    for (var i = 0; i < 3; i++) {
        var item = items[i];
        var last = parseFloat(item.last);
        var percent = parseFloat(item.change_percent_val);
        allAvePercent += percent;
        var code = item.pair_name;
        var msg = "{0},现价:{1},涨幅:{2}".format(code, last, percent);
        commons.toastLog(msg);
        data[code] = percent;
    }
    return allAvePercent / 3;
}
