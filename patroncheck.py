import os
import requests
from discotron import app, db, User
import time

with app.app_context():
    users = User.query.all()

    for user in users:
        while True:
            response = requests.get(f"https://lichess.org/api/user/{user.lichessid}")
            if response.status_code == 429:
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
            continue
        if patron and not user.lichesspatron: #patron on website but not in database
            #add patron on discord and db
            requests.put(f'''https://discordapp.com/api/guilds/280713822073913354/members/{user.discordid}/roles/751092271025487942''', headers=headers, data=None)
            setattr(user, 'lichesspatron', True)
            db.session.commit()
            continue
