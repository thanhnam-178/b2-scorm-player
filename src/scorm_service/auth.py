
"""Keycloak OIDC authentication for SCORM Service."""

import os

from authlib.integrations.starlette_client import OAuth

KEYCLOAK_ISSUER = os.environ["KEYCLOAK_ISSUER"].rstrip("/")
KEYCLOAK_CLIENT_ID = os.environ["KEYCLOAK_CLIENT_ID"]
KEYCLOAK_CLIENT_SECRET = os.environ["KEYCLOAK_CLIENT_SECRET"]
KEYCLOAK_REDIRECT_URI = os.environ["KEYCLOAK_REDIRECT_URI"]
KEYCLOAK_POST_LOGOUT_REDIRECT_URI = os.environ[
    "KEYCLOAK_POST_LOGOUT_REDIRECT_URI"
]
KEYCLOAK_SCOPES = os.getenv(
    "KEYCLOAK_SCOPES", "openid profile email"
)

oauth = OAuth()

oauth.register(
    name="keycloak",
    client_id=KEYCLOAK_CLIENT_ID,
    client_secret=KEYCLOAK_CLIENT_SECRET,
    server_metadata_url=(
        f"{KEYCLOAK_ISSUER}/.well-known/openid-configuration"
    ),
    client_kwargs={
        "scope": KEYCLOAK_SCOPES,
        "code_challenge_method": "S256",
    },
)
