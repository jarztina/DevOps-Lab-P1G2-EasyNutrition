# EasyNutrition: Leftover Food Recipe Advisor

Team DEVOPS P1-G2, INF1103 Team Project Part 2 (object-oriented version).

Take a photo of your leftover food. The app uses AI to find the ingredients in the photo, finds recipes that use them, and keeps only the recipes that fit your calorie limit and diet. This helps people cook what they already have and waste less food.

## What is new in Part 2

- **Object-oriented code.** Part 1 was procedural. Part 2 is rewritten as classes, with abstract classes, inheritance, composition, aggregation and polymorphism. The Flask routes are also a class (`WebApp`).
- **New feature: fix the AI's mistakes.** If the AI read the photo wrong, you can edit the ingredient list. The app then searches for new recipes, runs every check again, saves the new results, and shows a message such as "You added tofu and removed chicken. Recipes you can make: 1 before, 3 now."
- **Advanced feature: edit and delete saved recipes.** You can change the notes and the ingredient lists of a saved recipe, delete one recipe, or delete a whole scan. Each user can only change their own data.
- **More tests.** 235 tests run offline and inside Docker. They use fake AI replies and a fake database, so they cost nothing.
- **Bug fixes.** The AI client now picks the first text block of the reply, so a "thinking" block no longer crashes the app. The edit page now accepts long ingredient lines (up to 200 characters) written by the recipe source.
- **Continuous integration.** GitHub Actions runs the tests and builds the Docker image on every push and pull request.

## How it works

Photo and form -> `IOManager` -> `AIManager` -> `LogicManager` -> `PostgresDataManager` -> results page

`main.py` builds the four managers and gives them to `WebApp`. `WebApp` decides the order of calls and contains no business rules.

| Package | Classes | Job |
|---|---|---|
| `main.py` | `AppFactory` | Builds the managers, runs the database update, creates the Flask app. `main:app` is what gunicorn runs. |
| `web_app.py` | `WebApp` | Every Flask route is a method of this class. |
| `io_manager/` | `IOManager`, `InputCollector`, `Validator` classes, `SessionManager`, `PageRenderer` | Forms, input checks, login session and HTML pages. |
| `ai_manager/` | `AIManager`, `VisionClient`, `IngredientParser`, `SpoonacularSource` | Claude reads the photo. Spoonacular finds recipes. The AI answer is checked and retried on failure. |
| `logic_manager/` | `LogicManager`, `RecipeEvaluator`, `Rule` classes, `WeightedScorer`, `IngredientMatcher`, `CorrectionService` | Business rules and scoring. Accepts or rejects each recipe with reasons. |
| `data_manager/` | `PostgresDataManager`, `UserRepository`, `ScanRepository`, `RecipeRepository` | PostgreSQL: users, scans and recipes. |
| `database/` | `Database`, `SchemaMigrator`, `schema.sql` | The connection and the table definitions. |

## Object-oriented design

| Idea | Where we use it |
|---|---|
| Abstract classes | `AIService`, `RecipeSource`, `DataManager`, `Rule`, `Scorer`, `Validator` |
| Inheritance | `AIManager` extends `AIService`. The three repositories extend `BaseRepository`. Each rule extends `Rule`. |
| Polymorphism | `RecipeEvaluator` runs a list of `Rule` objects through the same `check()` method. |
| Composition | `PostgresDataManager` owns its repositories. `IOManager` owns the collector, the session manager and the renderer. `WebApp` owns the four managers. |
| Aggregation | The `Database`, the recipe source, and the rules and scorer are passed in from outside. |
| Association | One `IngredientMatcher` is shared by the rules and the scorer. |
| Encapsulation | Fields start with `_`. Other code uses public methods. |
| Dependency injection | Tests pass in fake parts (`FakeAI`, `FakeData`, `FakeDatabase`). |

SOLID evidence: a new rule is a new `Rule` class with no change to `RecipeEvaluator` (open/closed). Any `Scorer` or `RecipeSource` can replace the default (Liskov). Each class has one job (single responsibility). Managers depend on abstract classes, not on concrete ones (dependency inversion).

## Run with Docker (recommended)

1. Install Docker Desktop and make sure it is running.
2. Copy `.env.example` to `.env` and fill in the values (see below).
3. Run:

```
docker compose up --build
```

4. Open http://localhost:5000, register, and upload a photo.
5. To stop: press Ctrl+C, then run `docker compose down`.

An older database volume still works. `SchemaMigrator` adds the new `notes` column when the app starts.

## Run the tests in Docker

```
docker compose run --rm web python -m pytest -q
```

You should see `235 passed`.

## Run without Docker

1. Install Python 3.12 and PostgreSQL.
2. Create the database `nutrition_recipe_advisor` and run `database/schema.sql` in it.
3. Make a virtual environment and install the packages:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and fill it in.
5. Run `flask --app main run`.
6. Run the tests with `python -m pytest -q`.

## Settings (.env)

| Name | What it is |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL connection |
| `ANTHROPIC_API_KEY` | Claude API key |
| `AI_MODEL` | Claude model name |
| `SPOONACULAR_API_KEY` | Spoonacular API key |
| `SECRET_KEY` | Any long random text, used to sign login sessions |

Never commit `.env`. It is listed in `.gitignore`.

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request. It installs the packages, runs `pytest -q`, and builds the Docker image. A red cross on a pull request means a test or the build failed.

## Logic rules

- Calories must be above 0 and no more than the limit.
- Vegetarian, vegan and halal diets reject recipes with banned ingredients. Spoonacular's vegetarian and vegan flags are also checked.
- A recipe must use at least 2 of the confidently detected leftovers, and at least 40% of its ingredients must be leftovers.
- Accepted recipes get a score from 0 to 100: 40% leftover coverage, 30% relevance, 30% calorie fit.

## Error handling

Every manager returns `(ok, value)` instead of crashing. The user always sees a plain message and the app keeps running. Examples: a photo that is too big or not a JPG or PNG, an AI answer that is broken or empty, the recipe service being down, the database being down, a recipe or scan that does not exist, and a user trying to open someone else's data.

## Team

- Justin: logic manager, web app, main.py, integration
- Sebastian: ai manager
- Jovan: database, user and scan repositories, data manager facade
- Hanni: recipe repository, schema migration
- Jia Le: input validators and input collector
- Gabriel: session manager, page renderer, IO manager facade, templates and styling