import xbmc,xbmcaddon,xbmcvfs,xbmcgui

ADDON = xbmcaddon.Addon(id='script.tvguide.dvr')

path = xbmc.translatePath('special://home/addons/script.tvguide.dvr/commands.txt')
f = xbmcvfs.File(path,"rb")
data = f.read()
dialog = xbmcgui.Dialog()
dialog.textviewer('Command Keys', data)
