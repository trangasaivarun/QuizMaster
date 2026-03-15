-- =============================================================
--   QuizMaster  |  SQLite Schema
-- =============================================================

-- -----------------------------------------------------------
-- 1. USERS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name       VARCHAR(50)  NOT NULL,
    last_name        VARCHAR(50)  NOT NULL,
    email            VARCHAR(100) NOT NULL UNIQUE,
    phone            VARCHAR(10)  NOT NULL,
    password         VARCHAR(255) NOT NULL,
    gender           TEXT CHECK(gender IN ('male','female')) NOT NULL,
    bio              TEXT,
    profile_picture  VARCHAR(255) DEFAULT NULL,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- 2. ADMINS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS admins (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    email     VARCHAR(100) NOT NULL UNIQUE,
    password  VARCHAR(255) NOT NULL
);

-- Insert a default admin (password: admin123)
INSERT OR IGNORE INTO admins (email, password)
VALUES ('admin@quizmaster.com', 'admin123');

-- -----------------------------------------------------------
-- 3. QUIZZES
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS quizzes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           VARCHAR(150) NOT NULL,
    num_questions   INTEGER NOT NULL DEFAULT 10,
    description     TEXT,
    time_limit      INTEGER NOT NULL DEFAULT 10,
    time_per_question INTEGER NOT NULL DEFAULT 30,
    randomize       INTEGER NOT NULL DEFAULT 1,
    created_by      INTEGER NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES admins(id)
);

-- -----------------------------------------------------------
-- 4. QUESTIONS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS questions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id        INTEGER NOT NULL,
    question_text  TEXT NOT NULL,
    option_a       VARCHAR(255) NOT NULL,
    option_b       VARCHAR(255) NOT NULL,
    option_c       VARCHAR(255) NOT NULL,
    option_d       VARCHAR(255) NOT NULL,
    correct_option TEXT CHECK(correct_option IN ('A','B','C','D')) NOT NULL,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

-- -----------------------------------------------------------
-- 5. SCORES
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS scores (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    quiz_id      INTEGER NOT NULL,
    score        INTEGER NOT NULL DEFAULT 0,
    total        INTEGER NOT NULL DEFAULT 0,
    attempted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
    FOREIGN KEY (quiz_id)  REFERENCES quizzes(id) ON DELETE CASCADE
);

-- -----------------------------------------------------------
-- 6. USER ANSWERS  (stores each question's chosen answer for review/analytics)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_answers (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    score_id       INTEGER NOT NULL,
    question_id    INTEGER NOT NULL,
    chosen_option  TEXT CHECK(chosen_option IN ('A','B','C','D','')) NOT NULL DEFAULT '',
    is_correct     INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (score_id)    REFERENCES scores(id)    ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);
