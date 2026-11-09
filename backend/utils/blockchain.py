"""Mock blockchain anchoring for degree/certificate verification (Phase 3).

No real chain is involved. `anchor_document` fingerprints the uploaded file with SHA-256 and returns a
fake, random-looking transaction hash plus a fake block number. The fingerprint is real, so later we can
re-hash the stored file and detect tampering (see `file_matches`).

To go live, keep these function signatures and swap the body for a call to a real provider
(a public chain, a permissioned ledger or a credential-anchoring API). Nothing else in the app changes.
"""
import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

NETWORK = "aeterna-mock-chain"
_TX_RE = re.compile(r"^0x[0-9a-f]{64}$")


@dataclass(frozen=True)
class AnchorReceipt:
    tx_hash: str          # "0x" + 64 hex chars, like an Ethereum transaction hash
    document_sha256: str  # real fingerprint of the file that was anchored
    block_number: int     # fake
    network: str
    anchored_at: datetime


def sha256_of_file(file_obj) -> str:
    """SHA-256 of a Django File/UploadedFile/FieldFile, read in chunks. Leaves the file rewound."""
    h = hashlib.sha256()
    file_obj.seek(0)
    for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
        h.update(chunk)
    file_obj.seek(0)
    return h.hexdigest()


def anchor_document(file_obj, *, issuer_id: int, subject_id: int) -> AnchorReceipt:
    """Pretend to write the document fingerprint to a blockchain and return the receipt."""
    doc_hash = sha256_of_file(file_obj)
    now = timezone.now()
    # A random nonce makes every transaction hash unique, even if the same file is anchored twice.
    seed = f"{doc_hash}:{issuer_id}:{subject_id}:{now.isoformat()}:{secrets.token_hex(16)}"
    return AnchorReceipt(
        tx_hash="0x" + hashlib.sha256(seed.encode()).hexdigest(),
        document_sha256=doc_hash,
        block_number=int(now.timestamp()) // 12,  # looks like a ~12s block time
        network=NETWORK,
        anchored_at=now,
    )


def is_valid_tx_hash(value: str) -> bool:
    return bool(_TX_RE.match(value or ""))


def file_matches(file_obj, expected_sha256: str) -> bool:
    """True if the stored file still hashes to what was anchored (i.e. it has not been altered)."""
    try:
        return bool(expected_sha256) and sha256_of_file(file_obj) == expected_sha256
    except (OSError, ValueError):  # file missing from disk / storage
        return False
