This Telegram bot is created to facilitate the process of getting an
appointment for Shengen visa at the Netherlands embassy in Dublin, Ireland.
It checks the booking system every 5 seconds and sends alerts if there are some
available. It doesn't use or store personal or private data. Wish you best of
luck with your visa.

How to setup a bot
==================

1. Start conversation with https://t.me/BotFather
2. Create a new bot::

    > /newbot
    < Alright, a new bot. How are we going to call it? Please choose a name for
    your bot.
    > My Super awesome bot
    < Good. Now let's choose a username for your bot. It must end in `bot`.
    Like this, for example: TetrisBot or tetris_bot.
    > mysuperawesomebot
    > Done! Congratulations on your new bot. You will find it at
    t.me/mysuperawesomebot. You can now add a description, about section and
    profile picture for your bot, see /help for a list of commands. By the way,
    when you've finished creating your cool bot, ping our Bot Support if you
    want a better username for it. Just make sure the bot is fully operational
    before you do this.

    Use this token to access the HTTP API:
    987350479:AAG176kql1XZSL81RdLBJuYoYwpneeztHHw
    Keep your token secure and store it safely, it can be used by anyone to
    control your bot.

3. Setup commands::

    > /setcommands
    < Choose a bot to change the list of commands.
    > @mysuperawesomebot
    < OK. Send me a list of commands for your bot. Please use this format:

    command1 - Description


    For a description of the Bot API, see this page: https://core.telegram.org/bots/api
    > start - Just tells me that I can talk to you.
    help - Help for commands.
    terms - Information about terms of use and collected data.
    subscribe - Subscribe for notifications.
    unsubscribe - Unsubscribe for notifications.
    stats - Show some statistics data.
    < Success! Command list updated. /help

4. Optionally setup userpic & description.

5. Clone the repository and build a docker container::

    git clone https://github.com/alex-ac/netherappbot
    cd netherappbot
    docker build . -t netherappbot

6. Run the container. Remember to place database into volume and provide the 
   token::

    docker run -d -v /var/data netherappbot \
        netherappbot 987350479:AAG176kql1XZSL81RdLBJuYoYwpneeztHHw \
        sqlite:///var/data/bot.db


