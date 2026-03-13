from fastapi import APIRouter, Request, status

from api.dependencies import SessionDep
from api.models.feedback import Feedback
from api.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    data: FeedbackCreate,
    request: Request,
    db: SessionDep,
) -> FeedbackResponse:
    raw_ua = request.headers.get("user-agent")
    user_agent = raw_ua[:500] if raw_ua else None

    feedback = Feedback(
        message=data.message,
        page_url=data.page_url,
        user_agent=user_agent,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)
