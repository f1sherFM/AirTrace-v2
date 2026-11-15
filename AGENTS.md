# AirTrace Project Guidelines & Agent Rules

## Stack & Architecture
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, async/await.
- **Frontend**: Jinja2 SSR + Tailwind CSS + Vanilla JS (progressive hydration).
- **Domains**: Pure business logic in `domain/` (advisory, confidence scoring) - deterministic, zero side-effects.
- **Data & Config**: `config/cities.yaml` (75+ Russian cities, UTF-8, lowercased keys).

---

## Code Review Protocol (`/code-review`)
When the user requests a code review or invokes `/code-review`:
1. **Tooling**: Use the installed CodeRabbit plugin (`code-review` skill) and the `code-reviewer` subagent.
2. **Configuration**: Follow repository rules defined in [`.coderabbit.yaml`](.coderabbit.yaml).
3. **Severities**: Categorize and preserve findings by standard levels:
   - 🔴 **Critical**: Security vulnerabilities (XSS, injections, leaked secrets), race conditions, unhandled exceptions crashing the server.
   - 🟡 **Major / Important**: Performance bottlenecks (blocking IO in async paths), architectural leaks, breaking API changes.
   - 🟢 **Minor / Nits**: Tech debt, style inconsistencies, missing edge-case unit tests.
4. **Safety & Verification**: Always verify suggested fixes with automated tests (`pytest`) before committing.

---

## Code Standards
- **XSS Prevention**: Never insert unsanitized user/API/storage data into `innerHTML`. Use `escapeHtml()` or `textContent`.
- **FastAPI Routes**: Keep route handlers lightweight; delegate queries to `application/queries/` and domain logic to `domain/`.
- **Error Handling**: Never use bare `except: pass`. Always log exceptions with `logger.debug(..., exc_info=True)`.
