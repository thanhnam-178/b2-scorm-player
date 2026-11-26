import os

os.environ.setdefault(
    "KEYCLOAK_ISSUER",
    "http://localhost:8080/realms/test",
)
os.environ.setdefault(
    "KEYCLOAK_CLIENT_ID",
    "scorm-test",
)
os.environ.setdefault(
    "KEYCLOAK_CLIENT_SECRET",
    "test-secret",
)
os.environ.setdefault(
    "KEYCLOAK_REDIRECT_URI",
    "http://localhost:8004/api/v1/auth/callback",
)
os.environ.setdefault(
    "KEYCLOAK_POST_LOGOUT_REDIRECT_URI",
    "http://localhost:8104/",
)
os.environ.setdefault(
    "SESSION_SECRET",
    "test-session-secret-only-for-pytest",
)