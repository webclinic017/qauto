var commons = require("common.js");

main();

function main() {
    commons.toastLog(111);
    var isLock = commons.unLock();
    // var isLock = true;
    while (isLock) {
        isLock = commons.unLock();
        commons.toastLog("休眠30s");
        commons.sleep(30);
    }
}
