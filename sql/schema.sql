-- Instagram Telegram Bot Database Schema

-- Create database
CREATE DATABASE IF NOT EXISTS instagram_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE instagram_bot;

-- Action logs table
CREATE TABLE IF NOT EXISTS action_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(100) NOT NULL,
    success BOOLEAN DEFAULT TRUE,
    details TEXT,
    created_at DATETIME NOT NULL,
    INDEX idx_action_type (action_type),
    INDEX idx_created_at (created_at),
    INDEX idx_success (success)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Follows tracking table
CREATE TABLE IF NOT EXISTS follows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL,
    followed_at DATETIME NOT NULL,
    unfollowed_at DATETIME NULL,
    source VARCHAR(255) NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_followed_at (followed_at),
    INDEX idx_unfollowed_at (unfollowed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    updated_at DATETIME NOT NULL,
    INDEX idx_setting_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bot statistics table
CREATE TABLE IF NOT EXISTS bot_statistics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stat_date DATE NOT NULL,
    follows_count INT DEFAULT 0,
    unfollows_count INT DEFAULT 0,
    likes_count INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    story_views_count INT DEFAULT 0,
    errors_count INT DEFAULT 0,
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_stat_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
