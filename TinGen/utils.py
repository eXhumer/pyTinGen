from Crypto.Cipher.AES import MODE_ECB
from Crypto.Cipher.AES import new as new_aes_ctx
from Crypto.Cipher.PKCS1_OAEP import new as new_pkcs1_oaep_ctx
from Crypto.Hash import SHA256
from Crypto.PublicKey.RSA import import_key as import_rsa_key
from enum import IntEnum
from json import dumps as json_serialize
from json import loads as json_deserialize
from json import JSONDecodeError
from pathlib import Path
from random import randint
from zlib import compress as zlib_compress
from zlib import decompress as zlib_decompress
from zstandard import ZstdCompressor
from zstandard import ZstdDecompressor


class CompressionFlag(IntEnum):
    ZLIB_COMPRESSION = 0x0E
    ZSTD_COMPRESSION = 0x0D
    NO_COMPRESSION = 0x00


class EncryptionFlag(IntEnum):
    ENCRYPT = 0xF0
    NO_ENCRYPT = 0x00


def create_tinfoil_index(
    index_to_write: dict,
    out_path: Path,
    compression_flag: int,
    rsa_pub_key_path: Path = None,
    vm_path: Path = None
):
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
        to_write_buffer += ZstdCompressor(level=22).compress(
            to_compress_buffer
        )

    elif compression_flag == CompressionFlag.ZLIB_COMPRESSION:
        to_write_buffer += zlib_compress(to_compress_buffer, 9)

    elif compression_flag == CompressionFlag.NO_COMPRESSION:
        to_write_buffer += to_compress_buffer

    else:
        raise NotImplementedError(
            "Compression method supplied is not implemented yet."
        )

    data_size = len(to_write_buffer)
    flag = None
    to_write_buffer += (b"\x00" * (0x10 - (data_size % 0x10)))

    if rsa_pub_key_path is not None and rsa_pub_key_path.is_file():
        def rand_aes_key_generator() -> bytes:
            return randint(0, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF).to_bytes(
                0x10, byteorder="big"
            )

        rsa_pub_key = import_rsa_key(open(rsa_pub_key_path).read())
        rand_aes_key = rand_aes_key_generator()

        pkcs1_oaep_ctx = new_pkcs1_oaep_ctx(
            rsa_pub_key,
            hashAlgo=SHA256,
            label=b""
        )
        aes_ctx = new_aes_ctx(rand_aes_key, MODE_ECB)

        session_key += pkcs1_oaep_ctx.encrypt(rand_aes_key)
        to_write_buffer = aes_ctx.encrypt(to_write_buffer)
        flag = compression_flag | EncryptionFlag.ENCRYPT
    else:
        session_key += b"\x00" * 0x100
        flag = compression_flag | EncryptionFlag.NO_ENCRYPT

    Path(out_path.parent).mkdir(parents=True, exist_ok=True)

    with open(out_path, "wb") as out_stream:
        out_stream.write(b"TINFOIL")
        out_stream.write(flag.to_bytes(1, byteorder="little"))
        out_stream.write(session_key)
        out_stream.write(data_size.to_bytes(8, "little"))
        out_stream.write(to_write_buffer)


def read_index(index_path: Path, rsa_priv_key_path: Path = None) -> dict:
    if index_path is None or not index_path.is_file():
        raise RuntimeError(
            f"Unable to read non-existant index file \"{index_path}\""
        )

    encryption_flag = None
    compression_flag = None
    session_key = None
    data_size = None
    to_read_buffer = None

    with open(index_path, "rb") as index_stream:
        magic = str(index_stream.read(7))

        if magic != "TINFOIL":
            raise RuntimeError(
                "Invalid tinfoil index magic.\n\nExpected Magic = " +
                f"\"TINFOIL\"\nMagic in index file = \"{magic}\""
            )

        flags = index_stream.read(1)[0]
        encryption_flag = flags & 0xF0

        key_available = rsa_priv_key_path is not None and \
            rsa_priv_key_path.is_file()

        if encryption_flag == EncryptionFlag.ENCRYPT and not key_available:
            raise RuntimeError(
                "Unable to decrypt encrypted index without private key."
            )

        compression_flag = flags & 0x0F

        if compression_flag not in CompressionFlag:
            raise RuntimeError(
                "Unimplemented compression method encountered while reading " +
                "index header."
            )

        session_key = index_stream.read(0x100)
        data_size = int.from_bytes(index_stream.read(8), byteorder="little")
        to_read_buffer = index_stream.read()

    if encryption_flag == EncryptionFlag.ENCRYPT:
        rsa_priv_key = import_rsa_key(open(rsa_priv_key_path).read())
        pkcs1_oaep_ctx = new_pkcs1_oaep_ctx(
            rsa_priv_key,
            hashAlgo=SHA256,
            label=b""
        )
        aes_key = pkcs1_oaep_ctx.decrypt(session_key)
        aes_ctx = new_aes_ctx(aes_key, MODE_ECB)
        to_read_buffer = aes_ctx.decrypt(to_read_buffer)

    if compression_flag == CompressionFlag.ZSTD_COMPRESSION:
        to_read_buffer = ZstdDecompressor().decompress(
            to_read_buffer[:data_size]
        )

    elif compression_flag == CompressionFlag.ZLIB_COMPRESSION:
        to_read_buffer = zlib_decompress(to_read_buffer[:data_size])

    elif compression_flag == CompressionFlag.NO_COMPRESSION:
        to_read_buffer = to_read_buffer[:data_size]

    try:
        return json_deserialize(to_read_buffer)

    except JSONDecodeError:
        raise RuntimeError("Unable to deserialize index data.")
