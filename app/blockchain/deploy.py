import json
import os
from solcx import compile_standard, install_solc
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = os.path.dirname(__file__)
CONTRACT_PATH = os.path.join(BASE_DIR, "contracts", "TenderAwardRegistry.sol")
ABI_PATH = os.path.join(BASE_DIR, "contracts", "TenderAwardRegistryABI.json")
ADDRESS_PATH = os.path.join(BASE_DIR, "contracts", "StampAddress.txt")

# Read the Solidity contract
with open(CONTRACT_PATH, "r") as f:
    source_code = f.read()

# Install specific Solidity compiler
install_solc("0.8.0")

# Compile the contract
compiled_sol = compile_standard(
    {
        "language": "Solidity",
        "sources": {"TenderAwardRegistry.sol": {"content": source_code}},
        "settings": {
            "outputSelection": {
                "*": {
                    "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                }
            }
        },
    },
    solc_version="0.8.0",
)

# Extract ABI and bytecode
contract_interface = compiled_sol["contracts"]["TenderAwardRegistry.sol"]["TenderAwardRegistry"]
abi = contract_interface["abi"]
bytecode = contract_interface["evm"]["bytecode"]["object"]

# Connect to Ganache
ganache_url = os.getenv("WEB3_RPC", "http://ganache:8545")
w3 = Web3(Web3.HTTPProvider(ganache_url))
assert w3.is_connected(), "❌ Could not connect to Ganache"

private_key = os.getenv("BLOCKCHAIN_PRIVATE_KEY")
account = w3.eth.account.from_key(private_key)

# Deploy contract
TenderAwardRegistry = w3.eth.contract(abi=abi, bytecode=bytecode)
nonce = w3.eth.get_transaction_count(account.address)

transaction = TenderAwardRegistry.constructor().build_transaction({
    "from": account.address,
    "nonce": nonce,
    "gas": 3000000,
    "gasPrice": w3.to_wei("20", "gwei")
})

signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

contract_address = tx_receipt.contractAddress
print(f"✅ Deployed TenderAwardRegistry.sol at: {contract_address}")

# Save ABI and address
with open(ABI_PATH, "w") as abi_file:
    json.dump(abi, abi_file)

with open(ADDRESS_PATH, "w") as addr_file:
    addr_file.write(contract_address)

print(f"📄 ABI saved to: {ABI_PATH}")
print(f"🏷️ Address saved to: {ADDRESS_PATH}")
