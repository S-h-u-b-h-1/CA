import hashlib
import re
from sqlalchemy.orm import Session
from app.models.models import RawDocument, DocumentVersion

def compute_simhash(text: str) -> str:
    """
    Computes a 64-bit SimHash (locality-sensitive hash) represented as a 16-character hex string.
    This allows near-duplicate detection by comparing the Hamming distance of hashes.
    """
    # 1. Tokenize into words
    words = re.findall(r"\w+", text.lower())
    if not words:
        return "0000000000000000"

    # 2. Initialize weights array for 64 bits
    v = [0] * 64
    for word in words:
        # Generate 128-bit hash of the token using MD5
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        for i in range(64):
            # Inspect i-th bit of the hash
            bit = (h >> i) & 1
            if bit:
                v[i] += 1
            else:
                v[i] -= 1

    # 3. Aggregate into fingerprint
    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= (1 << i)

    return f"{fingerprint:016x}"


def get_hamming_distance(hash1: str, hash2: str) -> int:
    """Calculates the bitwise Hamming distance between two hex SimHashes"""
    try:
        h1 = int(hash1, 16)
        h2 = int(hash2, 16)
        # XOR to find differing bits
        xor = h1 ^ h2
        # Count set bits
        distance = bin(xor).count("1")
        return distance
    except ValueError:
        return 64


class DeduplicationEngine:
    @staticmethod
    def calculate_file_hashes(file_content: bytes) -> dict:
        """Generates cryptographic, similarity, and structural fingerprints for a file"""
        sha256 = hashlib.sha256(file_content).hexdigest()
        md5 = hashlib.md5(file_content).hexdigest()
        
        # Decode content safely as UTF-8 text for SimHash features extraction
        text = file_content.decode("utf-8", errors="ignore")
        similarity_hash = compute_simhash(text)
        
        # File structural fingerprint: combination of size and a hash of the first 512 bytes
        head = file_content[:512]
        head_md5 = hashlib.md5(head).hexdigest()
        file_fingerprint = f"sz_{len(file_content)}_head_{head_md5}"

        return {
            "sha256": sha256,
            "md5": md5,
            "similarity_hash": similarity_hash,
            "file_fingerprint": file_fingerprint
        }

    @staticmethod
    def check_duplicate_by_sha256(db: Session, organization_id: str, sha256_hash: str) -> RawDocument | None:
        """Finds any existing raw document with the exact same SHA256 hash in the same organization"""
        return db.query(RawDocument).filter(
            RawDocument.organization_id == organization_id,
            RawDocument.sha256_hash == sha256_hash,
            RawDocument.status == "ACTIVE"
        ).first()

    @staticmethod
    def create_document_version(
        db: Session, 
        organization_id: str, 
        raw_document: RawDocument, 
        new_file_path: str, 
        change_summary: str = "New version uploaded"
    ) -> DocumentVersion:
        """Increments the document's version indicator and adds a log to document_versions"""
        next_ver = raw_document.version + 1
        
        # Log old version before updating
        version_log = DocumentVersion(
            organization_id=organization_id,
            raw_document_id=raw_document.id,
            version_number=raw_document.version,
            file_path=raw_document.file_path,
            change_summary=change_summary
        )
        db.add(version_log)
        
        # Update raw document metadata
        raw_document.version = next_ver
        raw_document.file_path = new_file_path
        
        db.commit()
        db.refresh(raw_document)
        return version_log
