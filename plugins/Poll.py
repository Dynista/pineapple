# -*- coding: utf-8 -*-
from util import Events
from AbstractPlugin import AbstractPlugin


class Plugin(AbstractPlugin):
    def __init__(self, pm):
        super().__init__(pm, "Poll")

    @staticmethod
    def register_events():
        return [Events.Command('poll')]

    async def handle_command(self, message_object, command, args):
        if command == "poll":
            await self.poll(message_object, args[1].strip())

    async def poll(self, message_object, prompt):
        if prompt.strip() == "":
            prompt = "Yay or Nay?"
        # current message character limit is 2000, so we should never get a split embed, but in case it changes
        # in the future, attach reactions only to the last message
        poll_msg = (await self.pm.clientWrap.send_message(self.name, message_object.channel, "**Poll:**\n" + prompt))[-1]
        await poll_msg.add_reaction('\U00002714')
        await poll_msg.add_reaction('\U00002716')
