from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CurrentUser, require_current_user
from app.schemas.career_assistant import (
    CareerAssistantResponse,
    CareerAssistantSessionInput,
    InterviewRequest,
    ResumeReviewRequest,
    SkillGapRequest,
)
from app.services.career_assistant_service import CareerAssistantService

router = APIRouter(prefix='/api/career-assistant', tags=['career assistant'])
service = CareerAssistantService()


@router.post('/chat', response_model=CareerAssistantResponse, status_code=status.HTTP_200_OK)
async def chat_with_assistant(
    payload: CareerAssistantSessionInput,
    current_user: CurrentUser = Depends(require_current_user),
):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail='Please provide a message to continue.')
    session_id = payload.session_id
    result = await service.chat(current_user, payload.message.strip(), session_id, payload.session_type)
    msg = result.get('message') if isinstance(result, dict) else None
    msg_id = msg.get('id') if isinstance(msg, dict) else None
    message_id = UUID(str(msg_id)) if msg_id else None
    sess_id = result.get('session_id') if isinstance(result, dict) else None
    parsed_session_id = UUID(str(sess_id)) if sess_id else None
    return CareerAssistantResponse(
        response=result['response'],
        session_id=parsed_session_id,
        message_id=message_id,
    )


@router.post('/resume-review')
async def resume_review(payload: ResumeReviewRequest | None = None, current_user: CurrentUser = Depends(require_current_user)):
    return await service.generate_resume_review(current_user)


@router.post('/skill-gap')
async def skill_gap(payload: SkillGapRequest | None = None, current_user: CurrentUser = Depends(require_current_user)):
    return await service.generate_skill_gap(current_user, (payload.model_dump(exclude_none=True) if payload else {}))


@router.post('/interview')
async def interview(payload: InterviewRequest | None = None, current_user: CurrentUser = Depends(require_current_user)):
    return await service.generate_interview(current_user, (payload.model_dump(exclude_none=True) if payload else {}))


@router.get('/sessions')
async def list_sessions(current_user: CurrentUser = Depends(require_current_user)):
    return await service.list_sessions(current_user)


@router.get('/sessions/{session_id}')
async def get_session(session_id: UUID, current_user: CurrentUser = Depends(require_current_user)):
    return await service.get_session(current_user, session_id)
