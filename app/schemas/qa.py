"""
Q&A Schemas (Phase 3 - Task 3)

Pydantic schemas for questions and answers on tenders.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List


# Question Schemas
class QuestionCreate(BaseModel):
    """Schema for creating a question."""
    question_text: str = Field(..., min_length=10, max_length=2000, description="Question text (10-2000 characters)")


class QuestionUpdate(BaseModel):
    """Schema for updating a question."""
    question_text: str = Field(..., min_length=10, max_length=2000)


class QuestionOut(BaseModel):
    """Schema for question response."""
    id: UUID
    tender_id: UUID
    asked_by_id: UUID
    question_text: str
    is_answered: str
    created_at: datetime
    updated_at: datetime
    
    # Nested user info (optional, loaded separately)
    asked_by_name: Optional[str] = None
    asked_by_company: Optional[str] = None
    
    # Answers (optional, loaded separately)
    answers: Optional[List["AnswerOut"]] = []
    
    class Config:
        orm_mode = True


# Answer Schemas
class AnswerCreate(BaseModel):
    """Schema for creating an answer."""
    answer_text: str = Field(..., min_length=10, max_length=5000, description="Answer text (10-5000 characters)")


class AnswerUpdate(BaseModel):
    """Schema for updating an answer."""
    answer_text: str = Field(..., min_length=10, max_length=5000)


class AnswerOut(BaseModel):
    """Schema for answer response."""
    id: UUID
    question_id: UUID
    answered_by_id: UUID
    answer_text: str
    created_at: datetime
    updated_at: datetime
    
    # Nested user info (optional, loaded separately)
    answered_by_name: Optional[str] = None
    answered_by_company: Optional[str] = None
    
    class Config:
        orm_mode = True


# Update forward references for Pydantic v1
QuestionOut.update_forward_refs()
