import datetime
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import gzip
from bs4 import BeautifulSoup
import random
import traceback
import threading
import xbmc

from email.utils import parsedate_tz

from ... import util

DEBUG = True

BASE_URL = 'https://www.imdb.com'
COVER_BASE_URL = BASE_URL
MOVIES_URL = BASE_URL + '/calendar/?type=MOVIE'
TRAILERS_URL = BASE_URL + '/title/%s/videogallery/content_type-trailer/?ref_=ttvi_ref_typ'
BROWSER_UA = 'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko'
USER_AGENT = BROWSER_UA
RATINGS = {'NOT YET RATED': 'NR', 'NOTYETRATED': 'NR', 'G': 'G', 'PG': 'PG', 'PG13': 'PG-13', 'R': 'R', 'NC17': 'NC-17'}


class Scraper(object):
    def __init__(self):
        self.extras = self.__get_extras()
        cookieProcessor = urllib.request.HTTPCookieProcessor()
        self.opener = urllib.request.build_opener(cookieProcessor)
        self.opener.addheaders = [('User-agent', USER_AGENT), ('Accept-Encoding', 'gzip')]
        
    def get_all_movies(self, limit=0, details=True):
        return self.__get_movies('studios', limit, details)

    def get_most_popular_movies(self, limit=0, details=True):
        return self.__get_movies('most_pop', limit, details)

    def get_exclusive_movies(self, limit=0, details=True):
        return self.__get_movies('exclusive', limit, details)

    def get_most_recent_movies(self, limit=0, details=True):
        return self.__get_movies('just_added', limit, details)

    def __get_movies(self, source, limit, details):
        util.DEBUG_LOG('Searching movies with limit {0}'.format(limit))
        html = self.__get_url(MOVIES_URL)
        soup = BeautifulSoup(html, "html.parser")
        all_calendars = soup.find_all("article", class_="sc-48add019-1")
        if source != 'just_added':
            random.shuffle(all_calendars)
        i = 0
        
        movies_to_scrape = []
        for calendar in all_calendars:
            if limit and i >= limit:
                break
                
            release_date_string = calendar.find("h3", class_="ipc-title__text").text
            
            all_movies = calendar.find_all("li", class_="ipc-metadata-list-summary-item")
            for movie in all_movies:
                if limit and i >= limit:
                    util.DEBUG_LOG('Stopping has limit of %d reached' % (limit))
                    break
                movies_to_scrape.append({'movie': movie, 'release': release_date_string})
                i = i + 1
                
        threads = []
        movies = []

        # Limiting the trailers to 40 arbitrarily
        for movie in movies_to_scrape[:40]:
            thread = threading.Thread(target=self.getDetailsThreaded, args=(movie, movies, details))
            threads.append(thread)
            thread.start()

        for t in threads:
            t.join()

        return movies

    def getDetailsThreaded(self, movie, results, details):
        try:
            details = self.__get_details(movie, details)
            if details is None:
                return
            results.append(details)
        except:
            import traceback
            traceback.print_exc()

    def __get_details(self, item, details):
                release_date_string = item['release']
                movie = item['movie']
                                    
                try:
                    meta = {}
                    meta['mediatype'] = 'movie'
                    meta['source'] = 'imdb'
                    meta['releasedate'] = self.__date(release_date_string)
                    meta['releasedatetime'] = self.__datetime(release_date_string)
                    meta['premiered'] = release_date_string
                    meta['year'] = meta['premiered'][-4:]
                    title = movie.find("a", class_="ipc-metadata-list-summary-item__t")
                    meta['title'] = meta['originaltitle'] = title.text.split('(')[0].strip()
                    meta['location'] = BASE_URL + title['href']
                    videoid = re.findall('/title/(.*)/.*', title['href'])
                    meta['movie_id'] = videoid[0]
                
                    if details:
                        parsed = self.__get_json_info(meta['location'], "application/ld+json")
                        if parsed == None or 'trailer' not in parsed:
                            return None

                        meta['genre'] = ''
                        for genre in parsed['genre']:
                            # If genre is 'Sci-Fi', replace it with 'Science Fiction'
                            if genre == 'Sci-Fi':
                                genre = 'Science Fiction'
                            if len(meta['genre']) > 0:
                                meta['genre'] = meta['genre'] + ','
                            meta['genre'] = meta['genre'] + genre
                
                        meta['poster'] = parsed['image']
                        if 'contentRating' in parsed:
                            meta['rating'] = parsed['contentRating']
                        else:
                            meta['rating'] = 'NR'
                        if meta['rating'] in RATINGS.values():
                            meta['mpaa'] = meta['rating']
                        else:
                            meta['mpaa'] = RATINGS.get(meta['rating'], 'NR')
                    else:
                        meta['genre'] = ''
                        meta['poster'] = ''
                        meta['rating'] = 'NR'
                        meta['mpaa'] = 'NR'
                        
                    return meta
                except Exception as e:
                    util.DEBUG_LOG('Got exception {0}'.format(traceback.print_exc()))
                    return None

    def __get_json_info(self, url, expected_type):
        try:
            response = self.opener.open(url, timeout=10)
        except urllib.error.HTTPError as e:
            if e.status != 308:
               raise  # not a status code that can be handled here
            redirected_url = urllib.parse.urljoin(url, e.headers['Location'])
            #print('redirected to %s' % (redirected_url))
            response = self.opener.open(redirected_url, timeout=30)
        try:
            encoding = response.getheader('Content-Encoding')
            html = response.read()
            if encoding != None and encoding == 'gzip':
                html = gzip.decompress(html)
            soup = BeautifulSoup(html, "html.parser")
            all_scripts = soup.find_all("script")
            for script in all_scripts:
                if 'type' in script.attrs and script.attrs['type'] == expected_type:
                    parsed = json.loads(script.contents[0])
                    return parsed
        except Exception as e:
            util.DEBUG_LOG('Got exception {0}'.format(traceback.print_exc()))
            pass
            
        return None
        
    def get_trailers(self, location, movie_id):
        try:
            url = TRAILERS_URL % (movie_id)
            html = self.__get_url(url)
            soup = BeautifulSoup(html, "html.parser")
            title_block = soup.find("div", class_="subpage_title_block")
            h3 = title_block.find("h3")
            a = h3.find("a")
            title = a.text
            search_results = soup.find("div", class_="search-results")
            try:
                all_trailers = search_results.find_all("li")
            except:
                return
            trailer = random.choice(all_trailers)
            all_a = trailer.find_all("a")
            img = trailer.find("img")
            imgurl = img['loadlate'].split(',')[0]
            duration = re.findall('1_ZA([0-9]+%253A[0-9]+)', img['loadlate'])
            duration = duration[0].replace('%253A', ':')
            link = BASE_URL + all_a[0]['href']
            parsed = self.__get_json_info(link, "application/json")
            
            meta = {}
            title = '%s - %s' % (title, all_a[1].text)
            meta['title'] = title
            meta['studio'] = ''
            meta['thumb'] = imgurl
            meta['duration'] = duration
            meta['streams'] = {}
            for vt in parsed['props']['pageProps']['videoPlaybackData']['video']['playbackURLs']:
                quality = vt['displayName']['value'].lower()
                meta['streams'][quality] = vt['url']
            yield meta
        except Exception as e:
            util.DEBUG_LOG('Got exception {0}'.format(traceback.print_exc()))
                
    def __get_extras(self):
        plots = {}
        return plots

    def __date(self, date_str):
        if date_str:
            d = time.strptime(date_str, "%b %d, %Y")
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
                    d = time.strptime(date_str, "%b %d, %Y")
                    return datetime.datetime.fromtimestamp(time.mktime(d[:9]))
                except:
                    import traceback
                    traceback.print_exc()

        return None

    def __get_url(self, url, headers=None):
        if headers is None:
            headers = {'User-Agent': USER_AGENT, 'Accept-Encoding': 'gzip'}
        req = urllib.request.Request(url, None, headers)
        req2 = urllib.request.urlopen(req)
        encoding = req2.getheader('Content-Encoding')
        html = req2.read()
        if encoding != None and encoding == 'gzip':
            html = gzip.decompress(html)
        return html
