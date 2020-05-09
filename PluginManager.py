import asyncio
import glob
import importlib.util
from os.path import dirname, basename

import discord

import BotPreferences
import ClientWrapper
from util.Ranks import Ranks


class PluginManager(object):
    # Container for all loaded plugins, dictionary: { filename: Plugin object }
    plugins = {}

    # Event handler containers, dictionary: { Event name: (plugin, minimum_rank) }
    commands = {}
    join = {}
    leave = {}
    typing = {}
    delete = {}
    message = {}
    loop = {}

    # References to various managers
    botPreferences = None
    client = None
    clientWrap = None

    def __init__(self, directory, client):
        """
        Initializes some fields for plugins to use
        :param directory: Plugin directory path, should always be "plugins/"
        :param client: discord.Client object
        """
        self.dir = directory
        self.botPreferences = BotPreferences.BotPreferences(self)
        self.client = client
        self.clientWrap = ClientWrapper.ClientWrapper(self)
        self.comlist = {}
        self.loop_running = True

    def load_plugins(self):
        """
        Load all plugin files in the folder (specified by self.directory) as modules
        and into a container dictionary list.
        :return:
        """
        # Clear containers
        self.plugins.clear()
        self.commands.clear()
        self.join.clear()
        self.leave.clear()
        self.typing.clear()
        self.delete.clear()
        self.loop.clear()

        # Find all python files in the plugin directory
        modules = glob.glob(dirname(__file__) + "/" + self.dir + "/**/*.py", recursive=True)

        # Iterate over each file, import them as a Python module and add them to the plugin list
        for f in modules:
            spec = importlib.util.spec_from_file_location(basename(f)[:-3], f)
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)
            self.plugins[basename(f)] = plugin.Plugin(self)
            print("Loaded plugin: " + basename(f))

    def register_events(self):
        """
        Request every loaded plugin to present the events they would like to bind to. See util.Events for
        event descriptions
        """
        for name, plugin in self.plugins.items():
            events = plugin.register_events()
            self.comlist[basename(name).lower()] = []
            self.bind_event("Command", self.commands, plugin, events, self.comlist, name)
            self.bind_event("Message", self.message, plugin, events, self.comlist, name)
            self.bind_event("UserJoin", self.join, plugin, events, self.comlist, name)
            self.bind_event("UserLeave", self.leave, plugin, events, self.comlist, name)
            self.bind_event("MessageDelete", self.delete, plugin, events, self.comlist, name)
            self.bind_event("Typing", self.typing, plugin, events, self.comlist, name)
            self.bind_event("Loop", self.loop, plugin, events, self.comlist, name)

    ###
    #   Handling events
    ###
    async def handle_command(self, message_object, command, args):
        try:
            target, rank = self.commands[command.lower()]

            if isinstance(message_object.channel, discord.abc.PrivateChannel):
                if rank is Ranks.Default:
                    allowed = True
                else:
                    allowed = False
            else:
                allowed = self.user_has_permission(message_object.guild.id, message_object.author, rank)
            if allowed:
                await target.handle_command(message_object, command.lower(), args)
            else:
                await self.client.delete_message(message_object)
                await self.client.send_message(message_object.author,
                                               "You don't have the required permissions to do that (Rank required: "
                                               + rank.name + ")")
        except KeyError:
            pass

    async def handle_message(self, message):
        if hasattr(message.author, 'nick') and message.author.nick != self.botPreferences.nickName:
            for obj in self.message:
                name, rank = self.message[obj]
                await name.handle_message(message)

    async def handle_typing(self, channel, user, when):
        try:
            for obj in self.typing:
                name, rank = self.typing[obj]
                if self.user_has_permission(channel.guild.id, user, rank):
                    await name.handle_typing(channel, user, when)
        except AttributeError:
            pass

    async def handle_message_delete(self, message):
        for obj in self.delete:
            name, rank = self.delete[obj]
            if self.user_has_permission(message.guild.id, message.author, rank):
                await name.handle_message_delete(message)

    async def handle_member_join(self, member):
        for obj in self.join:
            name, rank = self.join[obj]
            await name.handle_member_join(member)

    async def handle_member_leave(self, member):
        for obj in self.leave:
            name, rank = self.leave[obj]
            await name.handle_member_leave(member)

    async def handle_loop(self):
        while self.loop_running:
            for obj in self.loop:
                name, rank = self.loop[obj]
                await name.handle_loop()
            await asyncio.sleep(5)

    ###
    #   Utility methods
    ###
    @staticmethod
    def bind_event(name, container, plugin, events, com_list, com_name):
        for cmd in (cmd for cmd in events if type(cmd).__name__ == name):
            # Data is stored as a tuple (Plugin, Required Rank) with the event binding's name as key in a dictionary
            container[cmd.name] = (plugin, cmd.minimum_rank)
            if name == "Command":
                com_list[basename(com_name).lower()].append([cmd.name, cmd.desc])

    def user_has_permission(self, server_id, user, permission_level):
        """
        Checks whether one of the user's roles has the right level for the requested permission_level
        Roles are defined in config.ini and parsed in BotPreferences
        :param server_id: Discord server ID
        :param user: discord.Member object containing the user that triggered the event
        :param permission_level: Minimal permission level specified by the triggered event
        :return: True/False, whether used is allowed to trigger this event
        """
        highest_rank = Ranks.Default
        if not hasattr(user, 'server'):
            return True

        try:
            for rank in user.roles:
                if rank.name in self.botPreferences.servers[server_id].admin and highest_rank < Ranks.Admin:
                    highest_rank = Ranks.Admin
                elif rank.name in self.botPreferences.servers[server_id].mod and highest_rank < Ranks.Mod:
                    highest_rank = Ranks.Mod
                elif rank.name in self.botPreferences.servers[server_id].member and highest_rank < Ranks.Member:
                    highest_rank = Ranks.Member
            return highest_rank >= permission_level
        except:
            return False
