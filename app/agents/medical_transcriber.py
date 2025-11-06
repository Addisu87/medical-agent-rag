import assemblyai as aai
import os
from app.core.config import settings
import logfire

class MedicalTranscriber:
    def __init__(self):
        aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
        logfire.info("MedicalTranscriber initialized")
    
    async def transcribe_audio(self, audio_file_path: str) -> str:
        with logfire.span("transcribe_audio"):
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
            
            config = aai.TranscriptionConfig(
                speaker_labels=True,
                speakers_expected=2,
                language_code="en",
                punctuate=True
            )
            
            transcript = aai.Transcriber().transcribe(audio_file_path, config)
            
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"Transcription failed: {transcript.error}")
            
            formatted_transcript = self._format_transcription(transcript)
            
            logfire.info(
                "Transcription completed",
                duration=transcript.audio_duration,
                word_count=len(formatted_transcript.split())
            )
            
            return formatted_transcript
    
    def _format_transcription(self, transcript) -> str:
        lines = []
        for utterance in transcript.utterances:
            speaker = "Doctor" if utterance.speaker == 'A' else "Patient"
            lines.append(f"{speaker}: {utterance.text}")
        return "\n".join(lines)