from cryptography.hazmat.backends import default_backend

from africoin import Blockchain
from flask import Flask, render_template, request, redirect, jsonify, session
import requests
from uuid import uuid4
import json
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends import default_backend
import base64
import re
from flask import send_from_directory


if __name__ == '__main__':
    # Creating a Web App
    app = Flask(__name__)
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

    # Creating an address for the node on Port 5000
    node_address = str(uuid4()).replace('-','')


    # Creating a Blockchain
    blockchain = Blockchain()

    NODES_FILE = 'nodes.json'

    def load_nodes():
        try:
            with open(NODES_FILE, 'r') as file:
                data = json.load(file)
                return data if isinstance(data, list) else []  # Ensure it's a list
        except FileNotFoundError:
            return []  # Return an empty list if the file doesn't exist

    def save_nodes(nodes):
        with open(NODES_FILE, 'w') as file:
            json.dump(nodes, file)


    @app.route('/connect_node', methods=['POST'])
    def connect_node():
        json_data = request.get_json()
        nodes = json_data.get('nodes')

        if not nodes:
            return jsonify({'error': 'No nodes provided'}), 400

        # Load existing nodes from the file
        current_nodes = load_nodes()

        for node in nodes:
            if node not in current_nodes:
                current_nodes.append(node)

        # Save the updated list of nodes back to the file
        save_nodes(current_nodes)

        response = {
            'message': 'All nodes are now connected. The Africoin Blockchain now contains the following nodes:',
            'total_nodes': current_nodes
        }
        return jsonify(response), 201


    @app.route('/nodes', methods=['GET'])
    def get_nodes():
        # Load nodes from the file and return them
        nodes = load_nodes()
        return jsonify({'nodes': nodes})


    @app.route('/')
    def index():
        return render_template('dashboard.html')


    @app.route('/blockchain_page')
    def blockchain_page():
        # Read the blockchain data from the JSON file
        try:
            with open('blockchain.json', 'r') as f:
                blockchain_data = json.load(f)
        except FileNotFoundError:
            blockchain_data = {"chain": []}  # Handle the case where the file does not exist
        return render_template('blockchain_page.html', blockchain_data=blockchain_data)


    @app.route('/download_blockchain')
    def download_blockchain():
        return send_from_directory(os.getcwd(), 'blockchain.json', as_attachment=True)

    @app.route('/nodes_page', methods=['GET'])
    def nodes_page():
        return render_template('nodes_page.html')


    @app.route('/wallet_page', methods=['GET'])
    def wallet_page():
        return render_template('wallet_page.html')


    WALLET_FILE = 'wallet.json'

    def save_wallet(public_key, private_key):
        """Save the wallet data to wallet.json."""
        wallet_data = {
            'public_key': public_key,
            'private_key': private_key
        }
        with open(WALLET_FILE, 'w') as file:
            json.dump(wallet_data, file)


    def load_wallet():
        """Load the wallet data from wallet.json."""
        if os.path.exists(WALLET_FILE):
            try:
                with open(WALLET_FILE, 'r') as file:
                    data = json.load(file)
                    return data
            except json.JSONDecodeError:
                print("Error: Corrupt wallet.json file")
                return None  # Handle corruption gracefully
        return None  # If file doesn't exist


    @app.route('/get_wallet', methods=['GET'])
    def get_wallet():
        """Endpoint to retrieve the wallet keys."""
        wallet_data = load_wallet()

        if not wallet_data or 'public_key' not in wallet_data or 'private_key' not in wallet_data:
            return jsonify({
                'public_key': 'No public key generated',
                'private_key': 'No private key generated'
            }), 404

        return jsonify(wallet_data)


    @app.route('/generate_wallet', methods=['POST'])
    def generate_wallet():
        """Generates a new ECDSA key pair and saves it to wallet.json."""
        if load_wallet():  # Prevent overwriting an existing wallet
            return jsonify({'error': 'Wallet already exists. Use GET /get_wallet'}), 400

        private_key = ec.generate_private_key(ec.SECP256K1())
        public_key = private_key.public_key()

        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

        # Save to wallet.json
        save_wallet(public_pem, private_pem)

        return jsonify({
            'public_key': public_pem,
            'private_key': private_pem
        })


    # Mine a block
    @app.route('/mine_block', methods=['POST'])
    def mine_block():
        try:
            data = request.json
            miner_address = data.get('miner_address')  # Get miner's address from request

            if not miner_address:
                return jsonify({'error': 'Miner address is required'}), 400

            previous_block = blockchain.get_previous_block()
            previous_proof = previous_block['proof']
            proof = blockchain.proof_of_work(previous_proof)
            previous_hash = blockchain.hash(previous_block)

            # Add a reward transaction using the new method
            blockchain.add_reward_transaction(receiver=miner_address, amount=1)

            # Create the new block
            block = blockchain.create_block(proof, previous_hash)

            # Persist the blockchain to blockchain.json
            with open('blockchain.json', 'w') as f:
                json.dump(blockchain.chain, f, indent=4)

            response = {
                'message': 'Congratulations! You just mined a block',
                'index': block['index'],
                'timestamp': block['timestamp'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
                'transactions': block['transactions']
            }

            return jsonify(response), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500


    @app.route('/get_chain', methods=['GET'])
    def get_chain():
        response = {
            'chain': blockchain.get_chain(),
            'length': len(blockchain.get_chain())
        }
        return jsonify(response), 200


    @app.route('/is_valid', methods=['GET'])
    def is_valid():
        is_valid = blockchain.is_chain_valid(blockchain.chain)
        if is_valid:
            response = {'message': 'All good, the blockchain is valid.'}
        else:
            response = {'message': 'Joe we have a problem, the blockchain is not valid.'}
        return jsonify(response), 200


    def get_private_key():
        """Retrieve the private key from the wallet.json file."""
        try:
            with open(WALLET_FILE, "r") as f:
                key_data = json.load(f)["private_key"]
            return key_data
        except Exception as e:
            print(f"Error retrieving private key: {e}")
            return None


    def sign_transaction(transaction):
        """Signs the transaction using the sender's private key."""
        private_key_pem = get_private_key()
        if not private_key_pem:
            return None

        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(), password=None
            )
        except ValueError as e:
            print("Private key decoding failed:", str(e))
            return None
        except UnsupportedAlgorithm as e:
            print("Unsupported algorithm:", str(e))
            return None

        transaction_str = json.dumps(transaction, sort_keys=True).encode()
        try:
            signature = private_key.sign(transaction_str, ec.ECDSA(hashes.SHA256()))
            return signature
        except Exception as e:
            print("Signing failed:", str(e))
            return None


    @app.route('/sign_transaction', methods=['POST'])
    def sign_transaction_route():
        try:
            data = request.json
            sender = data['sender']
            receiver = data['receiver']
            amount = data['amount']

            transaction = {"sender": sender, "receiver": receiver, "amount": amount}

            # Sign the transaction
            signature = sign_transaction(transaction)
            if signature:
                signature_b64 = base64.b64encode(signature).decode('utf-8')
                return jsonify({'signature': signature_b64})
            else:
                return jsonify({'error': 'Failed to sign transaction'}), 400
        except Exception as e:
            print("Unexpected error:", str(e))
            return jsonify({'error': str(e)}), 400


    def verify_signature(sender, transaction_data, signature_b64):
        """Verify the signature of the transaction using the sender's public key."""

        # Load the sender's public key from the wallet.json file
        with open("wallet.json", "r") as f:
            wallet_data = json.load(f)
            public_key_pem = wallet_data["public_key"]

        try:
            # Load the public key from the PEM format
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(), backend=default_backend()
            )

            # Prepare the transaction data for verification
            transaction_str = json.dumps(transaction_data, sort_keys=True).encode()

            # Decode the base64 signature
            signature = base64.b64decode(signature_b64)

            # Verify the signature using the public key
            public_key.verify(
                signature,
                transaction_str,
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False


    @app.route('/verify_transaction', methods=['POST'])
    def verify_transaction():
        json_data = request.get_json()
        required_keys = ['sender', 'receiver', 'amount', 'signature']

        if not all(key in json_data for key in required_keys):
            return jsonify({'error': 'Missing transaction fields'}), 400

        sender = json_data['sender']
        receiver = json_data['receiver']
        amount = json_data['amount']
        signature = json_data['signature']

        # Here you will verify the signature using the sender's public key
        # You can use your existing signature verification logic
        transaction_data = {'sender': sender, 'receiver': receiver, 'amount': amount}

        is_valid = verify_signature(sender, transaction_data, signature)

        return jsonify({'isValid': is_valid})


    @app.route('/add_transaction', methods=['POST'])
    def add_transaction():
        json_data = request.get_json()
        required_keys = ['sender', 'receiver', 'amount', 'signature']

        if not all(key in json_data for key in required_keys):
            return jsonify({'error': 'Missing transaction fields'}), 400

        sender = json_data['sender']
        receiver = json_data['receiver']
        amount = json_data['amount']
        signature = json_data['signature']

        # Verify the signature
        transaction_data = {'sender': sender, 'receiver': receiver, 'amount': amount}

        if not verify_signature(sender, transaction_data, signature):
            return jsonify({'error': 'Invalid signature!'}), 400

        # If valid, add to blockchain
        index = blockchain.add_transaction(sender, receiver, amount, signature)
        return jsonify({'message': f'This transaction will be added to block {index}'}), 201


    @app.route('/get_transactions', methods=['GET'])
    def get_transactions():
        return jsonify({'transactions': blockchain.transactions}), 200

    # Part 3 - Decentralizing our Blockchain

    @app.route('/replace_chain', methods=['GET'])
    def replace_chain():
        is_chain_replaced = blockchain.replace_chain()
        if is_chain_replaced:
            response = {
                'message': 'The nodes had different chains so the chain was replaced by the longest.',
                'new_chain': blockchain.chain
            }
        else:
            response = {
                'message': 'All good. The chain is the longest one.',
                'actual_chain': blockchain.chain
            }
        return jsonify(response), 200


    app.run(host='0.0.0.0', port=5000, debug=True)
