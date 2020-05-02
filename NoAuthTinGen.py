from argparse import ArgumentParser
from binascii import unhexlify
from pathlib import Path
from TinGen.utils import CompressionFlag
from TinGen.utils import create_tinfoil_index
from TinGen import UTinGen
from urllib3 import disable_warnings as disable_url_warnings

if __name__ == "__main__":
    disable_url_warnings()
    parser = ArgumentParser(description="Script that will allow you to easily generate an index file with Google Drive file links for use with Tinfoil without requiring authentication")
    parser.add_argument(nargs="*", metavar="FOLDER_ID_TO_SCAN", dest="folder_ids", help="Folder ID of Google Drive folders to scan")
    parser.add_argument("--index-path", default="index.tfl", help="File path for unencrypted index file to update")
    parser.add_argument("--add-nsw-files-without-title-id", action="store_true", help="Adds files without title ID")
    parser.add_argument("--add-non-nsw-files", action="store_true", help="Adds files without valid NSW ROM extension(NSP/NSZ/XCI/XCZ) to index")
    parser.add_argument("--encrypt", action="store_true", help="Encrypt the resulting index file")
    parser.add_argument("--public-key", default="public.pem", help="File path for public key to encrypt with")
    parser.add_argument("--vm-file", help="File path for VM file")
    parser.add_argument("--success", help="Success message to add to index")
    compression_parser = parser.add_mutually_exclusive_group()
    compression_parser.add_argument("--zstandard", action="store_true", help="Compresses index with Zstandard compression method")
    compression_parser.add_argument("--zlib", action="store_true", help="Compresses index with Zlib compression method")
    compression_parser.add_argument("--no-compress", action="store_true", help="Flag to not compress index")

    args = parser.parse_args()

    generator = UTinGen()
    generator.index_generator(args.folder_ids, add_non_nsw_files=args.add_non_nsw_files, add_nsw_files_without_title_id=args.add_nsw_files_without_title_id, success=args.success)

    compression_flag = CompressionFlag.ZSTD_COMPRESSION

    if args.zstandard:
        compression_flag = CompressionFlag.ZSTD_COMPRESSION
    elif args.zlib:
        compression_flag = CompressionFlag.ZLIB_COMPRESSION
    elif args.no_compress:
        compression_flag = CompressionFlag.NO_COMPRESSION

    vm_file = None
    public_key = None

    if args.encrypt:
        if args.vm_file:
            vm_file = args.vm_file
        if args.public_key:
            public_key = args.public_key

    create_tinfoil_index(generator.index, args.index_path, compression_flag, public_key, vm_file)