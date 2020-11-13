import os
import random
import urllib.request

import discord
import requests
from peewee import Model, TextField

from util import Events
from util.Ranks import Ranks
from AbstractPlugin import AbstractPlugin


class Plugin(AbstractPlugin):
    def __init__(self, pm):
        super().__init__(pm, "Gelbooru")
        self.base_url = "http://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit=100&tags="
        self.base_src = "http://gelbooru.com/index.php?page=post&s=view&id="

    @staticmethod
    def register_events():
        return [Events.Command("image",
                               desc="Search Gelbooru! Refer to the Gelbooru Cheat Sheet for tags "
                                    "http://gelbooru.com/index.php?page=help&topic=cheatsheet"),
                Events.Command("blacklist", Ranks.Mod,
                               desc="Adds gelbooru tag to blacklist"),
                Events.Command("unblacklist", Ranks.Mod, desc="Remove a tag from the blacklist")]

    async def handle_command(self, message_object, command, args):
        if command == "image":
            await self.search(message_object, args[1])
        if command == "blacklist":
            if args[1] is None or args[1] == "":
                await self.print_blacklist(message_object)
            else:
                await self.add_blacklist(message_object, args[1])
        if command == "unblacklist":
            await self.remove_blacklist(message_object, args[1])

    def get_models(self):
        return [BooruBlacklist]

    async def search(self, message_object, text):
        text = text.lower()  # moves all tags to lowercase
        search_tags = set(text.split())  # splits tags on second_place
        blacklist = self.get_blacklist(message_object)
        if len(search_tags) == 0:
            await self.pm.clientWrap.send_message(self.name, message_object.channel, "Please enter tags to search.")
            return
        search_tags.discard("rating:questionable")  # no loopholes
        search_tags.discard("rating:safe")  # no loopholes
        search_tags.discard("rating:explicit")  # no loopholes

        if len(search_tags.intersection(blacklist)) > 0:  # if all tags filtered, exit
            await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                                  "The tags used have been blacklisted by an Admin. :cry:")
            return

        search_tags.add("rating:safe")  # append safe tag to URL

        request_url = self.base_url
        for tag in search_tags.difference(blacklist):
            request_url += (tag + "%20")  # add tags not contained in blacklist to search
        for tag in blacklist:
            request_url += ("-" + tag + "%20")  # add "not tags" from blacklists to search
        response = requests.get(request_url)
        try:
            if len(response.json()) == 0:
                await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                                      "Can't find an image that matches your "
                                                      "tag(s) :cry:")
                return
        except:
            await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                                  "Can't find an image that matches your "
                                                  "tag(s) :cry:")
            return

        img_response = response.json()[random.randint(0, len(response.json()) - 1)]
        retries = 5  # retry search 10 times
        response_tags = set(img_response["tags"].split())
        while len(response_tags.intersection(blacklist)) > 0:
            img_response = response.json()[random.randint(0, len(response.json()) - 1)]  # find new image from query
            response_tags = set(img_response["tags"].split())  # split tags from results
            retries -= 1  # decrement recount timer
            if retries == 0:
                await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                                      "Can't find an image that matches your "
                                                      "tag(s) :cry:")
                return

        gel_url = self.base_src + str(img_response["id"])  # this is the link to the gelbooru page
        image_url = img_response["file_url"]
        filename = "cache/temp" + image_url[-5:]

        # downloads image to server
        hdr = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(image_url, headers=hdr)
        page = urllib.request.urlopen(req)
        data = page.read()
        f = open(filename, 'wb+')
        f.write(data)
        f.close()

        if os.path.getsize(filename) > message_object.guild.filesize_limit:
            await message_object.channel.send("The image that was found was too large to "
                                              "upload. " + image_url)
        else:
            await message_object.channel.send(file=discord.File(filename), content= "**Source:** <" + gel_url + ">")

        os.remove(filename)

    async def add_blacklist(self, message_object, text):
        """
        Add tags to the booru search blacklist
        :param message_object: Message containing the command
        :param text: Text to be split containing the tags
        :return: None
        """
        text = text.lower()  # moves all tags to lowercase
        block_tags = set(text.split())  # splits tags on second_place

        with self.pm.dbManager.lock(message_object.guild.id, self.get_name()):
            for item in block_tags:
                BooruBlacklist.insert(tag=item).on_conflict_ignore().execute()

        await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                              "{} Tags added".format(len(block_tags)))

    async def remove_blacklist(self, message_object, text):
        """
        Remove tags from the booru search blacklist
        :param message_object: Message containing the command!
        :param text: Text to be split containing the tags
        :return: None
        """
        text = text.lower()  # moves all tags to lowercase
        block_tags = set(text.split())  # splits tags on second_place

        with self.pm.dbManager.lock(message_object.guild.id, self.get_name()):
            for item in block_tags:
                BooruBlacklist.delete_by_id(item)

        await self.pm.clientWrap.send_message(self.name, message_object.channel, "Tags removed from the blacklist")

    async def print_blacklist(self, message_object):
        """
        Remove tags from the booru search blacklist
        :param message_object: Message containing the command
        :return: None
        """
        tags = self.get_blacklist(message_object)
        msg = "Blacklisted tags: "
        for tag in tags:
            msg += tag + " "
        await self.pm.clientWrap.send_message(self.name, message_object.channel, msg)

    def get_blacklist(self, message_object):
        try:
            tags = list()
            with self.pm.dbManager.lock(message_object.guild.id, self.get_name()):
                for row in BooruBlacklist.select():
                    try:
                        tags.append(row.tag)
                    except:
                        continue
            return tags
        except:
            return list()


class BooruBlacklist(Model):
    tag = TextField(primary_key=True, column_name='Tag')

    class Meta:
        table_name = 'booru_blacklist'
