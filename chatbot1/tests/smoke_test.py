"""Basic smoke tests for the college website.

Run from the project root after installing requirements:
    python tests/smoke_test.py

This file is intentionally additive; it does not alter application behaviour.
"""

import sys

try:
    import app
except Exception as exc:
    print("Could not import app.py:", exc)
    sys.exit(2)

client = app.app.test_client()

routes = ["/", "/chat", "/study-material", "/robots.txt", "/sitemap.xml", "/manifest.json"]
failed = []
for route in routes:
    try:
        response = client.get(route)
        print(f"{route:20} {response.status_code}")
        if response.status_code >= 500:
            failed.append((route, response.status_code))
    except Exception as exc:
        failed.append((route, repr(exc)))

if failed:
    print("\nFAILED:")
    for item in failed:
        print(" -", item)
    sys.exit(1)

print("\nSmoke test passed for all checked GET routes.")
