from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class DocumentBlock(BaseModel):
    id: str
    number: Optional[str] = None
    heading: Optional[str] = None
    raw_text: str
    clean_text: str
    lemma_text: Optional[str] = None
    position: int
    path: Optional[str] = None
    hierarchy_level: int = 10  # По умолчанию 10 (локальный акт)
    metadata: Optional[Dict[str, Any]] = None

class ComparisonResult(BaseModel):
    old_block: Optional[DocumentBlock] = None
    new_block: Optional[DocumentBlock] = None
    risk_level: str  # "green", "yellow", "red"
    risk_explanation: Optional[str] = None
    diff_type: str  # "equal", "changed", "added", "deleted"
    score: float
    # Новое поле: ссылки на законы, которые могут противоречить
    legal_context: Optional[List[Dict[str, Any]]] = None
