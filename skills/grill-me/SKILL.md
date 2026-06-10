---
name: grill-me
description: "Interview the user to extract missing context instead of guessing"
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Grill-Me — Context Extraction Skill

## Purpose

When the system lacks sufficient context to proceed with a task, this skill enables it to **interview Isiah** directly instead of guessing, hallucinating paths, or making assumptions that lead to errors.

Guessing is the #1 source of agent errors. This skill eliminates that failure mode.

---

## Trigger Conditions

Fire the grill-me skill when any of these are true:

1. **Ambiguous request** — The user's instruction could mean multiple things
2. **Missing file path** — The user references a file/folder that doesn't exist or has multiple candidates
3. **Unclear intent** — The user says "fix it" or "update that" without specifying what or where
4. **Conflicting instructions** — Two instructions contradict each other (e.g., "keep it simple" + "add full audit trail")
5. **Missing prerequisites** — The task requires information, credentials, or approvals not yet provided
6. **Out-of-scope request** — The user asks for something that doesn't match any known domain or workflow
7. **First-time task** — The user requests a task type that has never been done before in this session

---

## Interview Protocol

### Step 1: Acknowledge the Gap

```
I want to make sure I get this right. I'm missing some context about [specific gap].
Rather than guessing, let me ask:
```

### Step 2: Ask Specific Questions

**Bad:** "What do you want me to do?"
**Good:** "You mentioned 'the credit report.' I found three credit reports in the inbox — one from Experian (2026-05-01), one from Equifax (2026-05-15), and one from TransUnion (2026-06-01). Which one should I review?"

### Step 3: Offer Choices When Possible

```
Options:
A. Experian report from May 1
B. Equifax report from May 15  
C. TransUnion report from June 1
D. All three
E. None of the above (tell me which one)
```

### Step 4: Confirm Understanding

```
To confirm: you want me to review the TransUnion report from June 1,
check for UCC filings, and draft a dispute letter. Is that correct?
```

### Step 5: Proceed or Loop

- If confirmed: execute the task
- If corrected: update understanding and re-confirm
- If still unclear: loop back to Step 2 with more specific questions

---

## Template Questions by Gap Type

### Missing File/Folder

```
I need to locate [file/folder name]. I checked:
- [path A] — not found
- [path B] — not found

Where should I look? Or should I create it?
```

### Unclear Intent

```
You said "[quote user's instruction]". I see a few possible interpretations:
1. [Interpretation A]
2. [Interpretation B]
3. [Interpretation C]

Which one did you mean?
```

### Missing Approval

```
This task requires [approval tier] because it involves [reason].
Specifically, I need your approval to:
- [action 1]
- [action 2]

Do you authorize this? (yes/no)
```

### Conflicting Instructions

```
I see two instructions that conflict:
- [Instruction A]: "[quote]"
- [Instruction B]: "[quote]"

Which should take priority?
```

---

## Boundaries

- Do **not** grill the user on every trivial detail — use judgment
- If the user says "just do it" after you asked, proceed with your best interpretation and flag assumptions
- If you've asked 3+ questions in a row, offer to batch the answers: "Let me ask all my questions at once so you don't have to keep answering"
- Never make up file paths, case numbers, or legal citations — grill first