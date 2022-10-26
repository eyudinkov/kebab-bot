# Kebab Bot

Telegram Bot, which provides special commands and modes for telegram chat.  

## How to use

```
- Clone repository
$ https://github.com/eyudinkov/kebab-bot

- Enter in directory
$ cd kebab-bot

- Build local image
$ make build

- Setup your env vars in example.env and rename it to .env.

- Run container
$ make up

- Enjoy
```

## Commands and modes

### Commands

- `/kebab` - transform your message to bot message
- `/mute N` - mutes user for N minutes
- `/unmute` - unmutes user
- `/ban N` - fake command, which bans user for N minutes
- `/trust` - makes user trusted
- `/untrust` - makes user untrusted
- `/roll` - russian roulette
- `/leaders` - shows leaders of roll game
- `/wipe_leaders` - wipes leaders of roll game
- `/wipe_me` - wipes user history
- `/top` - shows active users of roll game in text format
- `/length` - shows length of telegram id
- `/longest` - shows the list of longest telegram ids
- `/version` - shows version of bot
- `/still TEXT` - blames user for being out of trend
- `/since TOPIC` - increases count of the presented topic (works only if `since_mode` is enabled)
- `/since_list` - shows the list of disscussed topics (works only if `since_mode` is enabled)
- `/namaz` - shows the time of namaz

### Modes

- `/since_mode_(ON/OFF)` - enables/disables `since` mode
- `/towel_mode_(ON/OFF)` - enables/disables `towel` mode
- `/smile_mode_(ON/OFF)` - enables/disables `smile` mode
