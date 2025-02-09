CREATE DATABASE scraper_db;
USE scraper_db;

CREATE TABLE scraped_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title TEXT,
    description TEXT,
    keywords TEXT,
    heading TEXT,
    paragraph TEXT,
    image_url TEXT,
    link_url TEXT,
    table_content TEXT
);
