#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Any, Mapping
from typing import List
from typing import Optional
from requests import Request
from TinGen.google.drive.v3.files import FILES_BASE_URL


def create(
    file_id: str,
    perm_info: Mapping[str, Any],
    fields: Optional[List[str]] = None,
    **params: Any,
) -> Request:
    '''Creates a new permission for a file.

    For more info,
    https://developers.google.com/drive/api/v3/reference/permissions/create
    '''
    if fields is not None:
        _fields = ','.join(fields)
        params.update({
            'fields': _fields,
        })

    data = json.dumps(perm_info)

    headers = {
        'Content-Type': 'application/json',
        'Content-Length': len(data)
    }

    return Request(
        'POST',
        f'{FILES_BASE_URL}/{file_id}/permissions',
        params=params,
        headers=headers,
        data=data
    )


def delete(
    file_id: str,
    perm_id: str,
    **params: Any,
) -> Request:
    '''Deletes a file permission with file ID and permission ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/permissions/delete
    '''
    return Request(
        'DELETE',
        f'{FILES_BASE_URL}/{file_id}/permissions/{perm_id}',
        params=params,
    )


def get(
    file_id: str,
    perm_id: str,
    fields: Optional[List[str]] = None,
    **params: Any,
) -> Request:
    '''Retrieve a file permission information by file ID and
    permission ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/permissions/get
    '''
    if fields is not None:
        _fields = ','.join(fields)
        params.update({
            'fields': _fields,
        })

    return Request(
        'GET',
        f'{FILES_BASE_URL}/{file_id}/permissions/{perm_id}',
        params=params,
    )


def list_(
    file_id: str,
    fields: Optional[List[str]] = None,
    **params: Any,
) -> Request:
    '''List all file permissions by file ID.

    For more information,
    https://developers.google.com/drive/api/v3/reference/permissions/list
    '''
    if fields is not None:
        _perm_fields = ','.join(fields)
        _fields = f'kind,nextPageToken,permissions({_perm_fields})'
        params.update({
            'fields': _fields,
        })

    return Request(
        'GET',
        f'{FILES_BASE_URL}/{file_id}/permissions',
        params=params,
    )


def update(
    file_id: str,
    perm_id: str,
    perm_info: Mapping[str, dict],
    fields: Optional[List[str]] = None,
    **params: Any,
) -> Request:
    '''Update file permission information.

    For more information,
    https://developers.google.com/drive/api/v3/reference/permissions/update
    '''
    params = {}

    if fields is not None:
        _perm_fields = ','.join(fields)
        params.update({
            'fields': _perm_fields,
        })

    data = json.dumps(perm_info)

    headers = {
        'Content-Type': 'application/json',
        'Content-Length': len(data),
    }

    return Request(
        'PATCH',
        f'{FILES_BASE_URL}/{file_id}/permissions/{perm_id}',
        headers=headers,
        params=params,
        data=data,
    )
