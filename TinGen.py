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

from googleapiclient.discovery import build as google_api_build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import TransportError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
from pathlib import Path
from tqdm import tqdm
from CryptoHelpers import encrypt_file
import socket, json, argparse, urllib.parse, time, re

class GDrive:
    def __init__(self, token_path, credentials_path, headless=False):
        credentials = self._get_creds(credentials=credentials_path, token=token_path, headless=headless)
        self.drive_service = google_api_build("drive", "v3", credentials=credentials)

    def _cred_to_json(self, cred_to_pass):
        cred_json = {
            'access_token': cred_to_pass.token,
            'refresh_token': cred_to_pass.refresh_token
        }
        return cred_json

    def _json_to_cred(self, json_to_pass, client_id, client_secret):
        cred_json = json.load(json_to_pass)
        creds = Credentials(
            cred_json['access_token'],
            refresh_token=cred_json['refresh_token'],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        return creds

    def _get_creds(self, credentials="credentials.json", token="gdrive.token", scopes=['https://www.googleapis.com/auth/drive'], headless=False):
        if Path(credentials).is_file():
            with open(credentials, "r") as c:
                cred_json = json.load(c)
            creds = None
            if Path(token).is_file():
                with open(token, "r") as t:
                    creds = self._json_to_cred(t, cred_json["installed"]["client_id"], cred_json["installed"]["client_secret"])
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials, scopes)
                    if headless:
                        creds = flow.run_console()
                    else:
                        creds = flow.run_local_server(port=0)
                with open(token, "w") as t:
                    json.dump(self._cred_to_json(creds), t, indent=2)
            return creds

    def _apicall(self, request, maximum_backoff=32):
        sleep_exponent_count = 0
        while True:
            success = True
            retry = False
            try:
                response = request.execute()
            except HttpError as error:
                success = False
                try:
                    error_details = json.loads(error.content.decode("utf-8"))["error"]
                except json.decoder.JSONDecodeError as error:
                    retry = True
                else:
                    if "errors" in error_details:
                        if error_details["errors"][0]["reason"] in ("dailyLimitExceeded", "userRateLimitExceeded", "rateLimitExceeded", "backendError", "sharingRateLimitExceeded", "failedPrecondition", "internalError", "domainPolicy", "insufficientFilePermissions", "appNotAuthorizedToFile"): # IF REQUEST IS RETRYABLE
                            retry = True
                    else:
                        raise error
            except (TransportError, socket.error, socket.timeout) as error:
                success = False
                retry = True
            if success:
                break
            if retry:
                sleep_time = 2^sleep_exponent_count
                if sleep_time < maximum_backoff:
                    time.sleep(sleep_time)
                    sleep_exponent_count += 1
                    continue
                else:
                    raise Exception("Maximum Backoff Limit Exceeded.")
            else:
                raise Exception("Unretryable Error")
        return response

    def _ls(self, folder_id, fields="files(id,name,size,permissionIds),nextPageToken", searchTerms=""):
        files = []
        resp = {"nextPageToken": None}
        while "nextPageToken" in resp:
            resp = self._apicall(self.drive_service.files().list(
                q = " and ".join(["\"%s\" in parents" % folder_id] + [searchTerms] + ["trashed = false"]),
                fields = fields,
                pageSize = 1000,
                supportsAllDrives = True,
                includeItemsFromAllDrives = True,
                pageToken = resp["nextPageToken"]
            ))
            files += resp["files"]
        return files

    def _lsd(self, folder_id):
        return self._ls(
            folder_id,
            searchTerms="mimeType contains \"application/vnd.google-apps.folder\""
        )

    def _lsf(self, folder_id, fields="files(id,name,size,permissionIds),nextPageToken"):
        return self._ls(
            folder_id,
            fields=fields,
            searchTerms="not mimeType contains \"application/vnd.google-apps.folder\""
        )

    def check_file_shared(self, file_to_check):
        shared = False
        if "permissionIds" in file_to_check:
            for permissionId in file_to_check["permissionIds"]:
                if permissionId[-1] == "k" and permissionId[:-1].isnumeric():
                    self.delete_file_permission(file_to_check["id"], permissionId)
                if permissionId == "anyoneWithLink":
                    shared = True
        return shared

    def delete_file_permission(self, file_id, permission_id):
        self._apicall(self.drive_service.permissions().delete(fileId=file_id, permissionId=permission_id, supportsAllDrives=True))

    def get_all_files_in_folder(self, folder_id, dict_files, dict_blacklist, recursion=True, files_pbar=None):
        for _file in self._lsf(folder_id):
            if "size" in _file:
                dict_files.update({_file["id"]: {"size": _file["size"], "name": _file["name"], "shared": self.check_file_shared(_file)}})
                if files_pbar is not None:
                    files_pbar.update(1)
                
        if recursion:
            for _folder in self._lsd(folder_id):
                self.get_all_files_in_folder(_folder["id"], dict_files, dict_blacklist, recursion=recursion, files_pbar=files_pbar)

    def share_file(self, file_id_to_share):
        self._apicall(self.drive_service.permissions().create(fileId=file_id_to_share, supportsAllDrives=True, body={
            "role": "reader",
            "type": "anyone"
        }))

    def upload_file(self, file_path, dest_folder_id=None):
        media = MediaFileUpload(file_path)
        if dest_folder_id is None:
            response = self._apicall(self.drive_service.files().create(media_body=media, body={"name": Path(file_path).name}, supportsAllDrives=True))
        else:
            response = self._apicall(self.drive_service.files().create(media_body=media, body={"name": Path(file_path).name, "parents": [dest_folder_id]}, supportsAllDrives=True))

        if "id" in response:
            self.share_file(response["id"])
            print("Add the following to tinfoil: gdrive:/{file_id}#{file_name}".format(file_id=response["id"], file_name=response["name"]))

class TinGen:
    def __init__(self, credentials_path="credentials.json", token_path="gdrive.token", index_path="index.tfl", regenerate_index=False, headless=False):
        self.index_path = index_path
        self.files_to_share = []
        self.gdrive_service = GDrive(token_path=token_path, credentials_path=credentials_path)
        self.index_json = {}
        if Path(self.index_path).is_file() and not regenerate_index:
            with open(self.index_path, "r") as index_json:
                try:
                    self.index_json = json.loads(index_json.read())
                except json.JSONDecodeError:
                    raise Exception("Error while trying to read the index json file. Make sure that it is a valid JSON file.")
        if "files" not in self.index_json:
            self.index_json.update({"files": []})
            self._update_index_file()

    def _update_index_file(self):
        Path(self.index_path).parent.resolve().mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w") as output_file:
            json.dump(self.index_json, output_file, indent=2)

    def index_updater(self, folder_ids, share_files=None, recursion=True, success=None, allow_files_without_tid=False):
        files_pbar = tqdm(desc="Files scanned", unit="file", unit_scale=True)
        all_files = {}
        for folder_id in folder_ids:
            self.gdrive_service.get_all_files_in_folder(folder_id, all_files, self.index_json["files"], recursion=recursion, files_pbar=files_pbar)
        files_pbar.close()
        for (file_id, file_details) in all_files.items():
            share_file = False
            if allow_files_without_tid or re.search(r"\%5B[0-9A-Fa-f]{16}\%5D", urllib.parse.quote(file_details["name"], safe="")):
                check = {"url": "gdrive:{file_id}#{file_name}".format(file_id=file_id, file_name=urllib.parse.quote(file_details["name"], safe="")), "size": int(file_details["size"])}
                if check not in self.index_json["files"]:
                    self.index_json["files"].append(check)
                    if share_files == "update" and not file_details["shared"]:
                        share_file = True
                if not share_file and share_files == "all" and not file_details["shared"]:
                    share_file = True
                if share_file:
                    self.files_to_share.append(file_id)
        if len(self.files_to_share) > 0:
            for i in tqdm(range(len(self.files_to_share)), desc="File Share Progress"):
                self.gdrive_service.share_file(self.files_to_share[i])
        if success is not None:
            self.index_json.update({"success": success})
        self._update_index_file()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script that will allow you to easily generate an index file with Google Drive file links for use with Tinfoil.")
    parser.add_argument(nargs="*", metavar="FOLDER_ID_TO_SCAN", dest="folder_ids", help="Folder ID of Google Drive folders to scan. Can use more than 1 folder IDs at a time.")
    parser.add_argument("--upload-to-folder-id", metavar="UPLOAD_FOLDER_ID", dest="upload_folder_id", help="Upload resulting index to folder id supplied.")
    parser.add_argument("--upload-to-my-drive", action="store_true", help="Upload resulting index to My Drive")
    parser.add_argument("--share-files", choices=["update", "all"], nargs="?", const="update", help="Use this flag if you want to share files that gets newly added to your index file. If you want to share files that was already added to your old index file, use \"--share-files all\"")
    parser.add_argument("--credentials", default="credentials.json", metavar="CREDENTIALS_FILE_NAME", help="Obtainable from https://developers.google.com/drive/api/v3/quickstart/python. Make sure to select the correct account before downloading the credentails file.")
    parser.add_argument("--token", default="gdrive.token", metavar="TOKEN_FILE_PATH", help="File Path of a Google Token file.")
    parser.add_argument("--index-file", metavar="INDEX_FILE_PATH", default="index.tfl", help="File Path for unencrypted index file to update.")
    parser.add_argument("--encrypt", nargs="?", metavar="ENC_INDEX_FILE_PATH", const="enc_index.tfl", help="Use this flag is you want to encrypt the resulting index file.")
    parser.add_argument("--public-key", metavar="PUBLIC_KEY_FILE_PATH", default="public.key", help="File Path for Public Key to encrypt with.")
    parser.add_argument("--disable-recursion", dest="recursion", action="store_false", help="Use this flag to stop folder IDs entered from being recusively scanned. (It basically means if you use this flag, the script will only add the files at the root of each folder ID passed, without going through the sub-folders in it.")
    parser.add_argument("--success", metavar="SUCCESS_MESSAGE", help="Success Message to add to index.")
    parser.add_argument("--regenerate-index", action="store_true", help="Use this flag if you want to regenrate the index file from scratch instead of appending to old index file.")
    parser.add_argument("--headless", action="store_true", help="Use this flag if you want to use the script in a headless environment.")

    args = parser.parse_args()
    generator = TinGen(token_path=args.token, credentials_path=args.credentials, index_path=args.index_file, regenerate_index=args.regenerate_index, headless=args.headless)
    generator.index_updater(args.folder_ids, share_files=args.share_files, recursion=args.recursion, success=args.success)

    upload_file = args.index_file

    if args.encrypt:
        encrypt_file(args.index_file, args.encrypt, public_key=args.public_key)
        upload_file = args.encrypt

    if args.upload_folder_id:
        generator.gdrive_service.upload_file(upload_file, args.upload_folder_id)
    if args.upload_to_my_drive:
        generator.gdrive_service.upload_file(upload_file)