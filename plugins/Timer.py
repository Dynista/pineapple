from collections import defaultdict

import arrow

from util import Events


class Plugin(object):
    def __init__(self, pm):
        self.pm = pm
        self.db = defaultdict(arrow.utcnow)
        self.name = "Timer"

    @staticmethod
    def register_events():
        return [Events.Command("timer"), Events.Command("reset")]

    async def handle_command(self, message_object, command, args):
        if command == "timer":
            await self.timer(message_object)
        if command == "reset":
            await self.reset(message_object)

    async def reset(self, message_object):
        delta = self.db[message_object.channel].humanize(only_distance=True)
        self.db[message_object.channel] = arrow.utcnow()
        await self.pm.clientWrap.send_message(self.name, message_object.channel, "Timer reset after {}.".format(delta))
        await message_object.delete()

    async def timer(self, message_object):
        delta = self.db[message_object.channel].humanize(only_distance=True)
        await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                              "Timer has been running for {}.".format(delta))
        await message_object.delete()
