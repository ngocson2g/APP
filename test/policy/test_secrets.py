# tests/policy/test_secrets.py
import pytest
from security_app.policy.secrets import mask_secrets

@pytest.mark.parametrize("input_text, expected_output", [
    # Basic password masking
    ("User password=secret123 login", "User password=****** login"),
    ("Set passwd: my_password!", "Set passwd: ******"),
    ("connection_string = 'user:password@host'", "connection_string = 'user:******@host'"), # Inside quotes ignored by simple regex, maybe ok
    ("Password= very_secure ", "Password= ****** "), # Spaces around value
    ("PASSword: TopSecret", "PASSword: ******"), # Case insensitive key

    # API Key / Token masking
    ("export API_KEY=abc123def456ghi789", "export API_KEY=******"),
    ("Using token: xyz-789-abc.pqr_stu", "Using token: ******"), # Token with symbols
    ("secret = my-long-secret-key-12345678", "secret = ******"),
    ("apikey= short ", "apikey= short "), # Too short to be masked (less than 6 chars)
    ("apikey=longenough123", "apikey=******"), # Long enough

    # Bearer token masking
    ("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", "Authorization: Bearer ******"),
    ("bearer abcdef123456", "bearer ******"), # Case insensitive key

    # sshpass masking
    ("sshpass -p mysecret ssh user@host", "sshpass -p ****** ssh user@host"),
    ("SSHPASS -p 'complex$pass' command", "SSHPASS -p ****** command"), # Case insensitive, quoted ignored by regex

    # --password flag masking
    ("command --password mypass arg", "command --password ****** arg"),
    ("tool --user U --password=SECURE arg", "tool --user U --password=****** arg"), # With equals ignored by regex

    # No secrets
    ("This string has no secrets.", "This string has no secrets."),
    ("Check the api_key_description field.", "Check the api_key_description field."), # Key name without value

    # Edge cases
    ("", ""),
    (None, ""),
    ("password=", "password="), # Key without value
    ("token = ", "token = "), # Key without value
])
def test_mask_secrets(input_text, expected_output):
    """Tests the secret masking functionality."""
    assert mask_secrets(input_text) == expected_output

# You could add more complex cases, e.g., secrets spanning multiple lines
# if your regexes and function are designed to handle them.
# The current regexes seem line-based.
