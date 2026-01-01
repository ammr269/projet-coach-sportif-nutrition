from pydantic import BaseModel, Field
from typing import List, Optional


class UserProfile(BaseModel):
    age: Optional[int] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    sex: Optional[str] = None
    goal: Optional[str] = Field(
        None,
        description='ex: perte_de_poids, maintien, prise_de_masse'
    )
    allergies: List[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    question: str
    profile: Optional[UserProfile] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
