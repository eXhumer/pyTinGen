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
from pathlib import Path
from tqdm import tqdm
from _crypto import encrypt_file
import socket, json, argparse, urllib.parse, time

class gdrive():
    def __init__(self, token_path, credentials_path):
        credentials = self._get_creds(credentials=credentials_path, token=token_path)
        self.drive_service = google_api_build("drive", "v3", credentials=credentials)

    def _cred_to_json(self, cred_to_pass):
        cred_json = {
            'token': cred_to_pass.token,
            'refresh_token': cred_to_pass.refresh_token,
            'id_token': cred_to_pass.id_token,
            'token_uri': cred_to_pass.token_uri,
            'client_id': cred_to_pass.client_id,
            'client_secret': cred_to_pass.client_secret,
        }
        return cred_json

    def _json_to_cred(self, json_to_pass):
        cred_json = json.load(json_to_pass)
        creds = Credentials(
            cred_json['token'],
            refresh_token=cred_json['refresh_token'],
            id_token=cred_json['id_token'],
            token_uri=cred_json['token_uri'],
            client_id=cred_json['client_id'],
            client_secret=cred_json['client_secret']
        )
        return creds

    def _get_creds(self, credentials="credentials.json", token="token.json", scopes=['https://www.googleapis.com/auth/drive']):
        if Path(credentials).is_file():
            creds = None
            if Path(token).is_file():
                with open(token, "r") as t:
                    creds = self._json_to_cred(t)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials, scopes)
                    creds = flow.run_local_server(port=0)
                with open(token, "w") as t:
                    json.dump(self._cred_to_json(creds), t, indent=2)
            return creds

    def _apicall(self, request, maximum_backoff=32):
        sleep_exponent_count = 0
        _error = None
        while True:
            success = True
            retry = False
            try:
                response = request.execute()
            except HttpError as error:
                _error = error
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
                _error = error
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

    def _ls(self, folder_id, fields="files(id,name,size,permissions(role,type)),nextPageToken", searchTerms=""):
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

    def _lsf(self, folder_id, fields="files(id,name,size,permissions(role,type)),nextPageToken"):
        return self._ls(
            folder_id,
            fields=fields,
            searchTerms="not mimeType contains \"application/vnd.google-apps.folder\""
        )

    def check_file_shared(self, file_to_check):
        for permission in file_to_check["permissions"]:
            if permission["role"] == "reader" and permission["type"] == "anyone":
                return True
        return False

    def get_all_files_in_folder(self, folder_id, dict_files, dict_blacklist, recursion=True):
        for _file in self._lsf(folder_id):
            dict_files.update({_file["id"]: {"size": _file["size"], "name": _file["name"], "shared": check_file_shared(_file)}})
        if recursion:
            for _folder in self._lsd(folder_id):
                self.get_all_files_in_folder(_folder["id"], dict_files, dict_blacklist, recursion=recursion)

    def share_file(self, file_id_to_share):
        self._apicall(self.drive_service.permissions().create(fileId=file_id_to_share, supportsAllDrives=True, body={
            "role": "reader",
            "type": "anyone"
        }))

    # def upload_to_my_drive(self):
    #     pass

    # def upload_to_folder(self, folder_id_to_upload_to):
    #     pass

class tinfoil_gdrive_generator():
    def __init__(self, folder_ids, credentials_path="credentials.json", token_path="token.json", output_path="index.json"):
        self.folder_ids = folder_ids
        self.output_path = output_path
        self.files_to_share = []
        self.gdrive_service = gdrive(token_path=token_path, 
        credentials_path=credentials_path)
        self.index_json = {}
        if Path(self.output_path).is_file():
            with open(self.output_path, "r") as index_json:
                try:
                    self.index_json = json.loads(index_json.read())
                except json.JSONDecodeError:
                    raise Exception("Error while trying to read the index json file. Make sure that it is a valid JSON file.")
        if "files" not in self.index_json:
            self.index_json.update({"files": []})
            self._update_index_file()

    def _update_index_file(self):
        with open(self.output_path, "w") as output_file:
            json.dump(self.index_json, output_file, indent=2)

    def index_updater(self, share_files=None, use_old_url_format=False, recursion=True):
        all_files = {}
        for folder_id in self.folder_ids:
            self.gdrive_service.get_all_files_in_folder(folder_id, all_files, self.index_json["files"], recursion=recursion)
        for (file_id, file_details, is_shared) in all_files.items():
            check = {}
            share_file = False
            if use_old_url_format:
                check = {"url": "https://docs.google.com/uc?export=download&id={file_id}#{file_name}".format(file_id=file_id, file_name=urllib.parse.quote_plus(file_details["name"])), "size": int(file_details["size"])}
            else:
                check = {"url": "gdrive:/{file_id}#{file_name}".format(file_id=file_id, file_name=urllib.parse.quote_plus(file_details["name"])), "size": int(file_details["size"])}
            if check not in self.index_json["files"]:
                self.index_json["files"].append(check)
                if share_files == "update" and not is_shared:
                    share_file = True
            if not share_file and share_files == "all" and not is_shared:
                share_file = True
            if share_file:
                self.files_to_share.append(file_id)
        if len(self.files_to_share) > 0:
            for i in tqdm(range(len(self.files_to_share)), desc="File Share Progress"):
                self.gdrive_service.share_file(self.files_to_share[i])
        self._update_index_file()

def main():
    parser = argparse.ArgumentParser(description="Script that will allow you to easily generate a JSON file with Google Drive file links for use with Tinfoil.")
    parser.add_argument(nargs="*", metavar="FOLDER_ID_TO_SCAN", dest="folder_ids", help="Folder ID of Google Drive folders to scan. Can use more than 1 folder IDs at a time.")
    # parser.add_argument("--upload-to-folder-id", metavar="UPLOAD_FOLDER_ID", dest="upload_folder_id")
    # parser.add_argument("--upload-to-my-drive", action="store_true")
    # parser.add_argument("--upload-to-scan-folders", action="store_true")
    parser.add_argument("--share-files", choices=["update", "all"], help="By default, the script only shares files that were newly added. If you want to share old files, use \"all\" instead of \"update\".")
    parser.add_argument("--credentials", default="credentials.json", metavar="CREDENTIALS_FILE_NAME", help="Obtainable from https://developers.google.com/drive/api/v3/quickstart/python. Make sure to select the correct account before downloading the credentails file.")
    parser.add_argument("--token", default="token.json", metavar="TOKEN_FILE_PATH", help="File Path of a Google Token file.")
    parser.add_argument("--output-json", metavar="OUTPUT_FILE_PATH", default="index.json", help="File Path JSON to update.")
    parser.add_argument("--encrypt-file", metavar="ENCRYPTED_DB_FILE_PATH", help="File Path to encrypt the output JSON file to.")
    parser.add_argument("--public-key", metavar="PUBLIC_KEY_FILE_PATH", default="public.key", help="File Path to Public Key to encrypt with.")
    parser.add_argument("--disable-recursion", dest="recursion", action="store_false", help="Use this flag to stop folder IDs entered from being recusively scanned. (It basically means if you use this flag, the script will only add the files at the root of the folder, without going through the sub-folders in it.")
    parser.add_argument("--use-old-url-format", action="store_true", help="Use this flag to generate link in old URL format. Works in Tinfoil 8.10 and above. Still preferred and recommended by blawar to use gdrive:/ format (with --share-files flag if not using OAuth2 / API Key), as tinfoil will take care of the task of making direct links from now on. Here is the order in which tinfoil requests the link from gdrive:/ protocol according to blawar, OAuth2 Token > User API Key > Tinfoil Workaround.")

    args = parser.parse_args()
    generator = tinfoil_gdrive_generator(args.folder_ids, token_path=args.token, credentials_path=args.credentials, output_path=args.output_json)
    generator.index_updater(share_files=args.share_files, use_old_url_format=args.use_old_url_format, recursion=args.recursion)
    # if args.upload_folder_id:
    #     generator.gdrive_service.upload_to_folder(args.upload_folder_id)
    # if args.upload_to_my_drive:
    #     generator.gdrive_service.upload_to_my_drive()
    # if args.upload_to_scan_folders and len(args.folder_ids) > 0:
    #     generator.gdrive_service.upload_to_folder(folder_id) for folder_id in args.folder_ids
    if args.encrypt_file:
        encrypt_file(args.output_json, args.encrypt_file, public_key=args.public_key)

if __name__ == "__main__":
    main()