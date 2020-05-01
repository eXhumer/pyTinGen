from argparse import ArgumentParser
from TinGen import TinGen
from pathlib import Path
from binascii import unhexlify
from TinGen.utils import create_encrypted_index

if __name__ == "__main__":
    parser = ArgumentParser(description="Script that will allow you to generate an index file with Google Drive file links for use with Tinfoil")
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
    parser.add_argument("--public-key", metavar="PUBLIC_KEY_FILE_PATH", default="public.pem", help="File Path for Public Key to encrypt with")
    parser.add_argument("--vm-file", help="File Path for VM File")

    parser.add_argument("--upload-to-folder-id", metavar="UPLOAD_FOLDER_ID", dest="upload_folder_id", help="Upload resulting index to folder id supplied")
    parser.add_argument("--upload-to-my-drive", action="store_true", help="Upload resulting index to My Drive")
    parser.add_argument("--new-upload-id", action="store_true", help="Uploads the newly generated index file with a new file ID instead of replacing old one")
    parser.add_argument("--share-uploaded-index", action="store_true", help="Shares the index file that is uploaded to Google Drive")

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
        create_encrypted_index(generator.index, Path(args.encrypt), Path(args.public_key), None if not args.vm_file else Path(args.vm_file))

    if args.upload_folder_id:
        file_to_upload = args.index_file if not args.encrypt else args.encrypt
        print(f"Uploading {file_to_upload} to {args.upload_folder_id}")
        generator.gdrive_service.upload_file(file_to_upload, args.upload_folder_id, args.share_uploaded_index, args.new_upload_id)

    if args.upload_to_my_drive:
        file_to_upload = args.index_file if not args.encrypt else args.encrypt
        print(f"Uploading {file_to_upload} to \"My Drive\"")
        generator.gdrive_service.upload_file(file_to_upload, None, args.share_uploaded_index, args.new_upload_id)

    print(f"Index Generation Complete")