import datetime

from util import Events
from AbstractPlugin import AbstractPlugin


class Plugin(AbstractPlugin):
    def __init__(self, pm):
        super().__init__(pm, "Ping")

    @staticmethod
    def register_events():
        return [Events.Command("ping", desc="Ping the bot"), Events.Command("pong", desc="Pong the bot")]

    async def handle_command(self, message_object, command, args):
        if command == "ping":
            await self.ping(message_object, "Pong")
        elif command == "pong":
            await self.ping(message_object, "Ping")

    async def ping(self, message_object, reply):
        speed = datetime.datetime.now() - message_object.created_at
        await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                              reply + " " + str(round(speed.microseconds / 1000)) + "ms")
