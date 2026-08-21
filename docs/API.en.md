# EvidentFolio API

[简体中文](API.md)

All business endpoints use `/api/v1`. Interactive OpenAPI documentation is available at `/api/docs`; the machine-readable schema is `/api/openapi.json`.

Successful responses use one envelope:

```json
{
  "success": true,
  "data": {},
  "message": null,
  "request_id": "request-uuid"
}
```

Errors contain a stable code, localized readable message, request ID, and optional field errors. Stack traces and server paths are never returned.

## Public endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/public/site` | Localized settings, categories, and tags |
| GET | `/public/projects` | Published project filtering, search, sorting, and pagination |
| GET | `/public/projects/{uuid}` | Published case study |
| GET | `/public/assets/{uuid}` | Authorized asset metadata |
| GET | `/public/assets/{uuid}/preview` | Safe Office/ZIP structured preview |
| GET | `/public/assets/{uuid}/content` | Inline content with HTTP Range support |
| GET | `/public/assets/{uuid}/download` | Download and count an asset |
| GET | `/public/assets/{uuid}/thumbnail` | Generated thumbnail |
| GET | `/public/resumes` | Public résumé versions only |
| GET | `/public/certificates` | Public credentials and honors |
| POST | `/analytics/events` | Non-blocking anonymous event batch |
| GET | `/setup/status` | Whether one-time initialization is open |
| POST | `/setup/initialize` | Create the first administrator; closes afterwards |

## Administration

Administration uses the HttpOnly `portfolio_session` cookie. Mutations also require the value of the readable `portfolio_csrf` cookie in `X-CSRF-Token`.

Main groups are `/admin/auth`, `/admin/projects`, `/admin/categories`, `/admin/tags`, `/admin/assets`, `/admin/resumes`, `/admin/certificates`, `/admin/settings`, `/admin/analytics`, `/admin/audit-logs`, and `/admin/ai`.

## UUID and authorization

External URLs and payloads never expose sequential database IDs. Public assets resolve stable UUIDs, while private assets return 404 without an administrator session even when their UUID is known. A UUID reduces enumeration; it does not replace authorization.

## Localization

Public read endpoints accept `locale=en` or infer English from `Accept-Language`. User-authored translations are selected server-side. Errors use `Accept-Language` and preserve stable language-independent error codes.

## Analytics meaning

Analytics stores pseudonymous behavioral signals. The high-attention score is an explainable ruleset based on events such as project dwell time, résumé views, downloads, demos, repositories, and repeat sessions. It does not identify a person or claim hiring intent.
