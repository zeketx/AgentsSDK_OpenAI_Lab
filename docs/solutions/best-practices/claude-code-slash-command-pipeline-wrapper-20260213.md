---
module: System
date: 2026-02-13
problem_type: best_practice
component: tooling
symptoms:
  - "No convenient entry point for running CLI pipelines from Claude Code"
  - "Users must remember CLI flags, argument formats, and seen-IDs paths"
root_cause: missing_tooling
resolution_type: tooling_addition
severity: low
tags: [slash-command, claude-code, pipeline-wrapper, leadgen]
---

# Best Practice: Claude Code Slash Commands as Pipeline Wrappers

## Problem

When a CLI pipeline has many flags and derived values (worksheet names, dedup paths, etc.), users must manually remember argument formats. A Claude Code slash command provides a natural-language entry point that handles derivation and validation automatically.

## Environment

- Module: System-wide pattern
- Affected Component: `.claude/commands/` — Claude Code slash commands
- Date: 2026-02-13

## Symptoms

- User must remember `--query`, `--location`, `--to-sheets`, `--worksheet-name`, `--seen-ids-path`, `--no-cross-run-dedupe` flags and their interactions
- New niche+city combinations require manually constructing a unique seen-IDs path to avoid cross-run deduplication collisions

## What Didn't Work

**Direct solution:** Identified the pattern on first attempt — slash commands are the canonical way to wrap CLI pipelines in Claude Code.

## Solution

Create `.claude/commands/<name>.md` with YAML frontmatter and a `## Workflow` section. Use `$ARGUMENTS` + `|`-delimited parsing for multi-word positional arguments.

**File: `.claude/commands/leadgen.md`**

```markdown
---
description: Run Google Maps leadgen for a niche + city and export to a Google Sheets tab
argument-hint: "<niche> | <city> [| <worksheet name>] [| force]"
---

# Leadgen

ARGUMENTS: $ARGUMENTS

Parse `$ARGUMENTS` by splitting on `|` and trimming whitespace:
- NICHE = part 1 (required)
- CITY  = part 2 (required)
- WORKSHEET_NAME = part 3 (optional) — derive as `{Title Case NICHE} - {first word of CITY}`
- FORCE = part 4 (optional) — if "force", add `--no-cross-run-dedupe`

SEEN_IDS_PATH = `data/leadgen/seen_ids/{niche_slug}_{city_slug}.json`

## Workflow
1. Validate NICHE and CITY; ask if missing
2. Derive WORKSHEET_NAME and SEEN_IDS_PATH
3. Run pipeline with derived values
4. Report sheet URL, worksheet name, record count, seen-IDs path
```

**Invocation examples:**

```
/leadgen coffee shops | Memphis, Tennessee
→ worksheet: "Coffee Shops - Memphis"
→ seen_ids: coffee_shops_memphis_tennessee.json

/leadgen tacos | Memphis, Tennessee | | force
→ full re-export (bypasses dedup)
```

## Why This Works

1. **`|` separators** avoid quoting issues with multi-word arguments like city names
2. **Auto-derivation** in the workflow removes the mental burden of constructing consistent worksheet/path names
3. **YAML frontmatter** (`description`, `argument-hint`) surfaces the command in Claude Code's `/` menu
4. **`$ARGUMENTS`** is the single injection point for all user-provided values
5. **Seen-IDs scoping per slug** ensures each niche+city combo deduplicates independently

## Prevention / Pattern to Follow

When adding any new data pipeline:
1. Create the CLI tool with explicit `--flags` first (testable in isolation)
2. Wrap it in `.claude/commands/<tool>.md` with `|`-delimited args for multi-word values
3. Derive all computed values (paths, names, slugs) inside the command's workflow — never ask users to compute them
4. Include a `force` escape hatch as the last `|` argument to bypass deduplication/caching

**Checklist for a good slash command:**
- [ ] `description` and `argument-hint` in frontmatter
- [ ] All required args validated before running
- [ ] Computed values (slugs, paths, names) derived in the workflow, not by the user
- [ ] `force` or equivalent override for full re-runs
- [ ] Final step reports key outputs (URLs, counts, file paths)

## Related Issues

No related issues documented yet.
