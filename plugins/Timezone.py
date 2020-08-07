from util import Events, Timezones
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
import pytz
import re
from AbstractPlugin import AbstractPlugin


class Plugin(AbstractPlugin):

    def __init__(self, pm):
        super().__init__(pm, "Timezone")
        self.output_timezones = [
            pytz.timezone('America/Los_Angeles'),
            pytz.timezone('America/New_York'), 
            pytz.timezone('Europe/London'),
            pytz.timezone('Europe/Amsterdam'),
            pytz.timezone('Europe/Kiev'),
            pytz.timezone('Asia/Tokyo'),
        ]
        self.short_output_format = '%b %d %Y- %H:%M'
        self.output_format = self.short_output_format + ' **%Z**'
        # this is currently unused
        tz_dict = {}
        now = datetime.utcnow()
        for tz_name in pytz.common_timezones:
            tz = pytz.timezone(tz_name)
            converted = now.astimezone(tz)
            utc_offset = tz.utcoffset(now)
            offset = (utc_offset.days * 60 * 60 * 24 + utc_offset.seconds) / 3600
            tz_abbreviation = converted.tzname()
            if tz_abbreviation not in tz_dict:
                tz_dict[tz_abbreviation] = {}
            if offset not in tz_dict[tz_abbreviation]:
                offset_name = '%g' % offset
                if offset >= 0:
                    offset_name = f'+{offset_name}'
                tz_dict[tz_abbreviation][offset_name] = tz_name
        self.tz_dict = tz_dict

    def get_times(self, time_object):
        """
        Given a time object as a parameter, return a dictionary of timezones and times. 
        """
        if time_object.tzinfo is None:
            time_object = pytz.timezone('UTC').localize(time_object)
        time_strings = []
        for output_timezone in self.output_timezones:
            converted = time_object.astimezone(output_timezone)
            time_string = converted.strftime(self.output_format)
            time_strings.append(time_string)
        return '\n'.join(time_strings)

    @staticmethod
    def register_events():
        helptext = """Given a time in either 12 or 24 hour format, display time conversions in several timezones. 
        Example: '1:00PM', '13:00', '13:00 PST'. If no time is specified, the current time in UTC is used. 
        Default timezone is UTC."""
        return [Events.Message('Timezone'), Events.Command('time', desc=helptext)]

    async def handle_message(self, message_object):
        upper = message_object.content.upper()
        parsed = re.match(
            # the lookahead is to make sure 'AM' and 'PM' are not treated as source timezone names
            r'^\s*(\d{1,2}(?::\d{2})?(?:\s?(?:AM|PM))?(?:\s*(?!AM|PM)([A-Z]+)))\s*TO\s*([A-Z]+)\s*$',
            upper)
        if not parsed:
            return
        await self.convert(message_object, parsed.group(1), parsed.group(2), parsed.group(3))

    async def handle_command(self, message_object, command, cmd_args):
        if cmd_args[1] == '':
            await self.time(message_object, None)
        elif not re.match(r"(\d{1,2}:\d{2})|((?i)\d{1,2}(am|pm))", cmd_args[1]):
            await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                                  'Unable to parse time. Check format(e.g. 5:00pm/5pm instead of 500pm)')
        elif command == 'time':
            await self.time(message_object, cmd_args[1])

    async def time(self, message_object, base_time):
        try:
            if base_time is None:
                base_time_obj = datetime.now(timezone.utc)
            else:
                base_time = base_time.upper()
                base_time_obj = parse(base_time, tzinfos=Timezones.TIMEZONE_INFO)
            
            response_text = self.get_times(base_time_obj)
            await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                                  response_text)
        except Exception as e:
            print(e)
            await self.pm.clientWrap.send_message(self.name, message_object.channel,
                                                  'Unable to parse time.')

    async def convert(self, message_object, base_time_string, base_tz_name, target_tz_name):
        try:
            # base_tz_name check is not really necessary, it's just here to avoid weird results
            # in case the parser decides to still go ahead and convert invalid timezones
            if target_tz_name not in Timezones.TIMEZONE_INFO or base_tz_name not in Timezones.TIMEZONE_INFO:
                return
            target_tz = timezone(timedelta(seconds=Timezones.TIMEZONE_INFO[target_tz_name]))
            time_object = parse(base_time_string, tzinfos=Timezones.TIMEZONE_INFO)
            converted = time_object.astimezone(tz=target_tz)
            time_string = converted.strftime(self.short_output_format) + f' **{target_tz_name}**'

            await self.pm.clientWrap.send_message(self.name, message_object.channel, time_string)

        except:
            # do nothing, don't think even print is necessary
            pass

    # this is currently unused
    async def convert_pytz(self, message_object, base_time_string, base_tz_name, target_tz_name):
        try:
            # base_tz_name check is not really necessary, it's just here to avoid weird results
            # in case the parser decides to still go ahead and convert invalid timezones
            if target_tz_name not in self.tz_dict or base_tz_name not in Timezones.TIMEZONE_INFO:
                return
            target_tzs = self.tz_dict[target_tz_name]
            time_object = parse(base_time_string, tzinfos=Timezones.TIMEZONE_INFO)
            time_strings = []
            for target_tz_offset in target_tzs:
                converted = time_object.astimezone(tz=pytz.timezone(target_tzs[target_tz_offset]))
                time_string = converted.strftime(self.output_format)
                time_strings.append(target_tzs[target_tz_offset] + ": " + time_string)

            await self.pm.clientWrap.send_message(self.name, message_object.channel, '\n'.join(time_strings))

        except:
            # do nothing, don't think even print is necessary
            pass
