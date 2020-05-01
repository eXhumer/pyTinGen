from urllib3 import disable_warnings as disable_url_warnings
from TinGen import UTinGen
from argparse import ArgumentParser
from pathlib import Path
from binascii import unhexlify
from TinGen.utils import create_encrypted_index

if __name__ == "__main__":
	disable_url_warnings()
	parser = ArgumentParser(description="Script that will allow you to easily generate an index file with Google Drive file links for use with Tinfoil without requiring authentication.")
	parser.add_argument(nargs="*", metavar="FOLDER_ID_TO_SCAN", dest="folder_ids", help="Folder ID of Google Drive folders to scan. Can use more than 1 folder IDs at a time. FOLDERS MUST BE PUBLIC FOR SCRIPT TO WORK")
	parser.add_argument("--index-file", metavar="INDEX_FILE_PATH", default="index.tfl", help="File Path for unencrypted index file to update.")
	parser.add_argument("--encrypt", nargs="?", metavar="ENC_INDEX_FILE_PATH", const="enc_index.tfl", help="Use this flag is you want to encrypt the resulting index file.")
	parser.add_argument("--public-key", metavar="PUBLIC_KEY_FILE_PATH", default="public.pem", help="File Path for Public Key to encrypt with.")
	parser.add_argument("--vm-file", help="File Path for VM File")
	parser.add_argument("--success", metavar="SUCCESS_MESSAGE", help="Success Message to add to index.")

	args = parser.parse_args()

	generator = UTinGen(index_path=args.index_file)
	generator.index_folders(args.folder_ids, success=args.success)

	if args.encrypt:
		create_encrypted_index(generator.index_json, Path(args.encrypt), Path(args.public_key), None if not args.vm_file else Path(args.vm_file))