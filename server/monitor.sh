#!/bin/sh
pre='/data/data/com.termux/files/usr/bin/'
cmd=$pre$1
echo $cmd
ps -fe|grep $cmd |grep -v grep
if [ $? -ne 0 ]
then
    echo "start process....."
    $cmd
else
    echo "runing....."
fi