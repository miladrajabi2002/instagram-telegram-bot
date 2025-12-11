#!/usr/bin/env python3
"""Generate encryption key for the bot."""

from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = Fernet.generate_key()
    print("")
    print("Generated Encryption Key:")
    print("="*50)
    print(key.decode())
    print("="*50)
    print("")
    print("Add this to your .env file:")
    print(f"ENCRYPTION_KEY={key.decode()}")
    print("")
