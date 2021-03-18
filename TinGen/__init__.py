from tqdm import tqdm
from typing import List
from pathlib import Path
from typing import Optional
from json import JSONDecodeError
from TinGen.gdrive import GDrive
from TinGen.gdrive import UGdrive
from json import dump as json_writer
from json import load as json_reader
from TinGen.utils import format_bytes
from re import compile as regex_compile
from datetime import datetime, timezone
from urllib.parse import quote as url_encode


class TinGen:
    def __init__(
        self,
        credentials_path: str,
        token_path: str,
        headless: bool,
        tinfoil_min_ver: str,
        theme_blacklist: Optional[List[str]] = None,
        theme_whitelist: Optional[List[str]] = None,
        theme_error: Optional[str] = None,
    ):
        self.gdrive_service = GDrive(token_path, credentials_path, headless)
        self.files_shared_status = {}
        self.title_ext_infos = {
            "nsp": {
                "count": 0,
                "size": 0,
            },
            "nsz": {
                "count": 0,
                "size": 0,
            },
            "xci": {
                "count": 0,
                "size": 0,
            },
            "xcz": {
                "count": 0,
                "size": 0,
            },
        }

        self.index = {"files": [], "version": tinfoil_min_ver}

        if theme_blacklist:
            self.index.update({"themeBlackList": theme_blacklist})

        if theme_blacklist:
            self.index.update({"themeWhitelist": theme_whitelist})

        if theme_error:
            self.index.update({"themeError": theme_error})

    def read_index(
        self,
        index_path
    ):
        """Reads index file and updates the index for the instance."""
        pathlib_index = Path(index_path)
        if pathlib_index.exists() and pathlib_index.is_file():
            with open(pathlib_index, "r") as index_fp:
                try:
                    file_json = json_reader(index_fp)
                    if "files" in file_json:
                        for file_entry in file_json["files"]:
                            if file_entry not in self.index["files"]:
                                self.index["files"].append(file_entry)
                except JSONDecodeError:
                    print(
                        f"WARNING: {pathlib_index} is not a valid JSON file."
                    )

    def write_index_to_file(
        self,
        index_path
    ):
        """Writes the instance index to index file"""
        Path(index_path).parent.resolve().mkdir(parents=True, exist_ok=True)
        with open(index_path, "w") as index_fp:
            json_writer(self.index, index_fp, indent=2)

    def scan_folder(
        self,
        folder_id: str,
        files_progress_bar: tqdm,
        recursion: bool,
        add_nsw_files_without_title_id: bool,
        add_non_nsw_files: bool
    ):
        """Scans the folder id for files and updates the instance index"""
        title_id_pattern = r"\%5B[0-9A-Fa-f]{16}\%5D"

        files = self.gdrive_service.get_all_files_in_folder(
            folder_id,
            recursion,
            files_progress_bar
        )

        pattern = regex_compile(title_id_pattern)
        for (file_id, file_details) in files.items():
            url_encoded_file_name = url_encode(file_details["name"], safe="")
            file_ext = url_encoded_file_name[-3:]
            file_valid_nsw_check = add_non_nsw_files or \
                file_ext in self.title_ext_infos.keys()
            file_title_id_check = add_nsw_files_without_title_id or \
                pattern.search(url_encoded_file_name)
            if file_title_id_check and file_valid_nsw_check:
                if file_ext in self.title_ext_infos:
                    old_val_count = self.title_ext_infos[file_ext]["count"]
                    old_val_size = self.title_ext_infos[file_ext]["size"]
                    self.title_ext_infos[file_ext]["count"] = old_val_count + 1
                    self.title_ext_infos[file_ext]["size"] = old_val_size + \
                        int(file_details["size"])

                file_entry_to_add = {
                    "url": f"gdrive:{file_id}#{url_encoded_file_name}",
                    "size": int(file_details["size"])
                }
                if file_entry_to_add not in self.index["files"]:
                    self.index["files"].append(file_entry_to_add)
                    self.files_shared_status.update({
                        file_id: file_details["shared"]
                    })

    def share_index_files(
        self,
    ):
        """Share files in index. Does nothing for files already shared."""
        for file_entry in tqdm(
            self.index["files"],
            desc="File Share Progress",
            unit="file",
            unit_scale=True
        ):
            entry_file_id = file_entry["url"].split(":")[1].split("#")[0]
            if not self.files_shared_status.get(entry_file_id):
                self.gdrive_service.share_file(entry_file_id)

    def add_nsw_title_info_to_success(
        self,
    ):
        msg = ""

        for ext in self.title_ext_infos.keys():
            title_count = self.title_ext_infos[ext]["count"]
            if title_count == 0:
                continue
            fmt_title_count = "{:,}".format(title_count)
            title_size_fmt = format_bytes(self.title_ext_infos[ext]["size"])
            msg += f"{ext.upper()}\n├─ Title Count: {fmt_title_count}"
            msg += f"\n└─ Size: {title_size_fmt[0]} {title_size_fmt[1]}\n"

        self.index.update({"success": msg})

    def add_datetime_to_success(
        self,
        add_date: bool,
        add_time: bool,
    ):
        now_dt_utc = datetime.now(timezone.utc)
        fmt_str = ""
        if add_date:
            fmt_str = "%B %d, %Y"
            if add_time:
                fmt_str += " | "
        if add_time:
            fmt_str += "%I:%M%p UTC"
        dt_str = now_dt_utc.strftime(fmt_str)
        msg = f"\nIndex Updated: {dt_str}\n"
        if self.index.get("success", False):
            self.index.update({"success": self.index["success"] + msg})
        else:
            self.index.update({"success": msg})

    def update_index_success_message(
        self,
        success_message: str
    ):
        """Updates the index success message with new message"""
        if self.index.get("success", False):
            separator = "\n--------------\n\n"
            self.index.update({"success": self.index["success"] +
                              separator + success_message})
        else:
            self.index.update({"success": success_message})

    def index_generator(
        self,
        folder_ids: list,
        recursion: bool,
        add_nsw_files_without_title_id: bool,
        add_non_nsw_files: bool,
    ):
        files_progress_bar = tqdm(
            desc="Files scanned",
            unit="file",
            unit_scale=True
        )

        for folder_id in folder_ids:
            self.scan_folder(
                folder_id,
                files_progress_bar,
                recursion,
                add_nsw_files_without_title_id,
                add_non_nsw_files
            )


class UTinGen:
    def __init__(
        self
    ):
        self.index = {"files": []}
        self.gdrive_service = UGdrive()

    def index_generator(
        self,
        folder_ids,
        add_non_nsw_files: bool,
        add_nsw_files_without_title_id: bool,
        success: str = None,
    ) -> None:
        title_id_pattern = r"\%5B[0-9A-Fa-f]{16}\%5D"
        pattern = regex_compile(title_id_pattern)
        for folder_id in folder_ids:
            files = self.gdrive_service.get_files_in_folder_id(folder_id)
            for (file_id, file_details) in files.items():
                if add_non_nsw_files or file_details["name"][-4:] in (
                    ".nsp",
                    ".nsz",
                    ".xci",
                    ".xcz",
                ):
                    file_name = url_encode(file_details["name"], safe="")
                    if add_nsw_files_without_title_id or pattern.search(
                        title_id_pattern,
                        file_name,
                    ):
                        size = int(file_details["size"])
                        self.index["files"].append({
                            "url": f"gdrive:{file_id}#{file_name}",
                            "size": size,
                        })
        if success is not None:
            self.index.update({"success": success})
