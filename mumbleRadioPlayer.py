#!/usr/local/bin/python3
import struct

import time
import sys
import signal
import configparser
import urllib.request, urllib.error, urllib.parse
import json
import re
import audioop
import subprocess as sp
import pymumble.pymumble_py3 as pymumble
import argparse
import os.path
import http.client
from os import listdir
import pafy
import threading
from random import shuffle
import requests
import bs4 as bs
import sqlite3

class MumbleRadioPlayer:
    def __init__(self):
        signal.signal(signal.SIGINT, self.ctrl_caught)

        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read("configuration.ini")

        parser = argparse.ArgumentParser(description='Bot for playing radio stream on Mumble')
        parser.add_argument("-s", "--server", dest="host", type=str, required=True, help="The server's hostame of a mumble server")
        parser.add_argument("-u", "--user", dest="user", type=str, required=True, help="Username you wish, Default=abot")
        parser.add_argument("-P", "--password", dest="password", type=str, default="", help="Password if server requires one")
        parser.add_argument("-p", "--port", dest="port", type=int, default=64738, help="Port for the mumble server")
        parser.add_argument("-c", "--channel", dest="channel", type=str, default="", help="Default chanel for the bot")

        args = parser.parse_args()
        self.volume = self.config.getfloat('bot', 'volume')
        self.channel = args.channel
        self.playing = False
        self.playing_file = False
        self.playing_file_name = None
        self.url = None
        self.exit = False
        self.nb_exit = 0
        self.thread = None
        self.in_playlist = False
        self.pl_items = []
        self.cur_item = 0


        self.user_agent = { 'User-Agent': 'Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0' }

        self.mumble = pymumble.Mumble(args.host, user=args.user, port=args.port, password=args.password,
                                      debug=self.config.getboolean('debug', 'mumbleConnection'))
        self.mumble.callbacks.set_callback("text_received", self.message_received)

        self.mumble.set_codec_profile("audio")
        self.mumble.start()  # start the mumble thread
        self.mumble.is_ready()  # wait for the connection
        self.set_comment()
        self.mumble.users.myself.unmute()  # by sure the user is not muted
        if self.channel:
            self.mumble.channels.find_by_name(self.channel).move_in()
            # self.mumble.users.myself['channel_id'] = self.mumble.channels.find_by_name(self.channel)
        self.mumble.set_bandwidth(200000)
        self.loop()

    def ctrl_caught(self, signal, frame):
        print("\ndeconnection asked")
        self.exit = True
        self.stop()
        if self.nb_exit > 2:
            print("Forced Quit")
            sys.exit(0)
        self.nb_exit += 1

    def next_in_pl(self, query=False):
        if self.in_playlist and len(self.pl_items) > self.cur_item:
            res = self.pl_items[self.cur_item]
            if not query:
                self.cur_item += 1
            return res
        return None

    def add_yt_pl(self, yt_pl_id, name):
        self.db.execute('INSERT INTO playlists(yt_pl_id, name) values (?, ?);', (yt_pl_id, name))
        self.db.commit()

    def del_yt_pl(self, num):
        self.db.execute('DELETE FROM playlists where id=?', (num,))
        self.db.commit()

    def list_yt_pls(self, actor):
        self.mumble.users[actor].send_message('<br/>'+'<br/>'.join( map(lambda x: '%d. %s' % ( x[0], x[1] ), self.db.execute('SELECT id, name FROM playlists;').fetchall() )))

    def queue(self, yt_id):
        video = pafy.new(yt_id)
        self.pl_items.insert(self.cur_item, { 'pafy': video })

    def play_yt_pl_from_list(self, pl_id):
        res = self.db.execute('SELECT yt_pl_id, name from playlists WHERE id=?', (pl_id,)).fetchone()
        if res:
            self.send_msg_channel('Playing: %s' % res[1])
            self.play_yt_playlist(res[0])
        else:
            self.send_msg_channel('That\' not on the list...')

    def message_received(self, text):
        self.db = sqlite3.connect('barry.db')
        message = text.message
        if message[0] == '!':
            message = message[1:].split(' ')
            if len(message) > 0:
                command = message[0]
                parameter = ''
                parameters = []
                if len(message) > 1:
                    parameters = message[1:]
                    parameter = ' '.join(parameters)
            else:
                return

            print(command + ' - ' + parameter + ' by ' + self.mumble.users[text.actor]['name'])
            if command == self.config.get('command', 'play_stream') and parameter:
                self.play_stream(parameter)

            elif command == self.config.get('command', 'play_file') and parameter:
                path = self.config.get('bot', 'music_folder') + parameter
                # print(path)
                if "/" in parameter:
                    self.mumble.users[text.actor].send_message(self.config.get('strings', 'bad_file'))
                elif os.path.isfile(path):
                    self.launch_play_file(path)
                    self.playing_file_name = parameter
                else:
                    self.mumble.users[text.actor].send_message(self.config.get('strings', 'bad_file'))

            elif command == self.config.get('command', 'stop'):
                self.stop()

            elif command == self.config.get('command', 'kill'):
                if self.is_admin(text.actor):
                    self.stop()
                    self.exit = True
                else:
                    self.mumble.users[text.actor].send_message(self.config.get('strings', 'not_admin'))

            elif command == self.config.get('command', 'stop_and_getout'):
                self.stop()
                if self.channel:
                    self.mumble.channels.find_by_name(self.channel).move_in()

            elif command == self.config.get('command', 'joinme'):
                self.mumble.users.myself.move_in(self.mumble.users[text.actor]['channel_id'])

            elif command == self.config.get('command', 'volume'):
                if parameter is not None and parameter.isdigit() and 0 <= int(parameter) <= 100:
                    self.volume = float(float(parameter) / 100)
                    self.send_msg_channel(self.config.get('strings', 'change_volume') % (
                        int(self.volume * 100), self.mumble.users[text.actor]['name']))
                else:
                    self.send_msg_channel(self.config.get('strings', 'current_volume') % int(self.volume * 100))

            elif command == self.config.get('command', 'current_music'):
                if self.url is not None:
                    self.send_msg_channel(get_title(self.url))
                elif self.playing_file:
                    duration = ''
                    if self.in_playlist:
                        duration = self.pl_items[self.cur_item-1]['pafy'].duration
                    self.send_msg_channel('Now playing: %s [%s]' % ( self.playing_file_name, duration))
                else:
                    self.mumble.users[text.actor].send_message(self.config.get('strings', 'not_playing'))
            elif command == self.config.get('command', 'list'):
                folder_path = self.config.get('bot', 'music_folder')
                files = [f for f in listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
                if files :
                    self.mumble.users[text.actor].send_message('<br>'.join(files))
                else :
                     self.mumble.users[text.actor].send_message(self.config.get('strings', 'no_file')) 

            elif command == self.config.get('command', 'ytplay') and parameter:
                self.play_yt(parameter)
            elif command == self.config.get('command', 'ytplaylist') and parameters:
                if(len(parameters) > 1):
                    print(parameters[1])
                    shfl = parameters[1] == '1'
                    self.play_yt_playlist(parameters[0], shfl)
                else:
                    self.play_yt_playlist(parameters[0])
            elif command == self.config.get('command', 'next'):
                self.next_song()
            elif command == self.config.get('command', 'lyrics'):
                if parameters:
                    self.print_lyrics(text.actor, search_for=' '.join(parameters))
                else:
                    self.print_lyrics(text.actor)
            elif command == self.config.get('command', 'upnext'):
                if parameter and parameter.isdigit:
                    self.print_up_next(text.actor, num=int( parameter ))
                else:
                    self.print_up_next(text.actor)
            elif command == self.config.get('command', 'addpl'):
                if len(parameters) > 1:
                    self.add_yt_pl(parameters[0], ' '.join( parameters[1:] ))
                else:
                    self.send_msg_channel('Usage: !%s yt_pl_id name' % command)
            elif command == self.config.get('command', 'delpl'):
                if parameter and parameter.isdigit:
                    self.del_yt_pl(parameter)
            elif command == self.config.get('command', 'listpls'):
                self.list_yt_pls(text.actor)
            elif command == self.config.get('command', 'playlist'):
                if not parameter:
                    self.send_msg_channel('Usage: !%s playlist number' % command)
                    self.send_msg_channel('Use !listpls to obtain a list of playlists')
                else:
                    self.play_yt_pl_from_list(parameter)
            elif command == self.config.get('command', 'skip'):
                if parameter and parameter.isdigit:
                    self.skip(num=int(parameter))
                else:
                    self.skip()
            elif command == self.config.get('command', 'queue') and parameter:
                if not self.in_playlist:
                    self.send_msg_channel('Currently only possible in playlist mode')
                else:
                    self.queue(parameter)
            else:
                self.mumble.users[text.actor].send_message(self.config.get('strings', 'bad_command'))

    def is_admin(self, user):
        username = self.mumble.users[user]['name']
        list_admin = self.config.get('bot', 'admin').split(';')
        if username in list_admin:
            return True
        else:
            return False

    def print_lyrics(self, actor, search_for=None):
        if not self.playing:
            self.send_msg_channel('Not currently playing anything')
        elif not self.playing_file:
            self.send_msg_channel('Playing a stream, don\'t know the lyrics')
        elif self.playing_file_name is not None:
            if search_for is None:
                search_for = self.playing_file_name
            r = requests.get('http://search.azlyrics.com/search.php?q=%s' % search_for.replace(' ', '+'), headers=self.user_agent)
            soup = bs.BeautifulSoup(r.text, 'lxml')
            links = [l for l in soup.find_all('a') if 'lyrics' in  l.get('href')[20:]]
            if len(links) == 0:
                self.send_msg_channel('Could not find lyrics for %s' % search_for)
            else:
                lyric_page = requests.get(links[0].get('href'), headers=self.user_agent)
                soup = bs.BeautifulSoup(lyric_page.text, 'lxml')
                lyric_text = soup.find(class_='ringtone').find_next_sibling('div').text.replace('\n', '<br/>')
                self.mumble.users[actor].send_message(lyric_text)

    def print_up_next(self, actor, num=3):
        if not self.in_playlist:
            self.send_msg_channel('No clue what\'s next')
        else:
            song_list = self.pl_items[self.cur_item:self.cur_item+num]
            res = '<br/>' + '<br/>'.join(['%d. %s' % (i, song['pafy'].title) for i, song in enumerate(song_list, 1)])
            self.mumble.users[actor].send_message(res)

    def skip(self, num=1):
        if not self.in_playlist:
            self.send_msg_channel('Not in playlist, can\'t skip')
        self.pl_items = self.pl_items[0:self.cur_item] + self.pl_items[self.cur_item+num:]

    def play_yt_playlist(self, yt_pl_id, shuf=True):
        pl = pafy.get_playlist(yt_pl_id)
        self.stop()
        self.send_msg_channel('Playlist Title: %s' % pl['title'])
        self.pl_items = pl['items']
        if shuf:
            shuffle(self.pl_items)
        self.in_playlist = True
        self.cur_item = 0
        def launch_next():
            if not self.playing:
                return
            self.playing = False
            self.thread = None
            if self.exit:
                return
            n = self.next_in_pl()
            nn = self.next_in_pl(query=True)
            if nn:
                self.dl_pafy(n['pafy'])
            if n:
                self.play_yt_pafy(n['pafy'], launch_next)
            else:
                self.stop()
                print("Playlist finished")
        self.play_yt_pafy(self.next_in_pl()['pafy'], launch_next)

    def dl_pafy(self, pafy_obj):
        try:
            bestaudio = pafy_obj.getbestaudio()
            dl_dir = self.config.get('bot', 'yt_tmp_folder')
            filename = dl_dir + bestaudio.title.replace('/', '_') + '.' + bestaudio.extension
            if os.path.isfile(filename):  #Already downloaded this one
                print("Already downloaded, playing from file")
            else:
                print("Donwloading: %s" % (pafy_obj.title))
                # filename = bestaudio.download(filepath=dl_dir)
                bestaudio.download(filepath=filename)
                print("Donwloaded %s" % filename)
        except IOError as e:
            pass

    def play_yt_pafy(self, pafy_obj, next_func):
        try:
            bestaudio = pafy_obj.getbestaudio()
            dl_dir = self.config.get('bot', 'yt_tmp_folder')
            # filename = dl_dir + pafy_obj.videoid
            filename = dl_dir + bestaudio.title.replace('/', '_') + '.' + bestaudio.extension
            if os.path.isfile(filename):  #Already downloaded this one
                print("Already downloaded, playing from file")
            else:
                print("Donwloading: %s" % (pafy_obj.title))
                # filename = bestaudio.download(filepath=dl_dir)
                bestaudio.download(filepath=filename)
                print("Donwloaded %s" % filename)
            self.launch_play_file(filename, next_func)
            self.playing_file_name = pafy_obj.title
            self.send_msg_channel('Playing: %s [%s]' % ( self.playing_file_name, pafy_obj.duration ))
        except IOError as e:
            print(e)
            next_func()

    def play_yt(self, url):
        self.stop()
        video = pafy.new(url)
        bestaudio = video.getbestaudio()
        dl_dir = self.config.get('bot', 'yt_tmp_folder')
        print("Donwloading: %s - %s" % (video.title, dl_dir))
        filename = bestaudio.download(filepath=dl_dir)
        print("Donwloaded %s" % ( filename ))
        self.launch_play_file(filename)
        self.playing_file_name = video.title

    def play_stream(self, msg):
        if self.config.has_option('stream', msg):
            url = self.config.get('stream', msg)
            self.launch_play_stream(url)
        elif self.config.getboolean('bot', 'allow_new_url') and get_url(msg):
            self.launch_play_stream(get_url(msg))
        else:
            print("Bad input")

    def launch_play_stream(self, url):
        info = get_server_description(url)
        if info != False:
            self.stop()

            time.sleep(2)
            if self.config.getboolean('debug', 'ffmpeg'):
                ffmpeg_debug = "debug"
            else:
                ffmpeg_debug = "warning"
            command = ["ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-i', url, '-ac', '1', '-f', 's16le', '-ar', '48000', '-']

            self.url = url
            self.thread = sp.Popen(command, stdout=sp.PIPE, bufsize=480)
            self.set_comment("Stream from %s" % info)
            time.sleep(3)
            self.playing = True

    def launch_play_file(self, path, next_func=lambda x: None):
        self.stop()
        if self.config.getboolean('debug', 'ffmpeg'):
            ffmpeg_debug = "debug"
        else:
            ffmpeg_debug = "warning"
        command = ["ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-i', path, '-ac', '1', '-f', 's16le', '-ar', '48000', '-']
        # self.thread = sp.Popen(command, stdout=sp.PIPE, bufsize=480)
        self.popenAndCall(next_func, [command], {'stdout': sp.PIPE, 'bufsize': 480})
        self.playing = True
        self.playing_file = True

    def loop(self):
        raw_music = None
        while not self.exit:
            if self.playing:
                while self.mumble.sound_output.get_buffer_size() > 0.5 and self.playing:
                    time.sleep(0.01)
                if self.thread:
                    raw_music = self.thread.stdout.read(480)
                if raw_music:
                    self.mumble.sound_output.add_sound(audioop.mul(raw_music, 2, self.volume))
                else:
                    time.sleep(0.01)
            else:
                time.sleep(1)

        while self.mumble.sound_output.get_buffer_size() > 0:
            time.sleep(0.01)
        time.sleep(0.5)

    def next_song(self):
        if self.in_playlist and self.thread:
            self.thread.kill()

    def stop(self):
        if self.thread:
            self.playing = False
            self.in_playlist = False
            self.playing_file = None
            self.pl_items = []
            time.sleep(0.5)
            self.thread.kill()
            self.thread = None
            self.url = None

    def set_comment(self, txt=None):
        if txt is None:
            txt = ""
        self.mumble.users.myself.comment(txt + "<p /> " + self.config.get('bot', 'comment'))

    def send_msg_channel(self, msg, channel=None):
        # print(self.mumble.users.myself['channel_id'])
        if not channel:
            channel = self.mumble.channels.find_by_name(self.channel)
        if not channel:
            channel = self.mumble.channels[self.mumble.users.myself['channel_id']]
        channel.send_text_message(msg)

    def popenAndCall(self, onExit, popenArgs, popenKwargs):
        """
        Source:
        http://stackoverflow.com/questions/2581817/python-subprocess-callback-when-cmd-exits
        Runs the given args in a subprocess.Popen, and then calls the function
        onExit when the subprocess completes.
        onExit is a callable object, and popenArgs is a list/tuple of args that one
        would give to subprocess.Popen.
        """
        def runInThread(onExit, popenArgs):
            proc = sp.Popen(*popenArgs, **popenKwargs)
            self.thread = proc
            proc.wait()
            onExit()
            return
        thread = threading.Thread(target=runInThread, args=(onExit, popenArgs))
        thread.start()
        # returns immediately after the thread starts
        return thread

def get_url(url):
    if url.startswith('http'):
        return url
    p = re.compile('href="(.+)"', re.IGNORECASE)
    res = re.search(p, url)
    if res:
        return res.group(1)
    else:
        return False


def get_server_description(url):
    p = re.compile('(https?\:\/\/[^\/]*)', re.IGNORECASE)
    res = re.search(p, url)
    base_url = res.group(1)
    url_icecast = base_url + '/status-json.xsl'
    url_shoutcast = base_url + '/stats?json=1'
    title_server = None
    try:
        request = urllib.request.Request(url_shoutcast)
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode("utf-8"))
        title_server = data['servertitle']
    except urllib.error.HTTPError:
        pass
    except http.client.BadStatusLine:
        pass
    except ValueError:
        return False

    if not title_server:
        try:
            request = urllib.request.Request(url_icecast)
            response = urllib.request.urlopen(request)
            data = json.loads(response.read().decode("utf-8"))
            title_server = data['icestats']['source'][0]['server_name'] + ' - ' + data['icestats']['source'][0]['server_description']

            if not title_server:
                title_server = url
        except urllib.error.URLError:
            title_server = url
        except urllib.error.HTTPError:
            return False
        except http.client.BadStatusLine:
            pass
    return title_server


def get_title(url):
    request = urllib.request.Request(url, headers={'Icy-MetaData': 1})
    try:

        response = urllib.request.urlopen(request)
        icy_metaint_header = int(response.headers['icy-metaint'])
        if icy_metaint_header is not None:
            response.read(icy_metaint_header)

            metadata_length = struct.unpack('B', response.read(1))[0] * 16  # length byte
            metadata = response.read(metadata_length).rstrip(b'\0')
            print(metadata)
            # extract title from the metadata
            m = re.search(br"StreamTitle='(.*)';", metadata)  # Regex incorrect, won't work for artist or title with an apostrophe
            if m:
                title = m.group(1)
                if title:
                    return title
    except (urllib.error.URLError, urllib.error.HTTPError):
        pass
    return 'Impossible to get the music title'




if __name__ == '__main__':
    playbot = MumbleRadioPlayer()
