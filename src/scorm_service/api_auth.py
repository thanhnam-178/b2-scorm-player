
"""Authentication endpoints using Keycloak OIDC."""

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from scorm_service.auth import (
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_ISSUER,
    KEYCLOAK_POST_LOGOUT_REDIRECT_URI,
    KEYCLOAK_REDIRECT_URI,
    oauth,
)
from scorm_service.db import phien_lam_viec
from scorm_service.models import Enrollment, Person

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.get("/login")
async def login(request: Request):
    """Redirect the user to Keycloak login."""
    return await oauth.keycloak.authorize_redirect(
        request,
        KEYCLOAK_REDIRECT_URI,
    )


@router.get("/callback")
async def callback(request: Request):
    """Handle the authorization response from Keycloak."""
    try:
        token = await oauth.keycloak.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail="Keycloak authentication failed",
        ) from exc

    userinfo = token.get("userinfo")

    if not userinfo:
        raise HTTPException(
            status_code=401,
            detail="ID Token does not contain user information",
        )

    person_code = userinfo.get("person_code")

    if not person_code:
        raise HTTPException(
            status_code=403,
            detail="Keycloak account is not linked to a person_code",
        )

    with phien_lam_viec() as s:
        person = s.get(Person, person_code)

        if person is None:
            raise HTTPException(
                status_code=403,
                detail="person_code does not exist in the system",
            )

    request.session["person_code"] = person_code
    request.session["authenticated"] = True

    return RedirectResponse(
        url="/",
        status_code=303,
    )

@router.get("/logout")
async def logout(request: Request):
    """Log out from SCORM Service and Keycloak."""
    request.session.clear()

    logout_endpoint = (
        f"{KEYCLOAK_ISSUER}/protocol/openid-connect/logout"
    )

    params = urlencode(
        {
            "client_id": KEYCLOAK_CLIENT_ID,
            "post_logout_redirect_uri": (
                KEYCLOAK_POST_LOGOUT_REDIRECT_URI
            ),
        }
    )

    return RedirectResponse(
        url=f"{logout_endpoint}?{params}",
        status_code=302,
    )


@router.get("/session")
async def get_session(request: Request):
    """Return the current authentication session."""
    person_code = request.session.get("person_code")

    if not request.session.get("authenticated") or not person_code:
        return {
            "authenticated": False,
            "person_code": None,
            "can_upload": False,
        }

    can_upload = False

    with phien_lam_viec() as s:
        person = s.get(Person, person_code)

        if person is not None and person.person_type == "staff":
            enrollment = s.scalar(
                select(Enrollment).where(
                    Enrollment.person_code == person_code,
                    Enrollment.role.in_(["teacher", "editingteacher"]),
                    Enrollment.status == "registered",
                ).limit(1)
            )
            can_upload = enrollment is not None

    return {
        "authenticated": True,
        "person_code": person_code,
        "can_upload": can_upload,
    }
