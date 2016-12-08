from util import Events
import random
import discord
class Plugin(object):
    def __init__(self, pm):
        self.pm = pm

    @staticmethod
    def register_events():
        return [Events.Command("rate")]

    async def handle_command(self, message_object, command, args):
        if command == "rate":
            await self.rate(message_object, args[1])

    async def rate(self, message_object, user):
        #totally not rigged or something
        if(user == "theraga" or user == "Theraga" or user == "dynista" or user == "Dynista"):
            await self.pm.client.send_message(message_object.channel, "I would rate **" + user + "** 100.00/100")
        else:
            number = round(random.uniform(1,100),2)
            print(message_object.mentions)
            await self.pm.client.send_message(message_object.channel, "I would rate " +"**" + user +"** " + str(number) + "/100")
