import logging
import traceback

import discord

from PluginManager import PluginManager

logging.basicConfig(filename='pineapple.log', filemode='a', level=logging.INFO,
                    format=('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))

logger = logging.getLogger('discord')
logger.setLevel(logging.NOTSET)

logging.info("Starting Pineapple")
logging.info("Starting Discord Client")
# Creates a discord client, which we will use to connect and interact with the server.
# All methods with @client.event annotations are event handlers for this client.
client = discord.Client()

logging.info("Loading plugins")
# Loads and initializes the plugin manager for the bot
pm = PluginManager("plugins", "cache", client)
pm.load_plugins()
pm.register_events()
logging.info("Plugins loaded and registered")


@client.event
async def on_ready():
    """
    Event handler, fires when the bot has connected and is logged in
    """
    logging.info('Logged in as ' + client.user.name + " (" + str(client.user.id) + ")")

    # Change nickname to nickname in configuration
    for instance in client.guilds:
        await instance.me.edit(nick=pm.botPreferences.nickName)

        # Load rank bindings
        pm.botPreferences.bind_roles(instance.id)

    game = discord.Game('Use ' + pm.botPreferences.commandPrefix + 'help for help')
    await client.change_presence(status=discord.Status.online, activity=game)
    await pm.handle_loop()


@client.event
async def on_message(message):
    """
    Event handler, fires when a message is received in the server.
    :param message: discord.Message object containing the received message
    """
    try:
        if message.content.startswith(pm.botPreferences.commandPrefix) and client.user.id != message.author.id:
            # Send the received message off to the Plugin Manager to handle the command
            words = message.content.partition(' ')
            await pm.handle_command(message, words[0][len(pm.botPreferences.commandPrefix):], words[1:])
        elif message.guild is not None and client.user.id != message.author.id:
            await pm.handle_message(message)
    except Exception as e:
        await message.channel.send("Error: " + str(e))
        if pm.botPreferences.get_config_value("client", "debug") == "1":
            traceback.print_exc()


@client.event
async def on_typing(channel, user, when):
    """
    Event handler, fires when a user is typing in a channel
    :param channel: discord.Channel object containing channel information
    :param user: discord.Member object containing the user information
    :param when: datetime timestamp
    """
    try:
        await pm.handle_typing(channel, user, when)
    except Exception as e:
        await channel.send("Error: " + str(e))
        if pm.botPreferences.get_config_value("client", "debug") == "1":
            traceback.print_exc()


@client.event
async def on_message_delete(message):
    """
    Event handler, fires when a message is deleted
    :param message: discord.Message object containing the deleted message
    """
    try:
        if message.author.name != "PluginBot":
            await pm.handle_message_delete(message)
    except Exception as e:
        await message.channel.send("Error: " + str(e))
        if pm.botPreferences.get_config_value("client", "debug") == "1":
            traceback.print_exc()


@client.event
async def on_member_join(member):
    await pm.handle_member_join(member)


@client.event
async def on_member_remove(member):
    await pm.handle_member_leave(member)


@client.event
async def on_server_join(server):
    for instance in pm.client.guilds:
        pm.botPreferences.bind_roles(instance.id)


# Run the client and login with the bot token (yes, this needs to be down here)
client.run(pm.botPreferences.token)
