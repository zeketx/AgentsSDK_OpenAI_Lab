---
description: Run Google Maps leadgen for a niche + city and export to a Google Sheets tab
argument-hint: "<niche> | <city> [| <worksheet name>] [| force]"
---

# Leadgen

Run the Google Maps lead generation pipeline for a specific niche and city, then export results to the correct Google Sheets worksheet.

## Variables

ARGUMENTS: $ARGUMENTS

Parse `$ARGUMENTS` by splitting on `|` and trimming whitespace:
- NICHE = part 1 (required) — e.g. `coffee shops`
- CITY  = part 2 (required) — e.g. `Memphis, Tennessee`
- WORKSHEET_NAME = part 3 (optional) — if omitted, derive as `{Title Case NICHE} - {first word of CITY}`
- FORCE = part 4 (optional) — if the value is `force`, add `--no-cross-run-dedupe`

If NICHE or CITY is missing, stop and ask the user to provide them.

SEEN_IDS_PATH = `data/leadgen/seen_ids/{niche_slug}_{city_slug}.json`
where slug = value lowercased with spaces replaced by underscores.

## Workflow

1. Validate NICHE and CITY are present. If not, ask the user.
2. Derive WORKSHEET_NAME if not provided.
3. Derive SEEN_IDS_PATH from NICHE and CITY slugs.
4. Run:

```bash
python -m app.leadgen.ingest.google_maps \
  --query "NICHE" \
  --location "CITY" \
  --limit 100 \
  --to-sheets \
  --worksheet-name "WORKSHEET_NAME" \
  --seen-ids-path "SEEN_IDS_PATH"
```

(append `--no-cross-run-dedupe` if FORCE == "force")

5. Report: sheet URL, worksheet name, record count, and SEEN_IDS_PATH used.
