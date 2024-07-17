import asyncio
import json
import logging
import math
import os
import re
from contextlib import suppress
from dataclasses import dataclass
from functools import update_wrapper
from operator import attrgetter, itemgetter
from pprint import pformat
from random import choice, randrange
from typing import Any, Callable, List, Optional, Type, cast

import discord
import socketio
from aiofiles.tempfile import NamedTemporaryFile
from discord.app_commands.tree import ALL_GUILDS
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord.permissions import Permissions
from toolz.curried import compose_left
from yarl import URL

from nanachan.discord.application_commands import LegacyCommandContext, NanaGroup, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import AMQWebhook, Colour, Embed, EmbedField, MultiplexingContext
from nanachan.discord.views import AutoNavigatorView
from nanachan.extensions.waicolle import WaifuCollection
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import UpdateAMQSettingsBody, UpsertAMQAccountBody
from nanachan.settings import (
    AMQ_DEFAULT_SETTINGS,
    AMQ_PASSWORD,
    AMQ_ROOM,
    AMQ_ROOM_NAME,
    AMQ_ROOM_PASSWORD,
    AMQ_USERNAME,
    GLOBAL_COIN_MULTIPLIER,
    RequiresAMQ,
)
from nanachan.utils.misc import fake_method, get_session

PANIC_LEVEL = 1
logger = logging.getLogger(__name__)

LOGIN_URL = 'https://animemusicquiz.com/signIn'
SOCKET_TOKEN = 'https://animemusicquiz.com/socketToken'
WS_URL = 'https://socket.animemusicquiz.com:%s/socket.io/?token=%s'


##############################
#          AMQ Bot           #
##############################
@dataclass
class Player:
    username: str
    ingame: bool = True
    _ready: bool = False
    _host: bool = False
    team: Optional[int] = None

    @property
    def ready(self):
        return self._ready and self.ingame

    @ready.setter
    def ready(self, value):
        if not self.host:
            self._ready = value

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value):
        if value is not self._host:
            self._ready = value
            self._host = value


class AMQCommand:

    def __init__(self, category: str, event: str, func):
        self.func = func
        self.events_by_category = {category: [event]}
        update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        logger.log(PANIC_LEVEL, f'called {self.func.__name__}')
        return fake_method(self.instance, self.func)(*args, **kwargs)

    def add_event(self, category: str, event: str):
        self.events_by_category.setdefault(category, []).append(event)

    def set_instance(self, instance):
        self.instance = instance


class Roll(AMQCommand):

    @property
    def __doc__(self):  # type: ignore
        random_shows = 'konosuba', 'kaleid liner', 'index'
        return self.__func_doc__ % choice(random_shows)

    @__doc__.setter
    def __doc__(self, value: str):  # type:ignore
        self.__func_doc__ = value


def amq_command(category: str, event: str, cls: Type[AMQCommand] = AMQCommand):

    def decorator(func: Callable[..., Any]):
        if isinstance(func, cls):
            func.add_event(category, event)
        else:
            func = cls(category, event, func)

        return func

    return decorator


class Commands(dict):
    """ just a case-insensitive dict """

    def __setitem__(self, key, value):
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super().__getitem__(key.lower())

    def __contains__(self, key):
        return super().__contains__(key.lower())


class MetaAMQBot(type):
    """ adds decorated commands to the class """

    def __new__(cls, name, bases, attrs):
        _commands = {}

        for attr in attrs.values():
            if isinstance(attr, AMQCommand):
                for category, events in attr.events_by_category.items():
                    if category not in _commands:
                        _commands[category] = Commands()

                    for event in events:
                        _commands[category][event] = attr

        attrs['_commands'] = _commands

        return super().__new__(cls, name, bases, attrs)


class Players(dict):
    """ I hate it but I don't want to have to deal with that ever again """

    def __getitem__(self, i):
        return super().__getitem__(str(i))

    def __setitem__(self, i, v):
        super().__setitem__(str(i), v)
        logger.log(PANIC_LEVEL, str(self))

    def __contains__(self, i):
        return super().__contains__(str(i))

    def __delitem__(self, i):
        super().__delitem__(str(i))


class AMQBot(metaclass=MetaAMQBot):
    DISCONNECTED = 0
    LOGGING_IN = 1
    CONNECTING = 2
    CONNECTED = 3

    expr_answer = re.compile(r'^77+$')

    _commands: dict[str, dict[str, AMQCommand]]

    def __init__(self, bot: Bot):
        self.bot = bot
        self.loop = bot.loop

        assert AMQ_USERNAME is not None
        self.player = Player(AMQ_USERNAME)
        self.credits = 0
        self.friends = {}

        self.colors = {}
        self.color_event = asyncio.Event()

        self.players = Players()
        self.settings = Settings()

        self.connection_state = AMQBot.DISCONNECTED

        self.bot_settings = None

        self.connected_event = asyncio.Event()
        self.room_created = asyncio.Event()
        self.join_future = None
        self.default_settings: asyncio.Future[Settings] = self.loop.create_future()

        self.room_id: int | None = None
        self.password: str | None = AMQ_PASSWORD

        for event_commands in self._commands.values():
            for command in event_commands.values():
                command.set_instance(self)

    @property
    def username(self):
        return self.player.username

    @property
    def host(self):
        return self.player.host

    def settings_diff(self, new_settings):
        return {k: val for k, val in new_settings.items()
                if k not in self.settings or val != self.settings[k]}

    def update_settings(self, new_settings):
        diff = self.settings_diff(new_settings)
        self.settings.update(new_settings)
        logger.log(PANIC_LEVEL, f'new settings \n{dict(self.settings)}')
        return diff

    async def login(self):
        self.connection_state = AMQBot.LOGGING_IN
        req_data = {
            'username': self.username,
            'password': AMQ_PASSWORD
        }

        async with get_session().post(LOGIN_URL, json=req_data) as resp:
            if resp.status == 429:
                text = await resp.text()
                logger.warning(text)
                time = float(text.split(' ')[-2])
                await asyncio.sleep(time)
                return await self.login()

            resp.raise_for_status()
            return await resp.json()

    async def save(self, settings_name: str):
        if self.bot_settings is None:
            self.bot_settings = await load_settings()
        self.bot_settings[settings_name] = Settings(self.settings)
        await save(self.bot_settings)

    async def change_settings(self, settings_name: str):
        if not self.host:
            return self.settings

        if self.bot_settings is None:
            self.bot_settings = await load_settings()

        if settings_name not in self.bot_settings:
            logger.info(f'no settings called {settings_name} found')
            return

        logger.debug(f"changing current settings to '{settings_name}'")
        new_settings = self.bot_settings[settings_name].pre_load()
        new_settings_diff = self.settings_diff(new_settings)

        if new_settings_diff:
            await self.send_command('lobby', 'change game settings',
                                    **new_settings_diff)

        return new_settings

    async def send_command(self, command_type: str, command: str, **kwargs):
        request: dict[str, Any] = {
            'type': command_type,
            'command': command
        }

        if kwargs:
            request['data'] = kwargs.copy()

        logger.log(PANIC_LEVEL, f'sending: {request}')
        await self.sio.emit('command', request)

    async def create_room(self, room_settings):
        await self.send_command('roombrowser', 'host room', **room_settings)

    async def invite(self, name):
        logger.info('inviting ' + name)
        # wait for player's client to be ready (?)
        await asyncio.sleep(2)
        await self.send_command('social', 'invite to game', target=name)

    async def _join_room(self, room_id: int, password: Optional[str] = None):
        self.join_future = self.loop.create_future()
        await self.send_command('roombrowser', 'join game',
                                gameId=int(room_id), password=password)
        return await self.join_future

    async def _get_socket_info(self):
        async with get_session().get(SOCKET_TOKEN) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def connect(self, token: str, port: str):
        self.connection_state = AMQBot.CONNECTING
        logger.info("connecting to socketio")
        # if it fails here check that the request uses EIO=4
        # in the browser as the current python-socketio doesn't
        # support other values
        await self.sio.connect(WS_URL % (port, token))
        logger.info("waiting for connection to end")
        await self.sio.wait()
        return self.connection_state == AMQBot.CONNECTED

    async def launch(self):
        logger.debug('logging in')
        await self.login()
        socket_info = await self._get_socket_info()
        logger.log(PANIC_LEVEL, str(socket_info))

        self.sio = socketio.AsyncClient()
        self.sio.on('disconnect', self.disconnect)
        self.sio.on('command', self.on_command)
        self.sio.on('host room', self.on_host)

        while await self.connect(**socket_info):
            logger.debug('reconnecting')

    async def join_room(self, room_name: int, password: Optional[str] = None):
        await self.connected_event.wait()
        return await self._join_room(room_name, password)

    async def load(self, settings_name: str | None = None):
        await self.connected_event.wait()

        if settings_name is None:
            settings_name = AMQ_DEFAULT_SETTINGS

        if self.bot_settings is None:
            self.bot_settings = await load_settings()

        if settings_name not in self.bot_settings:
            return False

        if self.join_future is not None:
            await self.join_future

        if self.room_created.is_set():
            return await self.change_settings(settings_name)
        else:
            room_settings = self.bot_settings[settings_name]
            await self.create_room(room_settings)
            await self.room_created.wait()

        return self.settings

    ###################
    # SocketIO events #
    ###################

    async def on_command(self, msg):
        logger.debug(msg)
        handlers = self._commands['amq_events']
        if msg['command'] in handlers:
            if 'data' in msg:
                await handlers[msg['command']](msg['data'])
            else:
                await handlers[msg['command']](msg)

    @amq_command('amq_events', 'force logoff')
    @amq_command('amq_events', 'game closed')
    def disconnect(self, *_):
        logger.debug('disconnecting')
        self.connection_state = AMQBot.DISCONNECTED
        self.loop.create_task(self.sio.disconnect())

    @amq_command('amq_events', 'Host Game')
    async def on_host(self, data):
        logger.info('room created')
        self.room_id = data['gameId']
        self.player.host = True
        self.players['0'] = self.player

        self.update_settings(data['settings'])

        self.room_created.set()

        for friend, online in self.friends.items():
            if online:
                await self.invite(friend)

    ##################
    #   AMQ Events   #
    ##################

    @amq_command('amq_events', 'login complete')
    async def on_login_complete(self, data):
        self.connection_state = AMQBot.CONNECTED

        if logger.getEffectiveLevel() == PANIC_LEVEL:
            logger.log(PANIC_LEVEL, pformat(data))

        for friend in data['friends']:
            self.friends[friend['name']] = friend['online']

        self.credits = data['credits']

        if data['canReconnectGame']:
            self.join_future = self.loop.create_future()
            await self.send_command('roombrowser', 'rejoin game')
        else:
            await self.send_command('roombrowser', 'get rooms')

        self.connected_event.set()

    @amq_command('amq_events', 'New Rooms')
    async def on_new_rooms(self, data):
        if self.default_settings.done():
            return

        if len(data):
            settings = Settings(data[0]["settings"])
            settings.pre_load()
            self.default_settings.set_result(settings)

    async def send_request(self, name):
        if name not in self.friends:
            await self.send_command('social', 'friend request', target=name)

    @amq_command('amq_events', 'new friend')
    async def on_new_friend(self, data):
        self.friends[data['name']] = data['online']

    @amq_command('amq_events', 'friend removed')
    async def on_friend_removed(self, data):
        del self.friends[data['name']]

    @amq_command('amq_events', 'friend state change')
    async def on_friend_state_changed(self, data):
        self.friends[data['name']] = data['online']
        if data['online']:
            await asyncio.sleep(1)
            await self.invite(data['name'])

    @amq_command('amq_events', 'New Player')
    @amq_command('amq_events', 'Spectator Change To Player')
    async def on_new_player(self, data):
        player = Player(data['name'])
        if player != self.username:
            await self.send_request(player.username)

        self.players[data['gamePlayerId']] = player

    @amq_command('amq_events', 'New Spectator')
    async def on_new_spectator(self, data):
        name = data['name']
        await self.send_request(name)
        if data.get('gamePlayerId') in self.players:
            self.players[name].ingame = False

    @amq_command('amq_events', 'Join Game')
    async def on_join_game(self, data):
        try:
            self.settings = Settings(data['settings'])
            self.room_created.set()
            hostname = data['hostName']
            for p in data['players']:
                slot = p['gamePlayerId']
                player = Player(p['name'],
                                _ready=p['ready'],
                                _host=p['name'] == hostname,
                                team=p['teamNumber'])
                if player.username == self.username:
                    self.players[slot] = self.player
                else:
                    self.players[slot] = player

            message = f"Successfully joined {self.settings['roomName']}"
            self.room_id = data['gameId']

        except KeyError:
            message = 'Could not join the room'

        assert self.join_future is not None
        self.join_future.set_result(message)

    @amq_command('amq_events', 'join team')
    async def on_join_team(self, data):
        player = self.players[data['gamePlayerId']]
        player.team = data['newTeam']

    @amq_command('amq_events', 'Host Promotion')
    async def on_host_promotion(self, data):
        new_host = data['newHost']
        for player in self.players.values():
            player.host = player.username == new_host

        self.player.host = self.username == new_host

    @amq_command('amq_events', 'Room Settings Changed')
    async def on_room_settings_changed(self, data):
        for player in self.players.values():
            player.ready = False

        self.update_settings(data)

    @amq_command('amq_events', 'Quiz no songs')
    @amq_command('amq_events', 'quiz ready')
    async def on_quiz_ready(self, data):
        for i in self.players:
            self.players[i].ready = False

        if 'videoInfo' in data:
            await self.set_video_ready(data['videoInfo']['id'])

    @amq_command('amq_events', 'Change to Player')
    async def on_change_to_player(self, data):
        await self.send_command('lobby', 'set ready', ready=True)

    async def start_game(self):
        if not self.host:
            return

        await self.send_command('lobby', 'start game')

    async def _start(self):
        logger.log(PANIC_LEVEL, str(self.players))

        other_players = any(p.ingame for p in self.players.values()
                            if p.username != self.username)

        if other_players and all((p.ready or not p.ingame) for p in self.players.values()):
            await self.start_game()

    @amq_command('amq_events', 'Player Ready Change')
    async def on_ready(self, data):
        self.players[data['gamePlayerId']].ready = data['ready']
        await self._start()

    @amq_command('amq_events', 'Player Left')
    async def on_player_left(self, data):
        if data['player']['name'] == self.username:
            return

        self.players[data['player']['gamePlayerId']].ingame = False

        if 'newHost' in data:
            await self.on_host_promotion(data)

        await self._start()

    @amq_command('amq_events', 'Player Changed To Spectator')
    async def on_change_to_spectator(self, data):
        self.players[data['playerDescription']['gamePlayerId']].ingame = False
        await self._start()

    @amq_command('amq_events', 'quiz xp credit gain')
    async def on_credit(self, data):
        self.credits = data['credit']

    async def skip(self, *_):
        if self.host:
            await self.send_command('quiz', 'skip vote', skipVote=True)

    async def set_video_ready(self, song_id):
        if self.host:
            await self.send_command('quiz', 'video ready', songId=song_id)

    @amq_command('amq_events', 'answer results')
    async def update_data(self, data):
        await self.skip()
        amq_cog = AMQ.get_cog(self.bot)
        assert amq_cog is not None
        await amq_cog.on_answer_results(data)

    @amq_command('amq_events', 'play next song')
    async def on_next_song(self, data):
        if not self.host:
            return

        await self.skip()
        amq_cog = AMQ.get_cog(self.bot)
        assert amq_cog is not None
        await amq_cog.on_play_next_song(data)

    @amq_command('amq_events', 'quiz next video info')
    async def on_next_video_info(self, data):
        if 'videoInfo' in data:
            await self.set_video_ready(data['videoInfo']['id'])

        amq_cog = AMQ.get_cog(self.bot)
        assert amq_cog is not None
        await amq_cog.on_quiz_next_video_info(data)

    @amq_command('amq_events', 'battle royal ready')
    async def on_battle_royale_ready(self, data):
        size = data['mapSize']

        # jump to a random tile
        await self.send_command('quiz', 'tile selected',
                                x=randrange(size), y=randrange(size))

    @amq_command('amq_events', 'game chat update')
    async def on_chat_update(self, data):
        for msg in data['messages']:
            await self.on_message(msg)

    @amq_command('amq_events', 'Game Chat Message')
    async def on_message(self, data, private=False):
        if data['sender'] == self.username:
            return

        if private:
            sender = data['sender']
            if sender not in self.friends:
                await self.send_message("yeah, fuck you", sender)
                return

        else:
            sender = None

        words = [w for w in data['message'].split(' ') if w]
        command = words[0].lower()
        if AMQBot.expr_answer.search(command):
            command = '777'

        _commands = self._commands['bot_command']
        if command in _commands:
            message = await _commands[command](words, sender)
            if message:
                await self.send_message(message, sender)
        else:
            amq_cog = AMQ.get_cog(self.bot)
            assert amq_cog is not None
            await amq_cog.on_amq_message(data, private)

    @amq_command('amq_events', 'chat message')
    async def on_private_message(self, data):
        await self.on_message(data, True)

    @amq_command('amq_events', 'Game starting')
    async def on_game_starting(self, data):
        amq_cog = AMQ.get_cog(self.bot)
        assert amq_cog is not None
        await amq_cog.on_game_starting(data)

    @amq_command('amq_events', 'player answers')
    async def on_player_answers(self, data):
        amq_cog = AMQ.get_cog(self.bot)
        assert amq_cog is not None
        await amq_cog.on_player_answers(data)

    @amq_command('amq_events', 'quiz over')
    async def on_quiz_over(self, data):
        amq_cog = AMQ.get_cog(self.bot)
        assert amq_cog is not None
        await amq_cog.on_quiz_over(data)

    ##################
    #  Bot commands  #
    ##################

    @amq_command('bot_command', '7save')
    async def save_settings(self, words: List[str], sender: str):
        """ save the current settings """
        if len(words) < 2:
            return 'usage: 7save [settings_name]'

        if self.bot_settings is None:
            self.bot_settings = await load_settings()

        settings_name = words[1]
        if settings_name in self.bot_settings:
            return "I'm sorry Dave, I'm afraid I can't do that"

        await self.save(settings_name)
        return "saved the current settings as '%s'" % settings_name

    async def send_answer(self, answer: str):
        await self.send_command('quiz', 'quiz answer',
                                answer=answer, isPlaying=True, volumeAtMax=False)

    @amq_command('bot_command', '7invite')
    async def invite_players(self, words: List[str], _=None):
        tasks = (self.invite(name) for name in words[1:])
        await asyncio.gather(*tasks)

    @amq_command('bot_command', '777')
    async def answer(self, words: List[str], _):
        """ answer in my stead """
        answer = ' '.join(words[1:]).strip()
        await self.send_answer(answer)

    async def send_message(self, message, sender: str | None = None):
        if sender is None:
            teamMessage = False  # maybe I'll look into it later
            await self.send_command('lobby',
                                    'game chat message',
                                    msg=message,
                                    teamMessage=teamMessage)
        else:
            await self.send_command('social', 'chat message',
                                    target=sender, message=message)

    @amq_command('bot_command', '7kudeta')
    async def kudeta(self, words, _):
        if len(words) != 2:
            await asyncio.gather(
                self.send_answer('Little Witch Academia'),
                self.send_message('KUDETA'),
            )
            return

        await self.send_command('lobby', 'promote host', playerName=words[1])

    @amq_command('bot_command', '7projection')
    async def projection(self, *_):
        """ fallait venir en projection """
        await self.send_message('Fallait venir en projection !')

    @amq_command('bot_command', '7lobby')
    async def back_to_lobby(self, *_):
        """ return to lobby """
        await self.send_command('quiz', 'start return lobby vote')

    @amq_command('bot_command', '7credits')
    async def show_credits(self, _, sender: str):
        """ show my credits count """
        return str(self.credits)

    @amq_command('bot_command', '7roll', cls=Roll)
    async def roll(self, words: List[str], sender: str):
        """ a virtual dice for %s (and others) """
        try:
            n = int(words[1])
        except (ValueError, IndexError):
            n = 2

        return str(randrange(n) + 1)

    @amq_command('bot_command', '7help')
    async def help(self, _, sender: str):
        _commands = self._commands['bot_command']
        for command, callback in sorted(_commands.items(), key=itemgetter(0)):
            doc = callback.__doc__
            if doc:
                message = f'{command} - {doc.strip()}'
                await self.send_message(message, sender)

    @amq_command('bot_command', '7ings')
    async def set_settings(self, words: List[str], sender: str):
        """ change the settings """
        if self.bot_settings is None:
            self.bot_settings = await load_settings()

        if len(words) == 1:
            return ' | '.join(self.bot_settings)

        name = words[1]

        await self.change_settings(name)

    @amq_command('bot_command', '7spectate')
    async def spectate(self, _, sender: str):
        """ change to spectator """
        if not self.players:
            return "I'm sorry Dave, I'm afraid I can't do that"

        await self.send_command('lobby', 'change player to spectator',
                                playerName=self.username)

    @amq_command('bot_command', '7join')
    async def join(self, *_):
        """ join the game again """
        await self.send_command('lobby', 'change to player')

    def get_embed(self, colour: Colour | None = None):
        if colour is None:
            colour = Colour.default()

        invite_url = URL("https://animemusicquiz.com/invite")
        if self.room_id is not None:
            invite_url = invite_url.with_query(
                roomId=self.room_id, password=self.settings['password']
            )

        embed = Embed(title=self.settings['roomName'],
                      colour=colour,
                      url=str(invite_url))

        embed.set_author(
            name='AMQ',
            url='https://animemusicquiz.com',
            icon_url='http://animemusicquiz.com/favicon-32x32.png'
        )

        if self.settings.gamemode_extras:
            gamemode = f"{self.settings.gamemode} ({', '.join(self.settings.gamemode_extras)})"
        else:
            gamemode = self.settings.gamemode

        embed.add_field(
            name='Game mode',
            value=gamemode,
            inline=False
        )
        embed.add_field(
            name=self.settings.songs,
            value=', '.join(self.settings.songs_extras),
            inline=False
        )

        return embed


####################
#     Settings     #
####################

class Settings(dict):

    # selection modes
    selection_modes = {
        1: "AMQ Roulette",
        2: "Looting"
    }
    # scoring
    scoring = {
        1: "Count",
        2: "Speed",
        3: "Lives"
    }

    def pre_load(self):
        self['roomName'] = AMQ_ROOM_NAME
        self['password'] = AMQ_ROOM_PASSWORD
        self['privateRoom'] = True
        return self

    @property
    def gamemode(self):
        return Settings.selection_modes.get(self['showSelection'], "Unknown")

    @property
    def gamemode_extras(self):
        extras = []

        if Settings.scoring.get(self['scoreType']) == "Lives":
            lives = self['lives']
            if lives > 1:
                extras.append(f"{self['lives']} lives")
            else:
                extras.append('Sudden Death')

        if self.gamemode == "Looting":
            loots = self['inventorySize']['standardValue']
            extras.append(f'{loots} loots')

        return extras

    @property
    def songs(self):
        return f"{self['numberOfSongs']} songs"

    @property
    def songs_extras(self):
        song_settings = self['songType']
        song_types = [
            t for t, v in song_settings['standardValue'].items() if v]
        song_type_msgs = []
        for song_type in song_types:
            if song_settings.get('advancedOn', False):
                nb_type = song_settings['advancedValue'][song_type]
                song_type_msgs.append(f'{nb_type} {song_type}')
            else:
                song_type_msgs.append(song_type)

        return song_type_msgs

    def __str__(self):
        if self.gamemode_extras:
            gm = f"{self.gamemode} ({', '.join(self.gamemode_extras)})"
        else:
            gm = f'{self.gamemode}'

        if self.songs_extras:
            songs = f"{self.songs} ({', '.join(self.songs_extras)})"
        else:
            songs = f'{self.songs}'

        parts = [gm, songs]
        return '\n'.join(parts)


SETTINGS_KEY = 'settings'


async def load_settings():
    resp = await get_nanapi().amq.amq_get_settings()
    if not success(resp):
        raise RuntimeError(resp.result)
    settings = resp.result
    return {s.key: Settings(json.loads(s.value)) for s in settings}


async def save(settings: dict):
    resp = await get_nanapi().amq.amq_update_settings(
        UpdateAMQSettingsBody(settings=json.dumps(settings)))
    if not success(resp):
        raise RuntimeError(resp.result)


#############################
#     Discord extension     #
#############################

AMQ_THEME_TYPE = {
    1: 'Opening',
    2: 'Ending',
    3: 'Insert'
}

AMQ_FFMPEG_SPEED_FILTERS = {
    1: '-c copy',
    1.5: '-filter:a "atempo=1.5"',
    2: '-filter:a "atempo=2.0"',
    4: '-filter:a "atempo=2.0,atempo=2.0"'
}


@RequiresAMQ
class AMQ(Cog):
    """ Play AMQ with {bot_name} """
    emoji = '🎵'

    amq_group = NanaGroup(name="amq", guild_only=True)
    amq_admin_group = NanaGroup(name="amq",
                                default_permissions=Permissions(
                                    administrator=True),
                                guild_ids=[ALL_GUILDS])

    def __init__(self, bot: Bot):
        self.bot = bot
        self.amq: Optional[AMQBot] = None
        self.reset_tracker()

    def reset_tracker(self):
        self.round_infos = None
        self.answer_results = None
        self.player_answers = None
        self.songs = asyncio.Queue()

        self.song_embed = None

    def start_session(self):
        if self.amq is None or self.amq.connection_state == AMQBot.DISCONNECTED:
            self.amq = AMQBot(self.bot)
            self.bot.loop.create_task(self.amq.launch())

    @Cog.listener()
    async def on_ready(self):
        from .profiles import Profiles
        profiles_cog = Profiles.get_cog(self.bot)
        if profiles_cog is not None:
            profiles_cog.registrars['Anime Music Quiz'] = self.register

    @amq_group.command()
    @legacy_command()
    async def create(self, ctx):
        """Create an AMQ room with the default settings"""
        await self._load(ctx)

    @amq_group.command()
    @legacy_command()
    async def load(self, ctx, settings_name: str | None = None):
        """Load settings"""
        if settings_name is None:
            all_settings = await load_settings()
            if all_settings:
                embed = Embed(title='Saved settings', colour=Colour.default())

                for name, settings in all_settings.items():
                    embed.add_field(name=name,
                                    value=str(settings),
                                    inline=False)

                await ctx.send(embed=embed)
            else:
                await ctx.send('no saved settings found')
        else:
            await self._load(ctx, settings_name)

    async def _load(self, ctx, settings_name: Optional[str] = None):
        self.start_session()
        assert self.amq is not None
        if settings_name is None:
            settings_name = AMQ_DEFAULT_SETTINGS

        settings = await self.amq.load(settings_name)
        if not settings:
            raise commands.CommandError(f"unknown settings '{settings_name}'")

        embed = self.amq.get_embed(colour=Colour.default())
        await ctx.send(embed=embed)

    @amq_group.command()
    @legacy_command()
    async def save(self, ctx, settings_name: str):
        """Save the current settings of the room"""
        if self.amq is None:
            await ctx.send("I can't save the settings of the room if I'm not in a room")
            return

        await self.amq.save(settings_name)
        message = f'saved the current settings as {settings_name}\n'
        embed = self.amq.get_embed(colour=Colour.default())
        await ctx.send(message, embed=embed)

    @amq_group.command()
    @legacy_command()
    async def invite(self, ctx, amq_player: str):
        """Invite players to the room"""
        amq_players = [amq_player]

        if self.amq is None:
            await ctx.send("I can't invite players if I'm not in a room >.>")
            return

        await self.amq.invite_players(amq_players)
        if len(amq_players) == 1:
            await ctx.send(f"invited player {amq_players[0]}")
        else:
            await ctx.send(f"invited players {', '.join(amq_players)}")

    @amq_group.command()
    @legacy_command()
    async def join(self, ctx, room_id: int, password: str | None = None):
        """Join a room"""
        self.start_session()
        assert self.amq is not None
        message = await self.amq.join_room(room_id, password)
        await ctx.send(message, embed=self.amq.get_embed())

    @amq_group.command(description="give your answer to nanachan")
    @legacy_command(ephemeral=True)
    async def answer(self, ctx, answer: str):
        if self.amq is None:
            await ctx.send("Not connected to amq")
            return

        await self.amq.answer(["", answer], None)
        await ctx.send(self.bot.get_emoji_str("FubukiGO"))

    @amq_admin_group.command()
    @legacy_command()
    @has_permissions(administrator=True)
    async def disconnect(self, ctx):
        """Disconnect the bot from AMQ"""
        if self.amq is not None:
            self.amq.disconnect()
        await ctx.send(self.bot.get_emoji_str("FubukiGO"))

    ############
    # Tracking #
    ############

    async def register(self, interaction: discord.Interaction):
        """Register or change a member AMQ account"""
        def check(ctx: MultiplexingContext) -> bool:
            return ctx.author == interaction.user

        await interaction.response.edit_message(view=None)

        await interaction.followup.send(
            content=f"{interaction.user.mention}\nWhat is your AMQ username?")

        resp = await MultiplexingContext.set_will_delete(check=check)
        answer = resp.message
        username = answer.content

        resp1 = await get_nanapi().amq.amq_upsert_account(
            interaction.user.id,
            UpsertAMQAccountBody(discord_username=str(interaction.user),
                                 username=username))
        if not success(resp1):
            raise RuntimeError(resp1.result)
        await interaction.followup.send(
            content=self.bot.get_emoji_str('FubukiGO'))

    @amq_group.command()
    @legacy_command()
    async def players(self, ctx: LegacyCommandContext):
        """List AMQ registered players"""
        resp = await get_nanapi().amq.amq_get_accounts()
        if not success(resp):
            raise RuntimeError(resp.result)
        players = resp.result
        fields = [
            EmbedField(str(self.bot.get_user(
                row.user.discord_id)), row.username)
            for row in players
        ]
        fields.sort(key=compose_left(attrgetter('name'), str.casefold))
        assert ctx.guild is not None
        guild_icon = ctx.guild.icon.url if ctx.guild.icon is not None else None
        await AutoNavigatorView.create(
            self.bot,
            ctx.reply,
            title='AMQ players',
            fields=fields,
            footer_text=f"{len(fields)} players",
            author_name=str(ctx.guild),
            author_icon_url=guild_icon)

    async def on_game_starting(self, data):
        amq_room = self.bot.get_text_channel(AMQ_ROOM)

        assert self.amq is not None
        embed = Embed(title='Game Tracker', description=f"{self.amq.settings}")
        embed.set_author(name='AMQ',
                         url='https://animemusicquiz.com',
                         icon_url='http://animemusicquiz.com/favicon-32x32.png')

        if amq_room is not None:
            await amq_room.send(embed=embed)

    async def on_play_next_song(self, data):
        self.round_infos = data
        task = await self.songs.get()
        file = await task
        amq_room = self.bot.get_text_channel(AMQ_ROOM)
        if amq_room is not None:
            self.song_embed = await amq_room.send(
                f"**Round {self.round_infos['songNumber']} song**", file=file)

    async def on_quiz_next_video_info(self, data):
        coro = self._get_amq_extract(data)
        task = self.bot.loop.create_task(coro)
        self.songs.put_nowait(task)

    async def on_player_answers(self, data):
        self.player_answers = data
        if self.song_embed is not None:
            await self.song_embed.delete()
            self.song_embed = None

    async def on_answer_results(self, data):
        self.answer_results = data
        embed = await self._round_embed(data, self.player_answers)
        amq_room = self.bot.get_text_channel(AMQ_ROOM)
        if amq_room is not None:
            await amq_room.send(embed=embed)

    async def on_quiz_over(self, data):
        assert self.amq is not None
        nbteams = len(
            set(p.team for p in self.amq.players.values() if
                p.team is not None and p.username != self.amq.player.username))

        if self.answer_results is None:
            return

        base = nbteams if nbteams > 0 else len(self.answer_results['players'])
        multiplier = math.ceil(base / 2 - 1) * GLOBAL_COIN_MULTIPLIER

        async with asyncio.TaskGroup() as tg:

            if multiplier > 0:
                waifu_cog = self.bot.get_cog(WaifuCollection.__cog_name__)
                waifu_cog = cast(WaifuCollection, waifu_cog)

                for player in self.answer_results['players']:
                    player_id = player['gamePlayerId']

                    with suppress(KeyError):
                        username = self.amq.players[player_id].username
                        user = await self._amq_to_discord(username)

                        score = player.get('correctGuesses', player['score'])

                        if user is not None:
                            tg.create_task(
                                waifu_cog.reward_coins(user, multiplier * score,
                                                       'AMQ', AMQ_ROOM))

            amq_room = self.bot.get_text_channel(AMQ_ROOM)
            embed = await self._game_embed(self.answer_results)
            if amq_room is not None:
                await amq_room.send(embed=embed)

            self.reset_tracker()

    ########
    # Hook #
    ########

    async def on_amq_message(self, data, private=False):
        amq_room = self.bot.get_text_channel(AMQ_ROOM)
        assert amq_room is not None
        webhook = await self.bot.get_webhook(amq_room)

        d_user = await self._amq_to_discord(data['sender'])
        content = self.bot.get_emojied_str(data['message'])

        if d_user:
            webhook = AMQWebhook(webhook, private=private, user=d_user)
            msg = await webhook.send(content=content)
            await self.bot.on_message(msg)
        else:
            username = data['sender']
            webhook = AMQWebhook(webhook, private=private,
                                 display_name=username)
            await webhook.send(content=content)

    @Cog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        if self.amq is None:
            return

        if ctx.author.bot:
            return

        if ctx.command is not None:
            return

        if ctx.channel == self.bot.get_channel(AMQ_ROOM):
            if ctx.amqed:
                return

            content = ctx.message.clean_content

            if not content:
                return

            content = f"[{ctx.author}] " + content
            if len(content) > 150:
                content = content[:147] + '...'
            await self.amq.send_message(content)

    #########
    # Utils #
    #########

    async def _amq_to_discord(self, username: str) -> discord.User | None:
        resp = await get_nanapi().amq.amq_get_accounts(username=username)
        if not success(resp):
            raise RuntimeError(resp.result)
        players = resp.result
        if len(players) == 0:
            return None
        else:
            return self.bot.get_user(players[0].user.discord_id)

    async def _round_embed(self, results, answers) -> Embed:
        answers_dict = {
            a['gamePlayerId']: a['answer'] for a in answers['answers']
        }

        desc = (
            f"**{results['songInfo']['songName']}** — {results['songInfo']['artist']}\n"
            f"*{results['songInfo']['animeNames']['romaji']}*\n"
            f"{AMQ_THEME_TYPE[results['songInfo']['type']]}")

        if (nb := results['songInfo']['typeNumber']) > 0:
            desc += f" {nb}"

        assert self.round_infos is not None
        embed = Embed(title=f"Round {self.round_infos['songNumber']}",
                      description=desc)
        embed.set_author(name='AMQ',
                         url='https://animemusicquiz.com',
                         icon_url='http://animemusicquiz.com/favicon-32x32.png')

        for player in sorted(results['players'], key=itemgetter('position'))[:25]:
            player_id = player['gamePlayerId']

            with suppress(KeyError):
                assert self.amq is not None
                username = self.amq.players[player_id].username
                d_user = await self._amq_to_discord(username)

                value = self._player_stats(player)

                emoji = 'FubukiGO' if player['correct'] else 'FubukiStop'
                value += f"\n{self.bot.get_emoji_str(emoji)}"

                if answers_dict[player_id]:
                    value += f" *{answers_dict[player_id]}*"

                embed.add_field(name=str(d_user or username), value=value)

                embed.set_footer(
                    text=' • '.join(str(self.amq.settings).split('\n')))

        return embed

    async def _game_embed(self, results) -> Embed:
        embed = Embed(title='Game result')

        embed.set_author(name='AMQ',
                         url='https://animemusicquiz.com',
                         icon_url='http://animemusicquiz.com/favicon-32x32.png')

        for player in sorted(results['players'], key=itemgetter('position'))[:25]:
            player_id = player['gamePlayerId']

            with suppress(KeyError):
                assert self.amq is not None
                username = self.amq.players[player_id].username
                d_user = await self._amq_to_discord(username)

                value = self._player_stats(player)

                if (player.get('correctGuesses', None) or player['score']) == 0:
                    value = f"{self.bot.get_emoji_str('saladedefruits')} " + value

                if player['position'] == 1:
                    value = f"{self.bot.get_emoji_str('chousen')} " + value

                embed.add_field(name=str(d_user or username), value=value)

                embed.set_footer(
                    text=' • '.join(str(self.amq.settings).split('\n')))

        return embed

    def _player_stats(self, player) -> str:
        stats = f"**#{player['position']}** @ "

        if 'correctGuesses' in player:
            stats += (
                f"{player['score']} ❤️ • "
                f"{player['correctGuesses']} {self.bot.get_emoji_str('FubukiGO')}"
            )
        else:
            stats += f"{player['score']} {self.bot.get_emoji_str('FubukiGO')}"

        return stats

    async def _get_amq_extract(self, data) -> discord.File:
        url = data['videoInfo']['videoMap']['catbox']['0']

        async with NamedTemporaryFile() as f:
            headers = {
                'Referer': "https://animemusicquiz.com/"
            }
            async with get_session().get(url, headers=headers) as resp:
                resp.raise_for_status()
                filename = os.path.basename(resp.url.path)
                while buf := await resp.content.read(1024**2):
                    await f.write(buf)

            ffprobe_cmd = (
                f"ffprobe -v error -show_entries format=duration "
                f"-of default=noprint_wrappers=1:nokey=1 {f.name}")

            proc = await asyncio.create_subprocess_shell(
                ffprobe_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            stdout, stderr = await proc.communicate()
            if stderr:
                logger.error(stderr.decode())
            duration = float(stdout.decode())

            startPercent = data['startPont'] / 100
            bufferLength = (data['playLength'] + 13) * data['playbackSpeed']

            startFromDuration = duration - bufferLength
            if startFromDuration < 0:
                startFromDuration = 0

            startPoint = int(startFromDuration * startPercent)

            async with NamedTemporaryFile() as f_out:
                ffmpeg_cmd = (
                    f"ffmpeg -y -i {f.name} "
                    f"-ss {startPoint} "
                    f"-t {data['playLength']} "
                    f"{AMQ_FFMPEG_SPEED_FILTERS[data['playbackSpeed']]} "
                    f"-f mp3 -c:a libmp3lame {f_out.name}")

                async with NamedTemporaryFile() as err_out:
                    with open(err_out.name) as sync_out:
                        proc = await asyncio.create_subprocess_shell(ffmpeg_cmd,
                                                                     stdout=sync_out,
                                                                     stderr=sync_out)
                    await proc.wait()
                    if proc.returncode != 0:
                        await err_out.seek(0)
                        output = await err_out.read()
                        raise RuntimeError(output)

                filepath = cast(str, f_out.name)
                return discord.File(filepath, filename)


async def setup(bot: Bot):
    await bot.add_cog(AMQ(bot))
