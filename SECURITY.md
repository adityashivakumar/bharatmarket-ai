# Security policy

## Supported deployment model

BHARATMARKET AI's current Upstox integration is intended for **local development on the user's own machine**. The FastAPI endpoints do not currently implement user authentication or authorization. Do not expose port 8000 to the public internet or an untrusted LAN, and do not deploy this API as a public service until an authentication layer, authorization checks, HTTPS termination, rate limiting, and production secret management have been implemented and tested.

For local development, bind the backend to loopback only:

```powershell
python -m uvicorn api_server:app --host 127.0.0.1 --port 8000
```

Keep the frontend and backend on the same trusted machine. CORS is a browser policy, **not** an authentication or network-access control.

## Credentials

- Store `UPSTOX_ACCESS_TOKEN` only in the local, untracked `.env` file.
- Start from `.env.example`; never replace its placeholder with a real token in Git.
- Never put broker credentials in frontend code, `NEXT_PUBLIC_*` variables, screenshots, logs, issues, pull requests, or chat messages.
- If a credential is ever committed or disclosed, revoke/rotate it with the provider immediately. Removing it from the latest commit does not remove it from Git history.
- Keep local backups and generated tick files out of commits unless they have been reviewed and intentionally sanitized.

## Trading safety

The order ticket is paper-only and execution-disabled. Do not add broker order placement without a separate security review, explicit authorization, server-side risk controls, and end-to-end tests.

## Reporting

Do not publish secrets or personal data in a security report. Report suspected exposure privately to the repository owner and rotate affected credentials first.
