from fabric.api import local, run, cd, env

from utils import basedir

env.hosts = ['192.168.1.9:8022']


def commit():
    ret = local("git add --all && git commit -m 'u'")
    import ipdb; ipdb.set_trace()


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
        run('sh /data/data/com.termux/files/home/utils/monitor_api.sh')
