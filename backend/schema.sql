-- Select the database
USE dermacare_db;

-- -----------------------------------------------------
-- Table `users`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    contact_number VARCHAR(20),
    gender VARCHAR(20),
    date_of_birth VARCHAR(20),
    age INT,
    role VARCHAR(50) DEFAULT 'User',
    is_logged_in BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- -----------------------------------------------------
-- Table `medical_profiles`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS medical_profiles (
    id INT AUTO_INCREMENT,
    user_id INT NOT NULL,
    symptoms TEXT,
    symptom_duration VARCHAR(50) DEFAULT 'Less than 1 week',
    has_previous_conditions BOOLEAN DEFAULT FALSE,
    previous_condition_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Table `scan_history`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS scan_history (
    id INT AUTO_INCREMENT,
    user_id INT NOT NULL,
    disease VARCHAR(100) NOT NULL,
    confidence FLOAT NOT NULL,
    remedies JSON,
    scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Table `user_locations`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS user_locations (
    id INT AUTO_INCREMENT,
    uid INT NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (uid) REFERENCES users(id) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Table `user_login_history`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS user_login_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    session_id VARCHAR(255),
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP NULL,
    device_info VARCHAR(255),
    ip_address VARCHAR(100),
    status ENUM('LOGIN','LOGOUT','ACTIVE') DEFAULT 'LOGIN',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
