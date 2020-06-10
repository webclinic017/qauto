// var htmlparser = require("htmlparser.js");
var commons = require("common.js");

var config = {
    package_name: "com.hwabao.hbstockwarning",
};

var current_activity = currentActivity();
if (current_activity.indexOf(config.package_name) != -1) {
    commons.toastLog(current_activity);
}
