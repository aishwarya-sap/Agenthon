"""Startup launcher: bridge a bound CF service's AI Core credentials into AICORE_* env vars.

Why this exists
---------------
On classic Cloud Foundry the SAP Cloud SDK resolves AI Core credentials from mounted secret
files (App Foundation / Kyma only) or from the AICORE_* environment variables — it does NOT
read VCAP_SERVICES. So binding a service (user-provided or managed) lands the credentials in
VCAP_SERVICES where nothing consumes them. This launcher closes that gap generically: it copies
the credentials from the bound service into AICORE_* env vars, then hands off to the real entry
point (app/main.py) unchanged.

It is model/provider-agnostic and side-effect-free off-platform:
- If AICORE_CLIENT_ID is already set (local `export`, or `cf set-env`), it is respected and no
  mapping happens.
- If there is no VCAP_SERVICES (running locally / not bound), it is a no-op.

Wire it as the process entry point instead of app/main.py, e.g. in the Procfile:
    web: python app/_boot.py
main.py itself needs no change.
"""

import json
import os
import sys

# The keys the SAP Cloud SDK's set_aicore_config() consumes. Store them under these exact
# names in the bound service's credentials JSON so the mapping is a straight copy.
_AICORE_KEYS = (
    "AICORE_CLIENT_ID",
    "AICORE_CLIENT_SECRET",
    "AICORE_AUTH_URL",
    "AICORE_BASE_URL",
    "AICORE_RESOURCE_GROUP",  # optional; defaults to "default" in the SDK
)


def apply_vcap_aicore(environ=os.environ):
    """Map a bound service's AI Core credentials from VCAP_SERVICES into AICORE_* env vars.

    No-op when AICORE_CLIENT_ID is already present (an explicit export / cf set-env wins) or
    when VCAP_SERVICES is absent or unparseable. Picks the first bound service whose
    credentials carry AICORE_CLIENT_ID, so it works for a user-provided service or a managed
    one regardless of the binding's name.
    """
    if environ.get("AICORE_CLIENT_ID"):
        return
    raw = environ.get("VCAP_SERVICES")
    if not raw:
        return
    try:
        services = json.loads(raw)
    except (ValueError, TypeError):
        return
    for bindings in services.values():
        for binding in bindings:
            creds = (binding or {}).get("credentials") or {}
            if "AICORE_CLIENT_ID" in creds:
                for key in _AICORE_KEYS:
                    value = creds.get(key)
                    if value and not environ.get(key):
                        environ[key] = value
                return


def main():
    apply_vcap_aicore()
    entry = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    argv = [sys.executable, entry, *sys.argv[1:]]
    if os.name == "posix":
        # Replace this process (no extra memory on a tight org); the updated environment is
        # inherited, and `python app/main.py` runs exactly as it would directly.
        os.execv(sys.executable, argv)
    else:
        import subprocess

        raise SystemExit(subprocess.call(argv))


if __name__ == "__main__":
    main()
