from typing import List
from app.models.document import DocumentBlock, ValidationResult, IRDocument
from app.validation_engine.engine import ValidationEngine
from app.correction_engine.engine import CorrectionEngine
from app.ordering_engine.engine import OrderingEngine
from app.structure_builder.engine import StructureBuilder
from app.convergence_engine.engine import ConvergenceEngine
from app.ir_layer.engine import IRLayer
from app.ir_equality.engine import IREqualityEngine

class RecompilationLoopEngine:
    MAX_ITERATIONS = 5

    @staticmethod
    def run(
        blocks: List[DocumentBlock],
        complete_missing: bool = True,
    ) -> tuple[List[DocumentBlock], ValidationResult, bool, IRDocument]:
        """
        Orchestrates the active correction loop with formal IR Hash convergence.
        Returns: (final_blocks, final_validation, is_converged, final_ir_doc)
        """
        current_blocks = blocks
        prev_ir_hash = ""
        iteration = 0
        final_validation = None
        is_converged = False
        final_ir = None
        
        while iteration < RecompilationLoopEngine.MAX_ITERATIONS:
            # 1. Validate
            validation = ValidationEngine.validate(
                current_blocks,
                require_complete_structure=complete_missing,
            )
            final_validation = validation
            
            # 2. Generate IR and Hash for Convergence Check
            current_ir = IRLayer.generate_passive_ir(current_blocks)
            curr_ir_hash = IREqualityEngine.generate_canonical_hash(current_ir)
            current_ir.canonical_hash = curr_ir_hash
            final_ir = current_ir
            
            # 3. Check Convergence (V5.2)
            if ConvergenceEngine.check_convergence(prev_ir_hash, curr_ir_hash, validation):
                is_converged = True
                break
                
            prev_ir_hash = curr_ir_hash
                
            # 4. Correct (if invalid)
            if not validation.is_valid:
                corrected = CorrectionEngine.apply_corrections(current_blocks, validation.errors)
                struct = StructureBuilder.build(corrected)
                current_blocks = OrderingEngine.enforce_order(
                    struct,
                    complete_missing=complete_missing,
                )
                
            iteration += 1
            
        return current_blocks, final_validation, is_converged, final_ir

# Line count: 44
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
