# Tinfoil GDrive Generator exists so you can make your iwn index.json 
# Copyright (C) 2020 Tony Langhammer

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

#/bin/python3
import sys
import os
import base64
from Crypto.Signature import PKCS1_PSS
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA 
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from binascii import hexlify as hx, unhexlify as uhx
import random
import Crypto.Hash
import zlib
import pathlib

def encrypt_file(input, output, public_key="public.key"):
    pubKey = RSA.importKey(open(public_key).read())

    def wrapKey(key):
        cipher = PKCS1_OAEP.new(pubKey, hashAlgo = Crypto.Hash.SHA256, label=b'')
        return cipher.encrypt(key)

    aesKey = random.randint(0,0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF).to_bytes(0x10, 'big')

    buf = None

    with open(input, 'rb') as f:
        cipher = AES.new(aesKey, AES.MODE_ECB)
        buf = zlib.compress(f.read(), 9)
        sz = len(buf)
        buf = cipher.encrypt(buf + (b'\x00' * (0x10 - (sz % 0x10))))

    print(aesKey)

    pathlib.Path(output).parent.resolve().mkdir(exist_ok=True, parents=True)
    with open(output, 'wb') as f:
        f.write(b'TINFOIL\xFE')
        f.write(wrapKey(aesKey))
        f.write(sz.to_bytes(8, 'little'))
        f.write(buf)
        
    print('fin')