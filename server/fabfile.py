from fabric.api import local, run, cd, env
import time

from utils import basedir

env.hosts = ['192.168.1.9:8022']


def commit():
    local("git add --all && git commit -m 'u'")


def push():
    local("git push")


def prepare():
    commit()
    push()


def deploy():
    prepare()
    with cd(basedir):
        run('git checkout .')
        run('git pull')
        run('pkill python')
        time.sleep(3)
        run('/data/data/com.termux/files/usr/bin/sh /data/data/com.termux/files/home/utils/monitor_api.sh')
        time.sleep(3)
        run('/data/data/com.termux/files/usr/bin/sh /data/data/com.termux/files/home/utils/monitor_api.sh')
