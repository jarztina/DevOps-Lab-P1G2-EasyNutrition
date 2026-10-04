--
-- PostgreSQL database dump
--

\restrict RxCvL6jYHduNL0ogjoTmceLmeg41F7EeY59l5SG4zU1spKKPakbyhMO18sQyKUt

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    name character varying(100) NOT NULL,
    password_hash character varying(255) NOT NULL,
    calorie_target integer NOT NULL,
    dietary_preference character varying(100)
);


CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- PostgreSQL database dump complete
--

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
\unrestrict RxCvL6jYHduNL0ogjoTmceLmeg41F7EeY59l5SG4zU1spKKPakbyhMO18sQyKUt

