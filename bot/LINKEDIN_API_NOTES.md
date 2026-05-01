# LinkedIn API — Implementation Notes

## Status: Solved via Posts API + Little Text Format (LTF)

---

## The Problem

The original implementation used the **UGC API** (`/v2/ugcPosts`). Plain `@mentions` in that
API's text field are treated as literal strings — LinkedIn does not resolve them into tagged
profile links.

## The Solution — Little Text Format (LTF)

LinkedIn's newer **Posts API** (`/rest/posts`) supports **Little Text Format**, a markup
syntax that embeds real mentions and hashtags directly in the commentary string.

Reference: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/little-text-format

### Mention syntax

```
@[DisplayName](urn:li:organization:12345)   ← company / school
@[DisplayName](urn:li:person:abcXYZ)        ← person
```

### Hashtag syntax

```
#hashtag                                     ← plain, works natively
{hashtag|\#|MyTag}                           ← explicit LTF template
```

### Full Posts API payload

```json
{
  "author": "urn:li:person:YOUR_PERSON_URN",
  "commentary": "Just finished Week 2 at @[Ironhack](urn:li:organization:XXXXX). Amazing. #AI #Bootcamp",
  "visibility": "PUBLIC",
  "distribution": { "feedDistribution": "MAIN_FEED" },
  "lifecycleState": "PUBLISHED"
}
```

Headers required:
```
Authorization: Bearer <access_token>
LinkedIn-Version: 202502
X-Restli-Protocol-Version: 2.0.0
Content-Type: application/json
```

---

## How ICARUS Uses It

`linkedin_client.py` now uses the Posts API with LTF. A `KNOWN_MENTIONS` dict maps
lowercase names to their LinkedIn URNs. Before publishing, `_apply_mentions()` scans
the post text for `@Name` patterns and replaces them with the correct LTF syntax.

Claude is instructed to write `@Ironhack` in posts — ICARUS converts it automatically.

### Adding a new mention target

1. Find the LinkedIn numeric ID for the person or company:
   - Go to their LinkedIn page
   - View page source → search for `organizationUrn` or `fsd_company`
   - The numeric ID appears in the URL or source as e.g. `2414183`

2. Add to `KNOWN_MENTIONS` in `linkedin_client.py`:
   ```python
   KNOWN_MENTIONS = {
       "ironhack": "urn:li:organization:REPLACE_WITH_ID",
   }
   ```

---

## What Still Requires Marketing API

Mentioning arbitrary people or companies by name (without pre-knowing their URN) requires
a **name-to-URN search**, which is part of the Marketing Developer Platform. That product
is not available on personal developer apps.

For a fixed set of known entities (e.g. your bootcamp, regular collaborators), the
`KNOWN_MENTIONS` dict approach covers the practical use case without any additional API access.

---

## Migration Summary

| | Old (UGC API) | New (Posts API + LTF) |
|---|---|---|
| Endpoint | `/v2/ugcPosts` | `/rest/posts` |
| @mentions | Not supported | Supported via LTF |
| Hashtags | Literal text only | Native support |
| Headers | — | `LinkedIn-Version: 202502` required |
