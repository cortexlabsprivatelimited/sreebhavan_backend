# Sreebhavan API: Postman collection

This collection covers every endpoint of the FastAPI backend: 93 requests in 17 folders. Login runs once, and
the token is reused by every admin request. Requests that create records save the new IDs, so the next
requests (update, delete) work without copying anything by hand. Every response is checked against the
standard format (`success`, `status_code`, `message`, then `data` or `errors`).

| File | What it is |
|---|---|
| `Sreebhavan-API.postman_collection.json` | The collection |
| `Sreebhavan-Local.postman_environment.json` | Environment for `http://localhost:8000` |
| `Sreebhavan-Staging.postman_environment.json` | Template for a deployed server; fill in the URL |
| `sample.png` | Image used by *Uploads › Upload file* |

## 1. Import

1. Open Postman and click **Import**.
2. Drop in the collection and the environment file(s).
3. In the top-right environment picker, choose **Sreebhavan · Local** (or Staging).

## 2. Set the environment

Click the environment's eye icon, then **Edit**, and set:

| Variable | Example | Notes |
|---|---|---|
| `baseUrl` | `http://localhost:8000/api/v1` | Must end in `/api/v1` |
| `adminEmail` | `owner@example.com` | An admin created with `python -m app.cli create-owner` |
| `adminPassword` | your password | Stored as a secret |

Only these three go in the environment. Everything else (the token, saved IDs, dates) is kept in the
collection's own variables, which the scripts fill in.

## 3. Start the API

```bash
uv run uvicorn app.main:app --reload    # http://localhost:8000, Swagger at /docs
```

## 4. Use it

- **One request at a time:** run **1. Auth › Login** first, then any request. Requests that need an ID (for
  example *Update room*) skip themselves until the request that creates it (*Create room*) has run. The
  Postman console shows "Skipped: …" when that happens.
- **Everything at once:** right-click the collection, choose **Run collection**, then **Run**. The folders
  run in order:
  1. The admin folders create test records.
  2. **14. Public website** reads them back the way the website does.
  3. **15. Enquiries** works on the enquiry the public form just sent.
  4. **16. Cleanup** deletes everything the run created.
  5. **17. Sign out** logs out.

  Each run uses fresh names (`…-<runId>`), so you can run it again and again.

### Is a full run safe on real data?

The run is built to leave existing data as it was:

- **Edits to existing data copy the current values first.** *Save site settings*, *Update business* and *Save
  hall* send back exactly what the GET before them returned, so they change nothing. To really edit, replace
  the body; each request's description has an example.
- **Test records are clearly marked.** They use "Postman" in their names, and the test testimonial and SEO
  entry are inactive or `noindex`. Cleanup deletes every one of them by its saved ID.
- **Hall dates are far in the future.** The test booking and the test enquiry use random dates one to two
  years ahead.

Two parts are **not** safe on production:

- **Emails:** *Invite admin user* and *Send password reset* send real Supabase emails to a throwaway
  `postman-<runId>@example.com` address. *Forgot password* sends one to `adminEmail`.
- **The test enquiry stays:** the API cannot delete enquiries, so the one sent from **14. Public website**
  remains in the enquiry list.

Use Local or Staging for full runs.

## 5. Command line (CI)

The Postman CLI can run the same collection:

```bash
postman collection run postman/Sreebhavan-API.postman_collection.json \
  -e postman/Sreebhavan-Local.postman_environment.json \
  --env-var adminPassword='<password>' \
  --working-dir .
```

`--working-dir .` (run from the repo root) lets *Upload file* find `postman/sample.png`. Override any
environment value with `--env-var key=value`, and use `-i "7. Rooms"` to run a single folder.

## Collection variables

The scripts set these. You can also edit them under the collection's **Variables** tab.

| Variable | Set by | Meaning |
|---|---|---|
| `accessToken` | Login | Bearer token for every admin request (cleared by Logout) |
| `runId` | First request | Makes test slugs and emails unique |
| `month` | First request | Current month, `YYYY-MM` |
| `futureDate`, `enquiryDate` | First request | Random dates 1–2 years ahead |
| `businessId`, `hotelBusinessId` | List businesses | Sreebhavanam and the hotel |
| `bannerId`, `categoryId`, `itemId`, `cardId`, `roomId`, `roomImageId`, `packageId`, `hallImageId`, `bookingId`, `albumId`, `galleryImageId`, `testimonialId`, `faqId`, `seoId`, `userId`, `enquiryId` | The matching *Create* request | IDs for update and delete |
| `uploadUrl`, `uploadThumbUrl` | Upload file | Used by *Add photos (bulk)* |

To start over, clear the values in the **Variables** tab.

## Responses and errors

Results are in `data`, and paginated lists add `meta`:

```json
{ "success": true, "status_code": 200, "message": "Rooms fetched successfully", "data": [] }
```

Errors put the fields to fix in `errors`:

```json
{ "success": false, "status_code": 422, "message": "Validation failed",
  "errors": [{ "field": "name", "message": "Name is required." }] }
```

| Status | Meaning |
|---|---|
| 401 | Token missing or expired. Run **Login** again. |
| 403 | Staff calling an owner-only request (**13. Admin users**). |
| 409 | Conflict: duplicate slug, taken hall slot, a category that still has items. |
| 422 | Validation failed. See `errors`. |
| 429 | Too many enquiries from this IP. Wait `Retry-After` seconds. |

When a request fails, the Postman console prints the error message and fields.

## Keeping it up to date

The collection is generated from the FastAPI app:

```bash
uv run python scripts/build_postman.py
```

The build fails if an API endpoint is missing from the collection. When you add an endpoint, add it to the
request list in `scripts/build_postman.py`, then rebuild and re-import.
