import requests
import datetime
import re

class Scraper(object):
    def __init__(self, url):
        self.url = url
        self.movies = self.fetch_movies()

    def fetch_movies(self):
        try:
            response = requests.get(self.url)
            response.raise_for_status()  # This will raise an exception for HTTP error codes
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching movies: {e}")
            return []

    def get_movies(self, limit=0):
        extracted_movies = []
        for movie in self.movies[:limit or None]:
            try:
                # Adjusting to match given field names and processing
                release_date = datetime.datetime.strptime(movie["releasedate"], "%Y-%m-%d %H:%M:%S")
                genres = re.split(',\s*', movie.get("genres", ""))

                movie_details = {
                    "title": movie["title"],
                    "movie_id": movie["url"].split("/title/")[1].rstrip("/"),
                    "location": movie["url"],
                    "poster": movie["thumb"],
                    "genre": ", ".join(genres),
                    "rating": movie["rating"],
                    "releasedate": movie["releasedate"],
                    "releasedatetime": release_date,
                    "url": movie["url"],
                }
                extracted_movies.append(movie_details)
            except KeyError as e:
                print(f"Missing data in movie: {e}")
                continue

        return extracted_movies