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

import requests, json, urllib.parse, sys, argparse, urllib3, re
from pathlib import Path
from tqdm import tqdm
from CryptoHelpers import encrypt_file

class Gdrive:
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

	def get_files_in_folder_id(self, folder_id):
		pbar = tqdm(desc="Files scanned", unit="file", unit_scale=True)
		files = {}
		page_token = None

		try:
			for _ in range(100): # LIMITS TO 100 PAGES MAXIMUM, SHOULD CHANGE THIS LATER
				url = "https://clients6.google.com/drive/v2beta/files?openDrive=false&reason=102&syncType=0&errorRecovery=false&q=trashed%20%3D%20false%20and%20%27{folder_id}%27%20in%20parents&fields=kind%2CnextPageToken%2Citems(kind%2CfileSize%2Ctitle%2Cid)%2CincompleteSearch&appDataFilter=NO_APP_DATA&spaces=drive&maxResults=500&orderBy=folder%2Ctitle_natural%20asc&key={key}".format(folder_id=folder_id, key=self.get_folder_key(folder_id))
				
				if page_token is not None:
					url = "{url}&pageToken={page_token}".format(url=url, page_token=page_token)

				ls_response = self.make_request("GET", url, referer="https://drive.google.com/open?id={folder_id}".format(folder_id=folder_id))
				ls_json = json.loads(ls_response.text)
				pbar.update(len(ls_json["items"]))

				for drive_file in ls_json["items"]:
					if drive_file["kind"] != "drive#file" and "fileSize" not in drive_file:
						continue

					files.update({drive_file["id"]: {"name": drive_file["title"], "size": int(drive_file["fileSize"])}})

				if "nextPageToken" not in ls_json:
					break

				page_token = ls_json["nextPageToken"]
		except:
			pass

		pbar.close()
		return files

	def get_folder_key(self, folder_id):
		response = self.make_request("GET", "https://drive.google.com/open?id={folder_id}".format(folder_id=folder_id))

		try:
			start = response.text.index("__initData = ") + len("__initData = ")
			end = response.text.index(";", start)
			json_data = json.loads(response.text[start:end])
			return json_data[0][9][32][35] # :nospies:
		except:
			return ""

class UTinGen:
	def __init__(self, index_path="index.tfl"):
		self.index_path = index_path
		self.index_json = {"files": []}
		self.gdrive_service = Gdrive()

	def write_index_to_file(self):
		Path(self.index_path).parent.resolve().mkdir(parents=True, exist_ok=True)
		with open(self.index_path, "w") as output_file:
			json.dump(self.index_json, output_file, indent=2)

	def index_folders(self, folder_ids, success=None, allow_files_without_tid=False):
		for folder_id in folder_ids:
			for (file_id, file_details) in self.gdrive_service.get_files_in_folder_id(folder_id).items():
				if allow_files_without_tid or re.search(r"\%5B[0-9A-Fa-f]{16}\%5D", urllib.parse.quote(file_details["name"], safe="")):
					self.index_json["files"].append({"url": "gdrive:{file_id}#{file_name}".format(file_id=file_id, file_name=urllib.parse.quote(file_details["name"], safe="")), "size": int(file_details["size"])})
		if success is not None:
			self.index_json.update({"success": success})
		self.write_index_to_file()

if __name__ == "__main__":
	urllib3.disable_warnings()
	parser = argparse.ArgumentParser(description="Script that will allow you to easily generate an index file with Google Drive file links for use with Tinfoil without requiring authentication.")
	parser.add_argument(nargs="*", metavar="FOLDER_ID_TO_SCAN", dest="folder_ids", help="Folder ID of Google Drive folders to scan. Can use more than 1 folder IDs at a time. FOLDERS MUST BE PUBLIC FOR SCRIPT TO WORK")
	parser.add_argument("--index-file", metavar="INDEX_FILE_PATH", default="index.tfl", help="File Path for unencrypted index file to update.")
	parser.add_argument("--encrypt", nargs="?", metavar="ENC_INDEX_FILE_PATH", const="enc_index.tfl", help="Use this flag is you want to encrypt the resulting index file.")
	parser.add_argument("--public-key", metavar="PUBLIC_KEY_FILE_PATH", default="public.key", help="File Path for Public Key to encrypt with.")
	parser.add_argument("--success", metavar="SUCCESS_MESSAGE", help="Success Message to add to index.")

	args = parser.parse_args()

	generator = UTinGen(index_path=args.index_file)
	generator.index_folders(args.folder_ids, success=args.success)

	if args.encrypt:
		encrypt_file(args.index_file, args.encrypt, public_key=args.public_key)