# MumbleRadioPlayer
A fork of [MumbleRadioPlayer](https://github.com/azlux/MumbleRadioPlayer) by azlux. This fork focuses on YouTube playback. It use the excellent [pafy](https://github.com/mps-youtube/pafy) library to accomplish this.

======

1. [How to start the bot](#how-to-start-the-bot)
2. [Commands](#commands)
3. [Installation](#installation)
4. [Important](#important)
5. [How to help](#how-to-help)
6. [Additionnal informations](#additionnal-informations)
7. [TODO](#todo)
8. [Credits](#credits)

#### How to start the bot
Run the mumbleRadioPlayer.py to start the bot (don't forget the `chmod +x ./mumbleRadioPlayer.py`)
`
./mumbleRadioPlayer.py -server <server_url> -user <bot_name>
`

Optional parameters :
`
-channel <default_channel>
-port <port_number>
-password <password>
`

It's in Python 3.

#### Commands
You can change commands into the configuration file, The default is :
- !play
   - from a list of url (name you have add into the configuration file)
   - with a url
- !playfile (play a file from the path into the config file)
- !list (list all files into the path of !playfile)
- !stop
- !joinme (join the user who speak to me)
- !kill
- !oust (stop + go into the default channel)
- !v <number> (change volume with a percentage )
- !np (get the current music title - now playing feature)
##### Added commands
The following additional commands are available: 
`<x>` denotes a required parameter, `[x=1]` denotes an optional parameter with default value.
- !ytplay `<yt_id>` (`yt_id` is the last bit of a YT URL, will download the audio and play it)
- !ytpl `<yt_pl_id>` `[shuffle=1]` (`yt_pl_id` is the last bit of a YT playlist URL, will retrieve the list and then iterate over them, downloading and playing one at a time. Will shuffle by default, optional second parameter `shuffle` can be set to 0 to disable)
- !next (play the next song in the YT playlist)
- !upnext `[num=3]` (displays the next `num` songs that will be played (if in playlist))
- !addpl `<yt_pl_id>` `<name>` (adds YT playlist to DB as name for easier playback later on)
- !delpl `<idx>` (removes playlist number `idx` from the DB)
- !listpls (lists the playlists in the DB)
- !playlist `<num>` (starts playing playlist number `num` from the list)
- !skip `[num=1]` (skips the next `num` songs in the playlist)
- !q `<yt_id>` (prepends YT video with `yt_id` as id to the queue)

#### Installation
1. You need python 3 with opuslib and protobuf (look at the requirement of pymumble)
you will need pip3 (apt-get install python3-pip). Additionally the bot uses `requests`, `pafy`, `beautifulsoup4`, and `sqlite3`.
2. The Bot use ffmpeg, so you know what you have to do if ffmpeg aren't in your package manager.

commands (don't forget the sudo mode):
```
apt-get install ffmpeg
git clone --recurse-submodules https://github.com/azlux/MumbleRadioPlayer.git
cd ./MumbleRadioPlayer
pip3 install -r requirement.txt
chmod +x ./mumbleRadioPlayer.py
```

#### Important
What the bot cannot do:

1. A .pls file is **NOT** a stream url, it's just a text file. Take a look inside if you can found real stream url. A good url can be read by your browser natively.
2. The configuration file is **NOT** UTF-8 encoded, be careful

#### How to help
Because, Yes, You can help.
- If you find bugs, problems, errors, mistakes, you can create an issue on github.
- If you have a suggestion or want a new feature, you can create an issue.
- If you want to make change by your own, fork and pull. We will discuss about your code.

#### Additionnal informations
If a command doesn't work, try to find the error, or send me the command and I will try to reproduce it.

The bot change is own comment with the stream name. Now working with:
- ShoutCast
- IceCast

#### TODO
- [x] Make the bot speak in the channel
- [ ] Better comment use (and add !help)
- [ ] Option to use a certificate

=====
### Credits
Pymumble comes from [here](https://github.com/azlux/pymumble). It's, for now, the current fork alive of pymumble in PYTHON 3 now \o/
