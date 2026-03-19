from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum

# ... (Existing RiskLevel and DiffType Enums ...)

class RiskLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

class DiffType(str, Enum):
    EQUAL = "equal"
    CHANGED = "changed"
    ADDED = "added"
    DELETED = "deleted"
    SPLIT = "split"
    MERGE = "merge"

class DocumentBlock(BaseModel):
    id: str
    document_id: Optional[str] = None
    number: Optional[str] = None
    heading: Optional[str] = None
    raw_text: str
    clean_text: Optional[str] = None
    lemma_text: Optional[str] = None
    position: int
    path: Optional[str] = None
    hierarchy_level: int = 10
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class RiskTrigger(BaseModel):
    category: str  # e.g., "Modality", "Dates", "Financial", "Negation"
    fragment: str  # The specific text fragment that triggered the risk
    explanation: str # Human-readable explanation of why it is a risk

class ComparisonResult(BaseModel):
    type: str = "result" # Discriminator for frontend
    old_block: Optional[DocumentBlock] = None
    new_block: Optional[DocumentBlock] = None
    risk_level: RiskLevel
    diff_type: DiffType
    score: float = 1.0
    
    alignment_reason: Optional[str] = None
    change_summary: Optional[str] = None
    risk_triggers: List[RiskTrigger] = []
    human_comment: Optional[str] = None
    legal_context: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True

class CollapsedSection(BaseModel):
    type: str = "collapsed" # Discriminator for frontend
    start_index: int
    end_index: int
    block_count: int
    reason_code: str = "ADDED_ONLY_WITHOUT_CONTRAST_TRIGGERS"
    summary_text: str
    risk_distribution: Dict[RiskLevel, int]
    items: List[ComparisonResult] # Hidden items that can be expanded

class ComparisonResponse(BaseModel):
    summary: Dict[str, Any]
    results: List[Union[ComparisonResult, CollapsedSection]]
