import os
import requests
import logging
from discotron import app, db, User
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

with app.app_context():
    users = User.query.all()
    patrons_added = []
    patrons_removed = []

    for user in users:
        while True:
            response = requests.get(f"https://lichess.org/api/user/{user.lichessid}")
            if response.status_code == 429:
                logger.warning(f"Rate limited by Lichess API, sleeping for 2 minutes...")
                time.sleep(60*2) #sleep if getting ratelimited
                continue #try again
            time.sleep(1) #sleep to avoid ratelimiting
            break
        patron = response.json().get('patron', False)
        if patron == user.lichesspatron: #db is correct
            continue
        headers = {'Authorization': f'Bot {os.getenv("DISCORD_TOKEN")}'}
        if not patron and user.lichesspatron: #patron in database but not on website
            #remove patron on discord and db
            requests.delete(f'''https://discordapp.com/api/guilds/280713822073913354/members/{user.discordid}/roles/751092271025487942''', headers=headers, data=None)
            setattr(user, 'lichesspatron', False)
            db.session.commit()
            patrons_removed.append(user)
            continue
        if patron and not user.lichesspatron: #patron on website but not in database
            #add patron on discord and db
            requests.put(f'''https://discordapp.com/api/guilds/280713822073913354/members/{user.discordid}/roles/751092271025487942''', headers=headers, data=None)
            setattr(user, 'lichesspatron', True)
            db.session.commit()
            patrons_added.append(user)
            continue

    print("\n" + "="*50)
    print("PATRON CHECK REPORT")
    print("="*50)
    print(f"Total users checked: {len(users)}")
    print(f"\nPatrons added ({len(patrons_added)}):")
    for user in patrons_added:
        print(f"  - Discord: {user.discordid}, Lichess: {user.lichessid}")
    print(f"\nPatrons removed ({len(patrons_removed)}):")
    for user in patrons_removed:
        print(f"  - Discord: {user.discordid}, Lichess: {user.lichessid}")
    print("="*50)
