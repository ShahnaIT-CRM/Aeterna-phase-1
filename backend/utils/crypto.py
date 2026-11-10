"""Cryptography for signed degrees (Phase 4).

Each verified university owns an Ed25519 key pair.
  * The public key is stored as-is (base64 of the 32 raw bytes) and is published by the verify endpoint,
    so anyone can check a signature without trusting Aeterna.
  * The private key is stored only in encrypted form (Fernet / AES-128-CBC + HMAC) under a server-side
    master key (settings.PKI_MASTER_KEYS). It is decrypted in memory for the instant of one signature.

What gets signed is not the bare file hash but a canonical message that also names the degree
(id, teacher, university, course, level, year) and the hash. A genuine signed PDF therefore cannot be
re-attached to a different degree record.

Production upgrade path: move the private keys into a KMS/HSM and replace `sign_message`; nothing else changes.
"""
import base64
import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

ALGORITHM = "Ed25519"
MESSAGE_VERSION = 1


class KeyDecryptionError(Exception):
    """The stored private key could not be decrypted (wrong or rotated-away master key)."""


# ----------------------------------------------------------------------------- master key
def _fernet() -> MultiFernet:
    """First key encrypts, all keys can decrypt, so the master key can be rotated without downtime."""
    raw = [k.strip() for k in getattr(settings, "PKI_MASTER_KEYS", []) if k.strip()]
    if not raw:
        if settings.DEBUG or getattr(settings, "TESTING", False):  # dev/test only; never used in production
            raw = [base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest()).decode()]
        else:
            raise ImproperlyConfigured(
                "Set PKI_MASTER_KEYS (generate one with: python -c "
                "\"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\")."
            )
    return MultiFernet([Fernet(k.encode()) for k in raw])


# ----------------------------------------------------------------------------- keys
def generate_keypair() -> tuple[str, str]:
    """Return (public_key_b64, encrypted_private_key). Only these two strings are ever stored."""
    private = Ed25519PrivateKey.generate()
    raw_private = private.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    raw_public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return (
        base64.b64encode(raw_public).decode(),
        _fernet().encrypt(raw_private).decode(),
    )


def public_key_fingerprint(public_key_b64: str) -> str:
    """Short human-comparable id of a public key: first 16 hex chars of its SHA-256, in groups of 4."""
    digest = hashlib.sha256(base64.b64decode(public_key_b64)).hexdigest()[:16]
    return ":".join(digest[i:i + 4] for i in range(0, 16, 4))


# ----------------------------------------------------------------------------- hashing / message
def sha256_of_file(file_obj) -> str:
    """SHA-256 of a Django File/UploadedFile/FieldFile, read in chunks. Leaves the file rewound."""
    h = hashlib.sha256()
    if getattr(file_obj, "closed", False):
        file_obj.open("rb")
    file_obj.seek(0)
    for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
        h.update(chunk)
    file_obj.seek(0)
    return h.hexdigest()


def build_credential_message(*, qualification_id, teacher_id, university_id, course, level,
                             year_of_passing, document_sha256) -> bytes:
    """Deterministic bytes that get signed (sorted keys, no whitespace)."""
    payload = {
        "v": MESSAGE_VERSION,
        "qualification_id": qualification_id,
        "teacher_id": teacher_id,
        "university_id": university_id,
        "course": course,
        "level": level,
        "year_of_passing": year_of_passing,
        "document_sha256": document_sha256,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


# ----------------------------------------------------------------------------- sign / verify
def sign_message(encrypted_private_key: str, message: bytes) -> str:
    """Decrypt the private key in memory, sign, return the base64 signature."""
    try:
        raw = _fernet().decrypt(encrypted_private_key.encode())
    except InvalidToken as exc:
        raise KeyDecryptionError("Stored private key cannot be decrypted with the configured master key.") from exc
    return base64.b64encode(Ed25519PrivateKey.from_private_bytes(raw).sign(message)).decode()


def verify_signature(public_key_b64: str, message: bytes, signature_b64: str) -> bool:
    try:
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        key.verify(base64.b64decode(signature_b64), message)
        return True
    except (InvalidSignature, ValueError):
        return False


def file_matches(file_obj, expected_sha256: str) -> bool:
    """True if the stored file still hashes to what was signed (i.e. it has not been altered)."""
    try:
        return bool(expected_sha256) and sha256_of_file(file_obj) == expected_sha256
    except (OSError, ValueError):  # file missing from disk / storage
        return False
