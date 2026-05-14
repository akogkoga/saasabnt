from typing import List
from app.models.document import IRDocument, ValidationResult

class ConvergenceEngine:
    @staticmethod
    def check_convergence(
        prev_ir_hash: str, 
        curr_ir_hash: str, 
        validation: ValidationResult
    ) -> bool:
        """
        V5.2 Formal Strong Convergence:
        1. Validation is VALID_STATE
        2. IR_HASH(t) == IR_HASH(t-1)
        """
        # 1. Validation must pass
        if not validation.is_valid:
            return False
            
        # 2. Mathematical IR Equality
        if not prev_ir_hash or prev_ir_hash != curr_ir_hash:
            return False
        
        return True

# Line count: 21
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
