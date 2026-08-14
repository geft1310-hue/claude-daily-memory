"""Explicit-text-only bridge to Gemini through the official Google Gen AI SDK."""

from __future__ import annotations

import argparse
import sys

GEMINI_KEYRING_SERVICE = "claude-daily-memory"
GEMINI_KEYRING_ACCOUNT = "gemini-api-key"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send explicitly provided text to Gemini; this command never reads local files"
    )
    parser.add_argument("--project", help="Use Vertex AI in this Google Cloud project")
    parser.add_argument("--location", default="global")
    parser.add_argument("--model", default="gemini-3.5-flash")
    parser.add_argument("--text", required=True, help="Exact text to send")
    parser.add_argument("--confirm", action="store_true", help="Confirm the displayed text may be sent")
    args = parser.parse_args()

    if not args.confirm:
        print("Text that would be sent to Gemini:\n")
        print(args.text)
        print("\nNothing was sent. Repeat with --confirm after reviewing the text.")
        return 2

    try:
        import keyring
        from google import genai
    except ImportError:
        print("Install the optional Gemini dependencies first.", file=sys.stderr)
        return 1

    if args.project:
        try:
            import google.auth
        except ImportError:
            print("Install the optional Gemini dependencies first.", file=sys.stderr)
            return 1
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        client = genai.Client(
            vertexai=True,
            credentials=credentials,
            project=args.project,
            location=args.location,
        )
    else:
        api_key = keyring.get_password(GEMINI_KEYRING_SERVICE, GEMINI_KEYRING_ACCOUNT)
        if not api_key:
            print("Gemini API key is not set up in the system password storage.", file=sys.stderr)
            return 1
        client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=args.model, contents=args.text)
    print(response.text or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
