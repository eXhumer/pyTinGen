#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import List
from typing import Optional
from requests import Request
from uuid import uuid4 as uuid_generator
from TinGen.google.drive.v3 import DRIVE_V3_BASE_URL

DRIVES_BASE_URL = f'{DRIVE_V3_BASE_URL}/drives'


def create(
    drive_name: str,
    **drive_info,
) -> Request:
    '''Creates a new shared drive.

    For more information,
    https://developers.google.com/drive/api/v3/reference/drives/create
    '''
    req_id = uuid_generator()

    params = {
        'requestId': str(req_id),
    }

    drive_info.update({
        'name': drive_name,
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
    use_domain_admin_access: Optional[bool] = None,
) -> Request:
    '''Retrieve a shared drive information via Shared Drive ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/drives/get
    '''
    params = {}

    if fields is not None:
        _fields = ','.join(fields)
        params.update({'fields': _fields})

    if use_domain_admin_access is not None:
        params.update({
            'useDomainAdminAccess': use_domain_admin_access,
        })

    return Request(
        'GET',
        f'{DRIVES_BASE_URL}/{drive_id}',
        params=params
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
    q: Optional[str] = None,
    page_size: Optional[int] = None,
    page_token: Optional[str] = None,
    fields: Optional[List[str]] = None,
    use_domain_admin_access: Optional[bool] = None,
) -> Request:
    '''List all shared drives.

    For more information,
    https://developers.google.com/drive/api/v3/reference/drives/list
    '''
    params = {}

    if fields is not None:
        _drive_fields = ','.join(fields)
        _fields = f'kind,nextPageToken,drives({_drive_fields})'
        params.update({
            'fields': _fields,
        })

    if q is not None:
        params.update({
            'q': q,
        })

    if page_size is not None:
        params.update({
            'pageSize': page_size,
        })

    if page_token is not None:
        params.update({
            'pageToken': page_token,
        })

    if use_domain_admin_access is not None:
        params.update({
            'useDomainAdminAccess': use_domain_admin_access,
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
    use_domain_admin_access: Optional[bool] = None,
    **drive_info,
) -> Request:
    '''Update Shared Drive information.

    For more information,
    https://developers.google.com/drive/api/v3/reference/drives/update
    '''
    params = {}

    if use_domain_admin_access is not None:
        params.update({
            'useDomainAdminAccess': use_domain_admin_access,
        })

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
