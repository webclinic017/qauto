var common = require("./common");

function main() {
    // setInterval(function () {
    //     checkTermux();
    // }, 1000 * 1);
    checkTermux();
}

function checkTermux(retry) {
    var uri = "http://127.0.0.1:9000/ping";
    if (!retry) {
        retry = 0;
    }
    common.toastLog("检查 termux, retry {0}".format(retry));
    if (retry > 2) {
        // 检查3次后,重启termux
        restartTermux();
    }
    try {
        var ret = common.httpGet(uri);
        if (ret && ret.statusMessage == "OK") {
            var data = ret.body.json();
            if (data.code == 0) {
                common.toastLog("termux and python server正常...");
                return;
            }
        }
        retry += 1;
        common.sleep(3 * retry);
        checkTermux(retry);
    } catch (err) {
        retry += 1;
        common.sleep(5 * retry);
        checkTermux(retry);
    }
}

function restartTermux() {
    var package_name = "com.termux";
    cmd = "su -c am force-stop {0}".format(package_name);
    var ret = shell(cmd, true);
    print(ret);
    common.sleep(3);
    common.launch(package_name);
}

main();
