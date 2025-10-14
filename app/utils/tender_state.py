"""
Tender State Machine - Manages tender lifecycle and status transitions
"""
from typing import Optional, List
from datetime import datetime


class TenderStatus:
    """Valid tender status values"""
    DRAFT = "draft"
    PUBLISHED = "published"
    OPEN = "open"
    EVALUATION = "evaluation"
    AWARDED = "awarded"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class TenderStateMachine:
    """
    State machine for tender lifecycle.
    
    State Flow:
    draft → published → open → evaluation → awarded
                                         ↘ cancelled
    
    Status can also go to 'cancelled' from most states.
    """
    
    # Valid state transitions
    TRANSITIONS = {
        TenderStatus.DRAFT: [TenderStatus.PUBLISHED, TenderStatus.CANCELLED],
        TenderStatus.PUBLISHED: [TenderStatus.OPEN, TenderStatus.CANCELLED],
        TenderStatus.OPEN: [TenderStatus.EVALUATION, TenderStatus.CLOSED, TenderStatus.CANCELLED],
        TenderStatus.EVALUATION: [TenderStatus.AWARDED, TenderStatus.OPEN, TenderStatus.CANCELLED],
        TenderStatus.CLOSED: [TenderStatus.EVALUATION, TenderStatus.CANCELLED],
        TenderStatus.AWARDED: [],  # Terminal state
        TenderStatus.CANCELLED: []  # Terminal state
    }
    
    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if transition from one status to another is valid"""
        if from_status not in cls.TRANSITIONS:
            return False
        return to_status in cls.TRANSITIONS[from_status]
    
    @classmethod
    def get_allowed_transitions(cls, current_status: str) -> List[str]:
        """Get list of allowed status transitions from current status"""
        return cls.TRANSITIONS.get(current_status, [])
    
    @classmethod
    def validate_transition(cls, from_status: str, to_status: str, reason: Optional[str] = None) -> tuple[bool, str]:
        """
        Validate a status transition.
        
        Returns:
            (is_valid, error_message)
        """
        if from_status == to_status:
            return True, "Status unchanged"
        
        if not cls.can_transition(from_status, to_status):
            allowed = cls.get_allowed_transitions(from_status)
            return False, f"Cannot transition from '{from_status}' to '{to_status}'. Allowed: {allowed}"
        
        # Cancellation requires a reason
        if to_status == TenderStatus.CANCELLED and not reason:
            return False, "Cancellation requires a reason"
        
        return True, "Valid transition"
    
    @classmethod
    def is_terminal_status(cls, status: str) -> bool:
        """Check if status is terminal (no further transitions allowed)"""
        return status in [TenderStatus.AWARDED, TenderStatus.CANCELLED]
    
    @classmethod
    def can_receive_bids(cls, status: str) -> bool:
        """Check if tender can receive bids in current status"""
        return status == TenderStatus.OPEN
    
    @classmethod
    def can_edit_tender(cls, status: str) -> bool:
        """Check if tender details can be edited"""
        return status in [TenderStatus.DRAFT, TenderStatus.PUBLISHED]
    
    @classmethod
    def can_evaluate_bids(cls, status: str) -> bool:
        """Check if bids can be evaluated"""
        return status in [TenderStatus.EVALUATION, TenderStatus.CLOSED]
    
    @classmethod
    def can_award(cls, status: str) -> bool:
        """Check if tender can be awarded"""
        return status == TenderStatus.EVALUATION
    
    @classmethod
    def should_auto_close(cls, status: str, closing_date: datetime) -> bool:
        """Check if tender should automatically close based on closing date"""
        if status != TenderStatus.OPEN:
            return False
        return datetime.utcnow() >= closing_date
