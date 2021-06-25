import sqlalchemy
from sqlalchemy.orm import sessionmaker
from discotron import User

engine = sqlalchemy.create_engine('sqlite:///discotron.db')
Session = sessionmaker(bind=engine)
session = Session()

users = User.query.all()

for user in users:
    print(user)
print(len(users))
