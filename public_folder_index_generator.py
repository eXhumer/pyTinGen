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

class GdriveSession:
	def __init__(self, session_headers={}):
		self.session = requests.Session()
		self.session.headers.clear()
		self.session.cookies.clear()
		self.session.headers.update({
			"Accept": "*/*",
			"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 11_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.0 Mobile/15E148 Safari/604.1"
		})
		self.session.headers.update(session_headers)

	def make_request(self, method, url, **options):
		req_headers = {}
		if options.get("referer", False):
			req_headers.update({"Referer": options.get("referer")})
		return self.session.request(method, url, headers=req_headers, verify=False, stream=True)

	def get_files(self, id, j):
		files = []
		page_token = None
		try:
			for _ in range(100):
				url = 'https://clients6.google.com/drive/v2beta/files?openDrive=false&reason=102&syncType=0&errorRecovery=false&q=trashed%20%3D%20false%20and%20%27' + id + '%27%20in%20parents&fields=kind%2CnextPageToken%2Citems(kind%2CfileSize%2Ctitle%2Cid)%2CincompleteSearch&appDataFilter=NO_APP_DATA&spaces=drive&maxResults=500&orderBy=folder%2Ctitle_natural%20asc&key=' + get_key(j)
				
				if page_token is not None:
					url += '&pageToken=' + page_token
				r = self.make_request('GET', url, referer='https://drive.google.com/open?id=' + id)
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
				page_token = j2['nextPageToken']
		except:
			pass
		return files

	def process_dirs(self, ids):
		results = {"files": [], "success": "hello world"}
		for id in ids:
			url = 'https://drive.google.com/open?id=' + id
			r = self.make_request('GET', url)
			j = get_json(r.text)
			results["files"] += self.get_files(id, j)

def get_json(buf):
	try:
		start = buf.index('__initData = ') + len('__initData = ')
		end = buf.index(';', start)
		return json.loads(buf[start:end])
	except:
		return None

def get_key(j):
	try:
		return j[0][9][32][35] # :nospies:
	except:
		return ''

if __name__ == "__main__":
	if sys.argv[1] not in ["-h", "--help"]:
		file_name = sys.argv[1]
		ids = sys.argv[2:]
		gdrive_session = GdriveSession()
		results = gdrive_session.process_dirs(ids)
		with open(file_name, 'w') as outfile:
			json.dump(results, outfile)
	else:
		print("Usage: python3 public_folder_index_generator.py [FOLDER_IDS_TO_SCAN [FOLDER_IDS_TO_SCAN ...]]")