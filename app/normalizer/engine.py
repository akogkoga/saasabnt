import re
from typing import List, Sequence, Union

from app.models.document import DocumentBlock
from app.nlp_engine.engine import SemanticNLPEngine


class SemanticNormalizer:
    DISPLAY_LABELS = {
        "INTRODUCAO": "INTRODUÇÃO",
        "CONCLUSAO": "CONCLUSÃO",
        "REFERENCIAS": "REFERÊNCIAS",
        "RESUMO": "RESUMO",
        "ABSTRACT": "ABSTRACT",
        "SUMARIO": "SUMÁRIO",
        "APENDICES": "APÊNDICES",
        "ANEXOS": "ANEXOS",
    }

    @staticmethod
    def _is_known_heading_alias(text: str, intent: str) -> bool:
        canonical_text = SemanticNLPEngine.canonicalize(text)
        return canonical_text == intent

    @staticmethod
    def normalize(raw_blocks: Sequence[Union[str, DocumentBlock]]) -> List[DocumentBlock]:
        normalized_blocks = []

        for raw in raw_blocks:
            block = (
                raw.model_copy(deep=True)
                if isinstance(raw, DocumentBlock)
                else DocumentBlock(original_text=str(raw))
            )

            norm_text = re.sub(r"\s+", " ", block.original_text).strip()
            intent, confidence = SemanticNLPEngine.get_highest_intent(norm_text)

            if (
                confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE
                and intent in SemanticNormalizer.DISPLAY_LABELS
                and SemanticNormalizer._is_known_heading_alias(norm_text, intent)
            ):
                label = SemanticNormalizer.DISPLAY_LABELS[intent]
                prefix_match = re.match(r"^(\d+(?:\.\d+)*)\s*[-.)]?\s+(.+)$", norm_text)
                updated_text = f"{prefix_match.group(1)} {label}" if prefix_match else label
                if updated_text != norm_text:
                    block.runs = None
                norm_text = updated_text

            block.normalized_text = norm_text
            normalized_blocks.append(block)

        return normalized_blocks
