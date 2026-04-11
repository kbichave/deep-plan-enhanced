# Coding Standards

Read this file at the start of every section implementation. These standards apply to Python projects. For non-Python projects, apply the equivalent idioms for the target language.

---

## Before Writing Any Code

1. **Define type signatures first.** Write the function/class headers with full annotations before the body. This forces you to think about the interface before the implementation.

2. **Define custom exceptions.** If this section introduces new error conditions, define specific exception classes at the top:
   ```python
   class PaymentProcessingError(Exception):
       """Raised when a payment cannot be processed."""
       def __init__(self, reason: str, payment_id: str) -> None:
           super().__init__(f"Payment {payment_id} failed: {reason}")
           self.payment_id = payment_id
   ```

3. **Write test function signatures first.** From the TDD stubs in `claude-plan-tdd.md`, write test function skeletons before implementing. This clarifies what "done" looks like.

4. **Identify security boundary inputs.** Any data arriving from: user input, external APIs, file system, database queries — must be validated at the boundary. Mark these explicitly with a comment before implementing.

---

## Type Safety

- Use `str | None` not `Optional[str]` (Python 3.10+)
- Use `Protocols` for structural typing (duck typing with type checking):
  ```python
  from typing import Protocol
  class Hashable(Protocol):
      def __hash__(self) -> int: ...
  ```
- Use `TypedDict` for structured data dicts:
  ```python
  from typing import TypedDict
  class UserRecord(TypedDict):
      id: str
      email: str
      created_at: datetime
  ```
- Use `Generic[T]` for reusable abstractions:
  ```python
  from typing import Generic, TypeVar
  T = TypeVar("T")
  class Result(Generic[T]):
      value: T | None
      error: str | None
  ```
- Use `@overload` for functions with variant return types
- Use type aliases for readability: `UserId = NewType("UserId", str)`

---

## Error Handling

- **Specific exception types only.** Never `except Exception` or bare `except:` unless you are at the top-level boundary AND you re-raise or log with full context.
- **Log what failed, what input caused it, and what state the system was in.** A stack trace alone is not enough.
- **Distinguish recoverable from invariant violations:**
  - Transient failures (network, timeout) → retry with backoff
  - Invalid input → raise with descriptive message
  - Invariant violations → fail fast, do not attempt recovery
- **Never catch and silence.** If you swallow an exception, you are hiding a bug.

```python
# Wrong
try:
    result = db.query(sql)
except Exception:
    return None

# Right
try:
    result = db.query(sql)
except DatabaseConnectionError as e:
    logger.error("DB query failed", extra={"sql": sql, "error": str(e)})
    raise
```

---

## Resource Management

- **Context managers for all acquisition:** file handles, DB connections, HTTP sessions, locks, temporary files.
- **Never rely on garbage collection** to release resources.
- **Connection pools must have bounded sizes and health checks.** An unbounded pool is a memory leak waiting to happen.

```python
# Always
with open(path) as f:
    data = f.read()

# Always
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

---

## Testing

- **Parametrize for input combinations:**
  ```python
  @pytest.mark.parametrize("email,valid", [
      ("user@example.com", True),
      ("not-an-email", False),
      ("", False),
      (None, False),
  ])
  def test_email_validation(email, valid):
      assert validate_email(email) == valid
  ```

- **Property-based testing for data transformations** (use Hypothesis):
  ```python
  from hypothesis import given, strategies as st
  @given(st.text())
  def test_sanitize_never_raises(input_text):
      result = sanitize(input_text)
      assert isinstance(result, str)
  ```

- **Fixtures in `conftest.py`**, not test-local globals. Shared state between tests is a bug waiting to happen.

- **Mock only at system boundaries** (external APIs, DB, file system). Never mock internal functions — that tests implementation, not behaviour.

- **Tests must run in < 100ms each.** If a test is slow, it is testing the wrong thing or needs a fixture.

---

## Security

- **Parameterized queries only.** Never f-string SQL or shell commands:
  ```python
  # Wrong
  cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
  # Right
  cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
  ```

- **Path validation:** always resolve and check containment:
  ```python
  safe_root = Path("/app/uploads").resolve()
  target = (safe_root / user_filename).resolve()
  if not target.is_relative_to(safe_root):
      raise ValueError(f"Path traversal attempt: {user_filename}")
  ```

- **subprocess with list form, never `shell=True`:**
  ```python
  # Wrong
  subprocess.run(f"git log {branch}", shell=True)
  # Right
  subprocess.run(["git", "log", branch], capture_output=True, check=True)
  ```

- **No hardcoded secrets.** Use environment variables or secret management. Secrets must never appear in source code, logs, or error messages.

- **Avoid `pickle` for untrusted data.** Use JSON or a schema-validated format.

---

## Code Style

- `str | None` not `Optional[str]`
- List comprehensions over manual loops for simple transforms
- `set` for membership checks (O(1) not O(n))
- `"".join(parts)` not `result += part` in loops
- `dict.get(key, default)` for safe dict access
- `deque` from `collections` for FIFO/LIFO queues (not list.pop(0))
- **Google-style docstrings on all public functions and classes:**
  ```python
  def process_payment(amount: Decimal, currency: str) -> PaymentResult:
      """Process a payment through the configured payment gateway.

      Args:
          amount: Payment amount. Must be positive.
          currency: ISO 4217 currency code (e.g. "USD", "EUR").

      Returns:
          PaymentResult with transaction_id on success.

      Raises:
          PaymentProcessingError: If the gateway rejects the payment.
          ValueError: If amount is not positive or currency is invalid.
      """
  ```

---

## Post-Section Quality Gates

Run these before calling `tracker.close()`. All must pass.

```bash
# 1. Ruff linting — zero violations required
ruff check --select ALL <changed-files>

# 2. Type checking — zero errors required
mypy --strict <changed-files>

# 3. Security scan — HIGH severity = must fix before close
bandit -r <changed-files>

# 4. Test coverage — new code must be ≥ 85% covered
pytest --cov=<module> --cov-report=term-missing <test-files>
```

**Severity handling:**
- Ruff violations: fix all before close (no `# noqa` without documented reason)
- mypy errors: fix all before close (no `# type: ignore` without documented reason)
- bandit HIGH: fix before close; MEDIUM: log in `impl-findings.md`; LOW: note only
- Coverage < 85%: add tests before close

**Language detection:** If the project is not Python, skip ruff/mypy/bandit and substitute the equivalent tools for the target language (e.g. `eslint`/`tsc`/`npm audit` for TypeScript). The principle — lint + type check + security scan + coverage — applies regardless of language.
