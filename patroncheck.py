import os
import requests
import logging
from discotron import app, db, User
import time
from sqlalchemy.orm import Session

user_agent = "Lichess Discotron discotron.lichess.org"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Starting patron check...")

user_patron_status = {}
patrons_added = []
patrons_removed = []

with app.app_context():
    user_count = User.query.count()
    logger.info(f"Total users to check: {user_count}")

    with Session(db.engine) as session:
        result = session.scalars(db.select(User)).yield_per(300)

        for chunk in result.partitions():
            user_ids = [user.lichessid for user in chunk]

            while True:
                response = requests.post(
                    "https://lichess.org/api/users",
                    headers={'User-Agent': user_agent, 'Content-Type': 'text/plain'},
                    data=",".join(user_ids)
                )

                if response.status_code == 429:
                    logger.warning(f"Rate limited by Lichess API, sleeping for 2 minutes...")
                    time.sleep(60*2)  # sleep if getting ratelimited
                    continue  # try again

                break

            lichess_data = {user['id']: user for user in response.json()}
            for user in lichess_data.values():
                user_patron_status[user['id']] = user.get('patronColor', None) is not None

    print(user_patron_status)
    users = User.query.all()

    for idx, user in enumerate(users, start=1):
        logger.info(f"Checking user {idx}/{len(users)}: Lichess: {user.lichessid}, Discord: {user.discorduser}")
        patron = user_patron_status.get(user.lichessid, False)
        if patron == user.lichesspatron: #db is correct
            logger.info("No change needed.")
            continue
        headers = {'Authorization': f'Bot {os.getenv("DISCORD_TOKEN")}'}
        if not patron and user.lichesspatron: #patron in database but not on website
            #remove patron on discord and db
            logger.info(f"🔴 Removing patron role for Discord user: {user.discorduser}")
            requests.delete(f'''https://discordapp.com/api/guilds/280713822073913354/members/{user.discordid}/roles/751092271025487942''', headers=headers, data=None)
            setattr(user, 'lichesspatron', False)
            db.session.commit()
            patrons_removed.append(user.lichessid)
            continue
        if patron and not user.lichesspatron: #patron on website but not in database
            #add patron on discord and db
            logger.info(f"🟢 Adding patron role for Discord user: {user.discorduser}")
            requests.put(f'''https://discordapp.com/api/guilds/280713822073913354/members/{user.discordid}/roles/751092271025487942''', headers=headers, data=None)
            setattr(user, 'lichesspatron', True)
            db.session.commit()
            patrons_added.append(user.lichessid)
            continue

print("\n" + "="*50)
print("PATRON CHECK REPORT")
print("="*50)
print(f"Total users checked: {user_count}")
print(f"\nPatrons added ({len(patrons_added)}):")
for user in patrons_added:
    print(f"  - {user}")
print(f"\nPatrons removed ({len(patrons_removed)}):")
for user in patrons_removed:
    print(f"  - {user}")
print("="*50)
