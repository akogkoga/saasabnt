from typing import List
from app.models.document import DocumentBlock, BlockType
from app.nlp_engine.engine import SemanticNLPEngine
import re

class Classifier:
    @staticmethod
    def _looks_like_reference(text: str) -> bool:
        canonical = SemanticNLPEngine.canonicalize(text)
        if not canonical:
            return False

        reference_markers = [
            "HTTP",
            "WWW",
            "DISPONIVEL EM",
            "ACESSO EM",
            "EDITORA",
            "REVISTA",
            "JOURNAL",
            "VOL",
            "DOI",
        ]

        if any(marker in canonical for marker in reference_markers):
            return True
        if re.search(r"\b(19|20)\d{2}\b", canonical):
            return True
        if re.match(r"^[A-Z]{3,}( [A-Z]{2,})*,", canonical):
            return True

        return False

    @staticmethod
    def classify(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        for block in blocks:
            # V5.1: Stability Lock Check
            if block.is_locked:
                continue

            # Sort probabilities descending
            sorted_probs = sorted(block.probabilities.items(), key=lambda x: x[1], reverse=True)
            
            top_type_str, top_prob = sorted_probs[0]
            second_prob = sorted_probs[1][1] if len(sorted_probs) > 1 else 0
            
            block.predicted_type = BlockType(top_type_str)
            block.confidence = top_prob

            if block.predicted_type == BlockType.REFERENCE and not Classifier._looks_like_reference(block.normalized_text):
                if block.features.semantic.semantic_intent == "REFERENCIAS":
                    block.predicted_type = BlockType.HEADING
                else:
                    block.predicted_type = BlockType.PARAGRAPH
            
            # --- V5.1: Stability Lock ---
            if top_prob > 0.85:
                block.is_locked = True
            
            # --- Ambiguity Check ---
            if (top_prob - second_prob) < 0.08:
                block.is_ambiguous = True
                block.ambiguity_details = f"Top diff: {top_prob - second_prob:.4f}. Candidates: {top_type_str}, {sorted_probs[1][0]}"
                
                # Fallback rules
                if block.features.structural.position_norm > 0.9 and "reference" in [top_type_str, sorted_probs[1][0]]:
                    if Classifier._looks_like_reference(block.normalized_text):
                        block.predicted_type = BlockType.REFERENCE
                elif block.features.lexical.length_norm < 0.2 and block.features.lexical.casing_ratio > 0.8:
                    block.predicted_type = BlockType.HEADING

        return blocks

# Line count: 35
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
