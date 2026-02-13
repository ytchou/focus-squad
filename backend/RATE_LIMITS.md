# Rate Limit Reference

Rate limits protect against abuse and ensure fair usage across all users.

## Tier Definitions

| Tier | Limit | Use Case | Examples |
|------|-------|----------|----------|
| 5/min | Expensive/abuse-prone | Currency transfers, destructive ops | Credit gift, essence gift, account delete |
| 10/min | Write operations | State-changing writes | Purchase, rating submit, session cancel |
| 15/min | Profile updates | Low-risk writes | User profile, room layout, interests |
| 30/min | Moderate writes | High-frequency writes | Messages, reactions, flags |
| 60/min | Standard reads | Most GET endpoints | Default for unannotated endpoints |

## Current Endpoint Limits

### Essence & Shop (`/api/v1/essence`)
| Endpoint | Method | Limit | Rationale |
|----------|--------|-------|-----------|
| `/buy` | POST | 10/min | Purchase operation |
| `/gift` | POST | 5/min | Currency transfer |

### Users (`/api/v1/users`)
| Endpoint | Method | Limit | Rationale |
|----------|--------|-------|-----------|
| `/me` | PATCH | 15/min | Profile update |
| `/me` | DELETE | 5/min | Destructive operation |
| `/me/interests` | PUT | 15/min | Profile update |

### Sessions (`/api/v1/sessions`)
| Endpoint | Method | Limit | Rationale |
|----------|--------|-------|-----------|
| `/quick-match` | POST | 5/min | Credit-consuming action |
| `/create-private` | POST | 5/min | Credit-consuming action |
| `/invitations` | GET | 60/min | Standard read |
| `/{id}/cancel` | POST | 10/min | State change |
| `/{id}/rate` | POST | 10/min | Write operation |
| `/{id}/rate/skip` | POST | 10/min | Write operation |
| `/{id}/invite/respond` | POST | 10/min | State change |

### Room (`/api/v1/room`)
| Endpoint | Method | Limit | Rationale |
|----------|--------|-------|-----------|
| `/layout` | PUT | 15/min | Profile update |

### Credits (`/api/v1/credits`)
| Endpoint | Method | Limit | Rationale |
|----------|--------|-------|-----------|
| `/gift` | POST | 5/min | Currency transfer |

## Adding New Endpoints

When adding a new endpoint, apply the appropriate tier:

```python
from app.core.rate_limit import limiter

@router.post("/new-endpoint")
@limiter.limit("10/minute")  # Choose appropriate tier
async def new_endpoint(request: Request, ...):
    ...
```

**Important**: The `request: Request` parameter is required for rate limiting to work.

## Rate Limit Response

When a client exceeds the rate limit, they receive:

```json
{
  "detail": "Rate limit exceeded: 5 per 1 minute"
}
```

HTTP Status: `429 Too Many Requests`

Headers include:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in window
- `X-RateLimit-Reset`: Unix timestamp when limit resets
