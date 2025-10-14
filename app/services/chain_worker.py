# app/services/chain_worker.py
import os, json
from datetime import datetime
from decimal import Decimal
from app.db.session import SessionLocal
from app.db.models import Tender, Bid
from app.services.blockchain_service import record_award


def process_award(tender_id: str, winning_bid_id: str, award_amount: Decimal):
    """
    Worker entrypoint: receives tender award details and records on blockchain.
    
    Args:
        tender_id: UUID of the awarded tender
        winning_bid_id: UUID of the winning bid
        award_amount: Award amount
    """
    db = SessionLocal()
    try:
        # Fetch tender and winning bid
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        winning_bid = db.query(Bid).filter(Bid.id == winning_bid_id).first()
        
        if not tender or not winning_bid:
            print(f"❌ Tender or Bid not found: {tender_id}, {winning_bid_id}")
            return
        
        # Prepare award data for hashing
        award_data = {
            "tender_id": str(tender.id),
            "tender_title": tender.title,
            "winning_bid_id": str(winning_bid.id),
            "winning_company_id": str(winning_bid.company_id),
            "award_amount": str(award_amount),
            "awarded_at": tender.awarded_at.isoformat() if tender.awarded_at else datetime.utcnow().isoformat(),
            "posted_by": str(tender.posted_by_id)
        }
        
        # Convert amount to wei (or appropriate unit)
        # For simplicity, using amount as integer cents
        amount_wei = int(award_amount * 100)
        
        # Record award on blockchain
        data_hash, tx_hash = record_award(
            tender_id=str(tender.id),
            winning_bid_id=str(winning_bid.id),
            winning_company_id=str(winning_bid.company_id),
            award_amount=amount_wei,
            award_data=award_data
        )
        
        # Update tender with blockchain transaction details
        tender.award_hash_on_chain = data_hash
        tender.award_chain_tx = tx_hash
        
        # Update winning bid status
        winning_bid.status = "accepted"
        
        db.commit()
        print(f"✅ Award recorded on blockchain: tender={tender_id}, tx={tx_hash}")
        
    except Exception as e:
        print(f"❌ Blockchain award recording failed: {e}")
        db.rollback()
    finally:
        db.close()
