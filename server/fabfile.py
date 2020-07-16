from fabric.api import local


def commit():
    local("git add --all && git commit -m 'u'")


def push():
    local("git push")


def prepare():
    commit()
    push()
