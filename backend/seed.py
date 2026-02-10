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
user4 = DBUser(username="kalvoada", bio="")
user5 = DBUser(username="Džeminýj", bio="")
user6 = DBUser(username="Pan pastelka", bio="")
user7 = DBUser(username="Pan Rampouch", bio="")
user8 = DBUser(username="Velký černý dítě", bio="")
user9 = DBUser(username="někdo", bio="")
user10 = DBUser(username="Bažant", bio="")

users = [user1, user2, user3, user4, user5, user6, user7, user8, user9, user10]
db.add_all(users)
db.commit()

for user in users:
    db.refresh(user)
    print(f"Refreshed: {user.username} (ID: {user.id})")

# 4. CREATE MOCK POSTS
print("Creating posts...")
posts = [
    DBPost(content="Jebu všechny zmrdy", user_id=user1.id),
    DBPost(content="vn geng vn geng", user_id=user1.id),
    DBPost(content="džeah", user_id=user2.id),
    DBPost(content="", user_id=user2.id),
    DBPost(content="Gugugaga", user_id=user3.id),
    DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user4.id),
    DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user9.id),
    DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user9.id),
    DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user5.id),
    DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user3.id),
    DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user3.id),
    DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user8.id)
]

db.add_all(posts)
db.commit()

print("Database seeded successfully")
db.close()