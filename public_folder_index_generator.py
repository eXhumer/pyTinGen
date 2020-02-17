# Copyright 2020 eXhumer

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import requests, json, urllib.parse, sys

def makeRequest(method, url, hdArgs={}, start = None, end = None, accept = '*/*', referer = None):
	reqHd = {
		'Accept': accept,
		'Referer': referer,
		'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.0 Mobile/15E148 Safari/604.1'
	}
	reqHd.update(hdArgs)
	r = requests.request(method, url, headers=reqHd, verify=False, stream=True)
	return r

def getJson(buf):
	try:
		start = buf.index('__initData = ') + len('__initData = ')
		end = buf.index(';', start)
		return json.loads(buf[start:end])
	except:
		return None

def getKey(j):
	try:
		return j[0][9][32][35] # :nospies:
	except:
		return ''

def getFiles(id, j):
	files = []
	pageToken = None
	try:
		for _ in range(100):
			url = 'https://clients6.google.com/drive/v2beta/files?openDrive=false&reason=102&syncType=0&errorRecovery=false&q=trashed%20%3D%20false%20and%20%27' + id + '%27%20in%20parents&fields=kind%2CnextPageToken%2Citems(kind%2CfileSize%2Ctitle%2Cid)%2CincompleteSearch&appDataFilter=NO_APP_DATA&spaces=drive&maxResults=500&orderBy=folder%2Ctitle_natural%20asc&key=' + getKey(j)
			
			if pageToken is not None:
				url += '&pageToken=' + pageToken

			r = makeRequest('GET', url, referer = 'https://drive.google.com/open?id=' + id)

			j2 = json.loads(r.text)
			print(j2)

			for a in j2['items']:
				if a['kind'] != "drive#file":
					continue
				if 'fileSize' in a:
					files.append({'url': 'gdrive:' + a["id"] + '#' + urllib.parse.quote(a['title'], safe=''), 'size': int(a['fileSize'])})
				else:
					files.append({'url': 'gdrive:' + a["id"] + '#' + urllib.parse.quote(a['title'], safe='') })
			if 'nextPageToken' not in j2:
				break
			pageToken = j2['nextPageToken']
	except:
		pass

	return files

def processDir(id):
	url = 'https://drive.google.com/open?id=' + id

	r = makeRequest('GET', url)
	j = getJson(r.text)
	return getFiles(id, j)

if __name__ == "__main__":
	ids = sys.argv[2:]
	fileName = sys.argv[1]

	result = {'files': [], 'success': 'hello world'}
	for id in ids:
		result['files'] += processDir(id)

	with open(fileName, 'w') as outfile:
		json.dump(result, outfile)