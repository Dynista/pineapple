from util import Events
from util.Ranks import Ranks
from AbstractPlugin import AbstractPlugin


class Plugin(AbstractPlugin):
    def __init__(self, pm):
        super().__init__(pm, "Reload")

    @staticmethod
    def register_events():
        """
        Define events that this plugin will listen to
        :return: A list of util.Events
        """
        return [Events.Command("reload", Ranks.Admin)]

    async def handle_command(self, message_object, command, args):
        """
        Handle Events.Command events
        :param message_object: discord.Message object containing the message
        :param command: The name of the command (first word in the message, without prefix)
        :param args: List of words in the message
        """
        if command == "reload":
            await message_object.delete()
            await self.reload()

    async def reload(self):
        self.pm.load_plugins()
        self.pm.register_events()

        for instance in self.pm.client.guilds:
            self.pm.botPreferences.bind_roles(instance.id)
