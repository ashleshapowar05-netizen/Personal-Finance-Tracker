CREATE DATABASE IF NOT EXISTS finance_db;

USE finance_db;


CREATE TABLE IF NOT EXISTS users (

    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    email VARCHAR(150) NOT NULL UNIQUE,

    password_hash VARCHAR(255) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS transactions (

    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    type ENUM('Income', 'Expense') NOT NULL,

    category VARCHAR(50) NOT NULL,

    amount DECIMAL(10,2) NOT NULL,

    description VARCHAR(255),

    date DATE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
    ON DELETE CASCADE
);