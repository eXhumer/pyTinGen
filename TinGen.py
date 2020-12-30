#!/usr/bin/env python3
# -*- coding: utf8 -*-
from TinGen.utils import create_tinfoil_index
from TinGen.utils import CompressionFlag
from argparse import ArgumentParser
from TinGen import TinGen
from pathlib import Path

if __name__ == '__main__':
    parser = ArgumentParser(
        description='Script that will allow you to generate an index file ' +
        'with Google Drive file links for use with Tinfoil',
    )
    parser.add_argument(
        nargs='*',
        metavar='FOLDER_ID_TO_SCAN',
        dest='folder_ids',
        help='Folder IDs of Google Drive folders to scan',
    )
    parser.add_argument(
        '--credentials',
        default='credentials.json',
        metavar='CREDENTIALS_FILE_NAME',
        help='Path to Google Application Credentials',
    )
    parser.add_argument(
        '--token',
        default='gdrive.token',
        metavar='TOKEN_FILE_PATH',
        help='Path to Google OAuth2.0 User Token',
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Allows to perform Google OAuth2.0 User Token Authentication ' +
        'in headless environment',
    )
    parser.add_argument(
        '--index-file',
        metavar='INDEX_FILE_PATH',
        default='index.tfl',
        help='Path to output index file',
    )
    parser.add_argument(
        '--share-files',
        action='store_true',
        help='Share all files inside the index file',
    )
    parser.add_argument(
        '--no-recursion',
        dest='recursion',
        action='store_false',
        help='Scans for files only in top directory for each Folder ID ' +
        'entered',
    )
    parser.add_argument(
        '--add-nsw-files-without-title-id',
        action='store_true',
        help='Adds files without valid Title ID',
    )
    parser.add_argument(
        '--add-non-nsw-files',
        action='store_true',
        help='Adds files without valid NSW ROM extension(NSP/NSZ/XCI/XCZ) ' +
        'to index',
    )
    parser.add_argument(
        '--success',
        metavar='SUCCESS_MESSAGE',
        help='Adds a success message to index file to show if index is ' +
        'successfully read by Tinfoil',
    )
    parser.add_argument(
        '--encrypt',
        action='store_true',
        help='Encrypts the resulting index file with AES-ECB-256',
    )
    parser.add_argument(
        '--public-key',
        metavar='PUBLIC_KEY_FILE_PATH',
        default='public.pem',
        help='Path to RSA Public Key to encrypt AES-ECB-256 key with',
    )
    parser.add_argument(
        '--vm-file',
        help='Path to VM File',
    )
    parser.add_argument(
        '--upload-to-folder-id',
        metavar='UPLOAD_FOLDER_ID',
        dest='upload_folder_id',
        help='Upload resulting index to Folder ID supplied',
    )
    parser.add_argument(
        '--upload-to-my-drive',
        action='store_true',
        help='Upload resulting index to My Drive',
    )
    parser.add_argument(
        '--new-upload-id',
        action='store_true',
        help='Uploads the newly generated index file with a new File ID ' +
        'instead of replacing old one',
    )
    parser.add_argument(
        '--share-uploaded-index',
        action='store_true',
        help='Shares the index file that is uploaded to Google Drive',
    )

    compression_parser = parser.add_mutually_exclusive_group()
    compression_parser.add_argument(
        '--zstandard',
        '--zstd',
        action='store_true',
        help='Compresses index with Zstandard compression method',
    )
    compression_parser.add_argument(
        '--zlib',
        action='store_true',
        help='Compresses index with zlib compression method',
    )
    compression_parser.add_argument(
        '--no-compress',
        action='store_true',
        help='Flag to not compress index',
    )

    args = parser.parse_args()
    generator = TinGen(
        args.token,
        args.credentials,
        args.headless,
    )

    print('Generating index')
    generator.index_generator(
        args.folder_ids,
        args.recursion,
        args.add_nsw_files_without_title_id,
        args.add_non_nsw_files,
    )

    if args.success:
        print('Adding success message to index')
        generator.update_index_success_message(
            args.success.replace('\\n', '\n').replace('\\t', '\t'),
        )

    compression_flag = CompressionFlag.ZSTD_COMPRESSION

    if args.zstandard:
        compression_flag = CompressionFlag.ZSTD_COMPRESSION
    elif args.zlib:
        compression_flag = CompressionFlag.ZLIB_COMPRESSION
    elif args.no_compress:
        compression_flag = CompressionFlag.NO_COMPRESSION

    print(f'Creating generated index to {args.index_file}')
    if args.encrypt and args.vm_file and args.public_key:
        create_tinfoil_index(
            generator.index,
            Path(args.index_file),
            compression_flag,
            rsa_pub_key_path=Path(args.public_key),
            vm_path=Path(args.vm_file),
        )
    else:
        create_tinfoil_index(
            generator.index,
            Path(args.index_file),
            compression_flag,
        )

    if args.share_files:
        print('Sharing files in index')
        generator.share_index_files()

    if args.upload_folder_id:
        print(f'Uploading {args.index_file} to {args.upload_folder_id}')
        generator.gdrive_service.upload_file(
            args.index_file,
            args.upload_folder_id,
            args.share_uploaded_index,
            args.new_upload_id,
        )

    if args.upload_to_my_drive:
        print(f'Uploading {args.index_file} to \"My Drive\"')
        generator.gdrive_service.upload_file(
            args.index_file,
            None,
            args.share_uploaded_index,
            args.new_upload_id,
        )

    print('Index Generation Complete')
