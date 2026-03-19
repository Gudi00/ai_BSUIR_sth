from pydantic import BaseModel
from typing import List, Optional

class DocumentBlock(BaseModel):
    id: str
    number: Optional[str] = None
    heading: Optional[str] = None
    raw_text: str
    clean_text: str
    lemma_text: Optional[str] = None
    position: int
    path: Optional[str] = None  # Путь в структуре документа, например "Раздел 1 > Пункт 1.2"

class ComparisonResult(BaseModel):
    old_block: Optional[DocumentBlock] = None
    new_block: Optional[DocumentBlock] = None
    risk_level: str  # "green", "yellow", "red"
    risk_explanation: Optional[str] = None
    diff_type: str  # "equal", "changed", "added", "deleted", "split", "merge"
    score: float
