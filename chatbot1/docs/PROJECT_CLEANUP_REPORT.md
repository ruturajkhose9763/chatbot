# Project Cleanup Report

## Safety rule used
This cleanup copy does **not redesign or rewrite the existing application files**. The existing pages, routes, data files, JavaScript, CSS and Python source are preserved exactly so the current project behaviour is not intentionally changed.

## Verified
- `app.py` passes Python syntax compilation (`python -m py_compile app.py`).
- `static/script.js` passes Node syntax checking (`node --check static/script.js`).
- Main page: `templates/index.html` was not modified.
- Existing JSON/data files were not deleted.
- Existing routes and feature files were not deleted.

## Areas that need cleanup later (after a functional test)
1. `static/style.css` has repeated/stacked rules, especially the `ai-v2-*` and `login-v2-*` sections. These should be consolidated only after visual comparison.
2. `app.py` is large and contains multiple chatbot fallback layers. Refactoring should be done function-by-function with tests, not by deleting blocks based only on size.
3. `static/script.js` contains several independent UI systems. These can be modularised without changing behaviour.
4. Hard-coded service credentials appear in `app.py`. For production, move credentials to environment variables and rotate any credentials that were exposed in source.
5. The README contains example/default login credentials. Replace them before publishing the repository.
6. Add automated smoke tests for `/`, `/chat`, `/study-material`, authentication and the major admin POST routes.
7. Add a production configuration checklist for `SECRET_KEY`, `SITE_URL`, database, Cloudinary and deployment variables.

## Suggested next safe phase
- Make a byte-for-byte backup of the current working version.
- Refactor one file at a time.
- Run syntax checks after every change.
- Run Flask test-client smoke tests after every backend change.
- Compare the rendered home page before/after each frontend cleanup.
- Keep every existing route and JSON key unless a feature is intentionally retired.
