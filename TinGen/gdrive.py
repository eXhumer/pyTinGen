from tqdm import tqdm
from time import sleep
from pathlib import Path
from requests import Session
from json import JSONDecodeError
from json import load as json_reader
from json import dump as json_writer
from json import loads as json_deserialize
from googleapiclient.errors import HttpError
from socket import timeout as SocketTimeoutError
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.exceptions import TransportError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as google_api_build


class GDrive:
    @staticmethod
    def _cred_to_json(
        cred_to_pass
    ):
        return {
            "access_token": cred_to_pass.token,
            "refresh_token": cred_to_pass.refresh_token,
        }

    @staticmethod
    def _json_to_cred(
        json_stream,
        client_id,
        client_secret
    ):
        cred_json = json_reader(json_stream)
        creds = Credentials(
            cred_json["access_token"],
            refresh_token=cred_json["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        return creds

    @staticmethod
    def _get_creds(
        credentials="credentials.json",
        token="gdrive.token",
        scopes=['https://www.googleapis.com/auth/drive'],
        headless=False,
    ):
        if Path(credentials).is_file():
            with open(credentials, "r") as credentials_stream:
                cred_json = json_reader(credentials_stream)
            creds = None
            if Path(token).is_file():
                with open(token, "r") as token_stream:
                    creds = GDrive._json_to_cred(
                        token_stream,
                        cred_json["installed"]["client_id"],
                        cred_json["installed"]["client_secret"]
                    )
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials,
                        scopes,
                    )
                    if headless:
                        creds = flow.run_console()
                    else:
                        creds = flow.run_local_server(port=0)
                with open(token, "w") as token_stream:
                    json_writer(
                        GDrive._cred_to_json(creds),
                        token_stream,
                        indent=2,
                    )
            return creds

    def __init__(
        self,
        credentials_path: str,
        token_path: str,
        headless: bool
    ) -> None:
        credentials = GDrive._get_creds(
            credentials=credentials_path,
            token=token_path,
            headless=headless,
        )
        self.drive_service = google_api_build(
            "drive",
            "v3",
            credentials=credentials,
        )

    def _apicall(
        self,
        request,
        maximum_backoff=32
    ):
        sleep_exponent_count = 0
        while True:
            success = True
            retry = False
            try:
                return request.execute()
            except HttpError as error:
                success = False
                try:
                    error_details = json_deserialize(
                        error.content.decode("utf-8"),
                    )["error"]
                    if "errors" in error_details:
                        if error_details["errors"][0]["reason"] in (
                            "dailyLimitExceeded",
                            "userRateLimitExceeded",
                            "rateLimitExceeded",
                            "backendError",
                            "sharingRateLimitExceeded",
                            "failedPrecondition",
                            "internalError",
                            "domainPolicy",
                            "insufficientFilePermissions",
                            "appNotAuthorizedToFile"
                        ):  # IF REQUEST IS RETRYABLE
                            retry = True
                    else:
                        raise error
                except JSONDecodeError:
                    retry = True
            except (TransportError, SocketTimeoutError, SocketTimeoutError):
                success = False
                retry = True
            if success:
                break
            if retry:
                sleep_time = 2 ^ sleep_exponent_count
                if sleep_time < maximum_backoff:
                    sleep(sleep_time)
                    sleep_exponent_count += 1
                    continue
                else:
                    raise Exception("Maximum Backoff Limit Exceeded.")
            else:
                raise Exception("Unretryable Error")

    def _ls(
        self,
        folder_id,
        fields="files(id,name,size,permissionIds),nextPageToken",
        searchTerms=""
    ):
        files = []
        resp = {"nextPageToken": None}
        while "nextPageToken" in resp:
            resp = self._apicall(self.drive_service.files().list(
                q=" and ".join([
                    "\"%s\" in parents" % folder_id,
                    searchTerms,
                    "trashed = false",
                ]),
                fields=fields,
                pageSize=1000,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageToken=resp["nextPageToken"]
            ))
            files += resp["files"]
        return files

    def _lsd(
        self,
        folder_id
    ):
        return self._ls(
            folder_id,
            searchTerms="mimeType contains " +
            "\"application/vnd.google-apps.folder\""
        )

    def _lsf(
        self,
        folder_id,
        fields="files(id,name,size,permissionIds),nextPageToken"
    ):
        return self._ls(
            folder_id,
            fields=fields,
            searchTerms="not mimeType contains " +
            "\"application/vnd.google-apps.folder\""
        )

    def _lsd_my_drive(
        self
    ):
        return self._ls(
            "root",
            searchTerms="mimeType contains " +
            "\"application/vnd.google-apps.folder\""
        )

    def _lsf_my_drive(
        self,
        fields="files(id,name,size,permissionIds),nextPageToken",
    ):
        return self._ls(
            "root",
            fields=fields,
            searchTerms="not mimeType contains " +
            "\"application/vnd.google-apps.folder\""
        )

    def check_file_shared(
        self,
        file_to_check,
    ):
        shared = False
        if "permissionIds" in file_to_check:
            for permissionId in file_to_check["permissionIds"]:
                if permissionId[-1] == "k" and permissionId[:-1].isnumeric():
                    self.delete_file_permission(
                        file_to_check["id"],
                        permissionId,
                    )
                if permissionId == "anyoneWithLink":
                    shared = True
        return shared

    def delete_file_permission(
        self,
        file_id,
        permission_id
    ):
        self._apicall(
            self.drive_service.permissions().delete(
                fileId=file_id,
                permissionId=permission_id,
                supportsAllDrives=True
            )
        )

    def get_all_files_in_folder(
        self,
        folder_id: str,
        recursion: bool,
        progress_bar: tqdm
    ) -> dict:
        files = {}

        for _file in self._lsf(folder_id):
            if "size" in _file:
                files.update({
                    _file["id"]: {
                        "size": _file["size"],
                        "name": _file["name"],
                        "shared": self.check_file_shared(_file)
                    }
                })
                progress_bar.update(1)

        if recursion:
            for _folder in self._lsd(folder_id):
                files.update(self.get_all_files_in_folder(
                    _folder["id"],
                    recursion,
                    progress_bar
                ))

        return files

    def share_file(
        self,
        file_id_to_share
    ):
        self._apicall(
            self.drive_service.permissions().create(
                fileId=file_id_to_share,
                supportsAllDrives=True,
                body={
                    "role": "reader",
                    "type": "anyone"
                }
            )
        )

    def upload_file(
        self,
        file_path,
        dest_folder_id,
        share_index,
        new_upload_id
    ):
        existing_file_id = None

        root_files = self._lsf(dest_folder_id) if dest_folder_id else \
            self._lsf_my_drive()

        for _file in root_files:
            if _file["name"] == Path(file_path).name:
                print(
                    "File with same name was found in destination folder. " +
                    "File in destination folder will be updated instead of " +
                    "creating new file."
                )
                existing_file_id = _file["id"]
                break

        if existing_file_id is not None and new_upload_id:
            existing_file_id = None

        media = MediaFileUpload(file_path)

        if existing_file_id:
            response = self._apicall(self.drive_service.files().update(
                fileId=existing_file_id,
                media_body=media,
                supportsAllDrives=True
            ))
        else:
            if dest_folder_id:
                response = self._apicall(self.drive_service.files().create(
                    media_body=media,
                    body={
                        "name": Path(file_path).name,
                        "parents": [dest_folder_id]
                    },
                    supportsAllDrives=True
                ))
            else:
                response = self._apicall(self.drive_service.files().create(
                    media_body=media,
                    body={
                        "name": Path(file_path).name
                    },
                    supportsAllDrives=True
                ))

        if "id" in response:
            file_id = response["id"]
            if share_index:
                print(
                    f"Sharing {Path(file_path).name}"
                )
                self.share_file(file_id)
            print(
                "Shorten the following link with tiny.cc and add it to " +
                f"Tinfoil: https://drive.google.com/uc?id={file_id}",
            )


class UGdrive:
    def __init__(
        self,
        session_headers={}
    ):
        self.session = Session()
        self.session.headers.clear()
        self.session.cookies.clear()
        self.session.headers.update({
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 11_4_1 like " +
            "Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) " +
            "Version/11.0 Mobile/15E148 Safari/604.1"
        })
        self.session.headers.update(session_headers)

    def make_request(
        self,
        method,
        url,
        **options
    ):
        req_headers = {}
        if options.get("referer", False):
            req_headers.update({"Referer": options.get("referer")})
        return self.session.request(
            method,
            url,
            headers=req_headers,
            verify=False,
            stream=True,
        )

    def get_files_in_folder_id(
        self,
        folder_id
    ):
        pbar = tqdm(desc="Files scanned", unit="file", unit_scale=True)
        files = {}
        page_token = None

        # LIMITS TO 100 PAGES MAXIMUM, SHOULD CHANGE THIS LATER
        for _ in range(100):
            url = "https://clients6.google.com/drive/v2beta/files?" + \
                "openDrive=false&reason=102&syncType=0&errorRecovery=false" + \
                f"&q=trashed%20%3D%20false%20and%20%27{folder_id}%27%20in" + \
                "%20parents&fields=kind%2CnextPageToken%2Citems(kind" + \
                "%2CfileSize%2Ctitle%2Cid)%2CincompleteSearch&" + \
                "appDataFilter=NO_APP_DATA&spaces=drive&maxResults=500&" + \
                "orderBy=folder%2Ctitle_natural%20asc&" + \
                f"key={self.get_folder_key(folder_id)}"

            if page_token is not None:
                url = f"{url}&pageToken={page_token}"

            ls_response = self.make_request(
                "GET",
                url,
                referer=f"https://drive.google.com/open?id={folder_id}"
            )
            ls_json = json_deserialize(ls_response.text)
            pbar.update(len(ls_json["items"]))

            for drive_file in ls_json["items"]:
                if drive_file["kind"] != "drive#file" and "fileSize" not in \
                        drive_file:
                    continue

                files.update({
                    drive_file["id"]: {
                        "name": drive_file["title"],
                        "size": int(drive_file["fileSize"])
                    }
                })

            if "nextPageToken" not in ls_json:
                break

            page_token = ls_json["nextPageToken"]

        pbar.close()
        return files

    def get_folder_key(
        self,
        folder_id
    ):
        response = self.make_request(
            "GET",
            f"https://drive.google.com/open?id={folder_id}"
        )

        start = response.text.index("__initData = ") + len("__initData = ")
        end = response.text.index(";", start)
        json_data = json_deserialize(response.text[start:end])
        return json_data[0][9][32][35]  # :nospies:
