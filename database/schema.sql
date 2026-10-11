-- EasyNutrition database schema. Safe to run more than once.
-- Dev only: to rebuild from scratch, first run:
--   DROP TABLE IF EXISTS recipes, scans, users CASCADE;

CREATE TABLE IF NOT EXISTS users (
    user_id            SERIAL PRIMARY KEY,
    name               VARCHAR(100) NOT NULL,
    password_hash      VARCHAR(255) NOT NULL,
    calorie_target     INTEGER NOT NULL DEFAULT 2000 CHECK (calorie_target > 0),
    dietary_preference VARCHAR(100) NOT NULL DEFAULT 'none'
);

-- One account per name, ignoring upper/lower case ("Ann" and "ann" are the same).
CREATE UNIQUE INDEX IF NOT EXISTS users_name_unique ON users (lower(name));

CREATE TABLE IF NOT EXISTS scans (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    image_name     TEXT NOT NULL,
    calorie_limit  INTEGER NOT NULL,
    diet           TEXT NOT NULL,
    detected_items JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS recipes (
    id                SERIAL PRIMARY KEY,
    scan_id           INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    calories          NUMERIC(7,1),
    status            TEXT NOT NULL CHECK (status IN ('accepted', 'rejected')),
    score             REAL NOT NULL DEFAULT 0,
    leftovers_used    INTEGER NOT NULL DEFAULT 0,
    reasons           JSONB NOT NULL,
    ingredients_used  JSONB NOT NULL,
    extra_ingredients JSONB NOT NULL,
    steps             JSONB NOT NULL,
    spoonacular_id    INTEGER,
    source_url        TEXT
);

CREATE INDEX IF NOT EXISTS idx_scans_user ON scans(user_id);
CREATE INDEX IF NOT EXISTS idx_recipes_status ON recipes(status);