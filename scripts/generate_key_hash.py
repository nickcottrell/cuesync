#!/usr/bin/env python3
"""
Generate SHA-256 hash of upstream key for config.yaml

Usage:
    ./generate_key_hash.py <upstream_key>

Example:
    ./generate_key_hash.py my-secret-key-12345
"""

import sys
import hashlib


def generate_hash(key: str) -> str:
    """Generate SHA-256 hash of key"""
    return hashlib.sha256(key.encode()).hexdigest()


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    key = sys.argv[1]
    key_hash = generate_hash(key)

    print(f"Upstream Key: {key}")
    print(f"SHA-256 Hash: {key_hash}")
    print()
    print("Add this to config.yaml:")
    print(f"  upstream_key_hash: \"{key_hash}\"")


if __name__ == "__main__":
    main()
