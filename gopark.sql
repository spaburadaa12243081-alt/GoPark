-- -----------------------------------------------------
-- DATABASE: gopark
-- -----------------------------------------------------

CREATE DATABASE IF NOT EXISTS gopark;
USE gopark;

-- -----------------------------------------------------
-- TABLE: users
-- -----------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------
-- Sample Indexes (not required but recommended)
-- -----------------------------------------------------
CREATE INDEX idx_username ON users (username);
CREATE INDEX idx_email ON users (email);
