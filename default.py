#     Copyright (C) 2020 Team-Kodi
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# -*- coding: utf-8 -*-

from datetime import timedelta as datetime_timedelta
from json import loads as json_loads
from os.path import join as os_path_join, sep as os_path_sep
from re import compile as re_compile, search as re_search
from simplecache import SimpleCache
from six import PY2
from six.moves import urllib
from socket import setdefaulttimeout as socket_setdefaulttimeout
from time import time as time_time
from traceback import format_exc as traceback_format_exc
from xbmc import executebuiltin as xbmc_executebuiltin, executeJSONRPC as xbmc_executeJSONRPC, log as xbmc_log, \
    LOGDEBUG as xbmc_LOGDEBUG, LOGERROR as xbmc_LOGERROR, Monitor as xbmc_Monitor
from xbmcaddon import Addon as xbmcaddon_Addon
from xbmcgui import Dialog as xbmcgui_Dialog, DialogProgress as xbmcgui_DialogProgress, ListItem as xbmcgui_ListItem
from xbmcvfs import delete as xbmcvfs_delete, exists as xbmcvfs_exists

if PY2:
    from xbmc import translatePath as xbmcvfs_translatePath
else:
    from xbmcvfs import translatePath as xbmcvfs_translatePath

# Plugin Info
ADDON_ID      = 'script.kodinerds.android.update'
REAL_SETTINGS = xbmcaddon_Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = '/storage/emulated/0/download'
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
TIMEOUT   = 15
MIN_VER   = 5 #Minimum Android Version Compatible with Kodi
MAIN      = [
    {'Matrix': 'https://www.dropbox.com/sh/0n37s3j3iybww9q/AABN74pzb3CMJBiI76r4jZ48a?dl=0'},
    {'Matrix-FireTV': 'https://www.dropbox.com/sh/7n9tnp70jtjwegt/AAD2VUyUSJEq_iRyfxoHUTjHa?dl=0'},
    {'Nexus': 'https://www.dropbox.com/sh/5fjkqnuvwa7z3ml/AACcKF7nZJyQrlc-mCb_k3A8a?dl=0'},
    {'Nexus-FireTV': 'https://www.dropbox.com/sh/nmgbffz13vqtpza/AABawAkbvlsb4Z7HrfDFXjxwa?dl=0'}
]
DEBUG     = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
CLEAN     = REAL_SETTINGS.getSetting('Disable_Maintenance') == 'false'
VERSION   = REAL_SETTINGS.getSetting('Version')
CUSTOM    = (REAL_SETTINGS.getSetting('Custom_Manager') or 'com.android.documentsui')
FMANAGER  = {0:'com.android.documentsui',1:CUSTOM}[int(REAL_SETTINGS.getSetting('File_Manager'))]


def log(msg, level=xbmc_LOGDEBUG):
    if DEBUG == False and level != xbmc_LOGERROR: return
    if level == xbmc_LOGERROR: msg += ', {0}'.format(traceback_format_exc())
    xbmc_log('[{0}-{1}] {2}'.format(ADDON_ID, ADDON_VERSION, msg), level)

def selectDialog(label, items, pselect=-1, uDetails=True):
    select = xbmcgui_Dialog().select(label, items, preselect=pselect, useDetails=uDetails)
    if select >= 0: return select
    return None

socket_setdefaulttimeout(TIMEOUT)
class Installer(object):
    def __init__(self):
        self.myMonitor = xbmc_Monitor()
        self.cache = SimpleCache()
        if not self.chkVersion(): return
        self.buildMain('')
        
        
    def disable(self, build):
        xbmcgui_Dialog().notification(ADDON_NAME, VERSION, ICON, 8000)
        if not xbmcgui_Dialog().yesno(ADDON_NAME, LANGUAGE(30011).format(build), LANGUAGE(30012)): return False 
        xbmc_executeJSONRPC('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":"{0}","enabled":false}, "id": 1}'.format(ADDON_ID))
        xbmcgui_Dialog().notification(ADDON_NAME, LANGUAGE(30009), ICON, 4000)
        return False
        
        
    def chkVersion(self):
        try: 
            build = int(re_compile('Android (\d+)').findall(VERSION)[0])
        except: build = MIN_VER
        if build >= MIN_VER: return True
        else: return self.disable(build)
        

    def getAPKs(self, url):     
        log('getAPKs: path = {0}'.format(url))
        try:
            cacheResponse = self.cache.get('{0}.openURL, url = {1}'.format(ADDON_NAME, url))
            if not cacheResponse:
                cacheResponse = dict(entries=list())
                if url == '':
                    for item in MAIN:
                        for key in item.keys():
                            entry = dict()
                            entry.update(dict(tag='folder'))
                            entry.update(dict(name=key))
                            entry.update(dict(path_display=item[key]))
                            cacheResponse.get('entries').append(entry)
                else:
                    request = urllib.request.Request(url)
                    string_json = re_search('responseReceived\("(.*)"\)}\)', urllib.request.urlopen(request, timeout = TIMEOUT).read().decode('utf-8'))
                    if string_json:
                        json_entries = json_loads(string_json.group(1).replace('\\', '')).get('entries')
                        for json_entry in json_entries:
                            entry = dict()
                            href = json_entry.get('href')
                            if json_entry.get('is_dir'):
                                entry.update(dict(tag='folder'))
                            else:
                                entry.update(dict(tag='file'))
                                entry.update(dict(size=json_entry.get('bytes')))
                                href = href.replace('dl=0', 'dl=1')
                            entry.update(dict(name=json_entry.get('filename')))
                            entry.update(dict(path_display=href))
                            cacheResponse.get('entries').append(entry)

                self.cache.set('{0}.openURL, url = {1}'.format(ADDON_NAME, url), cacheResponse, expiration=datetime_timedelta(minutes=5))
            return cacheResponse
        except Exception as e:
            log('openURL Failed! {0}'.format(e), xbmc_LOGERROR)
            xbmcgui_Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return None
        
            
    def buildItems(self, path):
        entries = self.getAPKs(path).get('entries', {})
        if entries is None or len(entries) == 0: return
        for entry in entries:
            if entry.get('tag') == 'file' and entry.get('name').endswith('.apk'):
                label = entry.get('name')
                li = xbmcgui_ListItem(label, '{0} {1:.02f} MB'.format(label.split('.apk')[1], entry.get('size') / 1024 / 1024).replace('.', ','), path=entry.get('path_display'))
                li.setArt({'icon': ICON})
                yield (li)
            elif entry.get('tag') == 'folder':
                label = entry.get('name')
                li = xbmcgui_ListItem(label, path=entry.get('path_display'))
                li.setArt({'icon': ICON})
                yield (li)
        
        
    def buildMain(self, path):
        log('buildMain')
        items  = list(self.buildItems(path))
        if len(items) == 0: return
        else: select = selectDialog(ADDON_NAME, items)
        if select is None or select < 0: return #return on cancel.
        newURL = items[select].getPath()
        if newURL.find('.apk') > 0: 
            dest = xbmcvfs_translatePath(os_path_join(SETTINGS_LOC, items[select].getLabel()))
            REAL_SETTINGS.setSetting("LastPath", dest)
            return self.downloadAPK(items[select].getPath(), dest)
        else:
            self.buildMain(newURL)
                

    def fileExists(self, dest):
        if xbmcvfs_exists(dest):
            if not xbmcgui_Dialog().yesno(ADDON_NAME, '{0}: {1}'.format(LANGUAGE(30004), dest.rsplit(os_path_sep, 1)[-1]), nolabel=LANGUAGE(30005), yeslabel=LANGUAGE(30006)): return True
        elif CLEAN and xbmcvfs_exists(dest): self.deleleAPK(dest)
        return False
        
        
    def deleleAPK(self, path):
        count = 0
        #some file systems don't release the file lock instantly.
        while not self.myMonitor.abortRequested() and count < 3:
            count += 1
            if self.myMonitor.waitForAbort(1): return 
            try: 
                if xbmcvfs_delete(path): return
            except: pass
            
        
    def downloadAPK(self, url, dest):
        if self.fileExists(dest): return self.installAPK(dest)
        start_time = time_time()
        dia = xbmcgui_DialogProgress()
        fle = dest.rsplit(os_path_sep, 1)[1]
        dia.create(ADDON_NAME, LANGUAGE(30002).format(fle))
        try: urllib.request.urlretrieve(url, dest, lambda nb, bs, fs: self.pbhook(nb, bs, fs, dia, start_time, fle))
        except Exception as e:
            dia.close()
            xbmcgui_Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            log('downloadAPK, Failed! ({0}) {1}'.format(url, e), xbmc_LOGERROR)
            return self.deleleAPK(dest)
        dia.close()
        return self.installAPK(dest)
        
        
    def pbhook(self, numblocks, blocksize, filesize, dia, start_time, fle):
        try: 
            percent = min(numblocks * blocksize * 100 / filesize, 100) 
            currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
            kbps_speed = numblocks * blocksize / (time_time() - start_time) 
            if kbps_speed > 0: eta = int((filesize - numblocks * blocksize) / kbps_speed)
            else: eta = 0 
            kbps_speed = kbps_speed / 1024 
            if eta < 0: eta = divmod(0, 60)
            else: eta = divmod(eta, 60)
            total   = (float(filesize) / (1024 * 1024))
            label   = '[B]Downloading: [/B] {0}'.format(os_path_join(SETTINGS_LOC, fle))
            label2  = '{0:.02f} MB of {1:.02f} MB'.format(currently_downloaded,total)
            label2 += ' | [B]Speed:[/B] {0:.02f} Kb/s'.format(kbps_speed)
            label2 += ' | [B]ETA:[/B] {0:02d}:{1:02d}'.format(eta[0], eta[1])
            dia.update(int(percent), '{0} {1}'.format(label, label2.replace('.', ',')))
        except Exception('Download Failed'): dia.update(100)
        if dia.iscanceled(): raise Exception('Download Canceled')
            
            
    def installAPK(self, apkfile):
        xbmc_executebuiltin('StartAndroidActivity({0},,,"content://{1}")'.format(FMANAGER, apkfile))


if __name__ == '__main__': Installer()