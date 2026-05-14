import hashlib
import json
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import math

class BlockType(str, Enum):
    TITLE = "title"
    HEADING = "heading"
    CHAPTER = "chapter"
    PARAGRAPH = "paragraph"
    SHORT_CITATION = "short_citation"
    LONG_CITATION = "long_citation"
    REFERENCE = "reference"
    FOOTNOTE = "footnote"
    CAPA = "capa"
    FOLHA_ROSTO = "folha_rosto"
    SUMARIO = "sumario"
    SUMARIO_ENTRY = "sumario_entry"
    TABLE = "table"
    IMAGE = "image"

class DocumentState(str, Enum):
    RAW = "raw"
    NORMALIZED = "normalized"
    CLASSIFIED = "classified"
    STRUCTURED = "structured"
    ORDERED = "ordered"
    VALIDATED = "validated"
    CORRECTED = "corrected"
    FINALIZED = "finalized"

class ErrorType(str, Enum):
    MISSING_REFERENCES = "missing_references"
    INVALID_ORDERING = "invalid_ordering"
    LOW_CONFIDENCE_STRUCTURE = "low_confidence_structure"
    ORPHAN_BLOCK = "orphan_block"
    SECTION_MISPLACEMENT = "section_misplacement"

class LexicalFeatures(BaseModel):
    length_norm: float = 0.0
    casing_ratio: float = 0.0
    punctuation_ratio: float = 0.0

class StructuralFeatures(BaseModel):
    position_norm: float = 0.0
    isolation_score: float = 0.0
    format_hint_score: float = 0.0

class SemanticFeatures(BaseModel):
    keyword_match: float = 0.0
    intent_distance: float = 0.0  # V6 NLP Intent distance
    semantic_intent: str = "UNKNOWN"
    chapter_pattern: float = 0.0

class FeatureVector(BaseModel):
    lexical: LexicalFeatures = Field(default_factory=LexicalFeatures)
    structural: StructuralFeatures = Field(default_factory=StructuralFeatures)
    semantic: SemanticFeatures = Field(default_factory=SemanticFeatures)

class GlobalContextVector(BaseModel):
    has_intro: bool = False
    has_concl: bool = False
    has_refs: bool = False
    chapter_density: float = 0.0
    ref_density: float = 0.0
    struct_depth: int = 0
    position_map: Dict[int, str] = Field(default_factory=dict)

class OriginalMetadata(BaseModel):
    is_bold: bool = False
    is_italic: bool = False
    is_heading_style: bool = False
    is_list: bool = False
    alignment: Optional[str] = None

class DocumentBlock(BaseModel):
    original_text: str
    normalized_text: str = ""
    metadata: OriginalMetadata = Field(default_factory=OriginalMetadata) # V6 Rich Parsing
    features: FeatureVector = Field(default_factory=FeatureVector)
    probabilities: Dict[str, float] = Field(default_factory=dict)
    predicted_type: BlockType = BlockType.PARAGRAPH
    confidence: float = 0.0
    is_ambiguous: bool = False
    ambiguity_details: Optional[str] = None
    is_locked: bool = False
    
    # Complex objects
    table_data: Optional[List[List[str]]] = None
    image_bytes: Optional[bytes] = None

class SemanticIR(BaseModel):
    type: BlockType
    text: str
    level: int = 0
    table_data: Optional[List[List[str]]] = None
    image_bytes: Optional[bytes] = None

class StyleIR(BaseModel):
    font_name: str = "Times New Roman"
    font_size: int = 12
    line_spacing: float = 1.5
    first_line_indent: float = 1.25
    left_indent: float = 0.0
    alignment: str = "justify"
    bold: bool = False
    page_break_before: bool = False
    is_table_style: bool = False

class IRBlock(BaseModel):
    semantic: SemanticIR
    style: StyleIR

class ValidationError(BaseModel):
    type: ErrorType
    message: str
    affected_block_indices: List[int] = Field(default_factory=list)

class ValidationResult(BaseModel):
    is_valid: bool = True
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    audit_log: List[str] = Field(default_factory=list)
    state: DocumentState = DocumentState.RAW

class IRSnapshot(BaseModel):
    version: str
    timestamp: float
    blocks: List[IRBlock]
    validation: ValidationResult

class IRDocument(BaseModel):
    global_margins: Dict[str, float] = Field(default_factory=lambda: {"top": 3.0, "left": 3.0, "bottom": 2.0, "right": 2.0})
    blocks: List[IRBlock] = Field(default_factory=list)
    state: DocumentState = DocumentState.RAW
    snapshots: Dict[str, IRSnapshot] = Field(default_factory=dict)
    canonical_hash: str = ""

class ABNTStructure(BaseModel):
    pre_textual: List[DocumentBlock] = Field(default_factory=list)
    textual_intro: List[DocumentBlock] = Field(default_factory=list)
    textual_dev: List[DocumentBlock] = Field(default_factory=list)
    textual_conclusion: List[DocumentBlock] = Field(default_factory=list)
    post_textual: List[DocumentBlock] = Field(default_factory=list)

# Compatibility aliases for older modules kept in the package.
BlockFeatures = FeatureVector
SemanticTree = ABNTStructure

# Line count: 122
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
