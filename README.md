<h1 align="center">SS13 Cogs</h1>


## Overview

These are utility cogs explicitly intended for SS13 servers leveraging off of the [/TG/](https://github.com/tgstation/tgstation) codebases. The idea is to provide a clean and convenient way to push data from the game to discord all while enjoying the many other benefits of having a [Red Bot V3 instance](https://github.com/Cog-Creators/Red-DiscordBot/tree/V3/develop). These cogs may work for other codebases, however, this has not been tested and it may require some added effort during setup.

| Cog      | Description                                                  |
| -------- | ------------------------------------------------------------ |
| GetNotes | **Pulls player notes from an SS13 [/TG/](https://github.com/tgstation/tgstation) schemed database**<br /><br />`setnotes` - Configuration options for the notes cog<br />`notes` -  Lists all of the notes for a given CKEY<br />`findplayer` - Searches the database for a player using their CID, IP, or CKEY and outputs an overview of the user. **Note**: It is recommended to restrict this command to admin specific channels. The results will automatically redact the CID and IP after 5-minutes. <br /><br />*Requires: mysql-connector-python>=8.0* -- `pip install mysql-connector-python` |
| Status   | **Obtains the current status of a hosted SS13 round and pertinent admin pings (e.g. Ahelps, round ending events, custom pings)**<br /><br />`adminwho` - Lists the current admins on the server &ast;<br />`players` - Lists the current players on the server&ast;<br />`setstatus`  - Configuration options for the status cog<br />`status` - Displays current round information<br /><br />_&ast; Requires additional setup, see [Additional Functions](#additional-functions) for more information_ |

## Setup

### Redbot:

Setup for your redbot V3 instance is a straightforward process. 

1. Add this repo/branch with `[p]repo add ss13-cogs https://github.com/crossedfall/crossed-cogs ss13/master`
2. Install the cogs you want to use with `[p]cog install ss13-cogs getnotes` and `[p]cog install ss13-cogs status`
3. Load your new cogs with `[p]load status getnotes`

_Any reference to [p] should be replaced with your prefix_

---

### GetNotes:

In order to fully utilize the GetNotes cog you will need to have a fully configured player database for your SS13 server configured using the [/TG/ schema](https://github.com/tgstation/tgstation/blob/master/SQL/tgstation_schema.sql). 

Once you have a database configured, you will need to provide a user that the bot can use to query said database. It is **highly** recommended that you ensure this user only has `SELECT` privileges and is separate from the one your server is configured to use. 

--

_Note:_ While the required `mysql-connector-python` package should be installed automatically.. If you get an error when using the notes cog where the `mysql-connector-python` module wasn't found, please ensure it is installed either by using your favorite terminal or (with the debug flag enabled on your bot) `[p]pipinstall mysql-connector-python` where `[p]` is your prefix.  

---

### Status:

The status cog operates by probing the server with a `?status` request and then parses that information out in a readable format, see the below example on how that might look.

|                      Online                       |                      Offline                      |
| :-----------------------------------------------: | :-----------------------------------------------: |
| ![1543959022724](https://i.imgur.com/7K1x9nd.png) | ![1544039500509](https://i.imgur.com/EXe4p1T.png) |

The status cog is also capable of displaying current round information within a set channel's topic description. This live status report will automatically update itself every 5-minutes. 

![topic](https://i.imgur.com/QSYgvBx.png)

In addition to the above, the status cog also has a listening function to serve incoming game data provided by your SS13 server. Currently, this cog serves new round and administrative notices using the following subsystem. In order for the status cog to receive said notifications, this controller subsystem will need to be added into your codebase and loaded into your dme file. (`code/controllers/subsystem/redbot.dm`)

```dm
SUBSYSTEM_DEF(redbot)
	name = "Bot Comms"
	flags = SS_NO_FIRE

/datum/controller/subsystem/redbot/Initialize(timeofday)
	var/comms_key = CONFIG_GET(string/comms_key)
	var/bot_ip = CONFIG_GET(string/bot_ip)
	var/round_id = GLOB.round_id
	if(config && bot_ip)
		var/query = "http://[bot_ip]/?serverStart=1&roundID=[round_id]&key=[comms_key]"
		world.Export(query)
	return ..()

/datum/controller/subsystem/redbot/proc/send_discord_message(var/channel, var/message, var/priority_type)
	var/bot_ip = CONFIG_GET(string/bot_ip)
	var/list/adm = get_admin_counts()
	var/list/allmins = adm["present"]
	. = allmins.len
	if(!config || !bot_ip)
		return
	if(priority_type && !.)
		send_discord_message(channel, "@here - A new [priority_type] requires/might need attention, but there are no admins online.") //Backup message should redbot be unavailable
	var/list/data = list()
	data["key"] = CONFIG_GET(string/comms_key)
	data["announce_channel"] = channel
	data["announce"] = message
	world.Export("http://[bot_ip]/?[list2params(data)]")
```


A new option (`BOT_IP`) within the [comms.txt](https://github.com/tgstation/tgstation/blob/master/config/comms.txt) config file (or within your legacy config file) will also have to be added. The `BOT_IP` should be the ip and listening port of your bot. For example, 

```txt
## Communication key for receiving data through world/Topic(), you don't want to give this out
COMMS_KEY SomeKeyHere

[...]

## Bot IP:Port for discord notifications
BOT_IP 127.0.0.1:8081
```

In order to process the new config option, the following entry must be added to the bottom of the [comms.dm](https://github.com/tgstation/tgstation/blob/master/code/controllers/configuration/entries/comms.dm) controller file:

```dm
[...]
/datum/config_entry/string/medal_hub_password
	protection = CONFIG_ENTRY_HIDDEN

/datum/config_entry/string/bot_ip
```



#### Usage:

Once the above is added into your codebase, you can send administrative notices directly into discord by calling the `send_discord_message(var/channel, var/message, var/priority_type)` function. The status cog can currently check for new round notifications, messages directed at the admin channel, and mentor tickets. 

For any admin notices (e.g. round ending events or ahelps) ensure that the `admin` channel is set. If you have a mentorHelp system in place, you can send mentor tickets to discord using the `mentor` channel instead. **Note:** `admin` notices will provide an `@here` ping if there aren't any admins currently online when the announcement is sent. Notices using the `mentor` channel will not provide `@here` pings. 

If, for example, you want to send new ticket admin notifications to discord you can do so using the following method within your [if(is_bwoik)](https://github.com/tgstation/tgstation/blob/master/code/modules/admin/verbs/adminhelp.dm#L192) statement.  

```dm
SSredbot.send_discord_message("admin", "Ticket #[id] created by [usr.ckey] ([usr.real_name]): [name]", "ticket")
```



![1544022902014](https://i.imgur.com/DaIsZ3Q.png)



As another example, if you wanted to show a round ending event (like the supermater shard delaminating), you can do so by adding a very similar method within the function handling the event, in this case the shard delaminating event.

```dm
SSredbot.send_discord_message("admin","The supermatter has just delaminated.","round ending event")
```



![1544023245022](https://i.imgur.com/9bihWqd.png)





##### Important Notes:

- The bot will automatically provide an `@here` mention in the designated admin channel, which can be adjusted with the `[p]setstatus adminchannel` command (_where [p] is your prefix_). It is recommend to create an admin monitoring channel where the bot has permissions to mention and post updates.


- In order to serve messages received by your game server, you will need to ensure that the `comms_key` for the bot and the server are the same. The bot will automatically drop any messages sent that do not contain your `comms_key`. This setting can be found within your [config file](https://github.com/tgstation/tgstation/blob/master/config/comms.txt#L2)

#### Additional Functions:

The `[p]players` and `[p]adminwho` commands will output a list of player/admin ckeys respectively. In order to use these functions you will need to add the below entries at the bottom of your [world_topic.dm](https://github.com/tgstation/tgstation/blob/master/code/datums/world_topic.dm) file. Using the commands without the below topics will cause the bot to report "0 players" whenever either command is used. This will not effect the player/admin counts in the status report, however.

```dm
/datum/world_topic/whois
	keyword = "whoIs"

/datum/world_topic/whois/Run(list/input)
	. = list()
	.["players"] = GLOB.clients

	return list2params(.)

/datum/world_topic/getadmins
	keyword = "getAdmins"

/datum/world_topic/getadmins/Run(list/input)
	. = list()
	var/list/adm = get_admin_counts()
	var/list/presentmins = adm["present"]
	var/list/afkmins = adm["afk"]
	.["admins"] = presentmins
	.["admins"] += afkmins

	return list2params(.)	
```



---

### Contact:

For questions or concerns, feel free to submit a new [issue](https://github.com/crossedfall/crossed-cogs/issues). I will make my best effort to address any concerns/feedback provided within a reasonable amount of time.



### Credits:

- [Tigercat2000](https://github.com/tigercat2000) for his subsystem template
- The [/TG/ community](https://github.com/tgstation) for their efforts on SS13 
- The [Cog-Creators](https://github.com/Cog-Creators) staff for their work on redbot
