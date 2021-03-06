import urllib2, base64, simplejson, time, datetime
json = simplejson

# Static text. 
TEXT_NAME = "TV-Headend Next Generation"
TEXT_TITLE = "TV-Headend" 

# Image resources.
ICON_DEFAULT = "icon-default.png"
ART_DEFAULT = "art-default.jpg"

ICON_ALLCHANS = R("icon_allchans.png")
ICON_BOUQUETS = R("icon_bouquets.png")

# Other definitions.
PLUGIN_PREFIX = "/video/tvheadend-ng"
DEBUG = True
DEBUG_EPG = False 
req_api_version = 15

####################################################################################################

def debug(str):
	if DEBUG == True: Log(str)

def debug_epg(str):
	if DEBUG_EPG == True: Log(str)

####################################################################################################

def Start():
	ObjectContainer.art = R(ART_DEFAULT)
	HTTP.CacheTime = 1

####################################################################################################

@handler(PLUGIN_PREFIX, TEXT_TITLE, ICON_DEFAULT, ART_DEFAULT)
def MainMenu():
	oc = ObjectContainer(no_cache = True)	

	result = checkConfig()
	if result["status"] == True:
		debug("Configuration OK!")
		oc.title1 = TEXT_TITLE
		oc.header = None
		oc.message = None 
		oc = ObjectContainer(title1 = TEXT_TITLE, no_cache = True)
		if Prefs["tvheadend_allchans"] != False:
			oc.add(DirectoryObject(key = Callback(getChannels, title = L("allchans")), title = L("allchans"), thumb = ICON_ALLCHANS))
		if Prefs["tvheadend_tagchans"] != False:
			oc.add(DirectoryObject(key = Callback(getChannelsByTag, title = L("tagchans")), title = L("tagchans"), thumb = ICON_BOUQUETS))
		if Prefs["tvheadend_recordings"] != False:
			oc.add(DirectoryObject(key = Callback(getRecordings, title = L("recordings")), title = L("recordings"), thumb = ICON_BOUQUETS))
		oc.add(PrefsObject(title = L("preferences")))
	else:
		debug("Configuration error! Displaying error message: " + result["message"])
		oc.title1 = None
		oc.header = L("header_attention")
                oc.message = result["message"]
		oc.add(PrefsObject(title = L("preferences")))

	return oc

####################################################################################################

def checkConfig():
	global req_api_version
	result = {
		"status" : False,
		"message" : ""
	}

	if Prefs["tvheadend_user"] and Prefs["tvheadend_pass"] and Prefs["tvheadend_host"] and Prefs["tvheadend_web_port"]:
		# To validate the tvheadend connection and api version.
		json_data = getTVHeadendJson("getServerVersion", "")
		if json_data != False:
			if json_data["api_version"] == req_api_version:
				result["status"] = True
				result["message"] = ""
				return result
			else:
				result["status"] = False
				result["message"] = L("error_api_version")
				return result
		else:
			result["status"] = False
			result["message"] = L("error_unknown")
			return result
	else:
		result["status"] = False
		result["message"] = L("error_connection")
		return result

def getTVHeadendJson(apirequest, arg1):
	debug("JSON-Request: " + apirequest)
	api = dict(
		getChannelGrid="api/channel/grid?start=0&limit=999999",
		getEpgGrid="api/epg/events/grid?start=0&limit=1000",
		getIdNode="api/idnode/load?uuid=" + arg1,
		getServiceGrid="api/mpegts/service/grid?start=0&limit=999999",
		getMuxGrid="api/mpegts/mux/grid?start=0&limit=999999",
		getChannelTags="api/channeltag/grid?start=0&limit=999999",
		getServerVersion="api/serverinfo",
		getRecordings="api/dvr/entry/grid_finished"
	)

	try:
		base64string = base64.encodestring("%s:%s" % (Prefs["tvheadend_user"], Prefs["tvheadend_pass"])).replace("\n", "")
		request = urllib2.Request("http://%s:%s/%s" % (Prefs["tvheadend_host"], Prefs["tvheadend_web_port"], api[apirequest]))
		request.add_header("Authorization", "Basic %s" % base64string)
		response = urllib2.urlopen(request)

		json_tmp = response.read().decode("utf-8")
		json_data = json.loads(json_tmp)
	except Exception, e:
		debug("JSON-Request failed: " + str(e))
		return False
	debug("JSON-Request successfull!")
	return json_data

####################################################################################################

def getEPG():
	json_data = getTVHeadendJson("getEpgGrid","")
	if json_data != False:
		debug_epg("Got EPG: " + json.dumps(json_data))
	else:
		debug_epg("Failed to fetch EPG!")	
	return json_data

def getChannelInfo(uuid, services, json_epg):
	result = {
		"iconurl":"",
		"epg_title":"",
		"epg_description":"",
		"epg_duration":0,
		"epg_start":0,
		"epg_stop":0,
		"epg_summary":"",
	}

	json_data = getTVHeadendJson("getIdNode", uuid)
	if json_data["entries"][0]["params"][2].get("value"):
		result["iconurl"] = json_data["entries"][0]["params"][2].get("value")

	# Check if we have data within the json_epg object.
	if json_epg != False and json_epg.get("entries"):
		for epg in json_epg["entries"]:
			if epg["channelUuid"] == uuid and time.time() > int(epg["start"]) and time.time() < int(epg["stop"]):
				if Prefs["tvheadend_channelicons"] == True and epg.get("channelIcon") and epg["channelIcon"].startswith("imagecache"):
					result["iconurl"] = "http://%s:%s/%s" % (Prefs["tvheadend_host"], Prefs["tvheadend_web_port"], epg["channelIcon"])
				if epg.get("title"):
					result["epg_title"] = epg["title"];
				if epg.get("description"):
					result["epg_description"] = epg["description"];
				if epg.get("start"):
					result["epg_start"] = time.strftime("%H:%M", time.localtime(int(epg["start"])));
				if epg.get("stop"):
					result["epg_stop"] = time.strftime("%H:%M", time.localtime(int(epg["stop"])));
				if epg.get("start") and epg.get("stop"):
					result["epg_duration"] = (epg.get("stop") - epg.get("start")) * 1000;
	return result

def getRecordingsInfo(uuid):
	result = {
		"iconurl":"",
		"rec_title":"",
		"rec_description":"",
		"rec_duration":0,
		"rec_start":"",
		"rec_stop":"",
		"rec_summary":"",
	}

	json_data = getTVHeadendJson("getIdNode", uuid)
	if json_data["entries"][0]["params"][8].get("value"):
		result["iconurl"] = json_data["entries"][0]["params"][8].get("value")
	if json_data["entries"][0]["params"][11].get("value"):
		result["rec_title"] = json_data["entries"][0]["params"][11].get("value")
	if json_data["entries"][0]["params"][13].get("value"):
		result["rec_description"] = json_data["entries"][0]["params"][13].get("value")
	if json_data["entries"][0]["params"][0].get("value"):
		result["rec_start"] = datetime.datetime.fromtimestamp(json_data["entries"][0]["params"][0].get("value")).strftime("%d-%m-%Y %H:%M")
	if json_data["entries"][0]["params"][3].get("value"):
		result["rec_stop"] = datetime.datetime.fromtimestamp(json_data["entries"][0]["params"][3].get("value")).strftime("%d-%m-%Y %H:%M")			
	if json_data["entries"][0]["params"][6].get("value"):
		result["rec_duration"] = json_data["entries"][0]["params"][6].get("value")*1000	
	return result

####################################################################################################

def getChannelsByTag(title):
	json_data = getTVHeadendJson("getChannelTags", "")
	tagList = ObjectContainer(no_cache=True)

	if json_data != False:
		tagList.title1 = L("tagchans")
		tagList.header = None
		tagList.message = None
		for tag in sorted(json_data["entries"], key=lambda t: t["name"]):
			if tag["internal"] == False:
				debug("Getting channellist for tag: " + tag["name"])
				tagList.add(DirectoryObject(key = Callback(getChannels, title = tag["name"], tag = tag["uuid"]), title = tag["name"]))
	else:
		debug("Could not create tagelist! Showing error.")
		tagList.title1 = None
		tagList.header = L("error")
		tagList.message = L("error_request_failed") 

	debug("Count of configured tags within TV-Headend: " + str(len(tagList)))
	if ( len(tagList) == 0 ):
		tagList.header = L("attention")
		tagList.message = L("error_no_tags")
	return tagList 

def getChannels(title, tag = int(0)):
	json_data = getTVHeadendJson("getChannelGrid", "")
	json_epg = getEPG()
	channelList = ObjectContainer(no_cache=True)

	if json_data != False:
		channelList.title1 = title
		channelList.header = None
		channelList.message = None
		for channel in sorted(json_data["entries"], key=lambda t: t["number"]):
			if tag > 0:
				tags = channel["tags"]
				for tids in tags:
					if (tag == tids):
						debug("Got channel with tag: " + channel["name"])
						chaninfo = getChannelInfo(channel["uuid"], channel["services"], json_epg)
						channelList.add(createTVChannelObject(channel, chaninfo, Client.Product, Client.Platform))
			else:
				chaninfo = getChannelInfo(channel["uuid"], channel["services"], json_epg)
				channelList.add(createTVChannelObject(channel, chaninfo, Client.Product, Client.Platform))
	else:
		debug("Could not create channellist! Showing error.")
		channelList.title1 = None;
		channelList.header = L("error")
		channelList.message = L("error_request_failed")
       	return channelList

def getRecordings(title):
	json_data = getTVHeadendJson("getRecordings", "")
	recordingsList = ObjectContainer(no_cache=True)

	if json_data != False:
		recordingsList.title1 = L("recordings")
		recordingsList.header = None
		recordingsList.message = None
		for recording in sorted(json_data["entries"], key=lambda t: t["title"]):
			debug("Got recordings with title: " + str(recording["title"]))
			recordinginfo = getRecordingsInfo(recording["uuid"])
			recordingsList.add(createRecordingObject(recording, recordinginfo, Client.Product, Client.Platform))
	else:
		debug("Could not create recordings list! Showing error.")
		recordingsList.title1 = None
		recordingsList.header = L("error")
		recordingsList.message = L("error_request_failed") 

	debug("Count of recordings within TV-Headend: " + str(len(recordingsList)))
	if len(recordingsList) == 0:
		recordingsList.header = L("attention")
		recordingsList.message = L("error_no_recordings")
	return recordingsList 

####################################################################################################

def PlayVideo(url):
	return Redirect(url)

def addMediaObject(vco, vurl):
	media = MediaObject(
		optimized_for_streaming = True,
		parts = [PartObject(key = Callback(PlayVideo, url=vurl))],
		video_codec = VideoCodec.H264,
		audio_codec = AudioCodec.AAC,
	)
	vco.add(media)
	debug("Creating MediaObject for streaming with URL: " + vurl)
	return vco

def createVideoChannelObject(url_path, vco, cproduct, cplatform, container):
	if not cproduct: cproduct = "undefined"
	if not cplatform: cplatform = "undefined"

	# Build streaming url.
	url = "http://%s:%s@%s:%s/%s" % (Prefs["tvheadend_user"], Prefs["tvheadend_pass"],
									Prefs["tvheadend_host"], Prefs["tvheadend_web_port"],
									url_path)

	# Decide if we have to stream for native streaming devices or if we have to transcode the content.
	if Prefs["tvheadend_mpegts_passthrough"] == True or cproduct == "Plex Home Theater" or cproduct == "PlexConnect":
		url += "?profile=pass"
	elif Prefs["tvheadend_custprof_ios"] and cplatform == "iOS":
		# Custom streaming profile for iOS.
		url += "?profile=" + Prefs["tvheadend_custprof_ios"]
	elif Prefs["tvheadend_custprof_android"] and cplatform == "Android":
    	# Custom streaming profile for Android.
		url += "?profile=" + Prefs["tvheadend_custprof_android"]
	elif Prefs["tvheadend_custprof_default"]:
        # Custom default streaming.
		url += "?profile=" + Prefs["tvheadend_custprof_default"]
	else:
		# Default streaming.
		pass

	vco = addMediaObject(vco, url)

	# Log the product and platform which requested a stream.
	debug("Created VideoObject for '" + cproduct + "' plex product on '" + cplatform + "' platform")
	# Log the url
	debug("Created VideoObject with URL: " + url)

	if container: return ObjectContainer(objects = [vco])
	return vco

def createTVChannelObject(channel, chaninfo, cproduct, cplatform, container = False):
	debug("Creating TVChannelObject. Container: " + str(container))
	title = channel["name"] 
	thumb = chaninfo["iconurl"] if chaninfo["iconurl"] else ""
	id = channel["uuid"] 
	summary = ""
	duration = 0

	# Add epg data. Otherwise leave the fields blank by default.
	debug("Info for mediaobject: " + str(chaninfo))
	if chaninfo["epg_title"] != "" and chaninfo["epg_start"] != 0 and chaninfo["epg_stop"] != 0 and chaninfo["epg_duration"] != 0:
		if container == False:
			title += " (" + chaninfo["epg_title"] + ") - (" + chaninfo["epg_start"] + " - " + chaninfo["epg_stop"] + ")"
			summary = ""
		else:
			summary = chaninfo["epg_title"] + "\n" + chaninfo["epg_start"] + " - " + chaninfo["epg_stop"] + "\n\n" + chaninfo["epg_description"] 
		duration = chaninfo["epg_duration"]
		#summary = "%s (%s-%s)\n\n%s" % (chaninfo["epg_title"],chaninfo["epg_start"],chaninfo["epg_stop"], chaninfo["epg_description"])

	key = Callback(createTVChannelObject, channel = channel, chaninfo = chaninfo, cproduct = cproduct, cplatform = cplatform, container = True)
	# Create raw VideoClipObject.
	vco = VideoClipObject(
		key = key,
		rating_key = id,
		title = title,
		summary = summary,
		duration = duration,
		thumb = thumb,
	)

	url_path = "stream/channel/" + id

	return createVideoChannelObject(url_path, vco, cproduct, cplatform, container);

def createRecordingObject(recording, recordinginfo, cproduct, cplatform, container = False):
	debug("Creating RecordingObject. Container: " + str(container))
	title = recordinginfo["rec_title"] 
	thumb = recordinginfo["iconurl"] if recordinginfo["iconurl"] else ""
	id = recording["uuid"] 
	summary = ""
	duration = 0

	# Add epg data. Otherwise leave the fields blank by default.
	debug("Info for mediaobject: " + str(recordinginfo))
	if recordinginfo["rec_title"] and recordinginfo["rec_start"] != 0 and recordinginfo["rec_stop"] != 0 and recordinginfo["rec_duration"] != 0:
		if container == False:
			title += " (" + recordinginfo["rec_title"] + ") - (" + recordinginfo["rec_start"] + " - " + recordinginfo["rec_stop"] + ")"
			summary = recordinginfo["rec_description"]
		else:
			summary = recordinginfo["rec_title"] + "\n" + recordinginfo["rec_start"] + " - " + recordinginfo["rec_stop"] + "\n\n" + recordinginfo["rec_description"] 
		duration = recordinginfo["rec_duration"]

	key = Callback(createRecordingObject, recording = recording, recordinginfo = recordinginfo, cproduct = cproduct, cplatform = cplatform, container = True)
	# Create raw VideoClipObject.
	vco = VideoClipObject(
		key = key,
		rating_key = id,
		title = title,
		summary = summary,
		duration = duration,
		thumb = thumb,
	)

	url_path = "dvrfile/" + id

	return createVideoChannelObject(url_path, vco, cproduct, cplatform, container);
