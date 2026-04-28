CREATE DATABASE IF NOT EXISTS topics_db;
USE topics_db;

CREATE TABLE IF NOT EXISTS topics (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO topics (title, description)
VALUES
  ('DevOps', 'Tools and practices for delivery and reliability.'),
  ('Cloud', 'Compute, storage, and networking on demand.'),
  ('Containers', 'Packaging apps with their dependencies.');
