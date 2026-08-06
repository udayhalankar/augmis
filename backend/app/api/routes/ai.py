from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.request_context import update_request_context
from app.core.security import require_saas_access
from app.services.audit_service import create_audit_log
from app.services.ai_service import (
    ask_ai,
    ask_ai_stream,
)
from app.services.student_evaluation_ai_service import (
    ask_career_guidance,
    ask_career_guidance_with_aptitude,
    generate_aptitude_test,
    generate_mock_student_profile,
)

router = APIRouter(prefix="/ai", tags=["AI"])


class AskRequest(BaseModel):
    query: str
    business_area: str = "All"


class SubjectScore(BaseModel):
    subject: str
    score: str


class StandardRecord(BaseModel):
    standard: int
    subjects: list[SubjectScore] = []


class CareerGuidanceRequest(BaseModel):
    board: str
    current_standard: int
    preferred_stream: str
    career_aspiration: str
    goal: str
    hobbies: list[str] = []
    interests: list[str] = []
    strengths: str = ""
    improvement_areas: str = ""
    academic_records: list[StandardRecord] = []


class AptitudeOptionResponse(BaseModel):
    id: str
    label: str
    signal: str = ""


class AptitudeQuestionResponse(BaseModel):
    id: str
    question: str
    dimension: str
    options: list[AptitudeOptionResponse]


class AptitudeAnswerRequest(BaseModel):
    question_id: str
    selected_option_id: str
    selected_option_label: str
    signal: str = ""


class CareerGuidanceWithAptitudeRequest(CareerGuidanceRequest):
    aptitude_questions: list[AptitudeQuestionResponse]
    aptitude_answers: list[AptitudeAnswerRequest]


@router.post("/ask")
def ask(
    payload: AskRequest,
    request: Request,
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    update_request_context(
        route=request.url.path,
        method=request.method,
        business_area=payload.business_area,
        component="copilot",
    )
    result = ask_ai(
        query=payload.query,
        current_user=current_user,
        db=db,
        business_area=payload.business_area,
    )

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="AI_ASK",
        event_category="AI",
        description="User asked AI Copilot question",
        resource_type="copilot",
        resource_id=None,
        request=request,
        metadata={
            "question_preview": payload.query[:300],
            "business_area": payload.business_area,
            "tokens_used": result.get("usage", {}).get("tokens_used"),
            "sources_count": len(result.get("sources", [])),
        },
    )

    return result


@router.post("/career-guidance")
def career_guidance(
    payload: CareerGuidanceRequest,
    request: Request,
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    update_request_context(
        route=request.url.path,
        method=request.method,
        component="career_guidance",
    )

    result = ask_career_guidance(
        student_profile=payload.model_dump(),
        current_user=current_user,
        db=db,
    )

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="AI_CAREER_GUIDANCE",
        event_category="AI",
        description="User generated AI career guidance for a student profile",
        resource_type="career_guidance",
        resource_id=None,
        request=request,
        metadata={
            "board": payload.board,
            "current_standard": payload.current_standard,
            "preferred_stream": payload.preferred_stream,
            "tokens_used": result.get("usage", {}).get("tokens_used"),
        },
    )

    return result


@router.post("/career-guidance/aptitude-test")
def career_guidance_aptitude_test(
    payload: CareerGuidanceRequest,
    request: Request,
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    update_request_context(
        route=request.url.path,
        method=request.method,
        component="career_guidance_aptitude_test",
    )

    result = generate_aptitude_test(
        student_profile=payload.model_dump(),
        current_user=current_user,
        db=db,
    )

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="AI_APTITUDE_TEST_GENERATED",
        event_category="AI",
        description="User generated an AI aptitude test for a student profile",
        resource_type="career_guidance",
        resource_id=None,
        request=request,
        metadata={
            "board": payload.board,
            "current_standard": payload.current_standard,
            "preferred_stream": payload.preferred_stream,
            "tokens_used": result.get("usage", {}).get("tokens_used"),
        },
    )

    return result


@router.post("/career-guidance/mock-profile")
def career_guidance_mock_profile(
    request: Request,
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    update_request_context(
        route=request.url.path,
        method=request.method,
        component="career_guidance_mock_profile",
    )

    result = generate_mock_student_profile(
        current_user=current_user,
        db=db,
    )

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="AI_MOCK_STUDENT_PROFILE_GENERATED",
        event_category="AI",
        description="User generated an AI sample student profile for testing",
        resource_type="career_guidance",
        resource_id=None,
        request=request,
        metadata={
            "tokens_used": result.get("usage", {}).get("tokens_used"),
        },
    )

    return result


@router.post("/career-guidance/final")
def career_guidance_final(
    payload: CareerGuidanceWithAptitudeRequest,
    request: Request,
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    update_request_context(
        route=request.url.path,
        method=request.method,
        component="career_guidance_final",
    )

    student_profile = {
        "board": payload.board,
        "current_standard": payload.current_standard,
        "preferred_stream": payload.preferred_stream,
        "career_aspiration": payload.career_aspiration,
        "goal": payload.goal,
        "hobbies": payload.hobbies,
        "interests": payload.interests,
        "strengths": payload.strengths,
        "improvement_areas": payload.improvement_areas,
        "academic_records": [record.model_dump() for record in payload.academic_records],
    }

    result = ask_career_guidance_with_aptitude(
        student_profile=student_profile,
        aptitude_questions=[question.model_dump() for question in payload.aptitude_questions],
        aptitude_answers=[answer.model_dump() for answer in payload.aptitude_answers],
        current_user=current_user,
        db=db,
    )

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="AI_CAREER_GUIDANCE_FINAL",
        event_category="AI",
        description="User generated final AI career guidance using student profile and aptitude test",
        resource_type="career_guidance",
        resource_id=None,
        request=request,
        metadata={
            "board": payload.board,
            "current_standard": payload.current_standard,
            "preferred_stream": payload.preferred_stream,
            "aptitude_answers_count": len(payload.aptitude_answers),
            "tokens_used": result.get("usage", {}).get("tokens_used"),
        },
    )

    return result


@router.post("/ask/stream")
async def ask_stream(
    payload: AskRequest,
    request: Request,
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    update_request_context(
        route=request.url.path,
        method=request.method,
        business_area=payload.business_area,
        component="copilot_stream",
    )
    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="AI_STREAM_STARTED",
        event_category="AI",
        description="User started AI streaming response",
        resource_type="copilot",
        resource_id=None,
        request=request,
        metadata={
            "question_preview": payload.query[:300],
            "business_area": payload.business_area,
        },
    )

    generator = ask_ai_stream(
        query=payload.query,
        current_user=current_user,
        db=db,
        business_area=payload.business_area,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
    )
