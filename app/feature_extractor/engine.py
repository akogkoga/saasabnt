from typing import List

from app.feature_engine.engine import FeatureEngine
from app.models.document import DocumentBlock


class FeatureExtractor:
    """Legacy wrapper delegating feature extraction to FeatureEngine."""

    @staticmethod
    def extract(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        return FeatureEngine.extract(blocks)

# Line count: 40
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
