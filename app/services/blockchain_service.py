from web3 import Web3
import os
import json
import hashlib

# Load blockchain configuration
WEB3_RPC = os.getenv("WEB3_RPC", "http://ganache:8545")
PRIVATE_KEY = os.getenv("BLOCKCHAIN_PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("STAMP_CONTRACT_ADDRESS")
ABI_PATH = os.getenv("STAMP_ABI_PATH", "/code/app/blockchain/contracts/TenderAwardRegistryABI.json")

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(WEB3_RPC))

# Load contract ABI
with open(ABI_PATH, "r") as f:
    contract_abi = json.load(f)

# Initialize contract
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

# Get account from private key
if PRIVATE_KEY:
    account = w3.eth.account.from_key(PRIVATE_KEY)
else:
    account = None


def record_award(
    tender_id: str,
    winning_bid_id: str,
    winning_company_id: str,
    award_amount: int,
    award_data: dict
) -> tuple:
    """
    Record a tender award on the blockchain.
    
    Args:
        tender_id: UUID of the tender
        winning_bid_id: UUID of the winning bid
        winning_company_id: UUID of the winning company
        award_amount: Award amount in wei (or smallest unit)
        award_data: Dict containing all award details for hashing
    
    Returns:
        (data_hash_hex, transaction_hash)
    """
    if not account:
        raise Exception("No blockchain private key configured")
    
    # Calculate hash of award data for verification
    award_json = json.dumps(award_data, sort_keys=True)
    data_hash = hashlib.sha256(award_json.encode()).digest()
    data_hash_hex = "0x" + data_hash.hex()
    
    # Prepare transaction
    nonce = w3.eth.get_transaction_count(account.address)
    
    # Build transaction to call recordAward function
    tx = contract.functions.recordAward(
        tender_id,
        winning_bid_id,
        winning_company_id,
        award_amount,
        data_hash_hex
    ).build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 1000000,  # Higher gas for string parameters
        'gasPrice': w3.eth.gas_price
    })
    
    # Sign and send transaction
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    # Wait for transaction receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    print(f"✅ Award recorded on blockchain: {tx_hash.hex()}")
    
    return data_hash_hex, tx_hash.hex()


def verify_award_by_tender_id(tender_id: str) -> dict:
    """
    Verifies an award by querying the contract storage directly.
    
    Returns:
        dict with verification status and award details
    """
    try:
        result = contract.functions.getAward(tender_id).call()
        (
            tender_id_returned,
            winning_bid_id,
            winning_company_id,
            award_amount,
            award_date,
            awarded_by,
            data_hash
        ) = result
        
        if not data_hash or data_hash == "":
            return {"verified": False, "error": "Award not found on chain"}
        
        return {
            "verified": True,
            "tender_id": tender_id_returned,
            "winning_bid_id": winning_bid_id,
            "winning_company_id": winning_company_id,
            "award_amount": award_amount,
            "award_date": award_date,
            "awarded_by": awarded_by,
            "hash_on_chain": data_hash,
            "method": "contract_storage"
        }
    except Exception as e:
        return {"verified": False, "error": f"Could not query contract: {str(e)}"}


def verify_award_by_tx(tx_hash: str) -> dict:
    """
    Verifies an award by checking the TenderAwarded event in the transaction.
    
    Returns:
        dict with verification status and award details
    """
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
    except Exception as e:
        return {"verified": False, "error": f"Could not fetch transaction: {str(e)}"}

    try:
        events = contract.events.TenderAwarded().process_receipt(receipt)
    except Exception as e:
        return {"verified": False, "error": f"Could not parse logs: {str(e)}"}

    for ev in events:
        return {
            "verified": True,
            "tender_id": ev["args"]["tenderId"],
            "winning_bid_id": ev["args"]["winningBidId"],
            "winning_company_id": ev["args"]["winningCompanyId"],
            "award_amount": ev["args"]["awardAmount"],
            "award_date": ev["args"]["awardDate"],
            "awarded_by": ev["args"]["awardedBy"],
            "hash_on_chain": ev["args"]["dataHash"],
            "method": "transaction_logs",
            "block_number": receipt.blockNumber,
            "tx_hash": tx_hash
        }
    
    return {"verified": False, "error": "No TenderAwarded event found in transaction"}


def get_award_count() -> int:
    """Get the total number of awards recorded on-chain"""
    try:
        return contract.functions.getAwardCount().call()
    except Exception as e:
        print(f"Error getting award count: {str(e)}")
        return 0
