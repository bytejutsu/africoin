from africoin import Blockchain
from flask import Flask, render_template, request, redirect, jsonify, session
import requests
from uuid import uuid4
import json
import os


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


    @app.route('/nodes_page', methods=['GET'])
    def nodes_page():
        return render_template('nodes_page.html')


    @app.route('/wallet_page', methods=['GET'])
    def wallet_page():
        return render_template('wallet_page.html')


    # Path to the wallet.json file
    WALLET_FILE = 'wallet.json'


    def load_wallet():
        """Load the wallet data from wallet.json."""
        if os.path.exists(WALLET_FILE):
            with open(WALLET_FILE, 'r') as file:
                return json.load(file)
        return {}


    def save_wallet(public_key, private_key):
        """Save the wallet data to wallet.json."""
        wallet_data = {
            'public_key': public_key,
            'private_key': private_key
        }
        with open(WALLET_FILE, 'w') as file:
            json.dump(wallet_data, file)

    @app.route('/get_wallet', methods=['GET'])
    def get_wallet():
        """Endpoint to retrieve the wallet keys."""
        try:
            # Load wallet data
            wallet_data = load_wallet()

            # Check if wallet.json exists and is not empty
            if not wallet_data:
                # If wallet.json doesn't exist or is empty, initialize it with empty keys
                wallet_data = {'public_key': '', 'private_key': ''}
                save_wallet(wallet_data['public_key'], wallet_data['private_key'])

            # Validate that both keys exist in the wallet data
            if 'public_key' not in wallet_data or 'private_key' not in wallet_data:
                # If keys are missing, indicate that no keys are generated
                wallet_data = {'public_key': 'No public key generated', 'private_key': 'No private key generated'}
                save_wallet(wallet_data['public_key'], wallet_data['private_key'])

            return jsonify(wallet_data)

        except Exception as e:
            # Handle any unexpected errors (e.g., file corruption)
            print(f"Error loading wallet: {e}")
            return jsonify({
                'error': 'Unable to load wallet data',
                'public_key': 'No public key generated',
                'private_key': 'No private key generated'
            }), 500

    @app.route('/generate_wallet', methods=['POST'])
    def generate_wallet():
        """Endpoint to generate and save a new key pair."""
        # Example key generation (replace with actual cryptographic logic)
        public_key = str(uuid4()).replace('-', '')
        private_key = str(uuid4()).replace('-', '')

        # Save the new keys to wallet.json
        save_wallet(public_key, private_key)

        return jsonify({
            'public_key': public_key,
            'private_key': private_key
        })


    @app.route('/')
    def index():
        return render_template('dashboard.html')

    # Mining a new block
    @app.route('/mine_block', methods=['GET'])
    def mine_block():
        previous_block = blockchain.get_previous_block()
        previous_proof = previous_block['proof']
        proof = blockchain.proof_of_work(previous_proof)
        previous_hash = blockchain.hash(previous_block)
        blockchain.add_transaction(sender=node_address, receiver='Dhia', amount=1)
        block = blockchain.create_block(proof, previous_hash)
        response = {'message': 'Congratulations! you just mined a block',
                    'index': block['index'],
                    'timestamp': block['timestamp'],
                    'proof': block['proof'],
                    'previous_hash': block['previous_hash'],
                    'transactions': block['transactions']
                    }
        return jsonify(response), 200


    @app.route('/get_chain', methods=['GET'])
    def get_chain():
        response = {
            'chain': blockchain.chain,
            'length': len(blockchain.chain)
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


    @app.route('/add_transaction', methods=['POST'])
    def add_transaction():
        json = request.get_json()
        transaction_keys = ['sender', 'receiver', 'amount']
        if not all (key in json for key in transaction_keys):
            return 'Some elements of the transaction are missing', 400
        index = blockchain.add_transaction(json['sender'], json['receiver'], json['amount'])
        response = {'message': f'This transaction will be added to block {index}'}
        return jsonify(response), 201


    @app.route('/get_transactions', methods=['GET'])
    def get_transactions():
        return jsonify({'transactions': blockchain.transactions}), 200

    # Part 3 - Decentralizing our Blockchain

    # Connecting new nodes
    # @app.route('/connect_node', methods=['POST'])
    # def connect_node():
    #     json = request.get_json()
    #     nodes = json.get('nodes')
    #     if nodes is None:
    #         return 'No node', 400
    #     for node in nodes:
    #         blockchain.add_node(node)
    #     response = {
    #         'message': 'All the nodes are now connected. The Africoin Blockchain now contains the following nodes' ,
    #         'total_nodes': list(blockchain.nodes)
    #     }
    #     return jsonify(response), 201


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
