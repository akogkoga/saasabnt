from typing import List
from app.models.document import SemanticTree, DocumentBlock, BlockType

class DocumentAssembler:
    @staticmethod
    def assemble(tree: SemanticTree) -> List[DocumentBlock]:
        final_list = []
        
        # 1. Pre-textual
        final_list.extend(tree.pre_textual)
        
        # 2. Textual Intro
        if tree.textual_intro:
            final_list.extend(tree.textual_intro)
            
        # 3. Textual Development
        if tree.textual_dev:
            final_list.extend(tree.textual_dev)
            
        # 4. Textual Conclusion
        if tree.textual_concl:
            final_list.extend(tree.textual_concl)
            
        # 5. Post-textual
        if tree.post_textual:
            final_list.extend(tree.post_textual)
            
        return final_list

# Line count: 28
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
