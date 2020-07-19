from datetime import datetime
# from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.tornado import TornadoScheduler
from apscheduler.triggers.cron import CronTrigger

from pytz import utc

import constant

import utils
import models
import remoteclient
import qauto_live

# https://www.cnblogs.com/shhnwangjian/p/7877985.html

# 配置执行器，并设置线程数
job_defaults = {
    'coalesce': utils.true,     # 默认情况下开启新的作业
    'misfire_grace_time': 60,   # 60秒限制
    'max_instances': 3,         # 设置调度程序将同时运行的特定作业的最大实例数3
}

scheduler = TornadoScheduler(
    job_defaults=job_defaults,
    timezone=utc,
)


def auto_ipo():
    broker = 'hb'
    uc = remoteclient.get_remote_client(broker)
    uc.unlock
    utils.time.sleep(10)
    ret = uc.prepare
    print(ret)
    ret = uc.auto_ipo
    print(ret)


def check_rt():
    broker = 'hb'
    uc = remoteclient.get_remote_client(broker)
    uc.unlock
    utils.time.sleep(10)
    ret = uc.prepare
    print(ret)
    extras = dict(
        money=1000,
    )
    ret = uc.trade(extras=extras, action='checkrt')
    print(ret)


def cron_test():
    now = datetime.now()
    print(now)


def keep_server_alive_cron():
    broker = 'hb'
    uc = remoteclient.get_remote_client(broker)
    print(uc)
    uc.unlock
    utils.time.sleep(3)
    uc.check_termux
    utils.time.sleep(60*5)
    uc.lock


def update_k_5min_data_cron():
    # 交易日检查
    now = datetime.now()
    print(now)
    istradeday = utils.is_trade_day(now)
    if not istradeday:
        print('非交易日')
        return

    broker = 'hb'
    uc = remoteclient.get_remote_client(broker)
    print(uc)
    # 交易基金(定投策略),twap策略,cmi策略
    funds = constant.live_trade_funds
    if (11 >= now.hour >= 9) or (15 >= now.hour >= 13):
        if (now.hour == 9) or (now.hour == 11):
            if (now.hour == 9 and now.minute < 30) or (now.hour == 11 and now.minute > 30):
                print('非交易时间')
                return

        ret = uc.unlock
        print(ret)
        funds = constant.live_trade_funds
        db = models.DB()
        dbname = 'k_5min_data'
        utils.asyncio_tasks(
            qauto_live.async_run_strategy,
            tasks=funds,
            db=db,
            dbname=dbname
        )
    else:
        print('非交易时间')
        uc.lock


def update_k_data_cron():
    now = datetime.now()
    print(now)
    istradeday = utils.is_trade_day(now)
    if not istradeday:
        print('非交易日')
        return
    funds = constant.live_trade_funds
    db = models.DB()
    dbname = 'k_data'
    live = utils.true
    utils.asyncio_tasks(
        qauto_live.async_update_live_k_data,
        tasks=funds,
        db=db,
        dbname=dbname,
        live=live,
    )


def update_index_daily_cron():
    istradeday = utils.is_trade_day()
    if not istradeday:
        print('非交易日')
        return
    utils.update_index_daily()


def start():
    # 更新分钟数据,策略下单使用
    # trigger = CronTrigger(second='*/1')
    # scheduler.add_job(cron_test, trigger=trigger)

    # 自动打新,检查溢价
    trigger = CronTrigger(hour=14, minute=45)
    scheduler.add_job(check_rt, trigger=trigger)
    trigger = CronTrigger(hour=9, minute=25)
    scheduler.add_job(auto_ipo, trigger=trigger)

    trigger = CronTrigger(
        hour='9,10,11,13,14', minute='0,5,10,15,20,25,30,35,40,45,50,55', second='30')
    scheduler.add_job(update_k_5min_data_cron,
                      trigger=trigger, max_instances=1)

    trigger = CronTrigger(
        hour='0,1,2,3,4,5,6,7,8,15,16,17,18,19,20,21,22,23', minute='0', second='30')
    scheduler.add_job(update_k_5min_data_cron,
                      trigger=trigger, max_instances=1)

    trigger = CronTrigger(day_of_week='1,2,3,4,5', hour=21, minute=10)
    # trigger = CronTrigger(trigger)
    scheduler.add_job(update_k_data_cron, trigger=trigger)
    scheduler.start()
    scheduler.print_jobs()

    # 更新指数数据,PE,PB
    # scheduler.add_job(update_index_daily_cron)
    # 更新每日k线数据
    # scheduler.add_job(update_k_data_cron, id='update_k_data_id')
    # scheduler.remove_job('update_k_data_id')


if __name__ == "__main__":
    print('start...')
    start()
    # update_k_data_cron()
    print('end...')
