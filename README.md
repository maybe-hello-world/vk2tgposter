# VK 2 Telegram reposter
Bot that repost vk posts from group or smth similar to telegram chat/channel  
To run fill config.py file and start bot: python3 bot.py  
If you want to start it in background and detach from console (to close it without stopping the bot) use "nohup python3 bot.py &"  

## Docker support
Pull from "maybehelloworld/vk2tgposter"  
In order to start you need to pass to /usr/src/app filled config.py file, file for storing last known id and log file.  
  
Example:
docker run -d --name vk2tgposter --restart unless-stopped \
    -v /home/username/vk2tgposter/config.py:/usr/src/app/config.py \
    -v /var/log/vk2tgposter/last_id.txt:/usr/src/app/last_id.txt \
    -v /var/log/vk2tgposter/bot.log:/usr/src/app/bot.log \
    maybehelloworld/vk2tgposter

