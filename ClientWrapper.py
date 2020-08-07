import random
from typing import List

import discord


EMBED_DESCRIPTION_MAX_LENGTH = 2048


class ClientWrapper(object):

    rng = random.Random()

    def __init__(self, pm):
        self.pluginManager = pm
        self.client = pm.client

    async def send_message_raw(self, name: str, channel: discord.TextChannel, message: str):
        em = discord.Embed(description=message, colour=self.get_color(name))
        msg = await channel.send(embed=em)
        return msg

    async def send_message(self, name: str, channel: discord.TextChannel, message: str) -> List[discord.Message]:
        if len(message) <= EMBED_DESCRIPTION_MAX_LENGTH:
            return [await self.send_message_raw(name, channel, message)]
        remaining_string: str = message
        sent_messages = []
        # TODO the splitting here doesn't care about text markup, so it might happen that e.g. code blocks get broken
        # It is also pretty naive in terms of balancing the length of resulting messages, there are
        # probably better algorithms if we want more balanced output
        while len(remaining_string) > EMBED_DESCRIPTION_MAX_LENGTH:
            truncated_string = remaining_string[:EMBED_DESCRIPTION_MAX_LENGTH]
            last_newline_index = truncated_string.rfind('\n')
            last_space_index = truncated_string.rfind(' ')
            if last_newline_index >= EMBED_DESCRIPTION_MAX_LENGTH / 3:
                remaining_string = remaining_string[last_newline_index + 1:]
                to_send = truncated_string[:last_newline_index].strip()
            elif last_space_index > 0:
                remaining_string = remaining_string[last_space_index + 1:]
                to_send = truncated_string[:last_space_index].strip()
            else:
                remaining_string = remaining_string[EMBED_DESCRIPTION_MAX_LENGTH:]
                to_send = truncated_string.strip()
            msg = await self.send_message_raw(name, channel, to_send)
            sent_messages.append(msg)
        remaining_string = remaining_string.strip()
        if len(remaining_string) > 0:
            msg = await self.send_message_raw(name, channel, remaining_string)
            sent_messages.append(msg)
        return sent_messages

    async def edit_message(self, name, old_message, new_message):
        em = discord.Embed(description=new_message, colour=self.get_color(name))
        await old_message.edit(embed=em)
        return old_message

    @staticmethod
    def get_color(name):
        ClientWrapper.rng.seed(name)
        r = ClientWrapper.rng.randint(0, 255)
        g = ClientWrapper.rng.randint(0, 255)
        b = ClientWrapper.rng.randint(0, 255)
        return discord.Color((r << 16) + (g << 8) + b)
