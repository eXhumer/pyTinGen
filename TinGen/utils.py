from Crypto.Cipher.PKCS1_OAEP import new as new_pkcs1_oaep_ctx
from Crypto.Cipher.AES import new as new_aes_ctx
from Crypto.Cipher.AES import MODE_ECB
from Crypto.PublicKey.RSA import import_key as import_rsa_key
from Crypto.Hash import SHA256
from pathlib import Path
from random import randint
from json import dumps as json_serialize
from zstandard import ZstdCompressor
from binascii import hexlify
from binascii import unhexlify

def rand_aes_key_generator() -> bytes:
    return randint(0, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF).to_bytes(0x10, "big")

def create_encrypted_index(index_to_write: dict, out_path: Path, rsa_pub_key_path: Path, vm_path: Path):
    if rsa_pub_key_path.is_file():
        index_buffer = bytes(json_serialize(index_to_write).encode())
        rsa_pub_key = import_rsa_key(open(rsa_pub_key_path).read())
        rand_aes_key = rand_aes_key_generator()

        aes_ctx = new_aes_ctx(rand_aes_key, MODE_ECB)
        pkcs1_oaep_ctx = new_pkcs1_oaep_ctx(rsa_pub_key, hashAlgo=SHA256, label=b"")

        to_compress_buffer = b""

        if vm_path is not None and vm_path.is_file():
            to_compress_buffer += b"\x13\x37\xB0\x0B"
            vm_buffer = b""

            with open(vm_path, "rb") as vm_stream:
                vm_buffer += vm_stream.read()

            to_compress_buffer += len(vm_buffer).to_bytes(4, "little")
            to_compress_buffer += vm_buffer

        to_compress_buffer += index_buffer

        index_compressed_buffer = ZstdCompressor(level=22).compress(to_compress_buffer)

        session_key = pkcs1_oaep_ctx.encrypt(rand_aes_key)
        encrypted_index = aes_ctx.encrypt(index_compressed_buffer + (b"\x00" * (0x10 - (len(index_compressed_buffer) % 0x10))))

        Path(out_path.parent).mkdir(parents=True, exist_ok=True)

        with open(out_path, "wb") as out_stream:
            out_stream.write(b"TINFOIL")
            out_stream.write(b"\xFD") # Compression indicator flag - 0xF0 | 0x0D for zstandard, 0xF0 | 0x0E for zlib, 0xF0 | 0x00 for no compression
            out_stream.write(session_key)
            out_stream.write(len(index_compressed_buffer).to_bytes(8, "little"))
            out_stream.write(encrypted_index)

    else:
        print(f"{rsa_pub_key_path} does not exist. Cannot encrypt without key.")