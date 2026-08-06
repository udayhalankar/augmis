import json
import logging
import re

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.subscription_service import add_ai_token_usage, validate_usage_limit
from app.services.token_usage_service import estimate_ai_usage_tokens

client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger = logging.getLogger(__name__)


CAREER_GUIDANCE_SYSTEM_PROMPT = """
You are an educational and career guidance advisor for students.

Your job:
- Review the student's academic history, interests, hobbies, goals, and preferred stream
- Identify strengths, patterns, and areas that need improvement
- Suggest realistic study streams and career directions
- Keep the tone encouraging, practical, and age-appropriate

Always:
- Avoid presenting the advice as guaranteed or final
- Do not shame the student for low marks
- Consider both marks and interests together
- Mention when the data is incomplete or limited
- Recommend 2 to 4 suitable career paths when possible
- Include practical next steps the student can act on soon
- End with a short note encouraging discussion with parents, teachers, or a career counselor
"""


APTITUDE_TEST_SYSTEM_PROMPT = """
You are an educational aptitude-test designer for students.

Your job:
- Read the student's academic history, interests, hobbies, strengths, goals, and preferred stream
- Create a short aptitude questionnaire tailored to the student
- Mix analytical, verbal, problem-solving, creativity, practical-interest, and career-preference style questions

Always:
- Return valid JSON only
- Create exactly 8 questions
- Keep language simple for school students
- Each question must have 4 answer options
- Make the options distinct and meaningful
- Avoid requiring specialist prior knowledge
"""


MOCK_STUDENT_PROFILE_SYSTEM_PROMPT = """
You generate realistic sample student profiles for testing a career-guidance form.

Your job:
- Return a believable student profile with academic history, interests, goals, and marks
- Make the sample varied, age-appropriate, and internally consistent

Always:
- Return valid JSON only
- Choose a current_standard between 8 and 12
- Include academic records from class 1 through current_standard
- Each class should have 3 to 6 subjects
- Scores should be plausible and varied
- Hobbies and interests should align reasonably with the likely career aspiration
"""

# Student evaluation does not use repository/work-area Copilot prompts.
# Keep this service limited to student profile, aptitude-test, and career-guidance flows.
# def build_user_prompt(query: str, business_area: str, context: str) -> str:
#     ...
#
# def build_portfolio_risk_prompt(query: str, work_area_payload: list[dict]) -> str:
#     ...


def build_career_guidance_prompt(student_profile: dict) -> str:
    return f"""
STUDENT PROFILE:
{json.dumps(student_profile, ensure_ascii=True, indent=2, default=str)}

Please provide:
1. Student profile snapshot
2. Academic strengths and weak areas
3. Recommended stream choice with reasoning
4. Best-fit career paths
5. Skills the student should build next
6. Short action plan for the next 6 to 12 months
7. Confidence note describing any limits in the input data
"""


def build_aptitude_test_prompt(student_profile: dict) -> str:
    return f"""
STUDENT PROFILE:
{json.dumps(student_profile, ensure_ascii=True, indent=2, default=str)}

Return JSON only in this shape:
{{
  "title": "string",
  "instructions": "string",
  "questions": [
    {{
      "id": "q1",
      "question": "string",
      "dimension": "analytical | verbal | creativity | practical | social | leadership | focus | career_interest",
      "options": [
        {{
          "id": "a",
          "label": "string",
          "signal": "string"
        }}
      ]
    }}
  ]
}}

Rules:
- Create exactly 8 questions.
- Each question must have exactly 4 options with ids "a", "b", "c", and "d".
- "signal" should briefly describe what the option suggests about the student.
- Keep the questionnaire suitable for the student's age.
"""


def build_career_guidance_with_aptitude_prompt(
    student_profile: dict,
    aptitude_questions: list[dict],
    aptitude_answers: list[dict],
) -> str:
    return f"""
STUDENT PROFILE:
{json.dumps(student_profile, ensure_ascii=True, indent=2, default=str)}

APTITUDE TEST QUESTIONS:
{json.dumps(aptitude_questions, ensure_ascii=True, indent=2, default=str)}

APTITUDE TEST ANSWERS:
{json.dumps(aptitude_answers, ensure_ascii=True, indent=2, default=str)}

Please provide:
1. Student profile snapshot
2. Aptitude findings from the test answers
3. Academic strengths and weak areas
4. Recommended stream choice with reasoning
5. Best-fit career paths
6. Skills the student should build next
7. Short action plan for the next 6 to 12 months
8. Confidence note describing any limits in the input data
"""


def build_mock_student_profile_prompt() -> str:
    return """
Return JSON only in this shape:
{
  "board": "string",
  "current_standard": 10,
  "preferred_stream": "string",
  "career_aspiration": "string",
  "goal": "string",
  "hobbies": ["string"],
  "interests": ["string"],
  "strengths": "string",
  "improvement_areas": "string",
  "academic_records": [
    {
      "standard": 1,
      "subjects": [
        {
          "subject": "string",
          "score": "string"
        }
      ]
    }
  ]
}

Rules:
- Use one of these boards: CBSE, ICSE, State Board, IB, IGCSE.
- Use one of these preferred streams: Science, Commerce, Arts / Humanities, Diploma / Vocational, Undecided.
- academic_records must start from class 1 and continue without gaps up to current_standard.
- score should be human-friendly like "87/100", "A", or "91 out of 100", but prefer numeric school marks.
- Make the profile suitable for testing a student career recommendation flow.
"""


def _extract_json_object(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in AI response")

    return json.loads(text[start : end + 1])


def _normalize_aptitude_test(payload: dict) -> dict:
    questions = payload.get("questions") or []
    normalized_questions = []

    for index, question in enumerate(questions[:8], start=1):
        options = question.get("options") or []
        normalized_options = []
        for option_index, option in enumerate(options[:4]):
            fallback_ids = ["a", "b", "c", "d"]
            normalized_options.append(
                {
                    "id": str(option.get("id") or fallback_ids[option_index]),
                    "label": str(option.get("label") or "").strip(),
                    "signal": str(option.get("signal") or "").strip(),
                }
            )

        if len(normalized_options) < 4:
            continue

        normalized_questions.append(
            {
                "id": str(question.get("id") or f"q{index}"),
                "question": str(question.get("question") or "").strip(),
                "dimension": str(question.get("dimension") or "career_interest").strip(),
                "options": normalized_options,
            }
        )

    if len(normalized_questions) != 8:
        raise ValueError("AI aptitude test did not return exactly 8 usable questions")

    return {
        "title": str(payload.get("title") or "Student Aptitude Test").strip(),
        "instructions": str(
            payload.get("instructions")
            or "Answer all questions honestly so the final recommendation can combine your profile and aptitude responses."
        ).strip(),
        "questions": normalized_questions,
    }


def _normalize_mock_student_profile(payload: dict) -> dict:
    current_standard = int(payload.get("current_standard") or 10)
    current_standard = min(max(current_standard, 1), 12)

    academic_records = []
    raw_records = payload.get("academic_records") or []
    record_map = {}

    for record in raw_records:
        try:
            standard = int(record.get("standard"))
        except (TypeError, ValueError):
            continue
        if 1 <= standard <= current_standard:
            record_map[standard] = record

    for standard in range(1, current_standard + 1):
        record = record_map.get(standard) or {"standard": standard, "subjects": []}
        subjects = []
        for subject in (record.get("subjects") or [])[:6]:
            subject_name = str(subject.get("subject") or "").strip()
            subject_score = str(subject.get("score") or "").strip()
            if not subject_name and not subject_score:
                continue
            subjects.append(
                {
                    "subject": subject_name or "General Studies",
                    "score": subject_score or "75/100",
                }
            )

        if not subjects:
            subjects = [
                {"subject": "English", "score": "78/100"},
                {"subject": "Mathematics", "score": "81/100"},
                {"subject": "Science", "score": "79/100"},
            ]

        academic_records.append(
            {
                "standard": standard,
                "subjects": subjects,
            }
        )

    return {
        "board": str(payload.get("board") or "CBSE").strip(),
        "current_standard": current_standard,
        "preferred_stream": str(payload.get("preferred_stream") or "Undecided").strip(),
        "career_aspiration": str(payload.get("career_aspiration") or "Software Engineer").strip(),
        "goal": str(payload.get("goal") or "Build a strong academic base and choose the right stream").strip(),
        "hobbies": [str(item).strip() for item in (payload.get("hobbies") or []) if str(item).strip()],
        "interests": [str(item).strip() for item in (payload.get("interests") or []) if str(item).strip()],
        "strengths": str(payload.get("strengths") or "Curious, disciplined, and willing to learn").strip(),
        "improvement_areas": str(
            payload.get("improvement_areas") or "Needs more consistency and confidence in difficult subjects"
        ).strip(),
        "academic_records": academic_records,
    }
# Student evaluation does not use business-area / work-area / repository Copilot logic.
# Keep this copied code commented out so the service remains student-only.
# def resolve_business_area_for_query(...):
#     ...
#
# def _has_specific_document_identifier(...):
#     ...
#
# def _should_use_portfolio_fact_mode(...):
#     ...
#
# def _is_broad_portfolio_risk_query(...):
#     ...
#
# def _get_portfolio_risk_payload(...):
#     ...
#
# def _build_portfolio_sources(...):
#     ...
#
# def ask_ai(...):
#     ...


def ask_career_guidance(
    student_profile: dict,
    current_user: dict,
    db: Session,
):
    validate_usage_limit(current_user["tenant_id"], "ai_tokens", db)

    user_prompt = build_career_guidance_prompt(student_profile)

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": CAREER_GUIDANCE_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.4,
        )
    except Exception:
        logger.exception(
            "OpenAI career guidance completion failed",
            extra={
                "category": "openai_request_failure",
                "is_critical": True,
                "metadata": {
                    "mode": "career_guidance",
                },
            },
        )
        raise

    answer = response.choices[0].message.content or ""
    actual_tokens = getattr(response.usage, "total_tokens", None)
    serialized_profile = json.dumps(student_profile, ensure_ascii=True, default=str)
    tokens_used = actual_tokens or estimate_ai_usage_tokens(
        question="Generate student career guidance",
        context=serialized_profile,
        answer=answer,
    )

    add_ai_token_usage(current_user["tenant_id"], tokens_used, db)

    return {
        "answer": answer,
        "usage": {
            "tokens_used": tokens_used,
        },
        "status": {
            "mode": "career_guidance",
            "message": "AI career guidance generated from student-submitted profile data.",
        },
    }


def generate_aptitude_test(
    student_profile: dict,
    current_user: dict,
    db: Session,
):
    validate_usage_limit(current_user["tenant_id"], "ai_tokens", db)

    user_prompt = build_aptitude_test_prompt(student_profile)

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": APTITUDE_TEST_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.5,
        )
    except Exception:
        logger.exception(
            "OpenAI aptitude test generation failed",
            extra={
                "category": "openai_request_failure",
                "is_critical": True,
                "metadata": {
                    "mode": "aptitude_test_generation",
                },
            },
        )
        raise

    raw_content = response.choices[0].message.content or ""
    parsed_test = _normalize_aptitude_test(_extract_json_object(raw_content))
    actual_tokens = getattr(response.usage, "total_tokens", None)
    serialized_profile = json.dumps(student_profile, ensure_ascii=True, default=str)
    tokens_used = actual_tokens or estimate_ai_usage_tokens(
        question="Generate student aptitude test",
        context=serialized_profile,
        answer=raw_content,
    )

    add_ai_token_usage(current_user["tenant_id"], tokens_used, db)

    return {
        "test": parsed_test,
        "usage": {
            "tokens_used": tokens_used,
        },
        "status": {
            "mode": "aptitude_test",
            "message": "AI aptitude test generated from student profile data.",
        },
    }


def ask_career_guidance_with_aptitude(
    student_profile: dict,
    aptitude_questions: list[dict],
    aptitude_answers: list[dict],
    current_user: dict,
    db: Session,
):
    validate_usage_limit(current_user["tenant_id"], "ai_tokens", db)

    user_prompt = build_career_guidance_with_aptitude_prompt(
        student_profile=student_profile,
        aptitude_questions=aptitude_questions,
        aptitude_answers=aptitude_answers,
    )

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": CAREER_GUIDANCE_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.4,
        )
    except Exception:
        logger.exception(
            "OpenAI final career guidance with aptitude failed",
            extra={
                "category": "openai_request_failure",
                "is_critical": True,
                "metadata": {
                    "mode": "career_guidance_with_aptitude",
                },
            },
        )
        raise

    answer = response.choices[0].message.content or ""
    actual_tokens = getattr(response.usage, "total_tokens", None)
    serialized_context = json.dumps(
        {
            "student_profile": student_profile,
            "aptitude_questions": aptitude_questions,
            "aptitude_answers": aptitude_answers,
        },
        ensure_ascii=True,
        default=str,
    )
    tokens_used = actual_tokens or estimate_ai_usage_tokens(
        question="Generate student career guidance from profile and aptitude test",
        context=serialized_context,
        answer=answer,
    )

    add_ai_token_usage(current_user["tenant_id"], tokens_used, db)

    return {
        "answer": answer,
        "usage": {
            "tokens_used": tokens_used,
        },
        "status": {
            "mode": "career_guidance_with_aptitude",
            "message": "AI career guidance generated from student profile and aptitude test results.",
        },
    }


def generate_mock_student_profile(
    current_user: dict,
    db: Session,
):
    validate_usage_limit(current_user["tenant_id"], "ai_tokens", db)

    user_prompt = build_mock_student_profile_prompt()

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": MOCK_STUDENT_PROFILE_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.8,
        )
    except Exception:
        logger.exception(
            "OpenAI mock student profile generation failed",
            extra={
                "category": "openai_request_failure",
                "is_critical": True,
                "metadata": {
                    "mode": "mock_student_profile",
                },
            },
        )
        raise

    raw_content = response.choices[0].message.content or ""
    profile = _normalize_mock_student_profile(_extract_json_object(raw_content))
    actual_tokens = getattr(response.usage, "total_tokens", None)
    tokens_used = actual_tokens or estimate_ai_usage_tokens(
        question="Generate mock student profile for testing",
        context="student career evaluation form",
        answer=raw_content,
    )

    add_ai_token_usage(current_user["tenant_id"], tokens_used, db)

    return {
        "profile": profile,
        "usage": {
            "tokens_used": tokens_used,
        },
        "status": {
            "mode": "mock_student_profile",
            "message": "AI-generated sample student profile created for testing.",
        },
    }

# Student evaluation does not need Copilot streaming / repository retrieval.
# async def ask_ai_stream(...):
#     ...
