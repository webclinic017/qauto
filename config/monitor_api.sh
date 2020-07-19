#!/bin/sh
cmd='/data/data/com.termux/files/usr/bin/python'
echo $cmd
ps -fe|grep $cmd |grep -v grep
if [ $? -ne 0 ]
then
    echo "start process....."
    nohup /data/data/com.termux/files/usr/bin/python /data/data/com.termux/files/home/qauto/server/wsgi.py >> /data/data/com.termux/files/home/qauto/server/log/app.log &
else
    echo "runing....."
fi