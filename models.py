from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, validator

class SurveySubmission(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(..., ge=13, le=120)
    consent: bool 
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = Field(None, max_length=1000)
    user_agent: Optional[str] = None
    submission_id: Optional[str] = None


    @validator("comments")
    def _strip_comments(cls, v):
        return v.strip() if isinstance(v, str) else v

    @validator("consent")
    def _must_consent(cls, v):
        if v is not True:
            raise ValueError("consent must be true")
        return v
        
#Good example of inheritance
class StoredSurveyRecord(SurveySubmission):
    name: str 
    email: str
    age: str
    consent: bool
    rating: int 
    comments: Optional[str] 
    user_agent: Optional[str]
    submission_id: Optional[str]
    received_at: datetime
    ip: str
