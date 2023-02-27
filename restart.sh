#!/bin/bash

ps -ef | grep -v grep | grep bot.py | awk '{print $2}' | xargs kill -9

python3 bot.py 2>&1 1>> run.log &
