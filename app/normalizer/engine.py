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
        aliases = SemanticNLPEngine.INTENT_DICTIONARY.get(intent, [])
        canonical_text = SemanticNLPEngine.canonicalize(text)
        return canonical_text in {
            SemanticNLPEngine.canonicalize(alias)
            for alias in aliases
        }

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
                confidence >= 0.9
                and intent in SemanticNormalizer.DISPLAY_LABELS
                and SemanticNormalizer._is_known_heading_alias(norm_text, intent)
            ):
                norm_text = SemanticNormalizer.DISPLAY_LABELS[intent]

            block.normalized_text = norm_text
            normalized_blocks.append(block)

        return normalized_blocks
