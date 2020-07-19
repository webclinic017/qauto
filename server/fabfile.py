from fabric.api import local, run, cd, env

from utils import basedir

env.hosts = ['192.168.1.2:8022']
# env.hosts = ['172.20.10.14:8022']


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
        run('/data/data/com.termux/files/usr/bin/sh /data/data/com.termux/files/home/qauto/config/monitor_api.sh')
