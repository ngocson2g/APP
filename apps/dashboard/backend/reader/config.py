# apps/dashboard/backend/reader/config.py
import os
import re

LOGS_BASE = os.environ.get("LOGS_DIR", "logs")

LIMITS_SERIES = 20

# Regex patterns
_RC_OK_LINE = re.compile(r"^RC=(?P<rc>-?\d+|None)\s*\|\s*OK=(?P<ok>True|False)\b")
_ID_LINE = re.compile(r"^ID\s*: (.+)$")
_TITLE_LINE = re.compile(r"^Title\s*: (.*)$")
_SEV_LINE = re.compile(r"^Severity\s*: (.*)$")
_DENIED_MARK = re.compile(r"^\s*DENIED\b", re.IGNORECASE)
_CMD_LINE = re.compile(r"^\$ (.+)$")

