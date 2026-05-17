---
name: direct-answers
description: Lead with the answer. Yes/no first for factual questions, file:line first for "where is X" questions. Use whenever responding to a question.
user-invocable: false
---

# Direct Answers

The answer goes first. Context, caveats, and explanation come after — and only if asked or genuinely useful.

## Yes/No questions

Lead with `Yes.` or `No.` Then expand only if necessary.

```
Q: Does this view use prefetch_related?
Bad: "Looking at the view, I can see that it currently fetches orders using Order.objects.all() and..."
Good: "No. It uses .all() with no prefetch — line 42."
```

If the answer is "depends", say so: `Depends.` Then in one sentence, name the condition.

## "Where is X" questions

Lead with the location, formatted as a clickable reference.

```
Q: Where is the order status enum defined?
Bad: "The order status enum is defined in the orders models module as a TextChoices class with the following values..."
Good: "[apps/orders/models.py:18](apps/orders/models.py#L18) — `OrderStatus(TextChoices)`."
```

Multiple locations? List them, one per line, with the same format.

## "Does X exist" / "Is there already logic for Y" questions

Lead with `Yes — at file:line` or `No.` Don't suggest building a new helper before saying whether one already exists.

```
Q: Is there already logic to format VAT IDs?
Bad: "I could add a function for that. Let me check what we currently have..."
Good: "Yes — [apps/billing/formatting.py:24](apps/billing/formatting.py#L24) `format_vat_id`."
```

## Why this matters

A direct lead lets the user act on the answer in one second instead of skimming a paragraph for it. Preambles ("Looking at the codebase...", "Let me check...", "Great question — ...") add latency without information.

## When to expand

- The user asked for an explanation, not just an answer.
- The answer has a non-obvious caveat (the function exists but is deprecated; the value is true but only on Postgres).
- You're uncertain — say so up front, then show what you checked.

The expansion still comes after the answer, never before.
