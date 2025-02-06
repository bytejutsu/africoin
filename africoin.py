import datetime
import hashlib
import json
from urllib.parse import urlparse

import requests

class Blockchain:

    def __init__(self, blockchain_file='blockchain.json'):
        self.blockchain_file = blockchain_file
        self.transactions = []
        self.load_chain()  # Load the blockchain from the file when the class is initialized
        self.nodes = set()

    def load_chain(self):
        """Loads the blockchain from the persistent file."""
        try:
            with open(self.blockchain_file, 'r') as file:
                data = json.load(file)
                self.chain = data
        except (FileNotFoundError, json.JSONDecodeError):
            self.chain = []  # If no file exists or there's an error, initialize an empty chain
            self.create_block(proof=1, previous_hash='0')  # Create the first block if the chain is empty

    def save_chain(self):
        """Saves the current blockchain to the persistent file."""
        with open(self.blockchain_file, 'w') as file:
            json.dump({'chain': self.chain}, file)

    def create_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': str(datetime.datetime.now()),
            'proof': proof,
            'previous_hash': previous_hash,
            'transactions': self.transactions  # Store only in-memory transactions
        }
        self.chain.append(block)
        self.transactions = []  # Reset transactions in memory
        self.save_chain()  # Save the updated chain to the file
        return block

    def get_chain(self):
        """Returns the persistent blockchain from the file."""
        return self.chain  # The chain is loaded from the file in self.load_chain()

    def get_previous_block(self):
        return self.chain[-1] if self.chain else None

    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while check_proof is False:
            hash_operation = hashlib.sha256(str(new_proof ** 2 - previous_proof ** 2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof ** 2 - previous_proof ** 2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
        return True

    def add_transaction(self, sender, receiver, amount, signature):
        self.transactions.append({
            'sender': sender,
            'receiver': receiver,
            'amount': amount,
            'signature': signature
        })

        previous_block = self.get_previous_block()
        return previous_block['index'] + 1 if previous_block else 1

    def add_reward_transaction(self, receiver, amount):
        """Adds a reward transaction without requiring a signature."""
        transaction = {
            'sender': 'BLOCK_REWARD',  # Special identifier for reward transactions
            'receiver': receiver,
            'amount': amount,
            'signature': None  # No signature needed for reward transactions
        }
        self.transactions.append(transaction)

        previous_block = self.get_previous_block()
        return previous_block['index'] + 1 if previous_block else 1

    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            self.save_chain()  # Save the new longest chain to the file
            return True
        return False
