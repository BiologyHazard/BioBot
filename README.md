# BioBot

## TODO

- autoreply 支持正则匹配

## 安装

1. 安装python

2. pip 安装依赖

    ```bash
    pip install -r requirements.txt
    ```

3. 安装 enchant

    ```bash
    # CentOS
    yum install enchant
    # Ubuntu
    sudo apt install enchant-2
    ```

4. 安装 ffmpeg

    ```bash
    sudo apt install ffmpeg
    ```

5. 下载meme资源

    ```bash
    meme download
    ```

6. 安装字体

    https://github.com/MeetWq/meme-generator/blob/main/docs/install.md

    https://github.com/noneplugin/nonebot-plugin-memes/issues/43

    ```
    cd /usr/share/fonts
    cp /root/BioBot/data/fonts/* .
    fc-cache -fv
    rm ~/.cache/matplotlib/*
    ```
    然后重启bot
