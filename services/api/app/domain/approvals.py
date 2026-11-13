from app.core.exceptions import ConflictError, ForbiddenError  # noqa: F401
from app.db.models import Approval, SupportCase, User


def validate_resume(
    approval: Approval,
    case: SupportCase,
    reviewer: User,
    action: str,
) -> None:
    """Validate that human approval is valid to resume the workflow.

    Verifies:
    1. Reviewer has required role (support / supervisor).
    2. Case version matches approval.case_version.
    3. Action hash matches computed hash of requested action + params.

    Raises ConflictError on version/action hash mismatch.
    Raises ForbiddenError on unauthorized reviewer or rejected approval.

    Frozen signature per BUILD_PLAN.md §4. Implemented by Codex in task P3-C1.
    """
    raise NotImplementedError("TODO(core): Codex task P3-C1")
