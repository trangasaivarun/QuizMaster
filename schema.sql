-- =============================================================
--   QuizMaster  |  MySQL Schema
--   Technologies: MySQL (as discussed in class)
-- =============================================================

CREATE DATABASE IF NOT EXISTS quizmaster;
USE quizmaster;

-- -----------------------------------------------------------
-- 1. USERS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    first_name       VARCHAR(50)  NOT NULL,
    last_name        VARCHAR(50)  NOT NULL,
    email            VARCHAR(100) NOT NULL UNIQUE,
    phone            VARCHAR(10)  NOT NULL,
    password         VARCHAR(255) NOT NULL,
    gender           ENUM('male','female') NOT NULL,
    bio              TEXT,
    profile_picture  VARCHAR(255) DEFAULT NULL,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- 2. ADMINS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS admins (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    email     VARCHAR(100) NOT NULL UNIQUE,
    password  VARCHAR(255) NOT NULL               -- stored as hashed value
);

-- Insert a default admin (password: admin123)
INSERT IGNORE INTO admins (email, password)
VALUES ('admin@quizmaster.com', 'admin123');

-- -----------------------------------------------------------
-- 3. QUIZZES
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS quizzes (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(150) NOT NULL,
    num_questions   INT NOT NULL DEFAULT 10,
    description     TEXT,
    time_limit      INT NOT NULL DEFAULT 10,       -- total minutes (kept for compatibility)
    time_per_question INT NOT NULL DEFAULT 30,     -- seconds per question
    randomize       TINYINT(1) NOT NULL DEFAULT 1, -- 1=shuffle questions & options
    created_by      INT NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES admins(id)
);

-- -----------------------------------------------------------
-- 4. QUESTIONS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS questions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    quiz_id        INT NOT NULL,                  -- FK → quizzes.id
    question_text  TEXT NOT NULL,
    option_a       VARCHAR(255) NOT NULL,
    option_b       VARCHAR(255) NOT NULL,
    option_c       VARCHAR(255) NOT NULL,
    option_d       VARCHAR(255) NOT NULL,
    correct_option ENUM('A','B','C','D') NOT NULL,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

-- -----------------------------------------------------------
-- 5. SCORES
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS scores (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    quiz_id      INT NOT NULL,
    score        INT NOT NULL DEFAULT 0,
    total        INT NOT NULL DEFAULT 0,
    attempted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
    FOREIGN KEY (quiz_id)  REFERENCES quizzes(id) ON DELETE CASCADE
);

-- -----------------------------------------------------------
-- 6. USER ANSWERS  (stores each question's chosen answer for review/analytics)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_answers (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    score_id       INT NOT NULL,
    question_id    INT NOT NULL,
    chosen_option  ENUM('A','B','C','D','') NOT NULL DEFAULT '',
    is_correct     TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (score_id)    REFERENCES scores(id)    ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);
