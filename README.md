# EasyNutrition: Leftover Food Recipe Advisor

Team DEVOPS P1-G2, INF1009 / INF1103 Team Project Part 1.

Take a photo of your leftover food. The app uses AI to find the ingredients in the photo, finds recipes that use them, and keeps only the recipes that fit your calorie limit and diet. This helps people cook what they already have and waste less food.

## How it works

Photo and form -> `io_manager` -> `ai_manager` -> `logic_manager` -> `data_manager` -> results page

| File | Job |
|---|---|
| `main.py` | Starts the Flask web app and calls the four managers in order. No business logic. |
| `io_manager.py` | Forms, input checks, login session, and HTML pages (templates). |
| `ai_manager.py` | Claude reads the photo and lists the ingredients. Spoonacular finds recipes. Checks the AI answer against a schema and retries on failure. |
| `logic_manager.py` | Business rules: calorie check, dietary check, leftover relevance check, and scoring. Accepts or rejects each recipe with reasons. |
| `data_manager.py` | PostgreSQL: users, scans and recipes. Each user sees only their own data. |

The code is 100% procedural: functions only, no classes.

## Run with Docker (recommended)

1. Install Docker Desktop and make sure it is running.
2. Copy `.env.example` to `.env` and fill in the values (see below).
3. Run:

```
   docker compose up --build
```

4. Open http://localhost:5000, register, and upload a photo.
5. To stop: press Ctrl+C, then run `docker compose down`.

## Run without Docker

1. Install Python 3.12 and PostgreSQL.
2. Create the database `nutrition_recipe_advisor` and run `database/schema.sql` in it.
3. Make a virtual environment and install packages:

```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and fill it in.
5. Run `flask --app main run` and run it in your own local server
## Settings (.env)

| Name | What it is |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL connection |
| `ANTHROPIC_API_KEY` | Claude API key |
| `AI_MODEL` | Claude model name |
| `SPOONACULAR_API_KEY` | Spoonacular API key |
| `SECRET_KEY` | Any long random text, used to sign login sessions |

Never commit `.env`. It is listed in `.gitignore`.

## Tests

```
pytest -q
```

26 tests cover `logic_manager` and `ai_manager`. They use fake AI and recipe replies, so they run offline and cost nothing.

## Logic rules

- Calories must be above 0 and no more than the limit.
- Vegetarian, vegan and halal diets reject recipes with banned ingredients. Spoonacular's vegetarian and vegan flags are also checked.
- A recipe must use at least 2 of the confidently detected leftovers, and at least 40% of its ingredients must be leftovers.
- Accepted recipes get a score from 0 to 100: 40% leftover coverage, 30% relevance, 30% calorie fit.

## Team

Update this list with each member's name and manager.

- io_manager: Gabriel and Jia Le
- ai_manager: Sebastian and Justin
- data_manager: Jovan and Han Ni
- logic_manager and integration: Justin
