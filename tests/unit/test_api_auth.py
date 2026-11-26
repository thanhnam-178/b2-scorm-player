from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from scorm_service.api_auth import router


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    app.include_router(router)

    return TestClient(app)


def mock_keycloak(userinfo):
    token = {"userinfo": userinfo}

    return patch(
        "scorm_service.api_auth.oauth.keycloak.authorize_access_token",
        new_callable=AsyncMock,
        return_value=token,
    )


def test_callback_success(client):
    person = SimpleNamespace(
        person_code="SV000002",
        person_type="staff",
    )

    with (
        mock_keycloak({"person_code": "SV000002"}),
        patch(
            "scorm_service.api_auth.phien_lam_viec"
        ) as mock_db,
    ):
        mock_db.return_value.__enter__.return_value.get.return_value = person
        mock_db.return_value.__enter__.return_value.scalar.return_value = (
            SimpleNamespace(role="teacher")
        )

        response = client.get(
            "/api/v1/auth/callback",
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/"

        session_response = client.get("/api/v1/auth/session")

    assert session_response.status_code == 200
    assert session_response.json() == {
        "authenticated": True,
        "person_code": "SV000002",
        "can_upload": True,
    }


def test_callback_person_code_not_found(client):
    with (
        mock_keycloak({"person_code": "SV999999"}),
        patch(
            "scorm_service.api_auth.phien_lam_viec"
        ) as mock_db,
    ):
        mock_db.return_value.__enter__.return_value.get.return_value = None

        response = client.get("/api/v1/auth/callback")

    assert response.status_code == 403


def test_callback_missing_person_code(client):
    with mock_keycloak({"sub": "keycloak-user"}):
        response = client.get("/api/v1/auth/callback")

    assert response.status_code == 403


def test_callback_keycloak_failure(client):
    with patch(
        "scorm_service.api_auth.oauth.keycloak.authorize_access_token",
        new_callable=AsyncMock,
        side_effect=Exception("Keycloak error"),
    ):
        response = client.get("/api/v1/auth/callback")

    assert response.status_code == 401


def test_logout_clears_session_and_redirects_to_keycloak(client):
    with client:
        client.get("/test-login/SV000002")

        response = client.get(
            "/api/v1/auth/logout",
            follow_redirects=False,
        )

        assert response.status_code == 302

        parsed_url = urlparse(response.headers["location"])
        params = parse_qs(parsed_url.query)

        assert parsed_url.scheme == "http"
        assert parsed_url.netloc == "localhost:8080"
        assert parsed_url.path == (
            "/realms/test/protocol/openid-connect/logout"
        )
        assert params["client_id"] == ["scorm-test"]
        assert params["post_logout_redirect_uri"] == [
            "http://localhost:8104/"
        ]

        assert "session" not in response.cookies


def test_logout_without_session(client):
    response = client.get(
        "/api/v1/auth/logout",
        follow_redirects=False,
    )

    assert response.status_code == 302


def test_callback_missing_userinfo(client):
    with (
        patch(
            "scorm_service.api_auth.oauth.keycloak.authorize_access_token",
            new_callable=AsyncMock,
            return_value={},
        ),
    ):
        response = client.get("/api/v1/auth/callback")

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "ID Token does not contain user information"
    )


def test_login_redirect_to_keycloak(client):
    expected_url = "http://localhost:8080/realms/test"

    with patch(
        "scorm_service.api_auth.oauth.keycloak.authorize_redirect",
        new_callable=AsyncMock,
        return_value=RedirectResponse(
            url=expected_url,
            status_code=302,
        ),
    ) as mock_redirect:
        response = client.get(
            "/api/v1/auth/login",
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["location"] == expected_url
    mock_redirect.assert_awaited_once()


def test_session_student_cannot_upload(client):
    person = SimpleNamespace(
        person_code="SV000002",
        person_type="student",
    )

    with (
        mock_keycloak({"person_code": "SV000002"}),
        patch(
            "scorm_service.api_auth.phien_lam_viec"
        ) as mock_db,
    ):
        mock_db.return_value.__enter__.return_value.get.return_value = person

        client.get(
            "/api/v1/auth/callback",
            follow_redirects=False,
        )

        response = client.get("/api/v1/auth/session")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "person_code": "SV000002",
        "can_upload": False,
    }


def test_session_unauthenticated_cannot_upload(client):
    response = client.get("/api/v1/auth/session")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": False,
        "person_code": None,
        "can_upload": False,
    }