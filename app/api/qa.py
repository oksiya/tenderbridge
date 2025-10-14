"""
Q&A API Endpoints (Phase 3 - Task 3)

Endpoints for asking and answering questions on tenders.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.deps import get_current_user, get_db
from app.db.models import Question, Answer, Tender, User, Company
from app.schemas.qa import (
    QuestionCreate,
    QuestionUpdate,
    QuestionOut,
    AnswerCreate,
    AnswerUpdate,
    AnswerOut
)
from app.services.notification_service import create_notification, NotificationType

router = APIRouter(prefix="/api/tenders", tags=["questions"])


@router.post("/{tender_id}/questions", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
def ask_question(
    tender_id: UUID,
    question_data: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ask a question on a tender.
    Anyone can ask questions on open/published tenders.
    """
    # Check if tender exists
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Only allow questions on open/published tenders
    if tender.status not in ["open", "published"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot ask questions on {tender.status} tenders. Tender must be open or published."
        )
    
    # Create question
    question = Question(
        tender_id=tender_id,
        asked_by_id=current_user.id,
        question_text=question_data.question_text
    )
    
    db.add(question)
    db.commit()
    db.refresh(question)
    
    # Notify tender owner's company users
    tender_company_users = db.query(User).filter(
        User.company_id == tender.posted_by_id
    ).all()
    
    for user in tender_company_users:
        create_notification(
            db=db,
            user_id=user.id,
            notification_type="question_asked",
            title=f"New Question on Tender",
            message=f"A new question has been asked on tender '{tender.title}'.",
            related_tender_id=tender_id,
            email_context={
                "tender": {
                    "id": str(tender.id),
                    "title": tender.title
                },
                "question": {
                    "text": question.question_text,
                    "asked_by": current_user.email
                }
            }
        )
    
    # Add user info to response
    question_out = QuestionOut.from_orm(question)
    question_out.asked_by_name = current_user.email
    
    if current_user.company:
        question_out.asked_by_company = db.query(Company).filter(
            Company.id == current_user.company_id
        ).first().name
    
    return question_out


@router.get("/{tender_id}/questions", response_model=List[QuestionOut])
def list_questions(
    tender_id: UUID,
    include_answers: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all questions on a tender.
    Includes answers if include_answers=true.
    """
    # Check if tender exists
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Get questions
    questions = db.query(Question).filter(
        Question.tender_id == tender_id
    ).order_by(Question.created_at.desc()).all()
    
    # Build response with user info and answers
    questions_out = []
    for question in questions:
        question_out = QuestionOut.from_orm(question)
        
        # Add asker info
        asker = db.query(User).filter(User.id == question.asked_by_id).first()
        if asker:
            question_out.asked_by_name = asker.email
            if asker.company_id:
                company = db.query(Company).filter(Company.id == asker.company_id).first()
                if company:
                    question_out.asked_by_company = company.name
        
        # Add answers if requested
        if include_answers:
            answers = db.query(Answer).filter(
                Answer.question_id == question.id
            ).order_by(Answer.created_at.asc()).all()
            
            answers_out = []
            for answer in answers:
                answer_out = AnswerOut.from_orm(answer)
                
                # Add answerer info
                answerer = db.query(User).filter(User.id == answer.answered_by_id).first()
                if answerer:
                    answer_out.answered_by_name = answerer.email
                    if answerer.company_id:
                        company = db.query(Company).filter(Company.id == answerer.company_id).first()
                        if company:
                            answer_out.answered_by_company = company.name
                
                answers_out.append(answer_out)
            
            question_out.answers = answers_out
        
        questions_out.append(question_out)
    
    return questions_out


@router.get("/questions/{question_id}", response_model=QuestionOut)
def get_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific question with its answers."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Build response
    question_out = QuestionOut.from_orm(question)
    
    # Add asker info
    asker = db.query(User).filter(User.id == question.asked_by_id).first()
    if asker:
        question_out.asked_by_name = asker.email
        if asker.company_id:
            company = db.query(Company).filter(Company.id == asker.company_id).first()
            if company:
                question_out.asked_by_company = company.name
    
    # Add answers
    answers = db.query(Answer).filter(
        Answer.question_id == question.id
    ).order_by(Answer.created_at.asc()).all()
    
    answers_out = []
    for answer in answers:
        answer_out = AnswerOut.from_orm(answer)
        
        # Add answerer info
        answerer = db.query(User).filter(User.id == answer.answered_by_id).first()
        if answerer:
            answer_out.answered_by_name = answerer.email
            if answerer.company_id:
                company = db.query(Company).filter(Company.id == answerer.company_id).first()
                if company:
                    answer_out.answered_by_company = company.name
        
        answers_out.append(answer_out)
    
    question_out.answers = answers_out
    
    return question_out


@router.post("/questions/{question_id}/answer", response_model=AnswerOut, status_code=status.HTTP_201_CREATED)
def answer_question(
    question_id: UUID,
    answer_data: AnswerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Answer a question.
    Only users from the tender owner's company can answer.
    """
    # Get question
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Get tender
    tender = db.query(Tender).filter(Tender.id == question.tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Check if user is from tender owner's company
    if current_user.company_id != tender.posted_by_id:
        raise HTTPException(
            status_code=403,
            detail="Only users from the tender owner's company can answer questions"
        )
    
    # Check if question is already answered
    existing_answer = db.query(Answer).filter(Answer.question_id == question_id).first()
    if existing_answer:
        raise HTTPException(
            status_code=400,
            detail="Question has already been answered. Use PUT to update the answer."
        )
    
    # Create answer
    answer = Answer(
        question_id=question_id,
        answered_by_id=current_user.id,
        answer_text=answer_data.answer_text
    )
    
    db.add(answer)
    
    # Update question status
    question.is_answered = "true"
    question.updated_at = answer.created_at
    
    db.commit()
    db.refresh(answer)
    
    # Notify question asker
    asker = db.query(User).filter(User.id == question.asked_by_id).first()
    if asker:
        create_notification(
            db=db,
            user_id=asker.id,
            notification_type="question_answered",
            title=f"Your Question Was Answered",
            message=f"Your question on tender '{tender.title}' has been answered.",
            related_tender_id=tender.id,
            email_context={
                "tender": {
                    "id": str(tender.id),
                    "title": tender.title
                },
                "question": {
                    "text": question.question_text
                },
                "answer": {
                    "text": answer.answer_text,
                    "answered_by": current_user.email
                }
            }
        )
    
    # Build response
    answer_out = AnswerOut.from_orm(answer)
    answer_out.answered_by_name = current_user.email
    
    if current_user.company_id:
        company = db.query(Company).filter(Company.id == current_user.company_id).first()
        if company:
            answer_out.answered_by_company = company.name
    
    return answer_out


@router.put("/questions/{question_id}/answer/{answer_id}", response_model=AnswerOut)
def update_answer(
    question_id: UUID,
    answer_id: UUID,
    answer_data: AnswerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an answer.
    Only the user who created the answer can update it.
    """
    # Get answer
    answer = db.query(Answer).filter(
        Answer.id == answer_id,
        Answer.question_id == question_id
    ).first()
    
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    # Check if user is the one who answered
    if answer.answered_by_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own answers"
        )
    
    # Update answer
    answer.answer_text = answer_data.answer_text
    answer.updated_at = db.query(Question).filter(Question.id == question_id).first().updated_at
    
    db.commit()
    db.refresh(answer)
    
    # Build response
    answer_out = AnswerOut.from_orm(answer)
    answer_out.answered_by_name = current_user.email
    
    if current_user.company_id:
        company = db.query(Company).filter(Company.id == current_user.company_id).first()
        if company:
            answer_out.answered_by_company = company.name
    
    return answer_out


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a question.
    Only the user who asked the question can delete it (if not yet answered).
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Check if user is the one who asked
    if question.asked_by_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own questions"
        )
    
    # Check if question is answered
    if question.is_answered == "true":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete answered questions"
        )
    
    db.delete(question)
    db.commit()
    
    return None
