#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Any, Mapping
from typing import List
from pathlib import Path
from typing import Optional
from requests import Request
from TinGen.google.drive.v3 import DRIVE_V3_BASE_URL

FILES_BASE_URL = f'{DRIVE_V3_BASE_URL}/files'


def copy(
    file_id: str,
    fields: Optional[List[str]] = None,
    file_info: Optional[Mapping[str, Any]] = None,
    **params: Any,
) -> Request:
    '''Make a server side copy using file ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/files/copy
    '''
    if fields is not None:
        _fields = ','.join(fields)
        params.update({
            'fields': _fields,
        })

    data = json.dumps(file_info)

    headers = {
        'Content-Type': 'application/json',
        'Content-Length': len(data),
    }

    return Request(
        'POST',
        f'{FILES_BASE_URL}/{file_id}/copy',
        params=params,
        headers=headers,
        data=data,
    )


def delete(
    file_id: str,
    **params: Any,
) -> Request:
    '''Delete a file using file ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/files/delete
    '''
    return Request(
        'DELETE',
        f'{FILES_BASE_URL}/{file_id}',
        params=params,
    )


def empty_trash() -> Request:
    '''Empty a user's trash.

    For more information,
    https://developers.google.com/drive/api/v3/reference/files/emptyTrash
    '''

    return Request(
        'DELETE',
        f'{FILES_BASE_URL}/trash',
    )


def export(
    file_id: str,
    fields: Optional[List[str]] = None,
    **params: Any,
) -> Request:
    '''Export a Google Doc to the requested MIME type.

    For more information,
    https://developers.google.com/drive/api/v3/reference/files/export
    '''
    if fields is not None:
        _fields = ','.join(fields)
        params.update({
            'fields': _fields,
        })

    return Request(
        'GET',
        f'{FILES_BASE_URL}/{file_id}/export',
        params=params,
    )


def generate_ids(
    fields: Optional[List[str]] = None,
    **params: Any,
) -> Request:
    '''Generates a set of file IDs which can be provided in create or copy
    requests.

    For more information,
    https://developers.google.com/drive/api/v3/reference/files/generateIds
    '''
    params = {}

    if fields is not None:
        _fields = ','.join(fields)
        params.update({
            'fields': _fields,
        })

    return Request(
        'GET',
        f'{FILES_BASE_URL}/generateIds',
        params=params,
    )


def list_(
    fields: Optional[List[str]] = None,
    **params,
) -> Request:
    '''Get a list of files.

    For more information,
    https://developers.google.com/drive/api/v3/reference/files/list
    '''
    if fields is not None:
        files_field = ','.join(fields)
        _fields = 'kind,nextPageToken,incompleteSearch,' + \
                  f'files({files_field})'
        params.update({
            'fields': _fields,
        })

    return Request(
        'GET',
        f'{FILES_BASE_URL}/generateIds',
        params=params,
    )


def create_new_resumable_upload(
    file_path: Path,
    file_id: Optional[str] = None,
    parents: Optional[List[str]] = None,
) -> Request:
    params = {
        'uploadType': 'resumable',
    }

    file_size = f'{file_path.stat().st_size}'

    method = 'POST'
    url = 'https://www.googleapis.com/upload/drive/v3/files'

    body = {
        'name': file_path.name,
        'size': file_size,
    }

    if file_id is not None:
        body.update({'id': file_id})
        url += f'/{file_id}'
        method = 'PATCH'

    if parents is not None:
        body.update({'parents': parents})

    data = json.dumps(body)

    headers = {
        'X-Upload-Content-Length': file_size,
        'Content-Length': f'{len(data)}',
        'Content-Type': 'application/json; charset=UTF-8',
    }

    return Request(
        method,
        url,
        data=data,
        headers=headers,
        params=params,
    )


def get_resumable_status(
    upload_id: str,
) -> Request:
    return Request(
        'PUT',
        'https://www.googleapis.com/upload/drive/v3/files',
        params={
            'uploadType': 'resumable',
            'upload_id': upload_id,
        },
    )


def upload_resumable_chunk(
    upload_id: str,
    file_path: Path,
    to_upload_start: Optional[int] = None,
    to_upload_end: Optional[int] = None,
) -> Request:
    file_size = file_path.stat().st_size
    if to_upload_start and to_upload_end:
        to_upload_size = to_upload_end - to_upload_start + 1
    else:
        to_upload_size = file_size

    with file_path.open(mode='rb') as file_stream:
        if to_upload_start:
            file_stream.seek(to_upload_start)
        data_chunk = file_stream.read(to_upload_size)

    return Request(
        'PUT',
        'https://www.googleapis.com/upload/drive/v3/files',
        params={
            'uploadType': 'resumable',
            'upload_id': upload_id,
        },
        headers={
            'Content-Length': f'{to_upload_size}',
            'Content-Range': f'bytes {to_upload_start}-' +
            f'{to_upload_end}/{file_size}'
        },
        data=data_chunk,
    )


def get(
    file_id: str,
    fields: Optional[List[str]] = None,
    **params: Any,
) -> Request:
    if fields:
        params.update({'fields': ','.join(fields)})
    return Request(
        'GET',
        f'https://www.googleapis.com/drive/v3/files/{file_id}',
        params=params,
    )


def download_file_chunked(
    file_id: str,
    download_start: Optional[int] = None,
    download_end: Optional[int] = None,
    **params: Any,
) -> Request:
    req = get(
        file_id,
        **params,
    )

    if download_start or download_end:
        req.headers['Range'] = 'bytes='

        if download_start:
            req.headers['Range'] += str(download_start)

        req.headers['Range'] += '-'

        if download_end:
            req.headers['Range'] += str(download_end)

    return req

# TODO - Streaming download
