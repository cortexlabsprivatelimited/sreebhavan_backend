# Public endpoints (`/api/v1/public`)

These endpoints serve the user website (`apps/web`). They need no token. Every GET sends
`Cache-Control: public, max-age=300, s-maxage=300, stale-while-revalidate=3600`; hall availability uses
`max-age=30`. Only active or available records are returned. Lists are sorted by `sort`, then by name or date.
Every response uses the standard envelope (see the README's *Response format*). The **Returns** column shows `data`.

| Method | Path | Returns |
|---|---|---|
| GET | `/settings` | Same object as `GET /admin/settings` |
| GET | `/businesses/{slug}` | `{ id, slug, name, logo_url, about, whatsapp, phone, timings[] }` |
| GET | `/banners?business=<slug>` | `[{ id, business_id, image_url, title, subtitle, cta_text, cta_link, sort }]`. Without `business`, returns the home-page banners. |
| GET | `/menu/categories` | `[{ id, name, name_ml, slug, image_url, sort }]` |
| GET | `/menu/items?category=<slug>&special=true` | `[{ id, category_id, name, name_ml, slug, price, image_url, description, is_special, sort }]`. Available items in active categories. |
| GET | `/menu/cards` | `[{ id, title, file_url }]` |
| GET | `/rooms` | `[{ id, slug, name, price, capacity, amenities[], description, images[{ id, url, alt, sort }] }]` |
| GET | `/rooms/{slug}` | One room (`404` if inactive) |
| GET | `/hall` | `{ name, capacity_seating, capacity_floating, facilities[], rules, images[] }`. `404` until the hall is set up. |
| GET | `/hall/packages` | `[{ id, name, price, inclusions[], sort }]` |
| GET | `/hall/availability?month=YYYY-MM` | `[{ date, slot, status }]`. Never includes customer name, phone or notes. |
| GET | `/gallery/albums` | `[{ id, slug, title, category, cover_url, sort, image_count }]` |
| GET | `/gallery/albums/{slug}` | Album plus `images[{ id, url, thumb_url, alt, caption, sort }]` |
| GET | `/testimonials?business=<slug>` | `[{ id, name, text, rating, business_id, sort }]`. Shared testimonials (`business_id: null`) are always included. |
| GET | `/faqs?business=<slug>` | `[{ id, business_id, question, answer, sort }]`. General FAQs are always included. |
| GET | `/seo/{page_key}` | `{ page_key, title, description, og_image, keywords, noindex }`. Item keys contain a slash, e.g. `/seo/room/deluxe-ac-room`. `404` if not set. |
| GET | `/sitemap-data` | `{ rooms: [{ slug, updated_at }], menu_categories: [...], albums: [...] }` |
| POST | `/enquiries` | `201`, `data: { id, whatsapp_url }` |

## `POST /enquiries`

```json
{
  "type": "hall",
  "name": "Arun",
  "phone": "98470 12345",
  "email": null,
  "date_from": "2026-12-12",
  "date_to": null,
  "slot": "evening",
  "guests": 400,
  "event_type": "Wedding",
  "room_id": null,
  "room_slug": null,
  "message": "Need stage decoration too.",
  "website": "",
  "turnstile_token": null
}
```

- `hall` requires `date_from` and `slot`. `room` requires `room_id` or `room_slug`. `hotel` needs neither.
- `date_to` must be on or after `date_from`, and the dates cannot be in the past (IST).
- `website` is the honeypot. Render it hidden and leave it empty.
- `turnstile_token` is required only when the server sets `TURNSTILE_SECRET_KEY`.
- Room and hall enquiries use the `sreebhavanam` WhatsApp number. Hotel enquiries use `sreebhavan-veg-hotel`'s.

| Status | `errors[].field` | When |
|---|---|---|
| 201 | none | Saved. Open `data.whatsapp_url`. |
| 409 | field `slot` | That hall date and slot is already booked |
| 422 | the field(s) to fix, e.g. `date_from`, `slot`, `room_id`, `phone` | Bad input |
| 400 | field `turnstile_token` | Turnstile is enabled and the check failed |
| 429 | none | Too many enquiries from this IP. The `Retry-After` header gives the wait in seconds. |

Example `whatsapp_url` text: *Hi Sreebhavanam, I'd like to enquire about the Event Hall on 12-Dec-2026 (Evening)
for a Wedding, about 400 guests. Name: Arun, Phone: 9847012345.*
