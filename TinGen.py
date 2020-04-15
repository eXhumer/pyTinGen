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
    def __init__(self, credentials_path: str, token_path: str, headless: bool):
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

    def _lsd_my_drive(self):
        return self._ls(
            "root",
            searchTerms="mimeType contains \"application/vnd.google-apps.folder\""
        )

    def _lsf_my_drive(self, fields="files(id,name,size,permissionIds),nextPageToken"):
        return self._ls(
            "root",
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

    def get_all_files_in_folder(self, folder_id: str, recursion: bool, progress_bar: tqdm) -> dict:
        files = {}

        for _file in self._lsf(folder_id):
            if "size" in _file:
                files.update({_file["id"]: {"size": _file["size"], "name": _file["name"], "shared": self.check_file_shared(_file)}})
                progress_bar.update(1)
                
        if recursion:
            for _folder in self._lsd(folder_id):
                files.update(self.get_all_files_in_folder(_folder["id"], recursion, progress_bar))

        return files

    def share_file(self, file_id_to_share):
        self._apicall(self.drive_service.permissions().create(fileId=file_id_to_share, supportsAllDrives=True, body={
            "role": "reader",
            "type": "anyone"
        }))

    def upload_file(self, file_path, dest_folder_id, new_upload_id):
        existing_file_id = None

        if dest_folder_id:
            for _file in self._lsf(dest_folder_id):
                if not new_upload_id or _file["name"] == Path(file_path).name:
                    print(f"File with same name was found in destination folder. File in destination folder will be updated instead of creating new file.")
                    existing_file_id = _file["id"]
                    break
        else:
            for _file in self._lsf_my_drive():
                if not new_upload_id or _file["name"] == Path(file_path).name:
                    print(f"File with same name was found in destination folder. File in destination folder will be updated instead of creating new file.")
                    existing_file_id = _file["id"]
                    break

        media = MediaFileUpload(file_path)

        if dest_folder_id is None:
            if existing_file_id:
                response = self._apicall(self.drive_service.files().update(fileId=existing_file_id, media_body=media))
            else:
                response = self._apicall(self.drive_service.files().create(media_body=media, body={"name": Path(file_path).name}, supportsAllDrives=True))
        else:
            if existing_file_id:
                response = self._apicall(self.drive_service.files().update(fileId=existing_file_id, media_body=media))
            else:
                response = self._apicall(self.drive_service.files().create(media_body=media, body={"name": Path(file_path).name, "parents": [dest_folder_id]}, supportsAllDrives=True))

        if "id" in response:
            self.share_file(response["id"])
            print("Add the following to tinfoil: gdrive:/{file_id}#{file_name}".format(file_id=response["id"], file_name=response["name"]))


class TinGen:
    def __init__(self, credentials_path: str, token_path: str, headless: bool):
        self.gdrive_service = GDrive(token_path, credentials_path, headless)
        self.files_shared_status = {}
        self.index = {"files": []}

    def read_index(self, index_path):
        """Reads index file and updates the index for the instance."""
        pathlib_index = Path(index_path)
        if pathlib_index.exists() and pathlib_index.is_file():
            with open(pathlib_index, "r") as index_fp:
                try:
                    file_json = json.load(index_fp)
                    if "files" in file_json:
                        for file_entry in file_json["files"]:
                            if file_entry not in self.index["files"]:
                                self.index["files"].append(file_entry)
                except json.JSONDecodeError:
                    print(f"WARNING: {pathlib_index} is not a valid JSON file.")

    def write_index_to_file(self, index_path):
        """Writes the instance index to index file"""
        Path(index_path).parent.resolve().mkdir(parents=True, exist_ok=True)
        with open(index_path, "w") as index_fp:
            json.dump(self.index, index_fp, indent=2)

    def scan_folder(self, folder_id: str, files_progress_bar: tqdm, recursion: bool, add_nsw_files_without_title_id: bool, add_non_nsw_files: bool):
        """Scans the folder id for files and updates the instance index"""
        files = self.gdrive_service.get_all_files_in_folder(folder_id, recursion, files_progress_bar)

        for (file_id, file_details) in files.items():
            url_encoded_file_name = urllib.parse.quote(file_details["name"], safe="")
            file_valid_nsw_check = add_non_nsw_files or url_encoded_file_name[-4:] in (".nsp", ".nsz", ".xci", ".xcz")
            file_title_id_check = add_nsw_files_without_title_id or re.search(r"\%5B[0-9A-Fa-f]{16}\%5D", url_encoded_file_name)
            if file_title_id_check and file_valid_nsw_check:
                file_entry_to_add = {"url": f"gdrive:{file_id}#{url_encoded_file_name}", "size": int(file_details["size"])}
                if file_entry_to_add not in self.index["files"]:
                    self.index["files"].append(file_entry_to_add)
                    self.files_shared_status.update({file_id: file_details["shared"]})

    def share_index_files(self):
        """Share files in index. Does nothing for files already shared."""
        for file_entry in tqdm(self.index["files"], desc="File Share Progress", unit="file", unit_scale=True):
            entry_file_id = file_entry["url"](":")[1].split("#")[0]
            if not self.files_shared_status.get(entry_file_id):
                self.gdrive_service.share_file(entry_file_id)

    def update_index_success_message(self, success_message: str):
        """Updates the index success message with new message"""
        self.index.update({"success": success_message})

    def index_generator(self, folder_ids: list, recursion: bool, add_nsw_files_without_title_id: bool, add_non_nsw_files: bool):
        files_progress_bar = tqdm(desc="Files scanned", unit="file", unit_scale=True)

        for folder_id in folder_ids:
            self.scan_folder(folder_id, files_progress_bar, recursion, add_nsw_files_without_title_id, add_non_nsw_files)

    def write_encrypted_index_to_file(self, encrypt_path: str, encryption_public_key: str):
        encrypt_file(json.dumps(self.index).encode("utf-8"), encrypt_path, public_key=encryption_public_key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script that will allow you to generate an index file with Google Drive file links for use with Tinfoil")
    parser.add_argument(nargs="*", metavar="FOLDER_ID_TO_SCAN", dest="folder_ids", help="Folder IDs of Google Drive folders to scan")

    parser.add_argument("--credentials", default="credentials.json", metavar="CREDENTIALS_FILE_NAME", help="File path to Google Credentials file")
    parser.add_argument("--token", default="gdrive.token", metavar="TOKEN_FILE_PATH", help="File path of a Google Token file")
    parser.add_argument("--headless", action="store_true", help="Allows to perform Google Token Authentication in headless environment")

    parser.add_argument("--index-file", metavar="INDEX_FILE_PATH", default="index.tfl", help="File path for index file")
    parser.add_argument("--update-mode", action="store_true", help="Updates existing index file keeping old files, if it exists, instead of regenerating a new file")
    parser.add_argument("--share-files", action="store_true", help="Share files all files inside the index file")
    parser.add_argument("--no-recursion", dest="recursion", action="store_false", help="Scans for files only in top directory for each folder ID entered")
    parser.add_argument("--add-nsw-files-without-title-id", action="store_true", help="Adds files without title ID")
    parser.add_argument("--add-non-nsw-files", action="store_true", help="Adds files without valid NSW ROM extension(NSP/NSZ/XCI/XCZ) to index")
    parser.add_argument("--success", metavar="SUCCESS_MESSAGE", help="Adds a success message to index file to show if index is successfully read by tinfoil")

    parser.add_argument("--encrypt", nargs="?", metavar="ENC_INDEX_FILE_PATH", const="enc_index.tfl", help="Encrypts the resulting index file")
    parser.add_argument("--public-key", metavar="PUBLIC_KEY_FILE_PATH", default="public.key", help="File Path for Public Key to encrypt with")

    parser.add_argument("--upload-to-folder-id", metavar="UPLOAD_FOLDER_ID", dest="upload_folder_id", help="Upload resulting index to folder id supplied")
    parser.add_argument("--upload-to-my-drive", action="store_true", help="Upload resulting index to My Drive")
    parser.add_argument("--new-upload-id", action="store_true", help="Uploads the newly generated index file to with a new file ID instead of replacing old one")

    args = parser.parse_args()
    generator = TinGen(args.token, args.credentials, args.headless)

    print(f"Generating index")
    generator.index_generator(args.folder_ids, args.recursion, args.add_nsw_files_without_title_id, args.add_non_nsw_files)

    if args.success:
        print(f"Adding success message to index")
        generator.update_index_success_message(args.success)

    if args.update_mode:
        print(f"Adding files from {args.index_file} to new index")
        generator.read_index(args.index_file)

    print(f"Writing generated index to {args.index_file}")
    generator.write_index_to_file(args.index_file)

    if args.share_files:
        print(f"Sharing files in index")
        generator.share_index_files()

    if args.encrypt:
        print(f"Encrypting index to {args.encrypt}")
        generator.write_encrypted_index_to_file(args.encrypt, args.public_key)

    if args.upload_folder_id:
        print(f"Uploading file to {args.upload_folder_id}")
        generator.gdrive_service.upload_file(args.index_file if not args.encrypt else args.encrypt, args.upload_folder_id, args.new_upload_id)

    if args.upload_to_my_drive:
        print(f"Uploading file to \"My Drive\"")
        generator.gdrive_service.upload_file(args.index_file if not args.encrypt else args.encrypt, None, args.new_upload_id)

    print(f"Index Generation Complete")