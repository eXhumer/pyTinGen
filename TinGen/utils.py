from binascii import hexlify
from binascii import unhexlify
from Crypto.Cipher.AES import MODE_ECB
from Crypto.Cipher.AES import new as new_aes_ctx
from Crypto.Cipher.PKCS1_OAEP import new as new_pkcs1_oaep_ctx
from Crypto.Hash import SHA256
from Crypto.PublicKey.RSA import import_key as import_rsa_key
from enum import IntEnum
from json import dumps as json_serialize
from pathlib import Path
from random import randint
from zlib import compress as zlib_compress
from zstandard import ZstdCompressor


class CompressionFlag(IntEnum):
    ZLIB_COMPRESSION = 0xFE
    ZSTD_COMPRESSION = 0xFD
    NO_COMPRESSION = 0x00


def create_tinfoil_index(index_to_write: dict, out_path: Path, compression_flag: int, rsa_pub_key_path: Path=None, vm_path: Path=None):
    to_compress_buffer = b""

    if vm_path is not None and vm_path.is_file():
        to_compress_buffer += b"\x13\x37\xB0\x0B"
        vm_buffer = b""

        with open(vm_path, "rb") as vm_stream:
            vm_buffer += vm_stream.read()

        to_compress_buffer += len(vm_buffer).to_bytes(4, "little")
        to_compress_buffer += vm_buffer

    to_compress_buffer += bytes(json_serialize(index_to_write).encode())

    to_write_buffer = b""
    session_key = b""

    if compression_flag == CompressionFlag.ZSTD_COMPRESSION:
        to_write_buffer += ZstdCompressor(level=22).compress(to_compress_buffer)

    elif compression_flag == CompressionFlag.ZLIB_COMPRESSION:
        to_write_buffer += zlib_compress(to_compress_buffer, 9)

    elif compression_flag == CompressionFlag.NO_COMPRESSION:
        to_write_buffer += to_compress_buffer

    else:
        raise NotImplementedError("Compression method supplied is not implemented yet.")

    to_write_buffer += (b"\x00" * (0x10 - (len(to_write_buffer) % 0x10)))

    if rsa_pub_key_path.is_file():
        def rand_aes_key_generator() -> bytes:
            return randint(0, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF).to_bytes(0x10, "big")

        rsa_pub_key = import_rsa_key(open(rsa_pub_key_path).read())
        rand_aes_key = rand_aes_key_generator()

        pkcs1_oaep_ctx = new_pkcs1_oaep_ctx(rsa_pub_key, hashAlgo=SHA256, label=b"")
        aes_ctx = new_aes_ctx(rand_aes_key, MODE_ECB)

        session_key += pkcs1_oaep_ctx.encrypt(rand_aes_key)
        to_write_buffer = aes_ctx.encrypt(to_write_buffer)

    else:
        session_key += b"\x00" * 0xFF

    Path(out_path.parent).mkdir(parents=True, exist_ok=True)

    with open(out_path, "wb") as out_stream:
        out_stream.write(b"TINFOIL")
        out_stream.write(bytes(compression_flag))
        out_stream.write(session_key)
        out_stream.write(len(to_write_buffer).to_bytes(8, "little"))
        out_stream.write(to_write_buffer)