# EasyNutrition: Leftover Food Recipe Advisor

Team DEVOPS P1-G2, INF1009 / INF1103 Team Project Part 2 (object-oriented version).

Take a photo of your leftover food. The app uses AI to find the ingredients in the photo, finds recipes that use them, and keeps only the recipes that fit your calorie limit and diet. This helps people cook what they already have and waste less food.

## What is new in Part 2

- **Object-oriented design.** Part 1 was functions only. Part 2 is rebuilt with classes. The four managers (IO, AI, Logic, Data) are kept, and each one is now a package of small classes.
- **New feature: Fix the AI's mistakes.** If the AI got an ingredient wrong, the user can edit the list (change, remove or add items). The app searches for new recipes and runs all the checks again. A message shows what changed.
- **Advanced feature: Edit and delete saved recipes (database CRUD).** On the History page a user can edit a recipe's notes and ingredient lists, delete a recipe, or delete a whole scan. Delete asks for confirmation.
- **Bug fix.** The AI client now picks the first text block of the reply, so a "thinking" block no longer crashes the app.

## How it works

Photo and form -> `WebApp` -> `IOManager` -> `AIManager` -> `LogicManager` -> `DataManager` -> results page

| Folder / file | What it holds |
|---|---|
| `main.py` | `AppFactory` builds the four managers and the Flask app (`main:app`). |
| `web_app.py` | `WebApp`: every route is a method. It owns one of each manager and only decides the order of calls. |
| `io_manager/` | `IOManager` (front door), `InputCollector`, `Validator` classes, `SessionManager`, `PageRenderer`. |
| `ai_manager/` | `AIManager` (front door), `AIService` (abstract), `VisionClient`, `IngredientParser`, `RecipeSource` (abstract), `SpoonacularSource`. |
| `logic_manager/` | `LogicManager` (front door), `RecipeEvaluator`, `Rule` (abstract) with 4 rules, `Scorer` (abstract) with `WeightedScorer`, `IngredientMatcher`, `CorrectionService`. |
| `data_manager/` | `DataManager` (abstract), `PostgresDataManager` (front door), `BaseRepository`, `UserRepository`, `ScanRepository`, `RecipeRepository`. |
| `database/` | `Database` (connections), `SchemaMigrator` (adds new columns to an old database), `schema.sql`. |
| `templates/`, `static/` | HTML pages and CSS. |
| `tests/` | pytest tests. No live AI and no real database needed. |

## OOP concepts used

| Idea | Where |
|---|---|
| Abstract classes / interfaces | `DataManager`, `AIService`, `RecipeSource`, `Rule`, `Scorer`, `Validator` |
| Inheritance | The three repositories inherit `BaseRepository`. Every rule inherits `Rule`. |
| Polymorphism | The evaluator calls `rule.check()` on any rule. The web-app tests swap in fake managers. |
| Encapsulation | Internal members start with an underscore, for example `self._database`. |
| Association | `LeftoverRule` and `WeightedScorer` share one `IngredientMatcher`. |
| Aggregation | `RecipeEvaluator` gets its rules and scorer from outside. `AIManager` gets its `RecipeSource` from outside. `PostgresDataManager` gets its `Database` from outside. |
| Composition | `PostgresDataManager` creates its repositories. `IOManager` creates its collector, session manager and renderer. |

SOLID: **S** each class has one job. **O** a new `Rule`, `Scorer` or `RecipeSource` is a new class, and existing code is not edited. **L** any `Rule`, `Scorer`, `RecipeSource` or `Validator` can replace another. **D** the web app and AI manager depend on abstract types, not concrete ones.

## Run with Docker (recommended)

1. Install Docker Desktop and make sure it is running.
2. Copy `.env.example` to `.env` and fill in the values (see below).
3. Build and start:

```
docker compose up --build
```

4. Open http://localhost:5000, register, and upload a photo.
5. To stop: press Ctrl+C, then run `docker compose down`.

An old database from Part 1 keeps working. On start the app adds the new `notes` column by itself.

## Run the tests in Docker

```
docker compose run --rm web pytest -q
```

The tests use fake AI replies and a fake database, so they run offline and cost nothing.

## Run without Docker

1. Install Python 3.12 and PostgreSQL.
2. Create the database (for example `nutrition_recipe_advisor`) and run `database/schema.sql` in it.
3. Make a virtual environment and install packages:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and fill it in (`DB_HOST=localhost`).
5. Run `flask --app main run`, or run the tests with `python -m pytest -q`.

## Settings (.env)

| Name | What it is |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL connection |
| `ANTHROPIC_API_KEY` | Claude API key |
| `AI_MODEL` | Claude model name |
| `SPOONACULAR_API_KEY` | Spoonacular API key |
| `SECRET_KEY` | Any long random text, used to sign login sessions |

Never commit `.env`. It is listed in `.gitignore`. No secret is stored in the code or the Docker image.

## Continuous Integration

A GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and pull request. It installs the packages, runs `pytest -q`, and builds the Docker image. A red tick means a test failed or the image did not build.

## Logic rules

- Calories must be above 0 and no more than the limit.
- Vegetarian, vegan and halal diets reject recipes with banned ingredients. Spoonacular's vegetarian and vegan flags are also checked.
- A recipe must use at least 2 of the confidently detected leftovers, and at least 40% of its ingredients must be leftovers.
- Accepted recipes get a score from 0 to 100: 40% leftover coverage, 30% relevance, 30% calorie fit.
- Items the AI is less than 60% sure about are ignored.

## Error handling

Every manager returns `(ok, value)`. When `ok` is false, `value` is a short message the user can read. The app handles: AI and recipe-service outages, bad or malformed AI answers (retried up to 3 times), missing keys, database down, duplicate usernames, bad uploads and forms, missing or foreign records (404), and unexpected crashes (friendly 500 page).

## Team

- io_manager: Jia Le (input checks) and Gabriel (sessions, pages, templates)
- ai_manager: Sebastian
- data_manager: Jovan (database, users, scans) and Hanni (recipes, schema updates)
- logic_manager, web app and integration: Justin
