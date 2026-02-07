from src.database.database import *
from src.database.models import *

# 1. RESET THE DATABASE
# This drops all tables and recreates them.
# WARNING: This deletes any existing data in social.db!
print("Resetting database...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# 2. CREATE A DB SESSION
db = SessionLocal()

# 3. CREATE MOCK USERS
print("Creating users...")
user1 = DBUser(username="peter paul", bio="El prezidente")
user2 = DBUser(username="peter boujon", bio="Peter cheater")
user3 = DBUser(username="Dušan knop", bio="")

db.add_all([user1, user2, user3])
db.commit()

# Refresh to ensure they have IDs assigned by the database
db.refresh(user1)
db.refresh(user2)
db.refresh(user3)

# 4. CREATE MOCK POSTS
print("Creating posts...")
posts = [
    DBPost(content="Jebu všechny zmrdy", user_id=user1.id),
    DBPost(content="vn geng vn geng", user_id=user1.id),
    DBPost(content="džeah", user_id=user2.id),
    DBPost(content="", user_id=user2.id),
    DBPost(content="Gugugaga", user_id=user3.id),
    DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user3.id)
]

db.add_all(posts)
db.commit()

print("Database seeded successfully")
db.close()