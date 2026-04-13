import os
import json
import logging
from typing import Dict, Any
from groq import Groq

from config import GROQ_API_KEY

logger = logging.getLogger(__name__)


def transcribe_audio(file_path: str) -> str:
    """
    Transcribe an audio file using Groq's Whisper model.
    Returns the transcribed text.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")

    client = Groq(api_key=GROQ_API_KEY)

    with open(file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(file_path, file.read()),
            model="whisper-large-v3-turbo",
            temperature=0,
            response_format="verbose_json",
        )

    return transcription.text


async def generate_mindmap_from_transcript(transcript: str) -> Dict[str, Any]:
    """
    Generate a structured mindmap from transcript text using Groq LLM.
    Returns a hierarchical JSON structure:
    {
      "root": "Main Topic",
      "children": [
        {
          "label": "Key Point 1",
          "children": [
            { "label": "Sub-point A", "children": [] },
            { "label": "Sub-point B", "children": [] }
          ]
        }
      ]
    }
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")

    client = Groq(api_key=GROQ_API_KEY)

    system_prompt = """You are an expert at extracting key concepts and creating structured mindmaps from text.

Given a transcript of speech, analyze it and extract the main topics, key points, and sub-points into a hierarchical mindmap structure.

Rules:
1. Identify the main topic/theme as the root
2. Extract 3-7 main branches (key points)
3. Each branch can have 2-5 sub-branches
4. Keep labels concise (max 8 words each)
5. Return ONLY valid JSON, no explanation
6. The structure must match this exact schema:
   {
     "root": "string",
     "children": [
       {
         "label": "string",
         "children": [
           { "label": "string", "children": [] }
         ]
       }
     ]
   }

Focus on the most important concepts and relationships. Avoid trivial details."""

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Transcript:\n\n{transcript}"},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    response_text = chat_completion.choices[0].message.content

    try:
        mindmap_data = json.loads(response_text)
        # Validate structure
        if "root" not in mindmap_data or "children" not in mindmap_data:
            raise ValueError("Invalid mindmap structure: missing 'root' or 'children'")
        return mindmap_data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse mindmap JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Mindmap generation failed: {e}")
        raise


def generate_fallback_mindmap(transcript: str) -> Dict[str, Any]:
    """
    Generate a simple fallback mindmap if AI generation fails.
    Splits transcript into sentences and groups them.
    """
    sentences = [s.strip() for s in transcript.replace('! ', '. ').replace('? ', '. ').split('.') if s.strip()]

    if not sentences:
        return {"root": "Empty Transcript", "children": []}

    # Group sentences by topic keywords (simple heuristic)
    main_topics = "Transcript Summary"
    children = []

    for i, sentence in enumerate(sentences[:10]):  # Limit to first 10 sentences
        children.append({
            "label": f"Point {i + 1}",
            "children": [{"label": sentence[:80] + ("..." if len(sentence) > 80 else ""), "children": []}]
        })

    return {"root": main_topics, "children": children}
