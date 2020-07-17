var common = require("./common");

var pre_path = "/sdcard/JSBOX";

// termux + jsbox
// docker: https://stageguard.top/2019/08/15/run-docker-on-qemu-alpine/#1-Docker
// postgres:
// pg_ctl -D $PREFIX/var/lib/postgresql start
// pg_ctl -D $PREFIX/var/lib/postgresql stop
// psql postgres
// ssh: https://wiki.termux.com/wiki/Remote_Access
// https://man.linuxde.net/sshd

main();

function main() {
    start();
}

function start() {
    var engine = engines.myEngine();
    common.toastLog(engine);

    common.checkAutoService();
    // var net_status = common.netStatus();
    // if (net_status == "网络断开") {
    //     common.toastLog(net_status);
    //     return;
    // }
    common.sleep(3)
    extras = common.engineArgsGet();
    if (!extras) {
        common.toastLog("获取参数错误");
    }
    common.toastLog(JSON.stringify(extras));
    if (extras.broker == "ht") {
        data = "{0}/ht.js".format(pre_path);
        common.RunIntentActivity(data, extras);
    } else if (extras.broker == "hb") {
        file = "{0}/hb.js".format(pre_path);
        common.RunIntentActivity(file, extras);
    } else if (extras.broker == "hte") {
        file = "{0}/hte.js".format(pre_path);
        common.RunIntentActivity(file, extras);
    }
}
