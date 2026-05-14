import re
from typing import List
from app.models.document import DocumentBlock, FeatureVector, LexicalFeatures, StructuralFeatures, SemanticFeatures
from app.nlp_engine.engine import SemanticNLPEngine

class FeatureEngine:
    @staticmethod
    def extract(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        total = len(blocks)
        for i, block in enumerate(blocks):
            text = block.normalized_text
            orig = block.original_text
            meta = block.metadata
            
            # 1. Lexical Features
            lex = LexicalFeatures()
            lex.length_norm = min(1.0, len(text) / 500)
            upper_count = sum(1 for c in text if c.isupper())
            lex.casing_ratio = upper_count / len(text) if len(text) > 0 else 0
            punct_count = sum(1 for c in text if c in '.,;:?!')
            lex.punctuation_ratio = punct_count / len(text) if len(text) > 0 else 0
            
            # 2. Structural Features (Now enriched with Metadata!)
            struc = StructuralFeatures()
            struc.position_norm = i / total if total > 0 else 0
            struc.isolation_score = 1.0 if orig.strip() == orig else 0.5
            
            # Use real metadata for hints
            if meta.is_bold or meta.is_heading_style:
                struc.format_hint_score = 1.0
            elif orig.startswith(('    ', '\t')):
                struc.format_hint_score = 0.5
                
            # 3. Semantic Features (V6 NLP Integration)
            sem = SemanticFeatures()
            
            intent, confidence = SemanticNLPEngine.get_highest_intent(text)
            sem.keyword_match = confidence # Direct NLP score
            sem.intent_distance = confidence # Stored for context
            sem.semantic_intent = intent
            
            sem.chapter_pattern = 1.0 if re.match(r'^\d+(\.\d+)*\s+', text) else 0.0
            
            # Boost chapter pattern if metadata says it's a heading
            if meta.is_heading_style and lex.length_norm < 0.3:
                 sem.chapter_pattern = max(sem.chapter_pattern, 0.8)
            
            block.features = FeatureVector(lexical=lex, structural=struc, semantic=sem)
            
        return blocks

# Line count: 42
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
