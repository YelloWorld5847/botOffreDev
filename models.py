from __future__ import annotations
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class Tag(BaseModel):
    id: Optional[str] = Field(None, alias='_id')
    name: str = ''
    image: Optional[str] = None
    isActive: Optional[bool] = None

class Pricing(BaseModel):
    value: float = 0
    volunteer: bool = False
    negotiable: bool = False

class Author(BaseModel):
    id: Optional[str] = Field(None, alias='_id')
    avatarUrl: Optional[str] = None
    name: Optional[str] = None

class Offer(BaseModel):
    id: str = Field(..., alias='_id')
    title: str = ''
    slug: str = ''
    content: Optional[str] = ''
    kind: Optional[str] = 'DEVELOPER'
    status: Optional[str] = 'ACTIVE'
    pricing: Optional[Pricing] = None
    tags: List[Tag] = Field(default_factory=list, alias='_tags')
    author: Optional[Author] = None
    total_applies: Optional[int] = 0
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    class Config:
        populate_by_name = True

class EvaluationResult(BaseModel):
    should_apply: bool
    reason: str
    confidence: float = 1.0
    matched_keywords: List[str] = Field(default_factory=list)
    rejected_keywords: List[str] = Field(default_factory=list)
