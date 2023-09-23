# BioBot
# TODO
+ autoreply支持正则匹配

# 安装

1. 安装python

1. 安装go-cqhttp

1. pip安装依赖  
    `$ pip install -r requirements.txt`

1. 安装enchant  
    `$ yum install enchant`

1. 下载meme资源  
    `$ meme download`

1. 安装字体  
    https://github.com/MeetWq/meme-generator/blob/main/docs/install.md
    https://github.com/noneplugin/nonebot-plugin-memes/issues/43

    `$ cd /usr/share/fonts`  
    `$ cp /root/BioBot/data/fonts/* .`  
    `$ fc-cache -fv`  
    `$ rm ~/.cache/matplotlib/*`  
    然后重启bot
