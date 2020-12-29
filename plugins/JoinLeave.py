import asyncio
import glob
import logging
import os
import random

import discord

from util import Events
from util.Ranks import Ranks
from AbstractPlugin import AbstractPlugin


class Plugin(AbstractPlugin):
    def __init__(self, pm):
        super().__init__(pm, "JoinLeave")

    @staticmethod
    def register_events():
        return [Events.UserJoin("welcome_msg"),
                Events.UserLeave("leave_msg"),
                Events.Command("togglewelcome", rank=Ranks.Mod, desc="Toggle the join/leave messages"),
                Events.Command("setdefaultchannel", rank=Ranks.Mod,
                               desc="Set the channel to use when posting join/leave messages"),
                Events.Command("setwelcomemessage", rank=Ranks.Mod,
                               desc="Set the message to display when a user joins the discord server. "
                                    "Insert {0} where you want to mention the new user"),
                Events.Command("ban", rank=Ranks.Mod),
                Events.Command("shadowban", rank=Ranks.Mod)]

    async def handle_member_join(self, member):
        enabled = await self.get_welcome_messages_config(member.guild.id)
        logging.info("User joined " + member.display_name)
        if enabled:
            files = glob.glob(os.getcwd() + "/images/" + "join" + "/" + '*.gif')
            files.extend(glob.glob(os.getcwd() + "/images/" + "join" + "/" + '*.png'))
            files.extend(glob.glob(os.getcwd() + "/images/" + "join" + "/" + '*.jpg'))
            file = random.choice(files)
            await asyncio.sleep(1)

            default_channel = self.pm.botPreferences.get_database_config_value(member.guild.id, "default_channel")
            if default_channel is not None:
                channel = discord.utils.find(lambda m: str(m.id) == default_channel, member.guild.channels)

                welcome_message = self.pm.botPreferences.get_database_config_value(member.guild.id, "welcome_message")
                if welcome_message is None:
                    welcome_message = "Welcome to the server {0}".format(member.mention)
                else:
                    welcome_message = welcome_message.format(member.mention)

                await channel.send(file=discord.File(file), content=welcome_message)

    async def handle_member_leave(self, member):
        channel = self.get_modlog_channel(member.guild)
        await self.pm.clientWrap.send_message(self.name, channel, member.display_name + " has left the server.")

    def get_modlog_channel(self, guild):
        channel = self.pm.botPreferences.get_database_config_value(guild.id, "modlog_channel")
        if channel is not None:
            return discord.utils.find(lambda m: str(m.id) == channel, guild.channels)

    async def handle_command(self, message_object, command, args):
        if command == "togglewelcome":
            await self.toggle_welcome(message_object)

        if command == "ban" and len(message_object.mentions) == 1:
            await self.fake_ban(message_object)

        if command == "shadowban" and len(message_object.mentions) == 1:
            await self.shadow_ban(message_object)

        if command == "setdefaultchannel":
            await self.set_default_channel(message_object)

        if command == "setwelcomemessage":
            await self.set_welcome_message(message_object, args[1])

    async def toggle_welcome(self, message_object):
        # Toggle welcome in config
        await message_object.delete()

        enabled = await self.get_welcome_messages_config(message_object.guild.id)
        self.pm.botPreferences.set_database_config_value(message_object.guild.id,
                                                         "welcome_messages",
                                                         not enabled)

        # Log action
        log_message = "Welcome/leave messages set to " \
                      + str(self.pm.botPreferences.get_database_config_value(message_object.guild.id,
                                                                             "welcome_messages")) \
                      + " by " + message_object.author.name + "#" + str(message_object.author.discriminator)
        logging.info(log_message)

        mod_channel = self.get_modlog_channel(message_object.guild)
        await self.pm.clientWrap.send_message(self.name, mod_channel, log_message)

    async def shadow_ban(self, message_object):
        # Log action
        log_message = "Shadow ban on " + message_object.mentions[
            0].display_name + " executed by " + message_object.author.name + "#" + str(
            message_object.author.discriminator)
        logging.info(log_message)

        mod_channel = self.get_modlog_channel(message_object.guild)
        await self.pm.clientWrap.send_message(self.name, mod_channel, log_message)

        # Execute ban silently
        cache_enabled = await self.get_welcome_messages_config(message_object.guild.id)
        self.pm.botPreferences.set_database_config_value(message_object.guild.id,
                                                         "welcome_messages",
                                                         False)

        await message_object.mentions[0].ban()
        await message_object.delete()
        await asyncio.sleep(5)

        self.pm.botPreferences.set_database_config_value(message_object.guild.id,
                                                         "welcome_messages",
                                                         cache_enabled)

    async def fake_ban(self, message_object):
        files = glob.glob(os.getcwd() + "/images/" + "leave" + "/" + '*.gif')
        files.extend(glob.glob(os.getcwd() + "/images/" + "leave" + "/" + '*.png'))
        files.extend(glob.glob(os.getcwd() + "/images/" + "leave" + "/" + '*.jpg'))
        file = random.choice(files)
        await asyncio.sleep(1)

        msg1 = await message_object.channel.send(file=discord.File(file),
                                                 content="Bye " + message_object.mentions[0].display_name)
        await asyncio.sleep(10)
        try:
            await message_object.delete()
        except:
            print("Failed to delete message")
        try:
            await msg1.delete()
        except:
            print("Failed to delete message")

    async def set_default_channel(self, message_object):
        self.pm.botPreferences.set_database_config_value(message_object.guild.id,
                                                         "default_channel",
                                                         message_object.channel.id)
        await message_object.channel.send("Set default channel to: #" + message_object.channel.name)

    async def set_welcome_message(self, message_object, text):
        self.pm.botPreferences.set_database_config_value(message_object.guild.id,
                                                         "welcome_message",
                                                         text)
        await message_object.channel.send("Set welcome message to: " + text)

    async def get_welcome_messages_config(self, server_id):
        db_enabled = self.pm.botPreferences.get_database_config_value(server_id, "welcome_messages")
        if db_enabled == "False":
            return False
        else:
            return True
