#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import List
from typing import Optional
from requests import Request
from google.drive.v3 import DRIVE_V3_BASE_URL

FILES_BASE_URL = f'{DRIVE_V3_BASE_URL}/files'


def copy(
    file_id: str,
    fields: Optional[List[str]] = None,
    ocr_language: Optional[str] = None,
    supports_all_drives: Optional[str] = None,
    keep_revision_forever: Optional[bool] = None,
    enforce_single_parent: Optional[bool] = None,
    ignore_default_visibility: Optional[bool] = None,
    include_permissions_for_view: Optional[str] = None,
    **file_info,
) -> Request:
    '''Make a server side copy using file ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/files/copy
    '''
    params = {}

    if enforce_single_parent is not None:
        params.update({
            'enforceSingleParent': enforce_single_parent,
        })

    if fields is not None:
        _fields = ','.join(fields)
        params.update({
            'fields': _fields,
        })

    if ignore_default_visibility is not None:
        params.update({
            'ignoreDefaultVisibility': ignore_default_visibility,
        })

    if include_permissions_for_view is not None:
        params.update({
            'includePermissionsForView': include_permissions_for_view,
        })

    if keep_revision_forever is not None:
        params.update({
            'keepRevisionForever': keep_revision_forever,
        })

    if ocr_language is not None:
        params.update({
            'ocrLanguage': ocr_language,
        })

    if supports_all_drives is not None:
        params.update({
            'supportsAllDrives': supports_all_drives,
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
    supports_all_drives: Optional[str] = None,
) -> Request:
    '''Delete a file using file ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/files/delete
    '''
    params = {}

    if supports_all_drives is not None:
        params.update({
            'supportsAllDrives': supports_all_drives,
        })

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
    mime_type: str,
    fields: Optional[List[str]] = None,
) -> Request:
    '''Export a Google Doc to the requested MIME type.

    For more information,
    https://developers.google.com/drive/api/v3/reference/files/export
    '''
    params = {}

    params.update({
        'mimeType': mime_type,
    })

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
    count: Optional[int],
    fields: Optional[List[str]] = None,
    space: Optional[str] = None,
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

    if count is not None:
        params.update({
            'count': count,
        })

    if space is not None:
        params.update({
            'space': space,
        })

    return Request(
        'GET',
        f'{FILES_BASE_URL}/generateIds',
        params=params,
    )


def list_(
    q: Optional[str] = None,
    spaces: Optional[str] = None,
    drive_id: Optional[str] = None,
    page_size: Optional[int] = None,
    page_token: Optional[str] = None,
    fields: Optional[List[str]] = None,
    corpora: Optional[str] = None,
    order_by: Optional[str] = None,
    supports_all_drives: Optional[str] = None,
    include_permissions_for_view: Optional[str] = None,
    include_items_from_all_drives: Optional[bool] = None,
) -> Request:
    '''Get a list of files.

    For more information,
    https://developers.google.com/drive/api/v3/reference/files/list
    '''
    params = {}

    if fields is not None:
        files_field = ','.join(fields)
        _fields = 'kind,nextPageToken,incompleteSearch,' + \
                  f'files({files_field})'
        params.update({
            'fields': _fields,
        })

    if corpora is not None:
        params.update({
            'corpora': corpora,
        })

    if drive_id is not None:
        params.update({
            'driveId': drive_id,
        })

    if include_items_from_all_drives is not None:
        params.update({
            'includeItemsFromAllDrives': include_items_from_all_drives,
        })

    if include_permissions_for_view is not None:
        params.update({
            'includePermissionsForView': include_permissions_for_view,
        })

    if order_by is not None:
        params.update({
            'orderBy': order_by,
        })

    if page_size is not None:
        params.update({
            'pageSize': page_size,
        })

    if page_token is not None:
        params.update({
            'pageToken': page_token,
        })

    if q is not None:
        params.update({
            'q': q,
        })

    if spaces is not None:
        params.update({
            'spaces': spaces,
        })

    if supports_all_drives is not None:
        params.update({
            'supportsAllDrives': supports_all_drives,
        })

    return Request(
        'GET',
        f'{FILES_BASE_URL}/generateIds',
        params=params,
    )

# TODO - Implement Upload/Download
