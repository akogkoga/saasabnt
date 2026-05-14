from typing import List
from app.models.document import DocumentBlock, GlobalContextVector
from app.nlp_engine.engine import SemanticNLPEngine


class GlobalContextEngine:
    @staticmethod
    def calculate(blocks: List[DocumentBlock]) -> GlobalContextVector:
        ctx = GlobalContextVector()
        if not blocks:
            return ctx

        chapter_count = 0
        ref_pattern_count = 0

        for i, block in enumerate(blocks):
            text = block.normalized_text
            canonical_text = SemanticNLPEngine.canonicalize(text)
            semantic_intent = block.features.semantic.semantic_intent

            if semantic_intent == "INTRODUCAO" or "INTRODUCAO" in canonical_text:
                ctx.has_intro = True
            if semantic_intent == "CONCLUSAO" or "CONCLUSAO" in canonical_text:
                ctx.has_concl = True
            if semantic_intent == "REFERENCIAS" or "REFERENCIAS" in canonical_text:
                ctx.has_refs = True

            if block.features.semantic.chapter_pattern > 0.5:
                chapter_count += 1

            if block.features.lexical.punctuation_ratio > 0.05 and block.features.lexical.casing_ratio > 0.1:
                ref_pattern_count += 1

            ctx.position_map[i] = text[:20]

        total = len(blocks)
        ctx.chapter_density = chapter_count / total
        ctx.ref_density = ref_pattern_count / total
        ctx.struct_depth = chapter_count

        return ctx
