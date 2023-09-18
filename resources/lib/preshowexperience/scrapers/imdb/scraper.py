import datetime
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
import xbmc

from email.utils import parsedate_tz

from ... import util

DEBUG = True

BASE_URL = 'https://www.imdb.com'
COVER_BASE_URL = BASE_URL
TRAILERS_URL = BASE_URL + '/trailers'
DETAILS_BASE_URL = BASE_URL
BROWSER_UA = 'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko'
USER_AGENT = BROWSER_UA
RATINGS = {'NOT YET RATED': 'NR', 'NOTYETRATED': 'NR', 'PG13': 'PG-13', 'NC17': 'NC-17'}


class Scraper(object):
    def __init__(self):
        self.extras = self.__get_extras()
        cookieProcessor = urllib.request.HTTPCookieProcessor()
        self.opener = urllib.request.build_opener(cookieProcessor)
        self.opener.addheaders = [('User-agent', USER_AGENT)]
        
    def get_all_movies(self, limit=0):
        return self.__get_movies('studios', limit)

    def get_most_popular_movies(self, limit=0):
        return self.__get_movies('most_pop', limit)

    def get_exclusive_movies(self, limit=0):
        return self.__get_movies('exclusive', limit)

    def get_most_recent_movies(self, limit=0):
        return self.__get_movies('just_added', limit)

    def __get_movies(self, source, limit):
        html = self.__get_url(TRAILERS_URL)
        soup = BeautifulSoup(html, "html.parser")
        trailers_elements = soup.find_all("div", class_="ipc-poster-card")
        for movie in trailers_elements:
            if limit and i >= limit:
                break
            meta = {}
            meta['mediatype'] = 'movie'
            meta['source'] = 'imdb'
            meta['rating'] = 'NR'
            meta['mpaa'] = RATINGS.get('NR', 'NR')
            title = movie.find("a", class_="ipc-poster-card__title")
            # Disabled as it takes too much time to get the genre
            #meta['genre'] = self.__get_genres(BASE_URL + title['href'])
            meta['genre'] = ''
            meta['title'] = meta['originaltitle'] = title.text
            release = movie.find("div", class_="ipc-poster-card__actions")
            premiered = self.__date(release.text)
            if premiered:
                meta['premiered'] = premiered
                meta['year'] = meta['premiered'][-4:]
            meta['releasedate'] = self.__date(release.text)
            meta['releasedatetime'] = self.__datetime(release.text)
            link = movie.find("a", class_="ipc-lockup-overlay")
            meta['location'] = COVER_BASE_URL + link["href"]
            videoid = re.findall(BASE_URL + '/video/(.*)/.*', meta['location'])
            meta['movie_id'] = videoid[0]
            media = movie.find("img", class_="ipc-image")
            meta['poster'] = media["src"]
            yield meta

    def __get_genres(self, url):
        try:
            response = self.opener.open(url, timeout=30)
            html = response.read()
            soup = BeautifulSoup(html, "html.parser")
            all_scripts = soup.find_all("script")
            for script in all_scripts:
                if 'type' in script.attrs and script.attrs['type'] == "application/ld+json":
                    parsed = json.loads(script.contents[0])
                    return parsed['genre']
        except:
            pass
            
        return []
        
    def get_trailers(self, location, movie_id):
        response = self.opener.open(location, timeout=30)
        html = response.read()
        soup = BeautifulSoup(html, "html.parser")
        jsontext = soup.find(id="__NEXT_DATA__")
        parsed = json.loads(jsontext.contents[0])
        
        video_url_1080p = None
        video_url_sd = None
        for vt in parsed['props']['pageProps']['videoPlaybackData']['video']['playbackURLs']:
            if vt['mimeType'] == 'video/mp4' and vt['displayName']['value'] == '1080p':
                video_url_1080p = vt['url']
            if vt['mimeType'] == 'video/mp4' and vt['displayName']['value'] == 'SD':
                video_url_sd = vt['url']

        if video_url_1080p is not None or video_url_sd is not None:
            meta = {}
            title = parsed['props']['pageProps']['videoPlaybackData']['video']['primaryTitle']['titleText']['text']
            meta['title'] = title
            meta['studio'] = ''
            thumb = parsed['props']['pageProps']['videoPlaybackData']['video']['thumbnail']['url']
            meta['thumb'] = thumb
            duration = parsed['props']['pageProps']['videoPlaybackData']['video']['runtime']['value']
            meta['duration'] = duration
            meta['streams'] =  { 'hd1080': video_url_1080p, 'sd': video_url_sd }
            yield meta

    def __get_stream_url(self, location):
        response = self.opener.open(location, timeout=30)
        html = response.read()
        soup = BeautifulSoup(html, "html.parser")
        jsontext = soup.find(id="__NEXT_DATA__")
        parsed = json.loads(jsontext.contents[0])
        for vt in parsed['props']['pageProps']['videoPlaybackData']['video']['playbackURLs']:
            if vt['mimeType'] == 'video/mp4' and vt['displayName']['value'] == '1080p':
                return vt['url']
        
        return None
                
    def __get_extras(self):
        plots = {}
        return plots

    def __date(self, date_str):
        if date_str:
            d = time.strptime(date_str, "%B %d, %Y")
            return '%02d.%02d.%04d' % (d[2], d[1], d[0])
        return ''

    def __datetime(self, date_str):
        if date_str:
            if date_str == 'Wed, 31 Dec 1969 16:00:00 -0800' or date_str == None:
                date_str = 'Thu, 01 Jan 1970 16:00:00 -0800'
                d = parsedate_tz(date_str)
                return datetime.datetime.fromtimestamp(time.mktime(d[:9]))
            else:
                try:
                    d = time.strptime(date_str, "%B %d, %Y")
                    return datetime.datetime.fromtimestamp(time.mktime(d[:9]))
                except:
                    import traceback
                    traceback.print_exc()

        return None

    def __get_url(self, url, headers=None):
        if headers is None:
            headers = {'User-Agent': USER_AGENT}
        req = urllib.request.Request(url, None, headers)
        html = urllib.request.urlopen(req).read()
        return html
