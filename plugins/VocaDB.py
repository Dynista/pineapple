import requests

from util import Events
from AbstractPlugin import AbstractPlugin


class Plugin(AbstractPlugin):
    def __init__(self, pm):
        super().__init__(pm, "VocaDB")

    @staticmethod
    def register_events():
        return [Events.Command("song", desc="Search for a song on VocaDB")]

    async def handle_command(self, message_object, command, args):
        if command == "song":
            await self.song(message_object, args)

    async def song(self, message_object, args):
        request_url = "https://vocadb.net/api/songs?query=" + args[1] + \
                      "&sort=FavoritedTimes&maxResults=2&fields=PVs&lang=Romaji" \
                      "&preferAccurateMatches=true&nameMatchMode=Auto"
        response = requests.get(request_url)
        try:
            if len(response.json()["items"]) == 0:
                await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                                      "Can't find a song that matches your search :cry:")
                return
        except:
            await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                                  "Can't find a song that matches your search :cry:")
            return

        results = response.json()
        msg = ""
        pv_posted = False
        for result in results["items"]:
            msg += "**Title:** " + result["name"] + "\n"
            msg += "**Artist:** " + result["artistString"] + "\n"
            msg += "**Language:** " + result["defaultNameLanguage"] + "\n"
            msg += "**VocaDB:** <https://vocadb.net/S/" + str(result["id"]) + ">"

            for pv in result["pvs"]:
                msg += "\n"
                if not pv_posted and pv["service"] == "Youtube":
                    msg += pv["url"]
                    pv_posted = True
                else:
                    msg += "<" + pv["url"] + ">"
            msg += "\n\n"

        await message_object.channel.send(msg)
