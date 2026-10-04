# VeriFact

**AI Claim Checker Application** — INF1009 Team Project, Lab P1 G2

Justin Ang · Gabriel Lee · Han Ni · Sebastian Goh · Jia Le · Jovan Ng

---

## 1. Problem Statement

As AI tools become easier to use, fraudulent information and hoaxes are increasingly generated and spread across social platforms to drive engagement. These often reuse real events with altered details (wrong dates, wrong numbers, outdated news presented as current).

Most existing fact-checking tools give a single flat verdict (e.g. "FALSE") without explaining which specific details are wrong. They also don't indicate whether a claim has circulated before. This makes it hard for users to recognize when something is a repeated hoax rather than new misinformation.

**VeriFact** checks a submitted claim against web sources, breaks down exactly which facts match or don't, and tracks recurring claims in its own database so users can spot patterns of repeated hoaxes over time.

### Target Users
- Social media users, especially students and young adults who get news primarily from platforms like TikTok, X, and Instagram
- News professionals
- Educators
- Anyone who wants a source-backed, detailed claim check rather than a simple true/false answer

---

## 2. User Inputs

- A local image (e.g. screenshot of a social media post)
- Pasted text of a claim
- A link to a news article

---

## 3. Use of AI

AI analyzes and evaluates the information a user submits. It identifies the specific claims being made and compares them against reliable sources and evidence found via web search.

The system also checks submitted claims against previously recorded ones, allowing it to identify recurring claims and suspicious patterns rather than treating every input as new.

**AI-generated outputs:**
- Verification result
- Summarized sources and evidence, with links
- Recurring claim detection
- Manipulation pattern flags
- Confidence indicator
- Risk score

---

## 4. Business Rules

- A claim is only marked **Verified** or **False** if at least two independent sources agree; otherwise it is marked **Unable to Verify**
- Source credibility is weighted — major outlets carry more weight than unverified or low-credibility sources
- If a submitted claim closely matches one already stored in the database, it is flagged as a **recurring claim** instead of being processed as new
- Manipulation pattern detection is applied to flag content designed to spread quickly (e.g. urgency language, impersonation of official sources)

---

## Architecture

VeriFact follows a 4-layer procedural pipeline — **100% functions, no class definitions anywhere in the codebase**:

```
User (image / text / link)
        ↓
   io_manager        — terminal input/output, validation, formatting
        ↓
   ai_manager         — builds prompts, calls AI API, validates structured JSON response
        ↓
   logic_manager      — business rules: verdict logic, recurrence detection, risk scoring
        ↓
   data_manager       — saves/loads records, filter & query functions
```

| Manager | Responsibility |
|---|---|
| `io_manager` | All terminal I/O lives here. Collects and validates user input (image path, pasted text, or URL), formats and prints all output. No `print()` calls anywhere else in the codebase. |
| `ai_manager` | Builds the prompt from the input, calls the AI API, parses and validates the JSON response, retries or logs gracefully on failure. No business logic — API interaction only. |
| `logic_manager` | Applies the business rules above to the AI-extracted data. Decides the final verdict, checks for recurring claims, computes the risk score. This is where the project's core logic lives. |
| `data_manager` | Handles all database reads/writes (PostgreSQL). Saves processed claims, loads history, and provides filter/query functions — including recurrence lookups and a "popular searches" view. |

### Hard Constraints
- 100% procedural no classes
- AI is the core engine every claim passes through the AI API
- AI must return structured, schema-validated JSON
- Persistence via PostgreSQL
- Runs in Docker
- Git history must show granular, meaningful commits

---

## Repo

[https://github.com/jarztina/DevOps-Lab-P1G2-VeriFact](https://github.com/jarztina/DevOps-Lab-P1G2-VeriFact)

---

## Status

🚧 In development.
