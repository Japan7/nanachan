#!/bin/sh -xe
poetry install

nohup sh -c 'redis-stack-server &' > redis-stack-server.out
