import base64
import hashlib
import json
import time
from typing import Optional

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization


def generate_es256_keypair() -> tuple[str, dict]:
    """Generate an ES256 (P-256) key pair. Returns (PEM private key, JWK public key)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": _int_to_base64url(public_numbers.x, 32),
        "y": _int_to_base64url(public_numbers.y, 32),
    }

    return private_pem, jwk


def sign_mandate(payload: dict, private_key_pem: str, vct: str) -> str:
    """Sign a mandate payload as a JWT using ES256."""
    headers = {
        "alg": "ES256",
        "typ": "mandate+jwt",
        "vct": vct,
    }
    return jwt.encode(payload, private_key_pem, algorithm="ES256", headers=headers)


def verify_mandate(token: str, public_key_jwk: dict) -> dict:
    """Verify a mandate JWT signature and return the payload."""
    public_key = _jwk_to_public_key(public_key_jwk)
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return jwt.decode(token, public_pem, algorithms=["ES256"])


def hash_mandate(token: str) -> str:
    """Compute base64url-encoded SHA-256 hash of a mandate JWT."""
    digest = hashlib.sha256(token.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _int_to_base64url(value: int, length: int) -> str:
    value_bytes = value.to_bytes(length, byteorder="big")
    return base64.urlsafe_b64encode(value_bytes).rstrip(b"=").decode()


def _base64url_to_int(b64: str) -> int:
    padding = 4 - len(b64) % 4
    if padding != 4:
        b64 += "=" * padding
    value_bytes = base64.urlsafe_b64decode(b64)
    return int.from_bytes(value_bytes, byteorder="big")


def _jwk_to_public_key(jwk: dict):
    x = _base64url_to_int(jwk["x"])
    y = _base64url_to_int(jwk["y"])
    public_numbers = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1())
    return public_numbers.public_key()
