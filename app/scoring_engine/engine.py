import math
from typing import List, Dict
from app.models.document import DocumentBlock, BlockType, GlobalContextVector

class ScoringEngine:
    # Local weights (from V4)
    WEIGHTS = {
        BlockType.HEADING:    [-3.0,  3.5, -4.0, 0.0, 0.5,  1.5,  6.0,  2.0],
        BlockType.PARAGRAPH:  [ 2.5, -2.0,  3.0, 0.0, 0.5, -1.0, -5.0, -4.0],
        BlockType.REFERENCE:  [ 0.0,  0.5,  2.0, 1.5, 0.0,  0.0, -2.0, -3.0],
        BlockType.CHAPTER:    [-3.0,  2.5, -4.0, 0.0, 0.5,  1.0,  2.0,  7.0],
    }

    @staticmethod
    def calculate_probabilities(blocks: List[DocumentBlock], ctx: GlobalContextVector) -> List[DocumentBlock]:
        for block in blocks:
            f = block.features
            raw_scores = {}
            
            # 1. Local scores
            v = [
                f.lexical.length_norm, f.lexical.casing_ratio, f.lexical.punctuation_ratio,
                f.structural.position_norm, f.structural.isolation_score, f.structural.format_hint_score,
                f.semantic.keyword_match, f.semantic.chapter_pattern
            ]
            
            for b_type, weights in ScoringEngine.WEIGHTS.items():
                local_score = sum(wi * vi for wi, vi in zip(weights, v))
                
                # 2. Global Context Influence
                global_boost = 0.0
                if b_type == BlockType.REFERENCE and ctx.has_refs and f.structural.position_norm > 0.8:
                    global_boost += 2.0
                if b_type == BlockType.CHAPTER and ctx.chapter_density > 0.05:
                    global_boost += 1.0
                
                raw_scores[b_type] = local_score + global_boost
            
            # 3. Softmax
            exp_scores = {bt: math.exp(s) for bt, s in raw_scores.items()}
            sum_exp = sum(exp_scores.values())
            block.probabilities = {bt.value: es / sum_exp for bt, es in exp_scores.items()}
            
        return blocks

# Line count: 44
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
