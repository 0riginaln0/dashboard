-- :name find_user :one
-- :doc Finds a single user by identifier.
SELECT * FROM users 
WHERE id = :id;

-- :name add_user :insert
INSERT INTO users
(name, age)
VALUES (:name, :age);

-- :name get_users :many
-- :doc Get all users
SELECT name, age FROM users;

-- :name delete_user :affected
-- :doc Deletes a user by id
DELETE FROM users
WHERE id = :id;
