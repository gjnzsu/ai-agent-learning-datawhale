from typing import Annotated

from fastapi import FastAPI, Header, HTTPException

from kyc_review_agent.contracts import ReviewResult, ReviewTaskRequest
from kyc_review_agent.errors import CaseAccessDeniedError, CaseNotFoundError
from kyc_review_agent.runtime import ReviewRuntime

app = FastAPI(title="KYC Review Agent PoC")
runtime = ReviewRuntime.default()


@app.get("/v1/health/live")
def live() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/v1/health/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}


@app.post("/v1/review-tasks", response_model=ReviewResult)
def review_task(
    request: ReviewTaskRequest,
    actor_id: Annotated[str, Header(alias="X-Actor-Id")],
) -> ReviewResult:
    try:
        return runtime.review(request, actor_id)
    except CaseAccessDeniedError as exc:
        raise HTTPException(status_code=403, detail="Case access denied.") from exc
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Case not found.") from exc
