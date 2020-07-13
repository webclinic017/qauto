from datetime import datetime
# from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from pytz import utc

import constant

import utils
import models
import qauto_live

# 配置执行器，并设置线程数
executors = {
    'default': ThreadPoolExecutor(20),
    'processpool': ProcessPoolExecutor(5)
}
job_defaults = {
    'coalesce': False,     # 默认情况下关闭新的作业
    'max_instances': 3     # 设置调度程序将同时运行的特定作业的最大实例数3
}

scheduler = BlockingScheduler(
    executors=executors,
    job_defaults=job_defaults,
    timezone=utc,
    # misfire_grace_time=600,
)


@scheduler.scheduled_job('interval', minutes=2)
def update_k_5min_data_cron():
    # 交易日检查
    now = datetime.now()
    istradeday = utils.is_trade_day(now)
    if not istradeday:
        print('非交易日')
        return

    # 交易基金(定投策略),twap策略,cmi策略
    funds = constant.live_trade_funds
    if (11 >= now.hour >= 9) or (15 >= now.hour >= 13):
        if (now.hour == 9) or (now.hour == 11):
            if (now.hour == 9 and now.minute < 30) or (now.hour == 11 and now.minute > 30):
                print('非交易时间')
                return

        funds = constant.live_trade_funds
        db = models.DB()
        dbname = 'k_5min_data'
        utils.async_tasks(
            qauto_live.async_run_strategy,
            tasks=funds,
            db=db,
            dbname=dbname
        )
    else:
        print('非交易时间')


@scheduler.scheduled_job('cron', hour='21')
def update_k_data_cron():
    now = datetime.now()
    istradeday = utils.is_trade_day(now)
    if not istradeday:
        print('非交易日')
        return
    funds = constant.live_trade_funds
    db = models.DB()
    dbname = 'k_data'
    codes = [x['code'] for x in funds]
    utils.async_tasks(
        utils.update_k_data,
        tasks=codes,
        db=db,
        dbname=dbname,
    )

@scheduler.scheduled_job('cron', hour='22')
def update_index_daily_cron():
    istradeday = utils.is_trade_day()
    if not istradeday:
        print('非交易日')
        return
    utils.update_index_daily()


# scheduler.add_job(update_k_5min_data_cron, 'interval', minutes=1)
# 更新分钟数据,策略下单使用
scheduler.add_job(update_k_5min_data_cron,
                  max_instances=1, misfire_grace_time=300)
# 更新指数数据,PE,PB
# scheduler.add_job(update_index_daily_cron)
# 更新每日k线数据
# scheduler.add_job(update_k_data_cron, id='update_k_data_id')
# scheduler.remove_job('update_k_data_id')

print('start...')
scheduler.start()
print('end...')
