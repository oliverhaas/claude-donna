---
name: use-source-material
description: When the user provides a URL, a prior message to copy from, an existing spec/changelog, or says "use my exact words" / "mostly as I said" / "based on this", fetch and reproduce the source before producing output. Don't paraphrase user-supplied material.
user-invocable: false
---

# Use Source Material

When the user hands you input (a URL, a previous message, a spec, a verbatim quote), that material is the source of truth. Fetch it, read it, and reproduce it. Don't paraphrase it, summarise it, or write fresh content "in the spirit of" it.

## Triggers

Any of these in a user message mean fetch-and-reproduce before drafting:

- A URL (GitHub issue, GitHub discussion, blog post, docs page, gist, anywhere)
- "Use my exact words" / "verbatim" / "as I said" / "mostly as I said"
- "Copy of my comment" / "based on this comment" / "from the discussion"
- "There's a spec at..." / "the changelog already has an entry"
- A file path to read content from
- Pasted prior message they want you to draw from

## Process

1. **Fetch first.** Use `WebFetch` for URLs, `Read` for paths, scroll back for prior chat messages. Get the actual content before writing anything.
2. **Reproduce, don't rewrite.** Copy headings, formatting, images, code blocks, and lists verbatim. If you reformat for the new context (e.g., GitHub markdown → docs markdown), preserve the wording.
3. **Carry over embedded media.** Images, embedded code blocks, links, and tables in the source go into your output too. If the source has a screenshot reference, fetch and include it.
4. **Only edit when asked.** "Tighten this" or "make it shorter" is an instruction to edit. Without that, treat the source as authoritative.

## What this rule prevents

- The user pastes a GitHub discussion URL and says "draft an issue based on this" → AI writes a generic summary instead of fetching the discussion's actual text and reproducing it with the user's wording and screenshots.
- The user says "the changelog spec already has an entry, use it" → AI writes a fresh entry that drifts from the spec.
- The user says "mostly as I said in my previous message" → AI rewrites the structure and tone instead of copying the message and lightly editing.

## When in doubt

If the source is ambiguous ("you know what I mean") or you can't reach it (fetch failed, URL 404s), say so explicitly and ask before drafting. Don't fill the gap with fresh writing. That's the failure mode this skill exists to prevent.
