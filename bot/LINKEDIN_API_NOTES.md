# LinkedIn API — Known Limitations & Findings

## @Mentions in Posts — Does Not Work via UGC API

### What was tried

The ICARUS bot posts to LinkedIn using the **UGC (User Generated Content) API** endpoint:

```
POST https://api.linkedin.com/v2/ugcPosts
```

The initial attempt included `@Ironhack` and similar mentions directly in the post text:

```json
{
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": {
        "text": "Just finished Week 2 at @Ironhack Berlin..."
      }
    }
  }
}
```

Plain `@mentions` in the text field are treated as literal strings — LinkedIn does not resolve them into tagged profile links.

### Why it doesn't work

LinkedIn's API separates **plain text** from **attributed entities** (tagged people or companies). To create a real @mention, the API requires:

1. The target person's or company's LinkedIn URN (e.g. `urn:li:organization:12345`)
2. The exact character offset and length of the mention in the text
3. The `attributes` array inside `shareCommentary`

Example of what a working mention payload would look like:

```json
{
  "shareCommentary": {
    "text": "Just finished Week 2 at Ironhack Berlin...",
    "attributes": [
      {
        "start": 24,
        "length": 15,
        "value": {
          "com.linkedin.common.CompanyAttributedEntity": {
            "company": "urn:li:organization:2821965"
          }
        }
      }
    ]
  }
}
```

### Why this is not implemented

- Resolving a name like "Ironhack" to a LinkedIn URN requires a separate **Organization Search API** call
- That API requires the **Marketing Developer Platform** product on the LinkedIn app
- Marketing Developer Platform access requires LinkedIn approval and is restricted to companies/agencies — not available for personal developer apps
- The ICARUS app uses the `w_member_social` scope (personal posting only), which does not include URN lookup

### Current workaround

Posts are created via the API without mentions. After posting, the user manually edits the post on LinkedIn to add the `@tag`. LinkedIn's post editor supports this natively.

### Potential solution path

If Marketing Developer Platform access were granted:
1. Call `GET https://api.linkedin.com/v2/organizationAcls` or use the typeahead search to resolve a company name to its URN
2. Store a small lookup table of frequently tagged people/companies and their URNs
3. Before posting, detect `@Name` patterns in the text and replace them with the correct attribute objects

This is buildable — it just requires API tier access that is not available on a personal developer app.
