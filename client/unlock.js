var common = require("./common");

main();

function main() {
    common.toastLog("正在解锁");
    var isLock = common.unLock();
    // var isLock = true;
    while (isLock) {
        isLock = common.unLock();
        common.toastLog("休眠30s");
        common.sleep(30);
    }
}
