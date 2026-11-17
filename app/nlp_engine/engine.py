import difflib
import re
import unicodedata
from typing import Tuple


class SemanticNLPEngine:
    """
    Lightweight NLP engine using string distance for ABNT intent mapping.
    """

    MIN_INTENT_CONFIDENCE = 0.85
    MAX_HEADING_CHARS = 90
    MAX_HEADING_WORDS = 8

    INTENT_DICTIONARY = {
        "INTRODUCAO": ["INTRODUCAO", "CONSIDERACOES INICIAIS", "PREFACIO", "APRESENTACAO"],
        "DESENVOLVIMENTO": [
            "DESENVOLVIMENTO",
            "FUNDAMENTACAO TEORICA",
            "REVISAO BIBLIOGRAFICA",
            "METODOLOGIA",
            "RESULTADOS E DISCUSSAO",
        ],
        "CONCLUSAO": ["CONCLUSAO", "CONSIDERACOES FINAIS", "FECHAMENTO", "SINTESE"],
        "REFERENCIAS": ["REFERENCIAS", "REFERENCIAS BIBLIOGRAFICAS", "BIBLIOGRAFIA", "FONTES"],
        "RESUMO": ["RESUMO"],
        "ABSTRACT": ["ABSTRACT"],
        "FOLHA_APROVACAO": ["FOLHA DE APROVACAO"],
        "DEDICATORIA": ["DEDICATORIA"],
        "AGRADECIMENTOS": ["AGRADECIMENTOS"],
        "EPIGRAFE": ["EPIGRAFE"],
        "LISTA_ILUSTRACOES": ["LISTA DE ILUSTRACOES"],
        "LISTA_TABELAS": ["LISTA DE TABELAS"],
        "LISTA_ABREVIATURAS": ["LISTA DE ABREVIATURAS", "LISTA DE SIGLAS"],
        "LISTA_SIMBOLOS": ["LISTA DE SIMBOLOS"],
        "SUMARIO": ["SUMARIO"],
        "APENDICES": ["APENDICES", "APENDICE"],
        "ANEXOS": ["ANEXOS", "ANEXO"],
    }

    @staticmethod
    def canonicalize(text: str) -> str:
        if not text:
            return ""

        normalized = unicodedata.normalize("NFKD", text)
        without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
        upper = without_accents.upper()
        upper = re.sub(r"^\s*\d+(\.\d+)*\s*[-.)]?\s*", "", upper)
        upper = re.sub(r"[^A-Z0-9 ]+", " ", upper)
        return re.sub(r"\s+", " ", upper).strip()

    @staticmethod
    def get_highest_intent(text: str) -> Tuple[str, float]:
        """
        Returns (intent_key, confidence_score [0.0 - 1.0]).
        """
        stripped = (text or "").strip()
        if not stripped or stripped.endswith("."):
            return "UNKNOWN", 0.0

        clean_text = SemanticNLPEngine.canonicalize(stripped)
        if not clean_text:
            return "UNKNOWN", 0.0

        text_tokens = clean_text.split()
        if (
            len(clean_text) > SemanticNLPEngine.MAX_HEADING_CHARS
            or len(text_tokens) > SemanticNLPEngine.MAX_HEADING_WORDS
        ):
            return "UNKNOWN", 0.0

        best_intent = "UNKNOWN"
        highest_score = 0.0

        for intent, synonyms in SemanticNLPEngine.INTENT_DICTIONARY.items():
            for synonym in synonyms:
                clean_synonym = SemanticNLPEngine.canonicalize(synonym)
                if not clean_synonym:
                    continue
                ratio = difflib.SequenceMatcher(None, clean_text, clean_synonym).ratio()
                synonym_tokens = clean_synonym.split()

                if clean_text == clean_synonym:
                    ratio = 1.0
                elif (
                    intent in {"APENDICES", "ANEXOS"}
                    and clean_text.startswith(clean_synonym + " ")
                    and len(text_tokens) <= 6
                ):
                    ratio = max(ratio, 0.95)
                elif (
                    intent in {"INTRODUCAO", "DESENVOLVIMENTO", "CONCLUSAO", "REFERENCIAS"}
                    and clean_text.startswith(clean_synonym + " ")
                    and len(text_tokens) <= len(synonym_tokens) + 1
                ):
                    ratio = max(ratio, 0.95)

                if ratio > highest_score:
                    highest_score = ratio
                    best_intent = intent

        if highest_score < SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
            return "UNKNOWN", 0.0

        return best_intent, highest_score
