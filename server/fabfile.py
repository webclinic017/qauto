from fabric.api import local, run, cd, env

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
    with cd(basedir):
        run('git pull')
        run('pkill python')
        run('sh /data/data/com.termux/files/home/utils/monitor_api.sh')
