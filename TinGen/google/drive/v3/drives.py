#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Any, Mapping
from typing import List
from typing import Optional
from requests import Request
from uuid import uuid4 as uuid_generator
from TinGen.google.drive.v3 import DRIVE_V3_BASE_URL

DRIVES_BASE_URL = f'{DRIVE_V3_BASE_URL}/drives'


def create(
    drive_info: Mapping[str, Any],
    **params: Any,
) -> Request:
    '''Creates a new shared drive.

    For more information,
    https://developers.google.com/drive/api/v3/reference/drives/create
    '''
    req_id = uuid_generator()

    params.update({
        'requestId': str(req_id),
    })

    data = json.dumps(drive_info)

    headers = {
        'Content-Type': 'application/json',
        'Content-Length': len(data),
    }

    return Request(
        'POST',
        DRIVES_BASE_URL,
        params=params,
        headers=headers,
        data=data,
    )


def delete(
    drive_id: str,
) -> Request:
    '''Deletes a new shared drive with shared drive ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/drives/delete
    '''
    return Request(
        'DELETE',
        f'{DRIVES_BASE_URL}/{drive_id}',
    )


def get(
    drive_id: str,
    fields: Optional[List[str]] = None,
    **params: Any,
) -> Request:
    '''Retrieve a shared drive information via Shared Drive ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/drives/get
    '''
    if fields is not None:
        _fields = ','.join(fields)
        params.update({'fields': _fields})

    return Request(
        'GET',
        f'{DRIVES_BASE_URL}/{drive_id}',
        params=params,
    )


def hide(
    drive_id: str,
) -> Request:
    '''Hides a shared drive with shared drive ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/drives/hide
    '''
    return Request(
        'POST',
        f'{DRIVES_BASE_URL}/{drive_id}/hide',
    )


def list_(
    fields: Optional[List[str]] = None,
    **params: Any,
) -> Request:
    '''List all shared drives.

    For more information,
    https://developers.google.com/drive/api/v3/reference/drives/list
    '''
    if fields is not None:
        _drive_fields = ','.join(fields)
        _fields = f'kind,nextPageToken,drives({_drive_fields})'
        params.update({
            'fields': _fields,
        })

    return Request(
        'GET',
        DRIVES_BASE_URL,
        params=params,
    )


def unhide(
    drive_id: str,
) -> Request:
    '''Unhides a shared drive with shared drive ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/drives/unhide
    '''
    return Request(
        'POST',
        f'{DRIVES_BASE_URL}/{drive_id}/unhide'
    )


def update(
    drive_id: str,
    drive_info: Mapping[str, Any],
    **params: Any,
) -> Request:
    '''Update Shared Drive information.

    For more information,
    https://developers.google.com/drive/api/v3/reference/drives/update
    '''
    data = json.dumps(drive_info)

    headers = {
        'Content-Type': 'application/json',
        'Content-Length': len(data),
    }

    return Request(
        'PATCH',
        f'{DRIVES_BASE_URL}/{drive_id}',
        headers=headers,
        params=params,
        data=data,
    )
