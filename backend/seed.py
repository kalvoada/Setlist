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

print("Creating posts...")
post1  = DBPost(content="Jebu všechny zmrdy", user_id=user1.id)
post2  = DBPost(content="vn geng vn geng", user_id=user1.id)
post3  = DBPost(content="džeah", user_id=user2.id)
post4  = DBPost(content="", user_id=user2.id)
post5  = DBPost(content="Gugugaga", user_id=user3.id)
post6  = DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user4.id)
post7  = DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user9.id)
post8  = DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user9.id)
post9  = DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user5.id)
post10 = DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user3.id)
post11 = DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user3.id)
post12 = DBPost(content="feinfeinfeinfeinfeinfeinfein", user_id=user8.id)

posts = [post1, post2, post3, post4, post5, post6, post7, post8, post9, post10, post11, post12]
db.add_all(posts)
db.commit()

print("Creating comments...")
comments = [
    DBComment(content="to je ale hustý", user_id=user2.id, post_id=post1.id),
    DBComment(content="naprosto souhlasím", user_id=user3.id, post_id=post1.id),
    DBComment(content="klasika", user_id=user5.id, post_id=post1.id),

    DBComment(content="vn geng!!!", user_id=user4.id, post_id=post2.id),
    DBComment(content="co to znamená", user_id=user7.id, post_id=post2.id),

    DBComment(content="džeah to je pravda", user_id=user1.id, post_id=post3.id),

    DBComment(content="to říkáš ty jo", user_id=user9.id, post_id=post5.id),
    DBComment(content="gugugaga na tebe taky", user_id=user6.id, post_id=post5.id),

    DBComment(content="fein fein fein", user_id=user1.id, post_id=post6.id),
    DBComment(content="víc fein", user_id=user2.id, post_id=post6.id),

    DBComment(content="tohle je spam", user_id=user10.id, post_id=post7.id),
    DBComment(content="^^^ pravda", user_id=user3.id, post_id=post7.id),

    DBComment(content="zajímavý obsah", user_id=user4.id, post_id=post10.id),
    DBComment(content="nesouhlasím", user_id=user8.id, post_id=post10.id),
    DBComment(content="proč ne", user_id=user5.id, post_id=post10.id),
]

db.add_all(comments)
db.commit()

print("Database seeded successfully")
db.close()