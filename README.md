# BioBot

## TODO

- autoreply 支持正则匹配

## 安装

1. 安装 python

2. pip 安装依赖

    ```bash
    pip install -r requirements.txt
    ```

3. 安装 enchant (wordle 插件)

    ```bash
    # CentOS
    yum install enchant
    # Ubuntu
    sudo apt install enchant-2
    ```

4. 安装 ffmpeg (maimai 插件)

    ```bash
    sudo apt install ffmpeg
    ```

5. 下载 meme 资源 (meme 插件)

    ```bash
    meme download
    ```

6. 安装字体 (meme 插件)

    https://github.com/MeetWq/meme-generator/blob/main/docs/install.md

    https://github.com/noneplugin/nonebot-plugin-memes/issues/43

    ```
    cd /usr/share/fonts
    cp /root/BioBot/data/fonts/* .
    fc-cache -fv
    rm ~/.cache/matplotlib/*
    ```

    然后重启bot
