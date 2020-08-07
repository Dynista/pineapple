import random

from util import Events
from AbstractPlugin import AbstractPlugin


class Plugin(AbstractPlugin):
    def __init__(self, pm):
        super().__init__(pm, "Rate")

    @staticmethod
    def register_events():
        return [Events.Command("rate", desc="Rate someone or something between 0 and 100")]

    async def handle_command(self, message_object, command, args):
        if command == "rate":
            await self.rate(message_object, args[1])

    async def rate(self, message_object, rated):
        number = round(random.uniform(1, 100), 2)
        print(message_object.mentions)
        if (rated):
            await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                                  "I would rate " + "**" + rated + "** " + str(number) + "/100")
        else:
            await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                                  "I rate this " + str(number) + "/100")
