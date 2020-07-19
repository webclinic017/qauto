#!/bin/sh
ps -fe|grep sshd |grep -v grep
if [ $? -ne 0 ]
then
    echo "start process....."
    sv up sshd
else
    echo "runing....."
fi
