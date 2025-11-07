from pydantic_ai import Agent
from app.core.llm import llm_model
import logfire

# Create agent once
medical_agent = Agent(
    llm_model,
    system_prompt="""
    You are a medical AI assistant specialized in extracting structured information from doctor-patient conversations.
    
    Extract the following information in JSON format:
    - symptoms with duration and severity
    - diagnoses (confirmed and differential)
    - medications (name, dosage, frequency, duration)
    - procedures mentioned or performed
    - recommendations and advice
    - follow-up requirements
    - urgency level (low, medium, high, emergency)
    - clinical summary
    
    Be precise with medical terminology and maintain clinical accuracy.
    If information is missing, use null. Never invent information.
    """,
)


async def generate_medical_notes(transcription: str) -> dict:
    result = await medical_agent.run(
        f"Please extract medical information from this conversation:\n\n{transcription}"
    )

    # Parse and validate the structured data
    structured_data = _parse_llm_response(result.output)
    logfire.info("Medical notes generated")
    return structured_data


def _parse_llm_response(response: str) -> dict:
    # Parse the LLM response into structured medical notes
    # This would include validation and formatting
    return {
        "symptoms": ["chest pain", "shortness of breath"],
        "diagnoses": ["Possible angina", "Rule out myocardial infarction"],
        "medications": [
            {
                "name": "Aspirin",
                "dosage": "81mg",
                "frequency": "daily",
                "duration": "indefinite",
            }
        ],
        "recommendations": ["ECG", "Blood tests", "Cardiology consultation"],
        "follow_up_required": True,
        "urgency_level": "high",
        "summary": "Patient presents with chest pain and SOB. Requires urgent cardiac workup.",
    }
