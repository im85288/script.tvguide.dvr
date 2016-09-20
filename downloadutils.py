# -*- coding: utf-8 -*-

###############################################################################

import logging
import requests
import re
import xbmc, xbmcvfs, xbmcgui
import BeautifulSoup
import urllib2
import os
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
    tmdbinfocache = {}
    top250 = {}
    tmdb_apiKey = "ae06df54334aa653354e9a010f4b81cb"

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

    def encodeString(self,string):
        return (string.encode('base64')).replace('\n','').replace('\r','').replace('\t','')

    def decodeString(self,string):
        return string.decode('base64')

    def checkIconExists(self, icon):
        try:
            ret = urllib2.urlopen(icon)
            if ret.code == 200:
                return True
            else:
                return False
        except urllib2.URLError, e:
            return False

    def getExternalId(self,title,media_type):
        #perform search on TMDB and return artwork
        matchFound = None
        media_id = None
        KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)
        # if the title has the year in remove it as tmdb cannot deal with it...
        # replace e.g. 'The Americans (2015)' with 'The Americans'
        title = re.sub(r'\s*\(\d{4}\)$', '', title, count=1)

        #get the id from window cache first
        cacheStr = "script.tvguide.dvr.externalid-%s" %title
        cache = WINDOW.getProperty(self.tryEncode(cacheStr)).decode("utf-8")
        if cache:
            return eval(cache)

        try:
            url = 'http://api.themoviedb.org/3/search/%s?api_key=%s&language=%s&query=%s' %(media_type,self.tmdb_apiKey,KODILANGUAGE,self.tryEncode(title))
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
                            url = 'http://api.themoviedb.org/3/movie/%s?api_key=%s&language=%s&append_to_response=videos' %(id,self.tmdb_apiKey,language)
                        elif media_type == "tv":
                            url = 'http://api.themoviedb.org/3/tv/%s?api_key=%s&append_to_response=external_ids,videos&language=%s' %(id,self.tmdb_apiKey,language)
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

    def getImdbId(self,title,media_type):
        #perform search on TMDB and return artwork
        matchFound = None
        media_id = None
        KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)
        # if the title has the year in remove it as tmdb cannot deal with it...
        # replace e.g. 'The Americans (2015)' with 'The Americans'
        title = re.sub(r'\s*\(\d{4}\)$', '', title, count=1)

        #get the id from window cache first
        cacheStr = "script.tvguide.dvr.imdbid-%s" %title
        cache = WINDOW.getProperty(self.tryEncode(cacheStr)).decode("utf-8")
        if cache:
            return eval(cache)

        try:
            url = 'http://api.themoviedb.org/3/search/%s?api_key=%s&language=%s&query=%s' %(media_type,self.tmdb_apiKey,KODILANGUAGE,self.tryEncode(title))
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
                            url = 'http://api.themoviedb.org/3/movie/%s?api_key=%s&language=%s&append_to_response=videos' %(id,self.tmdb_apiKey,language)
                        elif media_type == "tv":
                            url = 'http://api.themoviedb.org/3/tv/%s?api_key=%s&append_to_response=external_ids,videos&language=%s' %(id,self.tmdb_apiKey,language)
                        response = requests.get(url)
                        data = json.loads(response.content.decode('utf-8','replace'))
                        if data:
                            if not media_id and data.get("imdb_id"):
                                media_id = str(data.get("imdb_id"))
                            if not media_id and data.get("external_ids"):
                                media_id = str(data["external_ids"].get("imdb_id"))


        except Exception as e:
            xbmc.log("getExternalId - Error in getExternalId --> " + str(e),0)

        #store in cache for quick access later
        WINDOW.setProperty(self.tryEncode(cacheStr), repr(media_id))
        return media_id


    def getFanartTVArt(self, mediaId, type):
        """
        perform artwork lookup on fanart.tv

        mediaId: IMDB id for movies, tvdb id for TV shows
        """
        artwork={}
        KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)
        api_key = "639191cb0774661597f28a47e7e2bad5"
        if type == "movie":
            url = 'http://webservice.fanart.tv/v3/movies/%s?api_key=%s' %(mediaId,api_key)
        elif type == "tv":
            url = 'http://webservice.fanart.tv/v3/tv/%s?api_key=%s' %(mediaId,api_key)

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
            fanartTVTypes = [ ("logo","clearlogo"),("disc","discart"),("clearart","clearart"),("banner","banner"),("clearlogo","clearlogo"),("poster","poster"),("thumb","landscape"),("background","fanart"),("showbackground","fanart"),("characterart","characterart")]
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

    def getTmdbInfo(self, mediaId):
        result = {}
        if self.tmdbinfocache.get(mediaId):
            #get data from cache
            result = self.tmdbinfocache[mediaId]
        else:
            url = 'http://api.themoviedb.org/3/find/%s?external_source=imdb_id&api_key=%s' %(mediaId,self.tmdb_apiKey)
            response = requests.get(url)
            data = json.loads(response.content.decode('utf-8','replace'))
            if data and data.get("movie_results"):
                data = data.get("movie_results")
                if len(data) == 1:
                    url = 'http://api.themoviedb.org/3/movie/%s?api_key=%s' %(data[0].get("id"),self.tmdb_apiKey)
                    response = requests.get(url)
                    data = json.loads(response.content.decode('utf-8','replace'))
                    if data.get("budget") and data.get("budget") > 0:
                        mln = float(data.get("budget")) / 1000000
                        mln = "%.1f" % mln
                        result["budget"] = "$ %s mln." %mln.replace(".0","").replace(".",",")

                    if data.get("revenue","") and data.get("revenue") > 0:
                        mln = float(data.get("revenue")) / 1000000
                        mln = "%.1f" % mln
                        result["revenue"] = "$ %s mln." %mln.replace(".0","").replace(".",",")

                    result["tagline"] = data.get("tagline","")
                    self.tmdbinfocache[mediaId] = result
        return result

    def getChannelLogo(self,channelname):
        image = ""
        cache = WINDOW.getProperty(channelname.encode('utf-8') + "script.tvguide.dvr.channellogo")
        checked = WINDOW.getProperty(channelname.encode('utf-8') + "script.tvguide.dvr.channellogo.checked")
        if cache:
            return cache
        elif checked:
            return image
        else:
            try:

                #lookup with thelogodb
                if not image:
                    url = 'https://www.thelogodb.com/api/json/v1/7533/tvchannel.php?s=%s' %self.tryEncode(channelname)
                    response = requests.get(url)
                    if response.content:
                        data = json.loads(response.content.decode('utf-8','replace'))
                        xbmc.log("fetch channel json response %s" %data)
                        if data and data.has_key('channels'):
                            results = data['channels']
                            if results:
                                for i in results:
                                    rest = i['strLogoWide']
                                    if rest:
                                        if ".jpg" in rest or ".png" in rest:
                                            image = rest
                                            break

                if not image:
                    search_alt = channelname.replace(" HD","")
                    url = 'https://www.thelogodb.com/api/json/v1/7533/tvchannel.php?s=%s' %self.tryEncode(search_alt)
                    response = requests.get(url)
                    if response.content:
                        data = json.loads(response.content.decode('utf-8','replace'))
                        xbmc.log("fetch channel json response 2 %s" %data)
                        if data and data.has_key('channels'):
                            results = data['channels']
                            if results:
                                for i in results:
                                    rest = i['strLogoWide']
                                    if rest:
                                        if ".jpg" in rest or ".png" in rest:
                                            image = rest
                                            break
            except Exception as e:
                    xbmc.log("ERROR in searchChannelLogo ! --> " + str(e))

            if image:
                if ".jpg/" in image:
                    image = image.split(".jpg/")[0] + ".jpg"

            WINDOW.setProperty(channelname.encode('utf-8') + "script.tvguide.dvr.channellogo",image)
            WINDOW.setProperty(channelname.encode('utf-8') + "script.tvguide.dvr.channellogo.checked",'true')

            xbmc.log("fetch channel retrieved from channel logo db %s" %image)
            return image

    def getImdbTop250(self, mediaId):
        result = {}
        if self.top250.get(mediaId):
            #get data from cache
            result = self.top250[mediaId]

        return result

    def _getImdbTop250(self):
        if not self.top250:

            cacheStr = "script.tvguide.dvr.top250"
            cache = WINDOW.getProperty(self.tryEncode(cacheStr)).decode("utf-8")
            if cache:
                self.top250 = eval(cache)
                return

            results = {}
            #movie top250
            html = requests.get("http://www.imdb.com/chart/top", headers={'User-agent': 'Mozilla/5.0'}, timeout=20)
            soup = BeautifulSoup.BeautifulSoup(html.text)
            for table in soup.findAll('table'):
                if table.get("class") == "chart full-width":
                    for td in table.findAll('td'):
                        if td.get("class") == "titleColumn":
                            a = td.find("a")
                            if a:
                                url = a.get("href","")
                                imdb_id = url.split("/")[2]
                                imdb_rank = url.split("chttp_tt_")[1]
                                results[imdb_id] = imdb_rank

            #tvshows top250
            html = requests.get("http://www.imdb.com/chart/toptv", headers={'User-agent': 'Mozilla/5.0'}, timeout=20)
            soup = BeautifulSoup.BeautifulSoup(html.text)
            for table in soup.findAll('table'):
                if table.get("class") == "chart full-width":
                    for td in table.findAll('td'):
                        if td.get("class") == "titleColumn":
                            a = td.find("a")
                            if a:
                                url = a.get("href","")
                                imdb_id = url.split("/")[2]
                                imdb_rank = url.split("chttvtp_tt_")[1]
                                results[imdb_id] = imdb_rank

            WINDOW.setProperty(self.tryEncode(cacheStr), repr(results))
            self.top250 = results

    def setJSON(self,method,params):
        json_response = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method" : "%s", "params": %s, "id":1 }' %(method, self.tryEcode(params)))
        jsonobject = json.loads(json_response.decode('utf-8','replace'))
        return jsonobject

    def getJSON(self,method,params):
        json_response = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method" : "%s", "params": %s, "id":1 }' %(method, self.tryEncode(params)))
        jsonobject = json.loads(json_response.decode('utf-8','replace'))
        if(jsonobject.has_key('result')):
            jsonobject = jsonobject['result']
            if isinstance(jsonobject, list):
                return jsonobject
            if jsonobject.has_key('files'):
                return jsonobject['files']
            elif jsonobject.has_key('movies'):
                return jsonobject['movies']
            elif jsonobject.has_key('tvshows'):
                return jsonobject['tvshows']
            elif jsonobject.has_key('episodes'):
                return jsonobject['episodes']
            elif jsonobject.has_key('musicvideos'):
                return jsonobject['musicvideos']
            elif jsonobject.has_key('channels'):
                return jsonobject['channels']
            elif jsonobject.has_key('recordings'):
                return jsonobject['recordings']
            elif jsonobject.has_key('timers'):
                return jsonobject['timers']
            elif jsonobject.has_key('channeldetails'):
                return jsonobject['channeldetails']
            elif jsonobject.has_key('recordingdetails'):
                return jsonobject['recordingdetails']
            elif jsonobject.has_key('songs'):
                return jsonobject['songs']
            elif jsonobject.has_key('albums'):
                return jsonobject['albums']
            elif jsonobject.has_key('songdetails'):
                return jsonobject['songdetails']
            elif jsonobject.has_key('albumdetails'):
                return jsonobject['albumdetails']
            elif jsonobject.has_key('artistdetails'):
                return jsonobject['artistdetails']
            elif jsonobject.get('favourites'):
                return jsonobject['favourites']
            elif jsonobject.has_key('tvshowdetails'):
                return jsonobject['tvshowdetails']
            elif jsonobject.has_key('episodedetails'):
                return jsonobject['episodedetails']
            elif jsonobject.has_key('moviedetails'):
                return jsonobject['moviedetails']
            elif jsonobject.has_key('setdetails'):
                return jsonobject['setdetails']
            elif jsonobject.has_key('musicvideodetails'):
                return jsonobject['musicvideodetails']
            elif jsonobject.has_key('sets'):
                return jsonobject['sets']
            elif jsonobject.has_key('video'):
                return jsonobject['video']
            elif jsonobject.has_key('artists'):
                return jsonobject['artists']
            elif jsonobject.has_key('channelgroups'):
                return jsonobject['channelgroups']
            elif jsonobject.get('sources'):
                return jsonobject['sources']
            elif jsonobject.has_key('addons'):
                return jsonobject['addons']
            elif jsonobject.has_key('item'):
                return jsonobject['item']
            elif jsonobject.has_key('genres'):
                return jsonobject['genres']
            elif jsonobject.has_key('value'):
                return jsonobject['value']
            else:
                return {}
        else:
            return {}

    def listdir(self,file):
        try:
            results = xbmcvfs.listdir(os.path.join(file,''))
            return results
        except:
            return [],[]