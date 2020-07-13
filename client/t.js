var common = require("./common");
const { boundsRandomClick } = require("./common");
// common.common.toastLog(engines.myEngine());

// var args = common.engineArgsGet();
// common.common.toastLog(args)

// let intent = engines.myEngine().execArgv.intent
// extras = intent.extras
// log("extras = ", intent.extras);
// if (extras) {
//     let iter = extras.keySet().iterator();
//     extrasdict = {}
//     while (iter.hasNext()) {
//         let key = iter.next();
//         let value = extras.get(key);
//         extrasdict[key] = value
//     }
//     common.toastLog(extrasdict)
// }
// am start -n org.my.jsbox/org.my.jsbox.external.open.RunIntentActivity -d /sdcard/JSBOX/t.js -e type application/x-javascript

// var storage_app = common.storageApp();
// storage_app.clear();


extras = common.engineArgsGet();
common.toastLog(extras)