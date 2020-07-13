var flow = require("./flow");

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

flow.init({
    app_name: "华宝智投",
    package_name: "com.hwabao.hbstockwarning",
    config: config,
});

flow.run({
    checkPOSRT: function (fun) {
        var msg = "检查持仓溢价";
        flow.common.toastLog(msg);
        var item = fun.getItem();
        flow.jumpToTrade(fun, item);
        var pass_ele = fun.getPassItem();
        flow.checkInputPassword(fun, pass_ele);
        var pos_ele = text("资金持仓").idEndsWith("tv_menu_name").findOnce();
        pos_ele.parent().click();
        flow.common.sleep(3);
        var funds_ele = idEndsWith("listview")
            .className("android.widget.ListView")
            .findOnce();
        if (!funds_ele) {
            var msg = "未找到基金持仓";
            flow.common.toastLog(msg);
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
        flow.common.sleep(1);
        for (var i = 0; i < funds.length; i++) {
            var fund = funds[i];
            var fund_id = fund.code;
            var alias_fund = flow.init_param.config.alias_funds[fund_id];
            var data = {};
            // 处理跨基金
            if (alias_fund) {
                data = fun.getAllRT(fun, alias_fund);
                data.raw_fund_id = fund_id;
            } else {
                data = fun.getAllRT(fun, fund_id);
            }
            if (!data) {
                var msg = "交易额太小,跳过";
                flow.common.toastLog(msg);
                continue;
            }
            fun.dealWithRT(fun, data, fund);
        }
    },
    getLOFFunds: function (fun) {
        var msg = "检查集思录LOF";
        flow.common.toastLog(msg);
        var args = {
            ___jsl: 0,
            rp: 300,
            page: 1,
        };
        var storage_rt = flow.common.storageRT();
        var funds = storage_rt.get("funds", []);
        flow.common.toastLog(funds.length);
        for (var i = 0; i < funds.length; i++) {
            var fund_ele = funds[i];
            var uri = fund_ele.uri;
            flow.common.toastLog(uri);
            var res = flow.common.httpGet(uri, args);
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
                    flow.common.toastLog(msg);
                    continue;
                }
                // 溢价率大于2.75,成交额大于5w
                if (discount_rt >= 2.75 && volume > 5) {
                    var code = row.cell.fund_id;
                    var data = fun.getAllRT(fun, code);
                    if (!data) {
                        var msg = "交易额太小,跳过";
                        flow.common.toastLog(msg);
                        return;
                    }
                    fun.dealWithRT(fun, data, {});
                }
            }
        }
    },
    dealWithRT: function (fun, data, fund) {
        var msg = "{0},处理溢价".format(JSON.stringify(data.code));
        flow.common.toastLog(msg);
        var storage_rt = flow.common.storageRT();
        var apply_funds = storage_rt.get("apply_funds", []);
        // 判断是否已申购
        if (apply_funds.indexOf(data.code) != -1) {
            var msg = "{0},今日已申购".format(JSON.stringify(data.code));
            flow.common.toastLog(msg);
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
                if (
                    flow.init_param.config.white_funds.indexOf(data.code) != -1
                ) {
                    fun.dealWithRTInternal(fun, data, fund);
                    return;
                }
                // 判断是否跨基金
                if (data.raw_fund_id) {
                    // 跨基金
                    if (
                        flow.init_param.config.qdii_types.indexOf(
                            data.req.qtype
                        ) != -1
                    ) {
                        // QDII基金
                        if (data.jisilu_rt > 1.75) {
                            fun.dealWithRTInternal(fun.data, fund);
                        }
                    } else {
                        // LOF
                        if (data.jisilu_rt > 1.25) {
                            fun.dealWithRTInternal(fun, data, fund);
                        }
                    }
                } else {
                    // 未跨基金
                    if (
                        flow.init_param.config.qdii_types.indexOf(
                            data.req.qtype
                        ) != -1
                    ) {
                        // QDII基金
                        if (data.jisilu_rt > 0.75) {
                            fun.dealWithRTInternal(fun, data, fund);
                        }
                    } else {
                        // 国内LOF基金>0.3
                        if (data.jisilu_rt > 0.3) {
                            fun.dealWithRTInternal(fun, data, fund);
                        }
                    }
                }
            }
        } else {
            // 未持仓,没有底仓,溢价率需高于2.75
            if (
                flow.init_param.config.qdii_types.indexOf(data.req.qtype) != -1
            ) {
                // QDII大于3
                if (data.jisilu_rt > 3) {
                    fun.dealWithRTInternal(fun, data, fund);
                }
            } else {
                // LOF大于2.75
                fun.dealWithRTInternal(fun, data, fund);
            }
        }
    },
    dealWithRTInternal: function (fun, data, fund) {
        var is_open_apply = fun.checkIsOpenApply(data.code);
        if (is_open_apply) {
            // 国内LOF溢价,直接卖出
            // 国外QDII溢价,1.根据期货指数,2.当日涨跌幅
            var need_sell = false;
            // 判断QDII基金卖出
            if (data.req.qtype == "E") {
                // 纳斯达克期货,道琼斯期货,标普500涨幅
                var allAvePercent = fun.getAveFut();
                // 平均值小于-0.75,晚上有可能跌,卖出
                if (allAvePercent < -0.75) {
                    need_sell = true;
                } else {
                    need_sell = false;
                }
            } else {
                need_sell = true;
            }
            // 判断是否为持仓
            if (Object.keys(fund).length == 0) {
                need_sell = false;
                // 默认申购1000
                fund.market_value = flow.init_param.config.market_value;
                fund.sell_available = 0;
            }
            var msg = "{0},卖出:{1},买入:{2}".format(
                data.code,
                fund.sell_available,
                fund.market_value
            );
            data.money = fund.market_value;
            var has_apply = fun.apply(fun, data);
            // 判断是否申购成功
            if (has_apply) {
                // 更新已申购基金
                var storage_rt = flow.common.storageRT();
                var apply_funds = storage_rt.get("apply_funds", []);
                apply_funds.push(data.code);
                storage_rt.put("apply_funds", apply_funds);
                // 判断是否需要卖出
                if (need_sell) {
                    // 是否跨基金,跨基金则卖出相应基金raw_fund_id
                    data.size = fund.sell_available;
                    if (data.raw_fund_id) {
                        data.code = data.raw_fund_id;
                        fun.sell(fun, data);
                    } else {
                        fun.sell(fun, data);
                    }
                }
            }
        } else {
            var msg = "{0},暂停申购".format(data.code);
            flow.common.toastLog(msg);
        }
    },
    checkIsOpenApply: function (code) {
        var msg = "{0},检查是否开放申购".format(code);
        flow.common.toastLog(msg);
        var uri = "https://fundmobapi.eastmoney.com/FundMApi/FundVarietieValuationDetail.ashx?FCODE={0}&deviceid=2D&plat=Iphone&product=EFund&version=6.2.6&GTOKEN=".format(
            code
        );
        var is_open_apply = false;
        var res = flow.common.httpGet(uri);
        if (!res) {
            return is_open_apply;
        }
        var detail = res.body.json();
        is_open_apply = detail.Expansion.BUY;
        flow.common.toastLog(is_open_apply);
        return is_open_apply;
    },
    getAveFut: function () {
        // "SImain", "YMmain", "NQmain", "CLmain", "GCmain", "VIXmain", "CNmain", 'ESmain"
        var msg = "获取期货涨幅";
        flow.common.toastLog(msg);
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
        var res = flow.common.httpGet(uri, args, options);
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
            flow.common.toastLog(msg);
            data[code] = percent;
        }
        return allAvePercent / 3;
    },
    getAllRT: function (fun, code) {
        var msg = "{0},获取所有溢价率".format(code);
        flow.common.toastLog(msg);
        var ave_volume = fun.getAveVolume(code);
        if (ave_volume < 50) {
            // 平均成交量小于50w
            var msg = "{0},本月平均成交额:{1}".format(code, ave_volume);
            flow.common.toastLog(msg);
            return;
        }
        var req = fun.getReq(code);
        var jisilu_rt = 0,
            tt_fund_rt = 0,
            tencent_rt = 0;
        if (Object.keys(req).length != 0) {
            jisilu_rt = fun.getJiSiLuRT(fun, code, req);
        } else {
            flow.common.toastLog("集思录未收录");
        }
        // flow.common.toastLog(req);
        var tt_fund_rt = fun.getTTFundRT(fun, code);
        var tencent_rt = fun.getTencentRT(fun, code, req);
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
        flow.common.toastLog(msg);
        return rts;
    },
    getReq: function (code) {
        var storage_rt = flow.common.storageRT();
        var funds = storage_rt.get("funds", []);
        var req = {};
        for (var i = 0; i < funds.length; i++) {
            var fund_ele = funds[i];
            var sub_funds = fund_ele.funds;
            for (var j = 0; j < sub_funds.length; j++) {
                var fund_id = sub_funds[j];
                if (fund_id == code) {
                    req = fund_ele;
                    return req;
                }
            }
        }
        return req;
    },
    getAveVolume: function (code) {
        var msg = "{0},获取平均交易额".format(code);
        flow.common.toastLog(msg);
        var uri = "http://127.0.0.1:9000/get_volume";
        var args = {
            code: code,
        };
        var res = flow.common.httpGet(uri, args);
        if (!res) {
            return;
        }
        var detail = res.body.json();
        var volume = detail.volume;
        return parseFloat(volume / 10000);
    },
    getJiSiLuRT: function (fun, code, req) {
        var uri = req.detail_uri;
        var hist_uri = req.hist_uri;
        var data = {
            is_search: 1,
            fund_id: code,
            fund_type: req.qtype.split("_")[0],
            rp: 5,
            page: 1,
        };
        if (flow.init_param.config.qdii_types.indexOf(req.qtype) != -1) {
            uri = uri + code;
            var res = flow.common.httpGet(uri);
            if (!res) {
                flow.common.toastLog("集思录溢价获取失败");
                return;
            }
            var detail = res.body.json();
            if (detail.isError != 0) {
                flow.common.toastLog("集思录估值获取失败");
                flow.common.toastLog(uri);
                flow.common.toastLog(detail);
                return;
            }
            var jisilu_rt = parseFloat(detail.data.discount_rt);
            // flow.common.toastLog(detail.data);
            if (detail.data.apply_fee == "暂停") {
                var msg = "{0} : {1} : {2}: 溢价: {3} 暂停申购".format(
                    detail.data.fund_id,
                    detail.data.fund_nm,
                    detail.data.issuer_nm,
                    jisilu_rt
                );
                flow.common.toastLog(msg);
                return;
            }
            var res = flow.common.httpPost(hist_uri, data);
            var detail = res.body.json();
            var rows = detail.rows;
            var average_rt = fun.calHistAveRT(rows);
            return jisilu_rt - average_rt;
        } else {
            var res = flow.common.httpPost(uri, data);
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
                flow.common.toastLog(msg);
                return;
            }
            var rp = 22;
            var args = {
                ___jsl: 0,
                rp: rp,
                page: 1,
            };
            hist_uri = hist_uri.format(code);
            var res = flow.common.httpGet(hist_uri, args);
            var detail = res.body.json();
            var rows = detail.rows;
            var average_rt = fun.calHistAveRT(rows);
            return jisilu_rt - average_rt;
        }
    },
    getTTFundRT: function (fun, code) {
        var uri = "https://fundmobapi.eastmoney.com/FundMApi/FundValuationDetail.ashx?callback=&FCODE={0}&deviceid=Wap&plat=Wap&product=EFund&version=2.0.0&Uid=&_=".format(
            code
        );
        var res = flow.common.httpGet(uri);
        if (!res) {
            flow.common.toastLog("天天基金估值获取失败");
            return;
        }
        var detail = res.body.json();
        if (detail.ErrCode != 0) {
            flow.common.toastLog("天天基金估值获取失败");
            flow.common.toastLog(uri);
            flow.common.toastLog(detail);
            return;
        }
        var current_price = fun.getCurrentPrice(code);
        var tt_fund_gz = parseFloat(detail.Datas[0].gsz);
        // 实时溢价 = (现价 - 估值) / 估值
        var tt_fund_rt = ((current_price - tt_fund_gz) / tt_fund_gz) * 100;
        return tt_fund_rt;
    },
    getTencentRT: function (fun, code, req) {
        if (flow.init_param.config.qdii_types.indexOf(req.qtype) != -1) {
            flow.common.toastLog("腾讯财经没有QDII估值");
            return;
        }
        var uri = "http://web.ifzq.gtimg.cn/fund/newfund/fundSsgz/getSsgz?app=web&symbol=jj{0}&_var=".format(
            code
        );
        var res = flow.common.httpGet(uri);
        if (!res) {
            flow.common.toastLog("腾讯财经估值获取失败");
            return;
        }
        var detail = res.body.json();
        if (detail.code != 0) {
            flow.common.toastLog("腾讯财经估值获取失败");
            flow.common.toastLog(uri);
            flow.common.toastLog(detail);
            return;
        }
        var data = detail.data.data;
        var last_data = data[data.length - 1];
        var tencent_gz = parseFloat(last_data[1]);
        var current_price = fun.getCurrentPrice(code);
        // 实时溢价 = (现价 - 估值) / 估值
        var tencent_rt = ((current_price - tencent_gz) / tencent_gz) * 100;
        return tencent_rt;
    },
    calHistAveRT: function (rows) {
        var hist_rts = [];
        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];
            histRT = parseFloat(row.cell.est_error_rt);
            // 取绝对值相对保守
            // histRT = Math.abs(row.cell.est_error_rt);
            hist_rts.push(histRT);
            if (i > 21) {
                break;
            }
        }
        // flow.common.toastLog(hist_rts);
        var sum = 0;
        hist_rts.map((item) => (sum += item));
        var average_rt = sum / hist_rts.length;
        flow.common.toastLog(average_rt);
        return average_rt;
    },
    getCurrentPrice: function (code) {
        var symbol = flow.common.getSymbol(code);
        var uri = "http://data.gtimg.cn/flashdata/hushen/minute/{0}{1}.js".format(
            symbol,
            code
        );
        var res = flow.common.httpGet(uri);
        if (!res) {
            var msg = "{0} : 腾讯价格获取失败".format(code);
            flow.common.toastLog(msg);
            return;
        }
        var flash_price_str = res.body.string();
        var flash_price_arr = flash_price_str.split("\n");
        var current_price_str = flash_price_arr[flash_price_arr.length - 2];
        var current_price_arr = current_price_str.split(" ");
        var current_price = current_price_arr[1];
        // flow.common.toastLog(current_price);
        return current_price;
    },

    initJiSiLuFunds: function () {
        var msg = "集思录初始化";
        flow.common.toastLog(msg);
        var app_name = "jisilu";
        var storage_rt = flow.common.storageRT();
        var date_key = "{0}:{1}".format(app_name, "date");
        var date = flow.common.date();
        var last_date = storage_rt.get(date_key, "");
        if (date == last_date) {
            flow.common.toastLog("今日已经初始化");
            return;
        }
        storage_rt.clear();
        flow.common.toastLog(date);
        flow.common.toastLog(last_date);
        var args = {
            ___jsl: 0,
            rp: 300,
            page: 1,
        };
        var funds = [];
        var code_types = ["E", "C", "A"];
        for (var i = 0; i < code_types.length; i++) {
            var code_type = code_types[i];
            flow.common.toastLog(code_type);
            var uri = "https://www.jisilu.cn/data/qdii/qdii_list/" + code_type;
            flow.common.toastLog(uri);
            var res = flow.common.httpGet(uri, args);
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
            flow.common.toastLog(code_type);
            var uri = "https://www.jisilu.cn/data/lof/" + code_type + "/";
            flow.common.toastLog(uri);
            var res = flow.common.httpGet(uri, args);
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
        storage_rt.put(date_key, date);
        storage_rt.put("funds", funds);
        storage_rt.put("apply_funds", []);
    },

    inputPassword: function () {
        var centerX = 535,
            centerY = 1520,
            moveX = 355,
            moveY = 150;

        // click(centerX + moveX + random(1, 10), centerY - moveY + random(1, 10));
        click(centerX - moveX + random(1, 10), centerY - moveY + random(1, 10)); // 1
        flow.common.sleep(1);
        click(centerX + moveX + random(1, 10), centerY + moveY + random(1, 10)); // 9
        flow.common.sleep(1);
        click(centerX + random(1, 10), centerY - moveY + random(1, 10)); // 2
        flow.common.sleep(1);
        click(centerX - moveX + random(1, 10), centerY + moveY + random(1, 10)); // 7
        flow.common.sleep(1);
        click(360 + random(1, 10), 1860 + random(1, 10)); // 0
        flow.common.sleep(1);
        click(centerX + moveX + random(1, 10), centerY + random(1, 10)); // 6
        flow.common.sleep(1);
    },
    getPassItem: function () {
        var input_text = "交易密码解锁";
        var pass_item = textContains(input_text).findOnce();
        return pass_item;
    },
    getItem: function () {
        var trade_ele = text("交易").findOnce();
        item = trade_ele.parent().parent().parent();
        return item;
    },
    autoIpo: function (fun, user_no) {
        var msg = "可转债申购";
        flow.common.toastLog(msg);
        flow.common.sleep(7);
        var item = fun.getItem();
        flow.jumpToTrade(fun, item);
        click("新股/新债申购");
        flow.common.sleep(3);
        var count_ele = textStartsWith("待预约").findOnce();
        var count_text = count_ele.text();
        var count = parseInt(count_text.slice(3, count_text.length - 3));
        var num = 0;
        if (count > 0) {
            click("一键预约");
            flow.common.sleep(1);
            var num_ele = idEndsWith("tv_quick_numtitle").findOnce();
            var num_str = num_ele.text().replace(/[^0-9]/gi, "");
            num = parseInt(num_str);
            click("一键预约");
            flow.common.sleep(3);
            var dismiss_ele = idEndsWith("dismiss").findOnce();
            if (dismiss_ele) {
                dismiss_ele.click();
            }
        }
        var storage_rt = flow.common.storageRT();
        var date = flow.common.date();
        storage_rt.put("{0}:{1}".format(user_no, date), true);
        back();
        flow.common.sleep(1);
        back();
        flow.common.sleep(1);
        return num;
    },
    apply: function (fun, data) {
        var msg = "{0},申购 {1} 元".format(data.code, data.money);
        flow.common.toastLog(msg);
        var has_apply = false;
        var item = fun.getItem();
        flow.jumpToTrade(fun, item);
        click("场内基金");
        flow.common.sleep(1);
        click("场内申购");
        flow.common.sleep(3);
        click("输入基金代码");
        flow.common.sleep(1);
        var search_ele = idEndsWith("s_edittext").findOnce();
        search_ele.setText(data.code);
        flow.common.sleep(3);
        search_ele.click();
        flow.common.sleep(1);
        var result_eles = idEndsWith("s_listview").findOnce();
        if (!result_eles) {
            flow.common.toastLog("未找到相关code");
            return has_apply;
        }
        var code_ele = result_eles.findOne(textContains(data.code));
        if (!code_ele) {
            flow.common.toastLog("未找到相关code");
            return has_apply;
        }
        var code_x = code_ele.bounds().centerX(),
            code_y = code_ele.bounds().centerY();
        click(code_x, code_y);
        flow.common.sleep(1);
        var money_ele = idEndsWith("et_right").findOnce(1);
        money_ele.setText(data.money);
        flow.common.sleep(1);
        var btn_ele = idEndsWith("btn_ok").findOnce();
        btn_ele.click();
        flow.common.sleep(1);
        click("确定申购");
        flow.common.sleep(7);
        var entrust_ele = idEndsWith("btn_entrust_ok").findOnce();
        if (entrust_ele) {
            has_apply = true;
            entrust_ele.click();
            flow.common.sleep(1);
        }
        back();
        flow.common.sleep(1);
        back();
        flow.common.sleep(1);
        return has_apply;
    },
    sell: function (fun, data) {
        var msg = "{0},卖出:{1},价格:{2}".format(
            data.code,
            data.size,
            data.price
        );
        flow.common.toastLog(msg);
        var item = fun.getItem();
        flow.jumpToTrade(fun, item);
        var search_ele_pre = className("android.widget.ImageView")
            .depth(11)
            .findOnce();
        search_ele_pre.click();
        flow.common.sleep(1);
        var search_ele = className("android.widget.EditText")
            .depth(5)
            .findOnce();
        search_ele.setText(data.code);
        flow.common.sleep(1);
        var retsult_eles = className("android.widget.ListView")
            .depth(5)
            .findOnce();
        if (!retsult_eles) {
            flow.common.toastLog("未找到相关code");
            return;
        }
        var code_ele = retsult_eles.findOne(textContains(data.code));
        if (!code_ele) {
            flow.common.toastLog("未找到相关code");
            return;
        }
        var code_x = code_ele.bounds().centerX(),
            code_y = code_ele.bounds().centerY();
        click(code_x, code_y);
        flow.common.sleep(1);
        fun.sellInternal(fun, data);
        flow.common.sleep(1);
        back();
    },
    sellInternal: function (fun, data) {
        click("交易");
        flow.common.sleep(1);
        click("普通卖出");
        flow.common.sleep(5);
        // 限价修改
        var price_change_ele = idEndsWith("btn_plus").findOnce(2);
        var price_line_ele = price_change_ele.parent().child(1);
        var current_price = parseFloat(price_line_ele.text());
        flow.common.sleep(1);
        // 获取当前买入
        var buy_ele = idEndsWith("listview_buy").findOnce();
        var buy_one_ele = buy_ele.child(0);
        var buy_one_price = parseFloat(buy_one_ele.child(1).text());
        // 仓位卖出修改
        flow.common.sleep(1);
        var amount_change_ele = idEndsWith("btn_plus").findOnce(3);
        var amount_line_ele = amount_change_ele.parent().child(1);
        if (current_price - buy_one_price > 0.003) {
            var msg = "当前无买盘";
            flow.common.toastLog(msg);
            back();
            flow.common.sleep(1);
            back();
            flow.common.sleep(1);
            return;
        }
        // 没有设定价格,为买盘价格
        if (!data.price) {
            price = buy_one_price;
        } else {
            price = data.price;
        }
        price_line_ele.setText(price);
        flow.common.sleep(1);
        amount_line_ele.setText(data.size);
        click("卖出");
        flow.common.sleep(1);
        click("确认卖出");
        flow.common.sleep(1);
        click("我知道了");
        flow.common.sleep(1);
        back();
    },
});
