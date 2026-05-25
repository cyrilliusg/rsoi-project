"""PKCE (RFC 7636) helpers."""
import base64
import hashlib


def verify_challenge(*, code_verifier: str, code_challenge: str, method: str) -> bool:
    """Return True iff `code_verifier` matches `code_challenge` under `method`."""
    if method == "S256":
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return expected == code_challenge
    if method == "plain":
        return code_verifier == code_challenge
    return False
