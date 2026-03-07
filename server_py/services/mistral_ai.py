import asyncio
import os
import json
import logging
from typing import Any
from duckduckgo_search import DDGS

import httpx

from config import MISTRAL_API_KEY

logger = logging.getLogger(__name__)

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = "mistral-small-latest"
CONCURRENCY_LIMIT = 5

_semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)


async def _call_mistral(messages: list[dict], temperature: float = 0.3, timeout: float = 60.0) -> str:
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MISTRAL_MODEL,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    async with _semaphore:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(MISTRAL_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


def _web_search(query: str, max_results: int = 3) -> str:
    """Fetch latest data from the web using DuckDuckGo search."""
    try:
        results = DDGS().text(query, max_results=max_results)
        if not results:
            return ""
        context = []
        for r in results:
            context.append(f"Title: {r.get('title', '')}\nSnippet: {r.get('body', '')}")
        return "\n\n".join(context)
    except Exception as e:
        logger.warning(f"Web search failed for query '{query}': {e}")
        return ""


async def detect_csv_columns(headers: list[str], sample_rows: list[list[str]]) -> dict[str, str]:
    sample_text = "\n".join([",".join(headers)] + [",".join(row) for row in sample_rows[:3]])

    messages = [
        {
            "role": "system",
            "content": (
                "You are a data analyst assistant. Given CSV headers and sample rows, "
                "identify which columns map to: employee_name, email, department, manager_remarks. "
                "Return a JSON object mapping these keys to the actual column header names. "
                "Only include keys where you can confidently identify a matching column. "
                "Example: {\"employee_name\": \"Name\", \"email\": \"Email\", \"department\": \"Dept\", \"manager_remarks\": \"Manager Comments\"}"
            ),
        },
        {
            "role": "user",
            "content": f"CSV data:\n{sample_text}",
        },
    ]

    raw = await _call_mistral(messages)
    return json.loads(raw)


async def analyze_remarks(
    employee_name: str,
    department: str | None,
    remarks: str,
    existing_courses: list[dict[str, Any]],
) -> dict[str, Any]:
    courses_context = ""
    if existing_courses:
        courses_list = "\n".join(
            f"- ID:{c['id']} \"{c['title']}\": {c['description'][:100]}"
            for c in existing_courses
        )
        courses_context = f"\n\nExisting courses available:\n{courses_list}"

    messages = [
        {
            "role": "system",
            "content": (
                "You are an L&D (Learning & Development) analyst. Analyze employee manager remarks "
                "and provide training recommendations. Return a JSON object with:\n"
                "- \"summary\": A brief interpretation of the manager's feedback (1-2 sentences)\n"
                "- \"recommended_skills\": Array of skill areas the employee should develop\n"
                "- \"matched_courses\": Array of course IDs from existing courses that match (integers only)\n"
                "- \"suggested_trainings\": Array of objects with {\"title\", \"description\", \"reason\"} "
                "for new training that doesn't exist yet"
                + courses_context
            ),
        },
        {
            "role": "user",
            "content": (
                f"Employee: {employee_name}\n"
                f"Department: {department or 'Unknown'}\n"
                f"Manager Remarks: {remarks}"
            ),
        },
    ]

    raw = await _call_mistral(messages)
    result = json.loads(raw)

    return {
        "summary": result.get("summary", ""),
        "recommended_skills": result.get("recommended_skills", []),
        "matched_courses": [int(cid) for cid in result.get("matched_courses", [])],
        "suggested_trainings": result.get("suggested_trainings", []),
    }


async def generate_course_outline(title: str, audience: str = "all", depth: str = "intermediate") -> dict:
    search_context = _web_search(f"{title} tutorial concepts topics")
    context_str = f"Latest web context for {title}:\n{search_context}\n\n" if search_context else ""
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert curriculum designer. Given a course topic, generate a structured course outline. "
                "Return a JSON object with:\n"
                "- \"title\": A refined, professional course title\n"
                "- \"description\": Course description (2-3 sentences)\n"
                "- \"objectives\": Array of 4-6 learning objectives\n"
                "- \"chapters\": Array of 5-8 chapter objects, each with:\n"
                "  - \"title\": Chapter title\n"
                "  - \"summary\": What this chapter covers (1-2 sentences)\n"
                "  - \"search_terms\": Array of 2-3 search keywords for finding educational images\n"
                f"\nTarget audience: {audience}. Depth level: {depth}."
            ),
        },
        {
            "role": "user",
            "content": f"{context_str}Create a course outline for: {title}",
        },
    ]

    raw = await _call_mistral(messages, temperature=0.4, timeout=120.0)
    return json.loads(raw)


async def generate_chapter_content(
    course_title: str, chapter_title: str, chapter_summary: str,
    audience: str = "all", depth: str = "intermediate"
) -> dict:
    search_context = _web_search(f"{course_title} {chapter_title} {chapter_summary}")
    context_str = f"Latest web context:\n{search_context}\n\n" if search_context else ""
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert educational content writer. Write detailed chapter content in Markdown format. "
                "Include:\n"
                "- Rich explanations with headers (##, ###)\n"
                "- Code examples in fenced code blocks where relevant\n"
                "- Tables for comparisons or structured data\n"
                "- At least one Mermaid diagram using ```mermaid fenced code blocks (flowchart, sequence, or mindmap)\n"
                "- Bullet points and numbered lists\n"
                "- Bold/italic for emphasis\n\n"
                "Return a JSON object with:\n"
                "- \"content\": The full Markdown content (string)\n"
                "- \"quiz\": Object with \"questions\" array, each question has \"q\" (question text), "
                "\"options\" (array of 4 choices), \"correct\" (0-based index of correct answer)\n"
                "- \"tts_script\": A plain text narration script (2-3 paragraphs, no markdown, "
                "suitable for text-to-speech). Summarize the key points conversationally.\n\n"
                f"Target audience: {audience}. Depth: {depth}."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{context_str}"
                f"Course: {course_title}\n"
                f"Chapter: {chapter_title}\n"
                f"Summary: {chapter_summary}\n\n"
                "Write the full chapter content based on the provided topic and latest web context."
            ),
        },
    ]

    raw = await _call_mistral(messages, temperature=0.5, timeout=120.0)
    return json.loads(raw)


async def analyze_speaking_transcript(prompt: str, transcript: str) -> dict:
    """Analyze a speaking transcript and return scores + feedback."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are an English speaking coach. Analyze the given transcript in response to the prompt. "
                "Return a JSON object with:\n"
                "- \"pronunciation_score\": float 0-100 (estimate based on word choice and structure)\n"
                "- \"fluency_score\": float 0-100 (based on sentence flow, vocabulary, coherence)\n"
                "- \"feedback\": string with 2-3 sentences of constructive feedback\n"
                "- \"corrections\": string with 1-2 specific corrections or suggestions for improvement"
            ),
        },
        {
            "role": "user",
            "content": f"Prompt: {prompt}\n\nTranscript: {transcript}",
        },
    ]
    raw = await _call_mistral(messages, temperature=0.3, timeout=60.0)
    result = json.loads(raw)
    return {
        "pronunciation_score": float(result.get("pronunciation_score", 75.0)),
        "fluency_score": float(result.get("fluency_score", 75.0)),
        "feedback": str(result.get("feedback", "Good effort! Keep practicing.")),
        "corrections": str(result.get("corrections", "")),
    }

