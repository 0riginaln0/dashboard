-- name: find_user(id)^  
-- Finds a single user by identifier.  
SELECT * FROM users   
WHERE id = :id;  
  
-- name: add_user(name, age)!
INSERT INTO users 
(name, age)  
VALUES (:name, :age);
  
-- name: get_users() 
-- Get all users  
SELECT name, age FROM users;  
  
-- name: delete_user(id)!  
-- Deletes a user by id  
DELETE FROM users  
WHERE id = :id;