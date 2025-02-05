import json
from cryptography.hazmat.primitives import serialization

with open("wallet.json", "r") as f:
    key_data = json.load(f)["private_key"]
    print(key_data)
    private_key = serialization.load_pem_private_key(key_data.encode(), password=None)