"""
Pagination utilities for list endpoints
"""
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field
from fastapi import Query

T = TypeVar('T')


class PaginationParams:
    """
    Reusable pagination parameters for FastAPI endpoints
    
    Usage:
        @router.get("/items")
        def list_items(pagination: PaginationParams = Depends()):
            skip = pagination.skip
            limit = pagination.limit
    """
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(50, ge=1, le=200, description="Number of items to return (max 200)")
    ):
        self.skip = skip
        self.limit = limit


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper
    
    Returns:
        {
            "items": [...],
            "total": 100,
            "skip": 0,
            "limit": 50,
            "has_more": true
        }
    """
    items: list[T]
    total: int = Field(description="Total number of items")
    skip: int = Field(description="Number of items skipped")
    limit: int = Field(description="Number of items returned")
    has_more: bool = Field(description="Whether more items are available")
    
    class Config:
        from_attributes = True


def paginate_query(query, skip: int = 0, limit: int = 50):
    """
    Apply pagination to SQLAlchemy query
    
    Args:
        query: SQLAlchemy query object
        skip: Number of items to skip
        limit: Number of items to return
        
    Returns:
        tuple: (items, total_count)
    """
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return items, total


def create_paginated_response(items: list[T], total: int, skip: int, limit: int) -> dict:
    """
    Create paginated response dictionary
    
    Args:
        items: List of items for current page
        total: Total number of items
        skip: Number of items skipped
        limit: Number of items per page
        
    Returns:
        dict with pagination metadata
    """
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(items) < total
    }
