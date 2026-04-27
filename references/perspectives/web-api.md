# Web API Perspectives

domain: web-api

## Perspective 1: API Security Reviewer
Asks: What attack surfaces exist? What is the blast radius of a breach?
- Authentication mechanism (JWT, OAuth2, API keys, session cookies)
- Authorization model (RBAC, ABAC, resource-level permissions)
- Rate limiting and throttling configuration
- Input validation at API boundaries (body, query params, headers)
- CORS configuration and allowed origins
- API versioning strategy and deprecation process
- Webhook security (signature verification, replay protection)
- Secrets rotation policy and exposure surface

## Perspective 2: API Consumer / Integration Engineer
Asks: Can I integrate with this API without guessing?
- API documentation quality (OpenAPI/Swagger, examples, error codes)
- Error response format consistency across endpoints
- Pagination strategy (cursor, offset, keyset) and page size limits
- Idempotency support for write operations
- Backward compatibility policy and breaking change process
- SDK or client library generation and maintenance
- Request and response schema validation (JSON Schema, zod)
- Deprecation notice mechanism and migration guides

## Perspective 3: Platform Reliability Engineer
Asks: What happens at 3am when this API is under load?
- Request latency percentiles (p50, p95, p99) and SLOs
- Circuit breaker patterns for upstream dependencies
- Retry and backoff policies (client-side and server-side)
- Health check endpoints (liveness, readiness, startup)
- Graceful shutdown behavior (drain connections, finish requests)
- Connection pool configuration and resource limits
- Database query performance (N+1, missing indexes, slow queries)
- Async job processing and queue depth monitoring
