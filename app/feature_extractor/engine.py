import re
from typing import List
from app.models.document import DocumentBlock, BlockFeatures

class FeatureExtractor:
    @staticmethod
    def extract(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        total_blocks = len(blocks)
        for i, block in enumerate(blocks):
            text = block.normalized_text
            orig = block.original_text
            
            features = BlockFeatures()
            
            # 1. Length Score (Short text is often heading or citation)
            features.length_score = 1.0 if len(text) < 100 else (0.5 if len(text) < 300 else 0.0)
            
            # 2. Casing Score (All caps is high indicator for heading)
            features.casing_score = 1.0 if text.isupper() and len(text) > 3 else 0.0
            
            # 3. Numeric Pattern Score (Starting with 1, 1.1, etc)
            if re.match(r'^\d+(\.\d+)*\s+', text):
                features.numeric_pattern_score = 1.0
            
            # 4. Punctuation Score (Headings usually don't end with dots)
            if not text.endswith(('.', ':', ';', '?', '!')):
                features.punctuation_score = 1.0
            
            # 5. Position Score (References/Conclusion near end, Cover at start)
            rel_pos = i / total_blocks if total_blocks > 0 else 0
            features.position_score = rel_pos
            
            # 6. Semantic Match Score (Reserved keywords)
            keywords = ["INTRODUÇÃO", "CONCLUSÃO", "REFERÊNCIAS"]
            if any(k in text.upper() for k in keywords):
                features.semantic_match_score = 1.0

            block.features = features
            
        return blocks

# Line count: 40
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
