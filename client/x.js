var common = require("./common");

extras = {
    flag: "buy",
    size: 400,
    code: "159928",
};

intent = {
    packageName: "org.my.jsbox",
    className: "org.my.jsbox.external.open.RunIntentActivity",
    data: "/sdcard/JSBOX/t.js",
    type: "application/x-javascript",
    extras: extras,
};
cmd = "am start " + app.intentToShell(intent);

common.toastLog(cmd);

// app.startActivity(intent);

// magisk su
// subprocess.getstatusoutput(path)
// su -c am start  -n 'org.my.jsbox/org.my.jsbox.external.open.RunIntentActivity' -e 'flag' 'buy' -e 'size' 400 -e 'code' '159928' -t application/x-javascript -d /sdcard/JSBOX/t.js
// su -c am start -n com.android.camera/.Camera

// ret = shell(cmd, true)
// toastLog(ret)
// common.lock()
common.unLock();
