import time
from typing import List, Dict
from app.models.document import IRBlock, IRSnapshot, ValidationResult, IRDocument

class IRVersioningEngine:
    @staticmethod
    def create_snapshot(version: str, blocks: List[IRBlock], val_res: ValidationResult) -> IRSnapshot:
        return IRSnapshot(
            version=version,
            timestamp=time.time(),
            blocks=blocks,
            validation=val_res
        )

    @staticmethod
    def audit_diff(v_old: IRSnapshot, v_new: IRSnapshot) -> List[str]:
        diffs = []
        if len(v_old.blocks) != len(v_new.blocks):
            diffs.append(f"Block count changed: {len(v_old.blocks)} -> {len(v_new.blocks)}")
        
        # Simple structural diff
        for i in range(min(len(v_old.blocks), len(v_new.blocks))):
            if v_old.blocks[i].semantic.type != v_new.blocks[i].semantic.type:
                diffs.append(f"Block {i} type changed: {v_old.blocks[i].semantic.type} -> {v_new.blocks[i].semantic.type}")
        
        return diffs

# Line count: 26
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
