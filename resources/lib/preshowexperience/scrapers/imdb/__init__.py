import datetime
import os
import re
import requests
import time
import xbmc
import base64
import json
import gzip

from . import scraper
from .. import _scrapers
from ... import ratings
from ... import util

class Trailer(_scrapers.Trailer):
    def __init__(self, data):
        self.data = data
        self.data['rating'] = ratings.getRating('MPAA', self.data.get('mpaa', ''))

    @property
    def ID(self):
        return 'imdb:{0}'.format(self.data['movie_id'])

    @property
    def title(self):
        return self.data['title']

    @property
    def rating(self):
        return self.data['rating']

    @property
    def thumb(self):
        return self.data['poster']

    @property
    def genres(self):
        return re.split(' and |, ', self.data.get('genre', ''))

    @property
    def userAgent(self):
        return scraper.BROWSER_UA

    @property
    def release(self):
        return self.data.get('releasedatetime', datetime.datetime(2020, 1, 1))

    def getStaticURL(self):
        return None

    def getPlayableURL(self, res='720p'):
        try:
            return self._getPlayableURL(res)
        except:
            import traceback
            traceback.print_exc()

        return None

    def _getPlayableURL(self, res='720p'):
        return IMDBTrailerScraper.getPlayableURL()


class IMDBTrailerScraper(_scrapers.Scraper):
    LAST_UPDATE_FILE = os.path.join(util.STORAGE_PATH, 'imdb.last')

    def __init__(self):
        self.loadTimes()

    @staticmethod
    def get_trailer_url(video_id):
        vidurl = f"https://www.imdb.com/video/{video_id}"
        util.DEBUG_LOG('Video URL: {0}'.format(vidurl))
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
            'Accept-Language': 'en-US,en',
        }
        response = requests.get(vidurl, headers=headers)
        #util.DEBUG_LOG('Response: {0}'.format(response))

        if response.status_code != 200:
            util.DEBUG_LOG('Failed to fetch URL')
            util.DEBUG_LOG('Status code: {0}'.format(response.status_code))
            return None

        try:
            content = response.content
            #util.DEBUG_LOG('Content: {0}'.format(content))
            # Check if the content is compressed
            content = content.decode('utf-8')
        except Exception as e:
            util.DEBUG_LOG(f'Failed to decode content: {e}')
            return None

        # Debug print to check content snippet
        #util.DEBUG_LOG('Content snippet: {0}'.format(content[:500]))

        # Parsing the video playback URLs from the JSON data embedded within the HTML
        match = re.search(r'application/json">(.*?)</script>', content)
        if match:
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError as e:
                util.DEBUG_LOG(f'JSON decode error: {e}')
                return None
            video_data = data.get('props', {}).get('pageProps', {}).get('videoPlaybackData', {}).get('video', {})
            #util.DEBUG_LOG('Video Data: {0}'.format(video_data))
            streams = {item['displayName']['value']: item['url'] for item in video_data.get('playbackURLs', []) if item['videoMimeType'] == 'MP4'}
            #util.DEBUG_LOG('Streams: {0}'.format(streams))
            return streams

        util.DEBUG_LOG("No valid JSON data found in response.")
        return None

    @staticmethod
    def getPlayableURL(video_id, res=1080, url=None):
        #video_id = 'vi3952068121'
        streams = IMDBTrailerScraper.get_trailer_url(video_id)
        if streams:
            # Select the video URL based on desired resolution
            possible_resolutions = ['1080p', '720p', '480p']
            for resolution in possible_resolutions:
                if resolution in streams:
                    return streams[resolution]
        return None

    def loadTimes(self):
        self.lastAllUpdate = 0
        self.lastRecentUpdate = 0
        if not os.path.exists(self.LAST_UPDATE_FILE):
            return
        try:
            with open(self.LAST_UPDATE_FILE, 'r') as f:
                self.lastAllUpdate, self.lastRecentUpdate = [int(x) for x in f.read().splitlines()[:2]]
        except:
            util.ERROR()

    def saveTimes(self):
        with open(self.LAST_UPDATE_FILE, 'w') as f:
            f.write('{0}\n{1}'.format(int(self.lastAllUpdate), int(self.lastRecentUpdate)))

    def allIsDue(self):
        if time.time() - self.lastAllUpdate > 604800:  # One week
            self.lastAllUpdate = time.time()
            self.saveTimes()
            return True
        return False

    def recentIsDue(self):
        if time.time() - self.lastRecentUpdate > 86400:  # One day
            self.lastRecentUpdate = time.time()
            self.saveTimes()
            return True
        return False

    def getTrailers(self):
        url = base64.b64decode('aHR0cHM6Ly9wcmVzaG93ZXhwZXJpZW5jZS5jb20vcHJlc2hvd2ltZGJ0cmFpbGVycy9wcmVzaG93aW1kYnRyYWlsZXJzLnBocA==').decode()
        ms = scraper.Scraper(url)
        if self.allIsDue():
            util.DEBUG_LOG(' - Fetching trailers')
            return [Trailer(t) for t in ms.get_movies(None)]

        return []

    def updateTrailers(self):
        url = base64.b64decode('aHR0cHM6Ly9wcmVzaG93ZXhwZXJpZW5jZS5jb20vcHJlc2hvd2ltZGJ0cmFpbGVycy9wcmVzaG93aW1kYnRyYWlsZXJzLnBocA==').decode()
        ms = scraper.Scraper(url)
        if self.recentIsDue():
            util.DEBUG_LOG(' - Fetching trailers')
            return [Trailer(t) for t in ms.get_movies(None)]

        return []