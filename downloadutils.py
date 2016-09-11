# -*- coding: utf-8 -*-

###############################################################################

import logging
import requests
import re
import xbmc, xbmcvfs, xbmcgui
try:
    import simplejson as json
except:
    import json


###############################################################################

# Disable annoying requests warnings
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

###############################################################################
WINDOW = xbmcgui.Window(10000)

class DownloadUtils():
    """
    Manages any up/downloads
    """

    # Borg - multiple instances, shared state
    _shared_state = {}

    # How many failed attempts before declaring PMS dead?
    connectionAttempts = 2
    # How many 401 returns before declaring unauthorized?
    unauthorizedAttempts = 2
    omdbinfocache = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        # Requests session
        self.timeout = 30.0

    def tryEncode(self,text, encoding="utf-8"):
        try:
            return text.encode(encoding,"ignore")
        except:
            return text

    def tryDecode(self,text, encoding="utf-8"):
        try:
            return text.decode(encoding,"ignore")
        except:
            return text

    def getExternalId(self,title):
        #perform search on TMDB and return artwork
        matchFound = None
        media_id = None
        tmdb_apiKey = "ae06df54334aa653354e9a010f4b81cb"
        KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)
        media_type = 'movie'
        # if the title has the year in remove it as tmdb cannot deal with it...
        # replace e.g. 'The Americans (2015)' with 'The Americans'
        title = re.sub(r'\s*\(\d{4}\)$', '', title, count=1)

        #get the id from window cache first
        cacheStr = "script.tvguide.dvr.externalid-%s" %title
        cache = WINDOW.getProperty(self.tryEncode(cacheStr)).decode("utf-8")
        if cache:
            return eval(cache)

        try:
            url = 'http://api.themoviedb.org/3/search/%s?api_key=%s&language=%s&query=%s' %(media_type,tmdb_apiKey,KODILANGUAGE,self.tryEncode(title))
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = json.loads(response.content.decode('utf-8','replace'))
                #find exact match based on title
                if not matchFound and data and data.get("results",None):
                    for item in data["results"]:
                        name = item.get("name")
                        if not name: name = item.get("title")
                        original_name = item.get("original_name","")
                        title_alt = title.lower().replace(" ","").replace("-","").replace(":","").replace("&","").replace(",","")
                        name_alt = name.lower().replace(" ","").replace("-","").replace(":","").replace("&","").replace(",","")
                        org_name_alt = original_name.lower().replace(" ","").replace("-","").replace(":","").replace("&","").replace(",","")
                        if name == title or original_name == title:
                            #match found for exact title name
                            matchFound = item
                            break
                        elif name.split(" (")[0] == title or title_alt == name_alt or title_alt == org_name_alt:
                            #match found with substituting some stuff
                            matchFound = item
                            break

                    #if a match was not found, we accept the closest match from TMDB
                    if not matchFound and len(data.get("results")) > 0 and not len(data.get("results")) > 5:
                        matchFound = item = data.get("results")[0]

            if matchFound:
                id = str(matchFound.get("id",""))
                #lookup external tmdb_id and perform artwork lookup on fanart.tv
                if id:
                    languages = [KODILANGUAGE,"en"]
                    for language in languages:
                        if media_type == "movie":
                            url = 'http://api.themoviedb.org/3/movie/%s?api_key=%s&language=%s&append_to_response=videos' %(id,tmdb_apiKey,language)

                        response = requests.get(url)
                        data = json.loads(response.content.decode('utf-8','replace'))
                        if data:
                            if not media_id and data.get("imdb_id"):
                                media_id = str(data.get("imdb_id"))
                            if not media_id and data.get("external_ids"):
                                media_id = str(data["external_ids"].get("tvdb_id"))


        except Exception as e:
            xbmc.log("getExternalId - Error in getExternalId --> " + str(e),0)

        #store in cache for quick access later
        WINDOW.setProperty(self.tryEncode(cacheStr), repr(media_id))
        return media_id


    def getFanartTVArt(self, mediaId):
        """
        perform artwork lookup on fanart.tv

        mediaId: IMDB id for movies, tvdb id for TV shows
        """
        artwork={}
        KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)
        api_key = "639191cb0774661597f28a47e7e2bad5"
        type = "movie"
        if type == "movie":
            url = 'http://webservice.fanart.tv/v3/movies/%s?api_key=%s' %(mediaId,api_key)

        #get the id from window cache first
        cacheStr = "script.tvguide.dvr.artwork-%s" %mediaId
        cache = WINDOW.getProperty(self.tryEncode(cacheStr)).decode("utf-8")
        if cache:
            return eval(cache)

        try:
            response = requests.get(url, timeout=15)
        except Exception as e:
            xbmc.log("getfanartTVimages lookup failed--> " + str(e), 0)
            return artwork
        if response and response.content and response.status_code == 200:
            data = json.loads(response.content.decode('utf-8','replace'))
        else:
            #not found
            return artwork
        if data:

            #we need to use a little mapping between fanart.tv arttypes and kodi artttypes
            fanartTVTypes = [ ("logo","clearlogo"),("disc","discart"),("clearart","clearart"),("banner","banner"),("clearlogo","clearlogo"),("poster","poster"),("thumb","landscape"),("background","fanart")]
            prefixes = ["",type,"hd","hd"+type]
            for fanarttype in fanartTVTypes:
                 for prefix in prefixes:
                    fanarttvimage = prefix+fanarttype[0]
                    if data.has_key(fanarttvimage):
                        for item in data[fanarttvimage]:
                            if item.get("lang","") == KODILANGUAGE:
                                #select image in preferred language
                                if xbmcvfs.exists(item.get("url")):
                                    artwork[fanarttype[1]] = item.get("url")
                                    break
                        if not artwork.get(fanarttype[1]):
                            for entry in data[fanarttvimage]:
                                if entry.get("lang") in ("en", "00"):
                                    artwork[fanarttype[1]] = entry.get("url")
                                    break

        #store in cache for quick access later
        WINDOW.setProperty(self.tryEncode(cacheStr), repr(artwork))
        return artwork

    def getOmdbInfo(self, mediaId):
        result = {}
        if self.omdbinfocache.get(mediaId):
            #get data from cache
            result = self.omdbinfocache[mediaId]
        else:
            url = 'http://www.omdbapi.com/?i=%s&plot=short&tomatoes=true&r=json' %mediaId
            res = requests.get(url)
            omdbresult = json.loads(res.content.decode('utf-8','replace'))
            if omdbresult.get("Response","") == "True":
                result = omdbresult
                self.omdbinfocache[mediaId] = result
        return result