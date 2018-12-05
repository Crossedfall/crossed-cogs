<h1 align="center">SS13 Cogs</h1>



## Overview

These are utility cogs explicitly intended for SS13 servers leveraging off of the [/TG/](https://github.com/tgstation/tgstation) codebases. The idea is to provide a clean and convenient way to push data from the game to discord all while enjoying the many other benefits of having a Red Bot V3 instance. These cogs may work for other codebases, however, this has not been tested and it may require some added effort during setup.

| Cog      | Description                                                  |
| -------- | ------------------------------------------------------------ |
| GetNotes | Pulls player notes from a SS13 [/TG/](https://github.com/tgstation/tgstation) schemed database <br /><br />*Requires: Mysql-connector* -- `pip install mysql-connector` |
| Status   | Obtains the current status of a hosted SS13 round ) and pertinent admin pings (e.g. Ahelps, round ending events, custom pings) |

## Setup

### Redbot:

Setup for your redbot V3 instance is a straightforward process. 

1. Add this repo/branch with `[p]repo add ss13-cogs https://github.com/crossedfall/crossed-cogs ss13/master`
2. Install the cogs you want to use with `[p]cog install ss13 getnotes` and `[p]cog install ss13 status`
3. Load your new cogs with `[p]load status getnotes`

_Any reference to [p] should be replaced with your prefix_

### GetNotes:

In order to fully utilize the GetNotes cog you will need to have a fully configured player database for your SS13 server configured using the [/TG/ scheme](https://github.com/tgstation/tgstation/blob/master/SQL/tgstation_schema.sql). 

Once you have a database configured, you will need to provide a user that the bot can use to query said database. It is **highly** recommended that you ensure this user only has read privileges and is separate from the one your server is configured to use. 

--

_Note:_ While the required `mysql-connector` package should be installed automatically.. If you get an error when using the notes cog where the `mysql-connector` module wasn't found, please ensure it is installed either by using your favorite terminal or (with the debug flag enabled on your bot) `[p]pipinstall mysql-connector` where `[p]` is your prefix.  



### Status:

The status cog operates by probing the server with a `?status` request and then parses that information out in a readable format, see the below example on how that might look.

![1543959022724](https://i.imgur.com/7K1x9nd.png)



In addition to the above, the status cog also has a listening function to serve incoming game data provided by your SS13 server. Currently, this cog serves new round and administrative notices using the following subsystem. In order for the status cog to receive said notifications, this controller subsystem will need to be added into your codebase and loaded into your dme file. (`code/controllers/subsystem/redbot.dm`)



```dm
SUBSYSTEM_DEF(redbot)
	name = "Bot Comms"
	flags = SS_NO_FIRE

/datum/controller/subsystem/ast/Initialize(timeofday)
	if(config && GLOB.bot_ip)
		var/query = "http://[GLOB.bot_ip]/?serverStart=1&key=[global.comms_key]"
		world.Export(query)

/datum/controller/subsystem/ast/proc/send_discord_message(var/channel, var/message, var/priority_type)
	if(!config || !GLOB.bot_ip)
		return
	if(priority_type && !total_admins_active())
		send_discord_message(channel, "@here - A new [priority_type] requires/might need attention, but there are no admins online.") //Backup message should redbot be unavailable
	var/list/data = list()
	data["key"] = global.comms_key
	data["announce_channel"] = channel
	data["announce"] = message
	world.Export("http://[GLOB.bot_ip]/?[list2params(data)]")
```


A new option (`BOT_IP`) within within the [comms.txt](https://github.com/tgstation/tgstation/blob/master/config/comms.txt) config file (or within your legacy config file) will also have to be added. The `BOT_IP` should be the ip and listening port of your bot. For example, 

```txt
## Communication key for receiving data through world/Topic(), you don't want to give this out
COMMS_KEY SomeKeyHere

[...]

## Bot IP:Port for discord notifications
BOT_IP 127.0.0.1:8081
```



-------

Once the above is added into your codebase, you can send administrative notices directly into discord by calling the `send_discord_message` function. 

If, for example, you want to send new ticket admin notifications to discord you can do so using the following method within your `if(is_bwoik)` statement.  

`SSredbot.send_discord_message("admin", "Ticket #[id] created by [usr.ckey] ([usr.real_name]): [name]", "ticket")`

![1544022902014](https://i.imgur.com/DaIsZ3Q.png)



As another example, if you wanted to show a round ending event (like the supermater shard delaminating), you can do so by adding a very similar method within the function handling the event, in this case the shard delaminating event.

`SSredbot.send_discord_message("admin","The supermatter has just delaminated.","round ending event")`

![1544023245022](https://i.imgur.com/9bihWqd.png)

#### Important Notes:

The bot will automatically provide an `@here` mention in the designated admin channel, which can be adjusted with the `[p]setstatus adminchannel` command (_where [p] is your prefix_). It is recommend to create an admin monitoring channel where the bot has permissions to mention and post updates.

--

In order to serve messages received by your game server, you will need to ensure that the `comms_key` for the bot and the server are the same. The bot will automatically drop any messages sent that do not contain your `comms_key`. This setting can be found within your [config file](https://github.com/tgstation/tgstation/blob/master/config/comms.txt#L2)



### Contact:

For questions or concerns, feel free to submit a new [issue](https://github.com/crossedfall/crossed-cogs/issues). I will make my best effort to address any concerns/feedback provided within a reasonable amount of time.



### Credits:

- [Monster860](https://github.com/monster860) for his subsystem code
- The [/TG/ community](https://github.com/tgstation) for their efforts on SS13 
- The [Cog-Creators](https://github.com/Cog-Creators) staff for their work on redbot