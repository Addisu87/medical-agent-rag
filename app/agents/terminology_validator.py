from pydantic_ai import Agent
from app.core.llm import llm_model
from app.models.schemas import TerminologyValidation
from typing import List
import logfire

class TerminologyValidator:
    def __init__(self):
        self.agent = Agent(
            llm_model,
            system_prompt="""
            You are a medical terminology expert. Your task is to validate medical terms and suggest corrections.
            
            For each term:
            1. Identify if it's a valid medical term
            2. Provide confidence score (0-1)
            3. Suggest correction if misspelled
            4. Categorize the term (anatomy, medication, condition, procedure, etc.)
            
            Use standard medical references and be precise.
            """
        )
    
    async def validate_terms(self, terms: List[str]) -> List[TerminologyValidation]:
        with logfire.span("validate_terms"):
            results = []
            for term in terms:
                validation = await self._validate_single_term(term)
                results.append(validation)
            return results
    
    async def _validate_single_term(self, term: str) -> TerminologyValidation:
        result = await self.agent.run(f"Validate this medical term: {term}")
        
        # Parse the validation result
        return TerminologyValidation(
            term=term,
            is_medical=True,  # This would be determined from LLM response
            confidence=0.95,
            suggested_correction=None,
            category="condition"
        )
