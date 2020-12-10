import re
import os
import time
from datetime import datetime
from enum import Enum, auto
from typing import List, TypedDict, Literal, Optional
from asyncio import gather
from aiohttp import ClientSession
from pixivpy_async import *
import discord
from util import Events
from AbstractPlugin import AbstractPlugin


class Proxy(Enum):
    kotori = auto()
    pixivcat = auto()


class PixivImageUrls(TypedDict):
    square_medium: str
    medium: str
    large: str
    original: str


class PixivArtwork(TypedDict):
    url: str
    id: int
    type: str
    title: str
    caption: str
    author_name: str
    tags: List[str]
    create_date: datetime
    total_view: int
    total_bookmarks: int
    is_nsfw: bool
    image_urls: List[PixivImageUrls]


def get_tag_url(tag: str):
    return f'https://pixiv.net/tags/{tag}/artworks'


def tag_list_to_string(tags: List[str]):
    tag_links = map(lambda x: f'[{x}]({get_tag_url(x)})', tags)
    return ' • '.join(tag_links)


# Get a proxy url for the given image
def proxy_image_url(url: str, proxy: Proxy = Proxy.pixivcat):
    if proxy is Proxy.kotori:
        parsed = re.match(r'https?://(?:www.)?(.*)', url)
        if not parsed:
            raise Exception('Invalid URL')
        truncated = parsed.group(1)
        return f'https://api.kotori.love/pixiv/image/{truncated}'
    return url.replace('i.pximg.net', 'i.pixiv.cat', 1)


class Plugin(AbstractPlugin):

    session: ClientSession
    api: AppPixivAPI
    only_nsfw: bool
    use_download_images: bool
    preferred_image_size: Literal['square_medium', 'medium', 'large', 'original']
    images_limit: int
    cache_dir: str
    token_expires_at: int

    def __init__(self, pm):
        super().__init__(pm, "Pixiv")
        self.api = AppPixivAPI()
        self.session = ClientSession()
        self.only_nsfw = self.pm.botPreferences.get_config_value("Pixiv", "only_nsfw") != "0"
        self.use_download_images = self.pm.botPreferences.get_config_value("Pixiv", "download_images") != "0"
        self.preferred_image_size = self.pm.botPreferences.get_config_value("Pixiv", "preferred_image_size")
        self.images_limit = int(self.pm.botPreferences.get_config_value("Pixiv", "images_limit"))
        self.cache_dir = os.path.join(pm.cache_dir, 'pixiv')
        self.token_expires_at = 0
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    @staticmethod
    def register_events():
        return [Events.Message("Pixiv")]

    async def ensure_login(self):
        now = int(time.time())
        # give a minute grace period
        if now > self.token_expires_at - 60:
            await self.login()

    async def login(self):
        if self.api.refresh_token is not None:
            try:
                res = await self.api.login(refresh_token=self.api.refresh_token)
                self.token_expires_at = int(time.time()) + res['response']['expires_in']
                return
            except Exception:
                # will try to login with credentials
                pass
        username = self.pm.botPreferences.get_config_value("Pixiv", "username")
        password = self.pm.botPreferences.get_config_value("Pixiv", "password")
        res = await self.api.login(username, password)
        self.token_expires_at = int(time.time()) + res['response']['expires_in']

    async def handle_message(self, message_object):
        lower = message_object.content.lower()
        matches = re.findall(r'(https://(?:www.)?pixiv.net/(?:[a-z0-9/]+/)?([a-z]+)/(\d+))', lower)
        if len(matches) <= 0:
            return

        processed_matches: List[PixivArtwork] = []

        # pixiv API is queried sequentially for now
        for match in matches:
            url = match[0]
            endpoint = match[1]
            item_id = int(match[2])
            if endpoint == 'artworks':
                artwork_data = await self.fetch_artwork_data(item_id, url)
            else:
                # don't know yet what are the other endpoints on pixiv and if we are interested
                continue

            if artwork_data is None:
                continue
            if self.only_nsfw and not artwork_data['is_nsfw']:
                continue
            if not message_object.channel.is_nsfw() and artwork_data['is_nsfw']:
                continue

            if 0 < self.images_limit < len(artwork_data['image_urls']):
                artwork_data['image_urls'] = artwork_data['image_urls'][:self.images_limit]
            processed_matches.append(artwork_data)

        if self.use_download_images:
            await self.process_matches_download(processed_matches, message_object)
        else:
            await self.process_matches_proxy(processed_matches, message_object)

    async def fetch_artwork_data(self, item_id: int, url: str) -> Optional[PixivArtwork]:
        try:
            await self.ensure_login()
            json_response = await self.api.illust_detail(item_id)
            # print(json_response)
            # When the token expires we still seem to get a success response, but with 'error' field
            if 'error' in json_response:
                raise Exception
        except Exception:
            # exceptions shouldn't really happen, but leaving this just as an extra precaution
            await self.login()
            # Maybe catch error here too and log it?
            json_response = await self.api.illust_detail(item_id)
        illust = json_response['illust']
        if illust.type == 'ugoira':
            # TODO possible to download and convert them to webm
            return None
        image_urls: List[PixivImageUrls] = []
        if len(illust['meta_single_page']) > 0:
            urls = illust['image_urls']
            urls['original'] = illust['meta_single_page']['original_image_url']
            image_urls.append(urls)
        elif len(illust['meta_pages']) > 0:
            for img in illust['meta_pages']:
                image_urls.append(img['image_urls'])
        # not sure if this can even happen, but just in case?
        else:
            urls = json_response['illust']['image_urls']
            urls['original'] = urls['large']
            image_urls.append(urls)

        directly_mapped_keys = ['id', 'type', 'title', 'caption', 'total_view', 'total_bookmarks']
        # Cannot type because python doesn't seem to have Partial<> >_>
        artwork_info = {}
        for key in directly_mapped_keys:
            artwork_info[key] = illust[key]
        artwork_info['url'] = url
        artwork_info['author_name'] = illust['user']['name']
        artwork_info['tags'] = list(map(lambda x: x['name'], illust['tags']))
        artwork_info['create_date'] = datetime.strptime(illust['create_date'], '%Y-%m-%dT%H:%M:%S%z')
        artwork_info['image_urls'] = image_urls
        artwork_info['is_nsfw'] = illust['x_restrict'] == 1
        return artwork_info

    def select_preferred_image_url(self, image_urls: PixivImageUrls) -> str:
        # Since it refuses to accept the Literal as a valid key.. >_>
        # noinspection PyTypedDict
        return image_urls[self.preferred_image_size]  # type: ignore

    async def process_matches_download(self, matches: List[PixivArtwork], message_object):

        # TODO ensure that the image is below discord upload limit. Can either resize downloaded image with PIL
        #  or do a HEAD request, look at Content-Length and downgrade image size if necessary. The problem with
        #  latter is that Content-Length is not always present, especially on 'medium' images :(

        futures = []
        # fetch images in parallel
        for match in matches:
            image_urls = list(map(self.select_preferred_image_url, match['image_urls']))
            futures.append(self.download_images(image_urls))
        result = await gather(*futures)

        for i, match in enumerate(matches):
            image_paths = result[i]
            for j, image_path in enumerate(image_paths):
                message = f'<{match["url"]}>'
                if len(image_paths) > 1:
                    message += f' {j + 1}/{len(image_paths)}'
                await message_object.channel.send(file=discord.File(image_path), content=message)
                # delete locally saved image
                os.remove(image_path)

    async def process_matches_proxy(self, matches: List[PixivArtwork], message_object):
        for artwork_data in matches:
            for i, image_urls_set in enumerate(artwork_data['image_urls']):
                image_url = proxy_image_url(self.select_preferred_image_url(image_urls_set))
                original_image_url = proxy_image_url(image_urls_set['original'])
                tags = tag_list_to_string(artwork_data['tags'])
                title = f'{artwork_data["title"]} by {artwork_data["author_name"]}'
                if len(artwork_data['image_urls']) > 1:
                    title += f'. Image {i+1}/{len(artwork_data["image_urls"])}'
                url = artwork_data['url']
                posted = artwork_data['create_date']
                bookmarks = artwork_data['total_bookmarks']
                color = 0x0000dd
                description = f'[Original image]({original_image_url})'
                embed = discord.Embed(title=title, description=description, color=color, url=url, timestamp=posted)
                embed.add_field(name='Bookmarks', value=str(bookmarks), inline=True)
                embed.add_field(name='Tags', value=tags, inline=True)
                embed.set_image(url=image_url)
                await message_object.channel.send(embed=embed)

    async def download_image(self, image_url: str):
        headers = {'referer': 'https://www.pixiv.net/'}
        extension = image_url[image_url.rfind('.'):]
        async with self.session.get(image_url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception
            image_name = f'{str(time.time())}{extension}'
            image_path = os.path.join(self.cache_dir, image_name)
            with open(image_path, 'wb') as f:
                f.write(await resp.read())
            return image_path

    # download images in parallel
    async def download_images(self, image_urls: List[str]):
        futures = []
        for image_url in image_urls:
            futures.append(self.download_image(image_url))
        return await gather(*futures)

    async def get_head(self, url, headers):
        async with self.session.head(url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception
            print(resp.headers['CONTENT-LENGTH'])
            return url
