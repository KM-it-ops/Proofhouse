"""Secret hygiene in one place.

Which environment values count as secrets, how they are blanked out of text before it is shown to a model or
written to a record, and the small environment a model-driven process gets. Every surface that runs commands
or shows their output (``loop``, ``referee``, ``app_platforms``) uses these, so a new surface inherits the
discipline by default instead of copying a regex.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable

SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|DATABASE_URL|CONNECTION_STRING|AUTH", re.IGNORECASE)
# Variables a model-driven or checked process may see; anything secret-named is dropped even if it is listed.
ENV_ALLOWLIST = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "TEMP", "TMP", "TMPDIR",
                 "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
                 "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "COMMONPROGRAMFILES", "NUMBER_OF_PROCESSORS",
                 "PROCESSOR_ARCHITECTURE", "OS", "USERNAME", "USER", "LOGNAME", "SHELL", "TERM", "LANG", "LC_ALL",
                 "LC_CTYPE", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")
REDACTED = "[redacted]"
MIN_SECRET_LENGTH = 6


def secret_values(extra_names: Iterable[str] = ()) -> list[str]:
    """Values of the named key variables plus every secret-named variable, longest first (so a shorter secret
    inside a longer one is blanked too)."""
    names = {name for name in extra_names if name}
    names |= {name for name in os.environ if SECRET_NAME.search(name)}
    values = {os.environ[name] for name in names if len(os.environ.get(name, "")) >= MIN_SECRET_LENGTH}
    return sorted(values, key=len, reverse=True)


def clean(text: str, secrets: list[str], limit: int) -> str:
    """``text`` with every secret value blanked, kept to its last ``limit`` characters when it is longer."""
    for value in secrets:
        text = text.replace(value, REDACTED)
    return text if len(text) <= limit else "…" + text[-limit:]


def minimal_env() -> dict[str, str]:
    """The environment for a process a model drives or a check runs: the allowlist only, minus secret-named
    variables, and with no bytecode caches written."""
    wanted = {name.upper() for name in ENV_ALLOWLIST}
    env = {key: value for key, value in os.environ.items() if key.upper() in wanted and not SECRET_NAME.search(key)}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env
