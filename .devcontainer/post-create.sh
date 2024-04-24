#!/bin/sh -xe
sudo chown -R $(id -u):$(id -g) .venv/ /poetry-cache/

sudo apt update
DEBIAN_FRONTEND=noninteractive sudo apt install -y --no-install-recommends ffmpeg
sudo ln -s /usr/lib/x86_64-linux-gnu/libopus.so.0 /usr/lib/

curl -sSL https://install.python-poetry.org | python3 -

(
    cd
    wget https://packages.redis.io/redis-stack/redis-stack-server-6.2.4-v3.bullseye.x86_64.tar.gz
    tar xvf redis-stack-server*
    rm redis-stack-server*.tar.gz
    ln -s ~/redis-stack-server*/bin/* ~/.local/bin/
)
