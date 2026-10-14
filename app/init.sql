CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(btrim(title)) > 0),
    done BOOLEAN NOT NULL DEFAULT FALSE
);
