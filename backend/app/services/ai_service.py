from threading import Lock

import json
import logging
import re

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.request_context import update_request_context
from app.services.rag_service import retrieve_context
from app.services.repository_service import get_allowed_business_areas
from app.services.student_evaluation_ai_service import (
    ask_career_guidance,
    ask_career_guidance_with_aptitude,
    generate_aptitude_test,
    generate_mock_student_profile,
)
from app.services.summary_service import build_work_area_summary_payload
from app.services.subscription_service import add_ai_token_usage, validate_usage_limit
from app.services.token_usage_service import estimate_ai_usage_tokens

client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger = logging.getLogger(__name__)

_COPILOT_HISTORY_MAX_MESSAGES = 8
_COPILOT_HISTORY: dict[str, list[dict[str, str]]] = {}
_COPILOT_HISTORY_LOCK = Lock()


SYSTEM_PROMPT = """
You are Infomentica DSS Enterprise AI Copilot.

You help management teams of MSMEs make decisions using company documents.

Your role:
- Analyze repository-backed business documents and records
- Answer questions about specific indexed files, references, and business areas
- Identify delays, escalations, penalties, bottlenecks, and business exceptions
- Summarize executive concerns using only supplied context
- Recommend actions when the indexed evidence supports them

Always:
- Answer the current question directly in natural conversational language first
- Keep follow-up questions anchored to the recent conversation when references like "those", "the 6 POs", or "which ones" appear
- Do not start every answer with "Executive Summary"
- Use only provided context and recent conversation context supplied in the prompt
- If the user asks for a list, give the exact list backed by evidence
- Mention risks, business impact, and recommended actions only when the evidence supports them
- If information is insufficient, say so clearly
- If the user asks about a specific document or identifier, confirm whether it exists in the supplied context before discussing related records
- After the direct answer, include a short markdown section titled "Executive Summary"
"""



PORTFOLIO_RISK_SYSTEM_PROMPT = """
You generate portfolio-wide risk summaries from structured multi-business-area facts.

Your job:
- Cover every supplied business area with evidence
- Distinguish evidence-backed risks from evidence gaps
- Avoid turning a portfolio question into a contract-only answer unless contracts are the only area with evidence
- Say clearly when the current indexed evidence is concentrated in one business area

Always:
- Mention the business areas actually covered
- Mention exact entities, dates, values, statuses, thresholds, and identifiers when available
- Call out missing or thin evidence briefly instead of inventing risks
- Keep recommendations aligned to the evidence concentration and coverage gaps
- Answer the current question directly before the executive summary
- Do not broaden a follow-up question beyond its requested scope
"""


def _conversation_key(current_user: dict) -> str:
    return f"{current_user.get('tenant_id', '')}:{current_user.get('user_id', '')}"


def _get_recent_history(current_user: dict) -> list[dict[str, str]]:
    with _COPILOT_HISTORY_LOCK:
        return list(_COPILOT_HISTORY.get(_conversation_key(current_user), []))


def _append_history(current_user: dict, role: str, content: str) -> None:
    cleaned_content = " ".join(str(content or "").strip().split())
    if not cleaned_content:
        return

    with _COPILOT_HISTORY_LOCK:
        key = _conversation_key(current_user)
        history = list(_COPILOT_HISTORY.get(key, []))
        history.append({"role": role, "content": cleaned_content[:4000]})
        _COPILOT_HISTORY[key] = history[-_COPILOT_HISTORY_MAX_MESSAGES:]


def _format_history_for_prompt(history: list[dict[str, str]]) -> str:
    if not history:
        return "No prior conversation context."

    lines = []
    for item in history[-6:]:
        role = "User" if item.get("role") == "user" else "Assistant"
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"{role}: {content[:1200]}")
    return "\n".join(lines) if lines else "No prior conversation context."


def _normalize_match_text(value: str | None) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
        .split()
    )


def _canonicalize_token(token: str) -> str:
    token = str(token or "").strip().lower()
    if len(token) > 3 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _singularize_phrase(phrase: str) -> str:
    tokens = [_canonicalize_token(token) for token in _normalize_match_text(phrase).split()]
    return " ".join(token for token in tokens if token)


def _pluralize_token(token: str) -> str:
    if not token:
        return token
    if token.endswith("y") and len(token) > 1 and token[-2] not in "aeiou":
        return token[:-1] + "ies"
    if token.endswith("s"):
        return token
    return token + "s"


def _pluralize_phrase(phrase: str) -> str:
    tokens = [_canonicalize_token(token) for token in _normalize_match_text(phrase).split()]
    if not tokens:
        return ""
    tokens[-1] = _pluralize_token(tokens[-1])
    return " ".join(tokens)


def _business_area_aliases(area: str) -> set[str]:
    normalized_area = _normalize_match_text(area)
    if not normalized_area:
        return set()

    tokens = [token for token in normalized_area.split() if token]
    singular_area = _singularize_phrase(normalized_area)
    plural_area = _pluralize_phrase(normalized_area)
    aliases = {normalized_area, singular_area, plural_area}
    if len(tokens) > 1:
        acronym = "".join(token[0] for token in tokens)
        if acronym:
            aliases.add(acronym)
            aliases.add(f"{acronym}s")
    return {alias for alias in aliases if alias}


def _score_business_area_match(text: str, area: str) -> int:
    normalized_text = _normalize_match_text(text)
    if not normalized_text:
        return 0

    score = 0
    for alias in _business_area_aliases(area):
        if not alias:
            continue
        if re.search(rf"\b{re.escape(alias)}\b", normalized_text):
            score = max(score, 100 + len(alias))
    return score


def _is_explicit_portfolio_scope(query: str) -> bool:
    normalized = _normalize_match_text(query)
    if not normalized:
        return False

    phrases = [
        "all repositories",
        "all repository",
        "all business areas",
        "all business area",
        "across repositories",
        "across repository",
        "across business areas",
        "enterprise wide",
        "enterprise wide summary",
        "portfolio summary",
        "overall summary",
        "overall risk",
        "cross business area",
    ]
    return any(phrase in normalized for phrase in phrases)


def _looks_like_scoped_question(query: str) -> bool:
    normalized = _normalize_match_text(query)
    if not normalized:
        return False

    scoped_terms = [
        "summary",
        "summarize",
        "list",
        "show",
        "which",
        "what",
        "purchase order",
        "po",
        "contract",
        "invoice",
        "delivery note",
        "goods receipt",
        "grn",
        "service entry",
    ]
    return any(term in normalized for term in scoped_terms)


def _resolve_business_area_scope(
    query: str,
    current_user: dict,
    requested_business_area: str = "All",
    conversation_history: list[dict[str, str]] | None = None,
) -> dict:
    if requested_business_area and requested_business_area != "All":
        return {
            "business_area": requested_business_area,
            "needs_clarification": False,
            "assumption_note": None,
            "matched_areas": [requested_business_area],
        }

    normalized_query = _normalize_match_text(query)
    if not normalized_query:
        return {
            "business_area": "All",
            "needs_clarification": False,
            "assumption_note": None,
            "matched_areas": [],
        }

    allowed_business_areas = get_allowed_business_areas(current_user, "read")
    scored_direct_matches: list[tuple[int, str]] = []
    for area in allowed_business_areas:
        score = _score_business_area_match(normalized_query, area)
        if score > 0:
            scored_direct_matches.append((score, area))

    if scored_direct_matches:
        scored_direct_matches.sort(key=lambda item: (-item[0], str(item[1]).lower()))
        top_score = scored_direct_matches[0][0]
        top_matches = [area for score, area in scored_direct_matches if score == top_score]
        if len(top_matches) > 1:
            return {
                "business_area": "All",
                "needs_clarification": True,
                "assumption_note": None,
                "matched_areas": top_matches,
            }

        return {
            "business_area": top_matches[0],
            "needs_clarification": False,
            "assumption_note": None,
            "matched_areas": top_matches,
        }

    history = conversation_history or []
    if history and _is_follow_up_query(query, history):
        history_text = " ".join(item.get("content") or "" for item in history[-6:])
        scored_history_matches: list[tuple[int, str]] = []
        for area in allowed_business_areas:
            score = _score_business_area_match(history_text, area)
            if score > 0:
                scored_history_matches.append((score, area))

        if scored_history_matches:
            scored_history_matches.sort(key=lambda item: (-item[0], str(item[1]).lower()))
            top_score = scored_history_matches[0][0]
            top_matches = [area for score, area in scored_history_matches if score == top_score]
            if len(top_matches) == 1:
                return {
                    "business_area": top_matches[0],
                    "needs_clarification": False,
                    "assumption_note": f"Assumption: I treated this follow-up as referring to the {top_matches[0]} business area based on the recent conversation.",
                    "matched_areas": top_matches,
                }

    if _is_explicit_portfolio_scope(query):
        return {
            "business_area": "All",
            "needs_clarification": False,
            "assumption_note": "Assumption: I treated this as a cross-business-area question because the wording requested enterprise-wide scope.",
            "matched_areas": [],
        }

    if _looks_like_scoped_question(query):
        return {
            "business_area": "All",
            "needs_clarification": True,
            "assumption_note": None,
            "matched_areas": allowed_business_areas,
        }

    return {
        "business_area": "All",
        "needs_clarification": False,
        "assumption_note": "Assumption: I treated this as a broad enterprise question because no single business area was clearly identified.",
        "matched_areas": [],
    }


def _build_clarification_answer(query: str, matched_areas: list[str]) -> str:
    options = ", ".join(sorted({str(area) for area in matched_areas if str(area).strip()}))
    if not options:
        options = "contracts, purchase orders, vendor invoices, delivery notes, goods receipt notes, or service entry sheets"

    return (
        f'I need one clarification before I answer "{query}".\n\n'
        f"Please specify which business area you want me to use: {options}.\n\n"
        "## Executive Summary\n"
        "- The current question is ambiguous, so I am not assuming a business area.\n"
        "- Once you specify the area, I will answer within that scope only."
    )


def _is_follow_up_query(query: str, history: list[dict[str, str]]) -> bool:
    if not history:
        return False

    normalized = _normalize_match_text(query)
    if not normalized:
        return False

    follow_up_markers = [
        "those",
        "them",
        "that",
        "these",
        "which ones",
        "which one",
        "list them",
        "show them",
        "drill down",
        "more detail",
        "more details",
        "based on that",
        "from that",
        "the above",
        "the 6",
        "the six",
    ]
    if any(marker in normalized for marker in follow_up_markers):
        return True

    return len(normalized.split()) <= 12


def build_user_prompt(
    query: str,
    business_area: str,
    context: str,
    conversation_history: str,
    *,
    is_follow_up: bool,
) -> str:
    return f"""
CURRENT BUSINESS QUESTION:
{query}

BUSINESS AREA:
{business_area}

RECENT CONVERSATION CONTEXT:
{conversation_history}

DOCUMENT CONTEXT:
{context}

Instructions:
1. Answer the CURRENT BUSINESS QUESTION directly in natural conversational prose first.
2. This question is {"a follow-up to the recent conversation" if is_follow_up else "a standalone question unless the conversation context clearly helps"}.
3. Use RECENT CONVERSATION CONTEXT only to preserve continuity for follow-up references, counts, and previously discussed business scope.
4. Do not start with "Executive Summary".
5. Do not switch to unrelated business areas unless the user explicitly asks for cross-business-area coverage.
6. If the user asks for a list, return the exact evidence-backed list with identifiers, statuses, dates, values, or reasons when available.
7. If the available evidence does not support an exact count or list, say that clearly instead of generalizing.
8. After the direct answer, add a short markdown section titled "Executive Summary" with concise bullets covering findings, risks, and recommended actions only when evidence supports them.
9. Keep the answer and executive summary strictly within the requested business area unless the user explicitly asks for wider cross-business-area context.
"""


def build_portfolio_risk_prompt(
    query: str,
    work_area_payload: list[dict],
    conversation_history: str,
    *,
    is_follow_up: bool,
) -> str:
    area_requirements = [
        {
            "work_area": item.get("work_area"),
            "facts_count": item.get("facts_count") or 0,
            "rule_finding_count": item.get("rule_finding_count") or 0,
            "risk_labels": [
                finding.get("label")
                for finding in (item.get("rule_findings") or [])
                if finding.get("label")
            ][:10],
        }
        for item in work_area_payload
    ]
    return f"""
BUSINESS QUESTION:
{query}

RECENT CONVERSATION CONTEXT:
{conversation_history}

SCOPE:
All repositories and all business areas with indexed evidence.

STRUCTURED BUSINESS-AREA PAYLOAD:
{json.dumps(work_area_payload, ensure_ascii=True, default=str)}

BUSINESS AREAS THAT MUST BE COVERED:
{json.dumps(area_requirements, ensure_ascii=True, default=str)}

Instructions:
1. Answer the BUSINESS QUESTION directly in natural conversational prose first.
2. This question is {"a follow-up to the recent conversation" if is_follow_up else "a standalone enterprise question unless the conversation context clearly narrows it"}.
3. Use all supplied business-area payload, not just one dominant area.
4. Cover every business area that has facts or rule findings when the question is enterprise-wide.
5. Mention exact entities, record IDs, dates, values, statuses, and thresholds when available.
6. If a business area has no meaningful facts, say so briefly instead of inventing risks.
7. Do not generalize from contracts alone if other business areas have findings.
8. Use the BUSINESS AREAS THAT MUST BE COVERED list to ensure each business area with evidence is addressed separately when broad coverage is required.
9. If the indexed evidence is concentrated in one area, say that explicitly and explain that the current answer is evidence-limited, not enterprise-wide proof that other areas are risk-free.
10. After the direct answer, add a short markdown section titled "Executive Summary".
"""


# def build_career_guidance_prompt(student_profile: dict) -> str:
#     return f"""
# STUDENT PROFILE:
# {json.dumps(student_profile, ensure_ascii=True, indent=2, default=str)}

# Please provide:
# 1. Student profile snapshot
# 2. Academic strengths and weak areas
# 3. Recommended stream choice with reasoning
# 4. Best-fit career paths
# 5. Skills the student should build next
# 6. Short action plan for the next 6 to 12 months
# 7. Confidence note describing any limits in the input data
# """


# def build_aptitude_test_prompt(student_profile: dict) -> str:
#     return f"""
# STUDENT PROFILE:
# {json.dumps(student_profile, ensure_ascii=True, indent=2, default=str)}

# Return JSON only in this shape:
# {{
#   "title": "string",
#   "instructions": "string",
#   "questions": [
#     {{
#       "id": "q1",
#       "question": "string",
#       "dimension": "analytical | verbal | creativity | practical | social | leadership | focus | career_interest",
#       "options": [
#         {{
#           "id": "a",
#           "label": "string",
#           "signal": "string"
#         }}
#       ]
#     }}
#   ]
# }}

# Rules:
# - Create exactly 8 questions.
# - Each question must have exactly 4 options with ids "a", "b", "c", and "d".
# - "signal" should briefly describe what the option suggests about the student.
# - Keep the questionnaire suitable for the student's age.
# """


# def build_career_guidance_with_aptitude_prompt(
#     student_profile: dict,
#     aptitude_questions: list[dict],
#     aptitude_answers: list[dict],
# ) -> str:
#     return f"""
# STUDENT PROFILE:
# {json.dumps(student_profile, ensure_ascii=True, indent=2, default=str)}

# APTITUDE TEST QUESTIONS:
# {json.dumps(aptitude_questions, ensure_ascii=True, indent=2, default=str)}

# APTITUDE TEST ANSWERS:
# {json.dumps(aptitude_answers, ensure_ascii=True, indent=2, default=str)}

# Please provide:
# 1. Student profile snapshot
# 2. Aptitude findings from the test answers
# 3. Academic strengths and weak areas
# 4. Recommended stream choice with reasoning
# 5. Best-fit career paths
# 6. Skills the student should build next
# 7. Short action plan for the next 6 to 12 months
# 8. Confidence note describing any limits in the input data
# """


# def build_mock_student_profile_prompt() -> str:
#     return """
# Return JSON only in this shape:
# {
#   "board": "string",
#   "current_standard": 10,
#   "preferred_stream": "string",
#   "career_aspiration": "string",
#   "goal": "string",
#   "hobbies": ["string"],
#   "interests": ["string"],
#   "strengths": "string",
#   "improvement_areas": "string",
#   "academic_records": [
#     {
#       "standard": 1,
#       "subjects": [
#         {
#           "subject": "string",
#           "score": "string"
#         }
#       ]
#     }
#   ]
# }

# Rules:
# - Use one of these boards: CBSE, ICSE, State Board, IB, IGCSE.
# - Use one of these preferred streams: Science, Commerce, Arts / Humanities, Diploma / Vocational, Undecided.
# - academic_records must start from class 1 and continue without gaps up to current_standard.
# - score should be human-friendly like "87/100", "A", or "91 out of 100", but prefer numeric school marks.
# - Make the profile suitable for testing a student career recommendation flow.
# """


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


# def _normalize_aptitude_test(payload: dict) -> dict:
#     questions = payload.get("questions") or []
#     normalized_questions = []

#     for index, question in enumerate(questions[:8], start=1):
#         options = question.get("options") or []
#         normalized_options = []
#         for option_index, option in enumerate(options[:4]):
#             fallback_ids = ["a", "b", "c", "d"]
#             normalized_options.append(
#                 {
#                     "id": str(option.get("id") or fallback_ids[option_index]),
#                     "label": str(option.get("label") or "").strip(),
#                     "signal": str(option.get("signal") or "").strip(),
#                 }
#             )

#         if len(normalized_options) < 4:
#             continue

#         normalized_questions.append(
#             {
#                 "id": str(question.get("id") or f"q{index}"),
#                 "question": str(question.get("question") or "").strip(),
#                 "dimension": str(question.get("dimension") or "career_interest").strip(),
#                 "options": normalized_options,
#             }
#         )

#     if len(normalized_questions) != 8:
#         raise ValueError("AI aptitude test did not return exactly 8 usable questions")

#     return {
#         "title": str(payload.get("title") or "Student Aptitude Test").strip(),
#         "instructions": str(
#             payload.get("instructions")
#             or "Answer all questions honestly so the final recommendation can combine your profile and aptitude responses."
#         ).strip(),
#         "questions": normalized_questions,
#     }


# def _normalize_mock_student_profile(payload: dict) -> dict:
#     current_standard = int(payload.get("current_standard") or 10)
#     current_standard = min(max(current_standard, 1), 12)

#     academic_records = []
#     raw_records = payload.get("academic_records") or []
#     record_map = {}

#     for record in raw_records:
#         try:
#             standard = int(record.get("standard"))
#         except (TypeError, ValueError):
#             continue
#         if 1 <= standard <= current_standard:
#             record_map[standard] = record

#     for standard in range(1, current_standard + 1):
#         record = record_map.get(standard) or {"standard": standard, "subjects": []}
#         subjects = []
#         for subject in (record.get("subjects") or [])[:6]:
#             subject_name = str(subject.get("subject") or "").strip()
#             subject_score = str(subject.get("score") or "").strip()
#             if not subject_name and not subject_score:
#                 continue
#             subjects.append(
#                 {
#                     "subject": subject_name or "General Studies",
#                     "score": subject_score or "75/100",
#                 }
#             )

#         if not subjects:
#             subjects = [
#                 {"subject": "English", "score": "78/100"},
#                 {"subject": "Mathematics", "score": "81/100"},
#                 {"subject": "Science", "score": "79/100"},
#             ]

#         academic_records.append(
#             {
#                 "standard": standard,
#                 "subjects": subjects,
#             }
#         )

#     return {
#         "board": str(payload.get("board") or "CBSE").strip(),
#         "current_standard": current_standard,
#         "preferred_stream": str(payload.get("preferred_stream") or "Undecided").strip(),
#         "career_aspiration": str(payload.get("career_aspiration") or "Software Engineer").strip(),
#         "goal": str(payload.get("goal") or "Build a strong academic base and choose the right stream").strip(),
#         "hobbies": [str(item).strip() for item in (payload.get("hobbies") or []) if str(item).strip()],
#         "interests": [str(item).strip() for item in (payload.get("interests") or []) if str(item).strip()],
#         "strengths": str(payload.get("strengths") or "Curious, disciplined, and willing to learn").strip(),
#         "improvement_areas": str(
#             payload.get("improvement_areas") or "Needs more consistency and confidence in difficult subjects"
#         ).strip(),
#         "academic_records": academic_records,
#     }


def resolve_business_area_for_query(
    query: str,
    current_user: dict,
    requested_business_area: str = "All",
    conversation_history: list[dict[str, str]] | None = None,
) -> str:
    return _resolve_business_area_scope(
        query=query,
        current_user=current_user,
        requested_business_area=requested_business_area,
        conversation_history=conversation_history,
    )["business_area"]


def _has_specific_document_identifier(query: str) -> bool:
    normalized = " ".join(str(query or "").strip().split())
    if not normalized:
        return False

    return bool(
        re.search(
            r"\b([A-Z]{2,5}-\d{4}-\d{3,5}(?:-\d{3,5})?)\b",
            normalized,
            re.IGNORECASE,
        )
    )


def _should_use_portfolio_fact_mode(
    query: str,
    business_area: str,
    work_area_payload: list[dict],
    *,
    is_follow_up: bool = False,
) -> bool:
    if business_area and business_area != "All":
        return False

    if is_follow_up:
        return False

    if _has_specific_document_identifier(query):
        return False

    areas_with_evidence = [
        item
        for item in work_area_payload
        if item.get("facts_count") or item.get("rule_finding_count")
    ]
    return len(areas_with_evidence) > 1


def _is_broad_portfolio_risk_query(query: str, business_area: str) -> bool:
    if business_area and business_area != "All":
        return False

    normalized = " ".join(str(query or "").strip().lower().split())
    if not normalized or _has_specific_document_identifier(query):
        return False

    risk_terms = [
        "risk",
        "risks",
        "issue",
        "issues",
        "exposure",
        "exposures",
        "concern",
        "concerns",
    ]
    scope_terms = [
        "all documents",
        "my documents",
        "documents",
        "all repositories",
        "repository",
        "repositories",
        "portfolio",
        "across",
        "overall",
        "enterprise",
    ]

    has_risk_intent = any(term in normalized for term in risk_terms)
    has_portfolio_scope = any(term in normalized for term in scope_terms)
    has_broad_action = any(
        phrase in normalized
        for phrase in [
            "identify all",
            "list all",
            "what are the risks",
            "show all",
            "summarize risks",
            "identify risks",
        ]
    )
    return has_risk_intent and (has_portfolio_scope or has_broad_action)


def _get_portfolio_risk_payload(work_area_payload: list[dict]) -> list[dict]:
    return [
        item
        for item in work_area_payload
        if item.get("facts_count") or item.get("rule_finding_count")
    ]


def _build_portfolio_sources(work_area_payload: list[dict]) -> list[dict]:
    sources = []
    for item in work_area_payload:
        area_name = item.get("work_area")
        for fact in item.get("fact_samples") or []:
            if not fact.get("file_name"):
                continue
            sources.append(
                {
                    "file_name": fact.get("file_name"),
                    "document_id": fact.get("facts", {}).get("document_id"),
                    "repository_id": fact.get("facts", {}).get("repository_id"),
                    "business_area": area_name,
                    "metadata": {
                        "source_mode": "portfolio_fact_summary",
                        "record_id": fact.get("record_id"),
                    },
                    "preview": json.dumps(fact.get("facts") or {}, ensure_ascii=True, default=str)[:500],
                }
            )
            if len(sources) >= 20:
                return sources
    return sources

def ask_ai(
    query: str,
    current_user: dict,
    db: Session,
    business_area: str = "All",
):
    validate_usage_limit(current_user["tenant_id"], "ai_tokens", db)
    recent_history = _get_recent_history(current_user)
    is_follow_up = _is_follow_up_query(query, recent_history)
    scope_resolution = _resolve_business_area_scope(
        query=query,
        current_user=current_user,
        requested_business_area=business_area,
        conversation_history=recent_history,
    )
    resolved_business_area = scope_resolution["business_area"]
    update_request_context(business_area=resolved_business_area)
    formatted_history = _format_history_for_prompt(recent_history)

    if scope_resolution["needs_clarification"]:
        clarification_answer = _build_clarification_answer(
            query,
            scope_resolution.get("matched_areas") or [],
        )
        _append_history(current_user, "user", query)
        _append_history(current_user, "assistant", clarification_answer)
        return {
            "query": query,
            "business_area": "All",
            "answer": clarification_answer,
            "sources": [],
            "usage": {"tokens_used": 0},
            "status": {
                "mode": "needs_clarification",
                "source_count": 0,
                "message": "Copilot needs the user to clarify the target business area before answering.",
            },
        }

    work_area_payload = build_work_area_summary_payload(current_user, db)
    use_portfolio_mode = _should_use_portfolio_fact_mode(
        query,
        resolved_business_area,
        work_area_payload,
        is_follow_up=is_follow_up,
    ) or (
        not is_follow_up
        and _is_broad_portfolio_risk_query(query, resolved_business_area)
    )
    if use_portfolio_mode:
        relevant_payload = _get_portfolio_risk_payload(work_area_payload)

        if not relevant_payload:
            no_context_answer = (
                "I do not have enough indexed repository context to answer that across repositories right now.\n\n"
                "## Executive Summary\n"
                "- No indexed business-area facts are currently available for a portfolio-wide answer.\n"
                "- Run repository sync and confirm documents, facts, and rule findings are available."
            )
            _append_history(current_user, "user", query)
            _append_history(current_user, "assistant", no_context_answer)
            return {
                "query": query,
                "business_area": resolved_business_area,
                "answer": no_context_answer,
                "sources": [],
                "usage": {"tokens_used": 0},
                "status": {
                    "mode": "no_context",
                    "source_count": 0,
                    "message": "No indexed business-area facts are available for a portfolio risk summary.",
                },
            }

        user_prompt = build_portfolio_risk_prompt(
            query,
            relevant_payload,
            formatted_history,
            is_follow_up=is_follow_up,
        )

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": PORTFOLIO_RISK_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.2,
            )
        except Exception:
            logger.exception(
                "OpenAI portfolio summary failed for Copilot request",
                extra={
                    "category": "openai_request_failure",
                    "is_critical": True,
                    "metadata": {
                        "business_area": resolved_business_area,
                        "mode": "portfolio_fact_summary",
                    },
                },
            )
            raise

        answer = response.choices[0].message.content or ""
        actual_tokens = getattr(response.usage, "total_tokens", None)
        tokens_used = actual_tokens or estimate_ai_usage_tokens(
            question=query,
            context=json.dumps(relevant_payload, ensure_ascii=True, default=str),
            answer=answer,
        )
        add_ai_token_usage(current_user["tenant_id"], tokens_used, db)
        _append_history(current_user, "user", query)
        _append_history(current_user, "assistant", answer)

        return {
            "query": query,
            "business_area": resolved_business_area,
            "answer": answer,
            "sources": _build_portfolio_sources(relevant_payload),
            "usage": {
                "tokens_used": tokens_used,
            },
            "status": {
                "mode": "portfolio_fact_summary",
                "source_count": len(relevant_payload),
                "message": "AI response generated from structured facts across all indexed business areas.",
            },
        }

    rag_data = retrieve_context(
        query=query,
        current_user=current_user,
        db=db,
        top_k=8,
        business_area=resolved_business_area,
    )

    if not rag_data["sources"]:
        no_context_answer = (
            "I do not have enough indexed repository context to answer that yet.\n\n"
            "## Executive Summary\n"
            "- The tenant knowledge base is empty or inaccessible for this question.\n"
            "- Mount a repository, grant access, and run sync so documents are chunked and indexed before using Copilot."
        )
        _append_history(current_user, "user", query)
        _append_history(current_user, "assistant", no_context_answer)
        return {
            "query": query,
            "business_area": resolved_business_area,
            "answer": no_context_answer,
            "sources": [],
            "usage": {
                "tokens_used": 0,
            },
            "status": {
                "mode": "no_context",
                "source_count": 0,
                "message": (
                    "AI is available, but the tenant knowledge base is empty or inaccessible."
                ),
            },
        }

    user_prompt = build_user_prompt(
        query=query,
        business_area=resolved_business_area,
        context=rag_data["context"],
        conversation_history=formatted_history,
        is_follow_up=is_follow_up,
    )

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.2,
        )
    except Exception:
        logger.exception(
            "OpenAI chat completion failed for Copilot request",
            extra={
                "category": "openai_request_failure",
                "is_critical": True,
                "metadata": {
                    "business_area": resolved_business_area,
                },
            },
        )
        raise

    answer = response.choices[0].message.content or ""
    if scope_resolution.get("assumption_note"):
        answer = f"{scope_resolution['assumption_note']}\n\n{answer}"
    actual_tokens = getattr(response.usage, "total_tokens", None)
    tokens_used = actual_tokens or estimate_ai_usage_tokens(
        question=query,
        context=rag_data["context"],
        answer=answer,
    )

    add_ai_token_usage(current_user["tenant_id"], tokens_used, db)
    _append_history(current_user, "user", query)
    _append_history(current_user, "assistant", answer)

    return {
        "query": query,
        "business_area": resolved_business_area,
        "answer": answer,
        "sources": rag_data["sources"],
        "usage": {
            "tokens_used": tokens_used,
        },
        "status": {
            "mode": "source_backed",
            "source_count": len(rag_data["sources"]),
            "message": "AI response generated from indexed repository context.",
        },
    }


# def ask_career_guidance(
#     student_profile: dict,
#     current_user: dict,
#     db: Session,
# ):
#     validate_usage_limit(current_user["tenant_id"], "ai_tokens", db)

#     user_prompt = build_career_guidance_prompt(student_profile)

#     try:
#         response = client.chat.completions.create(
#             model=settings.OPENAI_MODEL,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": CAREER_GUIDANCE_SYSTEM_PROMPT,
#                 },
#                 {
#                     "role": "user",
#                     "content": user_prompt,
#                 },
#             ],
#             temperature=0.4,
#         )
#     except Exception:
#         logger.exception(
#             "OpenAI career guidance completion failed",
#             extra={
#                 "category": "openai_request_failure",
#                 "is_critical": True,
#                 "metadata": {
#                     "mode": "career_guidance",
#                 },
#             },
#         )
#         raise

#     answer = response.choices[0].message.content or ""
#     actual_tokens = getattr(response.usage, "total_tokens", None)
#     serialized_profile = json.dumps(student_profile, ensure_ascii=True, default=str)
#     tokens_used = actual_tokens or estimate_ai_usage_tokens(
#         question="Generate student career guidance",
#         context=serialized_profile,
#         answer=answer,
#     )

#     add_ai_token_usage(current_user["tenant_id"], tokens_used, db)

#     return {
#         "answer": answer,
#         "usage": {
#             "tokens_used": tokens_used,
#         },
#         "status": {
#             "mode": "career_guidance",
#             "message": "AI career guidance generated from student-submitted profile data.",
#         },
#     }


# def generate_aptitude_test(
#     student_profile: dict,
#     current_user: dict,
#     db: Session,
# ):
#     validate_usage_limit(current_user["tenant_id"], "ai_tokens", db)

#     user_prompt = build_aptitude_test_prompt(student_profile)

#     try:
#         response = client.chat.completions.create(
#             model=settings.OPENAI_MODEL,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": APTITUDE_TEST_SYSTEM_PROMPT,
#                 },
#                 {
#                     "role": "user",
#                     "content": user_prompt,
#                 },
#             ],
#             temperature=0.5,
#         )
#     except Exception:
#         logger.exception(
#             "OpenAI aptitude test generation failed",
#             extra={
#                 "category": "openai_request_failure",
#                 "is_critical": True,
#                 "metadata": {
#                     "mode": "aptitude_test_generation",
#                 },
#             },
#         )
#         raise

#     raw_content = response.choices[0].message.content or ""
#     parsed_test = _normalize_aptitude_test(_extract_json_object(raw_content))
#     actual_tokens = getattr(response.usage, "total_tokens", None)
#     serialized_profile = json.dumps(student_profile, ensure_ascii=True, default=str)
#     tokens_used = actual_tokens or estimate_ai_usage_tokens(
#         question="Generate student aptitude test",
#         context=serialized_profile,
#         answer=raw_content,
#     )

#     add_ai_token_usage(current_user["tenant_id"], tokens_used, db)

#     return {
#         "test": parsed_test,
#         "usage": {
#             "tokens_used": tokens_used,
#         },
#         "status": {
#             "mode": "aptitude_test",
#             "message": "AI aptitude test generated from student profile data.",
#         },
#     }


# def ask_career_guidance_with_aptitude(
#     student_profile: dict,
#     aptitude_questions: list[dict],
#     aptitude_answers: list[dict],
#     current_user: dict,
#     db: Session,
# ):
#     validate_usage_limit(current_user["tenant_id"], "ai_tokens", db)

#     user_prompt = build_career_guidance_with_aptitude_prompt(
#         student_profile=student_profile,
#         aptitude_questions=aptitude_questions,
#         aptitude_answers=aptitude_answers,
#     )

#     try:
#         response = client.chat.completions.create(
#             model=settings.OPENAI_MODEL,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": CAREER_GUIDANCE_SYSTEM_PROMPT,
#                 },
#                 {
#                     "role": "user",
#                     "content": user_prompt,
#                 },
#             ],
#             temperature=0.4,
#         )
#     except Exception:
#         logger.exception(
#             "OpenAI final career guidance with aptitude failed",
#             extra={
#                 "category": "openai_request_failure",
#                 "is_critical": True,
#                 "metadata": {
#                     "mode": "career_guidance_with_aptitude",
#                 },
#             },
#         )
#         raise

#     answer = response.choices[0].message.content or ""
#     actual_tokens = getattr(response.usage, "total_tokens", None)
#     serialized_context = json.dumps(
#         {
#             "student_profile": student_profile,
#             "aptitude_questions": aptitude_questions,
#             "aptitude_answers": aptitude_answers,
#         },
#         ensure_ascii=True,
#         default=str,
#     )
#     tokens_used = actual_tokens or estimate_ai_usage_tokens(
#         question="Generate student career guidance from profile and aptitude test",
#         context=serialized_context,
#         answer=answer,
#     )

#     add_ai_token_usage(current_user["tenant_id"], tokens_used, db)

#     return {
#         "answer": answer,
#         "usage": {
#             "tokens_used": tokens_used,
#         },
#         "status": {
#             "mode": "career_guidance_with_aptitude",
#             "message": "AI career guidance generated from student profile and aptitude test results.",
#         },
#     }


# def generate_mock_student_profile(
#     current_user: dict,
#     db: Session,
# ):
#     validate_usage_limit(current_user["tenant_id"], "ai_tokens", db)

#     user_prompt = build_mock_student_profile_prompt()

#     try:
#         response = client.chat.completions.create(
#             model=settings.OPENAI_MODEL,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": MOCK_STUDENT_PROFILE_SYSTEM_PROMPT,
#                 },
#                 {
#                     "role": "user",
#                     "content": user_prompt,
#                 },
#             ],
#             temperature=0.8,
#         )
#     except Exception:
#         logger.exception(
#             "OpenAI mock student profile generation failed",
#             extra={
#                 "category": "openai_request_failure",
#                 "is_critical": True,
#                 "metadata": {
#                     "mode": "mock_student_profile",
#                 },
#             },
#         )
#         raise

#     raw_content = response.choices[0].message.content or ""
#     profile = _normalize_mock_student_profile(_extract_json_object(raw_content))
#     actual_tokens = getattr(response.usage, "total_tokens", None)
#     tokens_used = actual_tokens or estimate_ai_usage_tokens(
#         question="Generate mock student profile for testing",
#         context="student career evaluation form",
#         answer=raw_content,
#     )

#     add_ai_token_usage(current_user["tenant_id"], tokens_used, db)

#     return {
#         "profile": profile,
#         "usage": {
#             "tokens_used": tokens_used,
#         },
#         "status": {
#             "mode": "mock_student_profile",
#             "message": "AI-generated sample student profile created for testing.",
#         },
#     }


async def ask_ai_stream(
    query: str,
    current_user: dict,
    db: Session,
    business_area: str = "All",
):
    validate_usage_limit(current_user["tenant_id"], "ai_tokens", db)
    recent_history = _get_recent_history(current_user)
    is_follow_up = _is_follow_up_query(query, recent_history)
    scope_resolution = _resolve_business_area_scope(
        query=query,
        current_user=current_user,
        requested_business_area=business_area,
        conversation_history=recent_history,
    )
    resolved_business_area = scope_resolution["business_area"]
    update_request_context(business_area=resolved_business_area)
    formatted_history = _format_history_for_prompt(recent_history)

    if scope_resolution["needs_clarification"]:
        clarification_answer = _build_clarification_answer(
            query,
            scope_resolution.get("matched_areas") or [],
        )
        clarification_status = {
            "type": "status",
            "mode": "needs_clarification",
            "source_count": 0,
            "message": "Copilot needs the user to clarify the target business area before answering.",
        }
        yield f"data: {json.dumps(clarification_status)}\n\n"
        yield f"data: {json.dumps({'type': 'token', 'content': clarification_answer})}\n\n"
        yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
        yield f"data: {json.dumps({'type': 'usage', 'tokens_used': 0})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        _append_history(current_user, "user", query)
        _append_history(current_user, "assistant", clarification_answer)
        return

    work_area_payload = build_work_area_summary_payload(current_user, db)
    use_portfolio_mode = _should_use_portfolio_fact_mode(
        query,
        resolved_business_area,
        work_area_payload,
        is_follow_up=is_follow_up,
    ) or (
        not is_follow_up
        and _is_broad_portfolio_risk_query(query, resolved_business_area)
    )
    if use_portfolio_mode:
        relevant_payload = _get_portfolio_risk_payload(work_area_payload)

        if not relevant_payload:
            no_context_status = {
                "type": "status",
                "mode": "no_context",
                "source_count": 0,
                "message": "No indexed business-area facts are available for a portfolio risk summary.",
            }
            no_context_answer = (
                "I do not have enough indexed repository context to answer that across repositories right now.\n\n"
                "## Executive Summary\n"
                "- No indexed business-area facts are currently available for a portfolio-wide answer.\n"
                "- Run repository sync and confirm documents, facts, and rule findings are available."
            )
            yield f"data: {json.dumps(no_context_status)}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': no_context_answer})}\n\n"
            yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
            yield f"data: {json.dumps({'type': 'usage', 'tokens_used': 0})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            _append_history(current_user, "user", query)
            _append_history(current_user, "assistant", no_context_answer)
            return

        user_prompt = build_portfolio_risk_prompt(
            query,
            relevant_payload,
            formatted_history,
            is_follow_up=is_follow_up,
        )

        try:
            collected_answer = ""
            if scope_resolution.get("assumption_note"):
                assumption_text = f"{scope_resolution['assumption_note']}\n\n"
                collected_answer += assumption_text
                yield f"data: {json.dumps({'type': 'token', 'content': assumption_text})}\n\n"
            stream = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": PORTFOLIO_RISK_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.2,
                stream=True,
            )

            for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    collected_answer += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            tokens_used = estimate_ai_usage_tokens(
                question=query,
                context=json.dumps(relevant_payload, ensure_ascii=True, default=str),
                answer=collected_answer,
            )
            add_ai_token_usage(current_user["tenant_id"], tokens_used, db)
            _append_history(current_user, "user", query)
            _append_history(current_user, "assistant", collected_answer)

            source_backed_status = {
                "type": "status",
                "mode": "portfolio_fact_summary",
                "source_count": len(relevant_payload),
                "message": "AI response generated from structured facts across all indexed business areas.",
            }
            yield f"data: {json.dumps(source_backed_status)}\n\n"
            yield f"data: {json.dumps({'type': 'sources', 'sources': _build_portfolio_sources(relevant_payload)})}\n\n"
            yield f"data: {json.dumps({'type': 'usage', 'tokens_used': tokens_used})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return
        except Exception as exc:
            logger.exception(
                "OpenAI streaming portfolio summary failed for Copilot request",
                extra={
                    "category": "openai_stream_failure",
                    "is_critical": True,
                    "metadata": {
                        "business_area": resolved_business_area,
                        "mode": "portfolio_fact_summary",
                    },
                },
            )
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
            return

    rag_data = retrieve_context(
        query=query,
        current_user=current_user,
        db=db,
        top_k=8,
        business_area=resolved_business_area,
    )

    if not rag_data["sources"]:
        no_context_status = {
            "type": "status",
            "mode": "no_context",
            "source_count": 0,
            "message": "AI is available, but the tenant knowledge base is empty or inaccessible.",
        }
        no_context_answer = (
            "I do not have enough indexed repository context to answer that yet.\n\n"
            "## Executive Summary\n"
            "- The tenant knowledge base is empty or inaccessible for this question.\n"
            "- Mount a repository, grant access, and run sync so documents are chunked and indexed before using Copilot."
        )
        yield (
            f"data: {json.dumps(no_context_status)}\n\n"
        )
        yield f"data: {json.dumps({'type': 'token', 'content': no_context_answer})}\n\n"
        yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
        yield f"data: {json.dumps({'type': 'usage', 'tokens_used': 0})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        _append_history(current_user, "user", query)
        _append_history(current_user, "assistant", no_context_answer)
        return

    user_prompt = build_user_prompt(
        query=query,
        business_area=resolved_business_area,
        context=rag_data["context"],
        conversation_history=formatted_history,
        is_follow_up=is_follow_up,
    )

    try:
        collected_answer = ""
        if scope_resolution.get("assumption_note"):
            assumption_text = f"{scope_resolution['assumption_note']}\n\n"
            collected_answer += assumption_text
            yield f"data: {json.dumps({'type': 'token', 'content': assumption_text})}\n\n"

        stream = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.2,
            stream=True,
        )

        for chunk in stream:
            token = chunk.choices[0].delta.content

            if token:
                collected_answer += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        tokens_used = estimate_ai_usage_tokens(
            question=query,
            context=rag_data["context"],
            answer=collected_answer,
        )
        add_ai_token_usage(current_user["tenant_id"], tokens_used, db)
        _append_history(current_user, "user", query)
        _append_history(current_user, "assistant", collected_answer)

        source_backed_status = {
            "type": "status",
            "mode": "source_backed",
            "source_count": len(rag_data["sources"]),
            "message": "AI response generated from indexed repository context.",
        }
        yield (
            f"data: {json.dumps(source_backed_status)}\n\n"
        )
        yield f"data: {json.dumps({'type': 'sources', 'sources': rag_data['sources']})}\n\n"
        yield f"data: {json.dumps({'type': 'usage', 'tokens_used': tokens_used})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as exc:
        logger.exception(
            "OpenAI streaming completion failed for Copilot request",
            extra={
                "category": "openai_stream_failure",
                "is_critical": True,
                "metadata": {
                    "business_area": resolved_business_area,
                },
            },
        )
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
