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


# apt update && apt upgrade
# apt install python python-dev pip clang
# pip install --upgrade pip
# pip install conda
# ## All the following packages are needed by conda
# pip install auxlib ruamel.yaml requests

# ## Install pycosat (this can be ignored if https://github.com/ContinuumIO/pycosat/pull/29 is fixed)
# wget https://pypi.python.org/packages/76/0f/16edae7bc75b79376f2c260b7a459829785f08e463ecf74a8ccdef62dd4a/pycosat-0.6.1.tar.gz#md5=c1fc35b17865f5f992595ae0362f9f9f
# tar -xf pycosat-0.6.1.tar.gz
# # Edit pycosat-0.6.1/picosat.c
# # Change "#include <sys/unistd.h>" to "#include <unistd.h>"
# tar -czvf pycosat-0.6.1.tar.gz tar -xf pycosat-0.6.1.tar.gz
# pip install --no-index --find-links file://path/to/tar -xf pycosat-0.6.1.tar.gz

# # Edit conda/utils.py:80, return None form "gnu_get_libc_version()"

# # Fix os.link problem (like https://github.com/termux/termux-packages/issues/29)
# # Change conda/install.py:162, substitute: os.link(src, dst) with shutil.copy(src, dst)
# # or pass option "--copy" in order to avoid the usage of os.link


# # Install numpy
# LDFLAGS="-lm -lcompiler_rt" pip install numpy

# # Won't work, pre-compiled binary is not compatible with aarch64
# conda install astropy --copy --no-deps

# # Note:
# # if you want to use astropy
# apt update && apt upgrade
# apt install python python-dev pip clang
# LDFLAGS="-lm -lcompiler_rt" pip install numpy
# pip install astropy