import os
import requests

from flask import Flask, session, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix
from authlib.integrations.flask_client import OAuth

from dotenv import load_dotenv
load_dotenv()


def get_env_or_secret(key):
    value = os.getenv(key)
    if value:
        return value
    with open(f"/run/secrets/{key}", "r") as f:
        return f.read().strip()


project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "discotron.db"))

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.secret_key = get_env_or_secret("SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = database_file
db = SQLAlchemy(app)


class User(db.Model):
    lichessid = db.Column(db.String(80), unique=True, nullable=False, primary_key=True)
    lichesspatron = db.Column(db.Boolean(), nullable=False)
    discorduser = db.Column(db.String(80), unique=True, nullable=False)
    discordid = db.Column(db.Integer(), unique=True, nullable=False)

    def __repr__(self):
        return f'{self.discorduser}, {self.discordid}, {self.lichessid}, {self.lichesspatron}'


app.config['LICHESS_CLIENT_ID'] = get_env_or_secret("LICHESS_CLIENT_ID")
app.config['LICHESS_ACCESS_TOKEN_URL'] = 'https://lichess.org/api/token'
app.config['LICHESS_AUTHORIZE_URL'] = 'https://lichess.org/oauth'

app.config["DISCORD_CLIENT_ID"] = get_env_or_secret("DISCORD_CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = get_env_or_secret("DISCORD_CLIENT_SECRET")
app.config["DISCORD_AUTHORIZE_URL"] = 'https://discord.com/api/oauth2/authorize'
app.config["DISCORD_ACCESS_TOKEN_URL"] = 'https://discordapp.com/api/oauth2/token'

oauth = OAuth(app)
oauth.register('lichess', client_kwargs={"code_challenge_method": "S256"})
oauth.register('discord')


@app.route('/')
def start():
    redirect_uri = url_for("authorizediscord", _external=True)
    return oauth.discord.authorize_redirect(redirect_uri, scope="identify", response_type="code")


@app.route('/authorizediscord')
def authorizediscord():
    if request.args.get('error') == 'access_denied':
        return "Discord authorization cancelled"
    token = oauth.discord.authorize_access_token()
    bearer = token['access_token']
    headers = {'Authorization': f'Bearer {bearer}'}
    response = requests.get("https://discord.com/api/users/@me", headers=headers).json()
    session['discorduser'] = f'''{response['username']}#{str(response['discriminator'])}'''
    session['discordid'] = response['id']
    redirect_uri = url_for("authorizelichess", _external=True)
    return oauth.lichess.authorize_redirect(redirect_uri)


@app.route('/authorizelichess')
def authorizelichess():
    token = oauth.lichess.authorize_access_token()
    bearer = token['access_token']
    headers = {'Authorization': f'Bearer {bearer}'}
    response = requests.get("https://lichess.org/api/account", headers=headers).json()
    session['lichessid'] = response['id']
    session['lichesspatron'] = response.get('patron', False)
    session['lichessusername'] = response['username']
    return redirect('outcome')


@app.route('/outcome')
def outcome():
    if not session['lichesspatron']:
        return("The Lichess account you have linked doesn't currently have patron.")
    user = User.query.filter_by(lichessid=session['lichessid']).first()
    if not user:
        # case where switching between lichess accounts, associated with the same discord account
        user = User.query.filter_by(discordid=session['discordid']).first()
    if user:
        session['olddiscordid'] = getattr(user, 'discordid', None)
        session['olddiscorduser'] = getattr(user, 'discorduser', None)
        session['oldlichessid'] = getattr(user, 'lichessid', None)
        db.session.delete(user)
        db.session.commit()
    user = User(lichessid=session['lichessid'],
                lichesspatron=session['lichesspatron'],
                discorduser=session['discorduser'],
                discordid=session['discordid'])
    db.session.add(user)
    db.session.commit()

    headers = {'Authorization': f'Bot {get_env_or_secret("DISCORD_TOKEN")}'}
    olddiscordid = session.get('olddiscordid')
    if olddiscordid:
        if user.discordid == olddiscordid and user.lichessid == session['oldlichessid']:
            requests.put(f'https://discordapp.com/api/guilds/280713822073913354/members/{user.discordid}/roles/751092271025487942', headers=headers, data=None)
            return(f'''Lichess user {session['lichessusername']} is already associated with discord user {user.discorduser} ID: {user.discordid}. Thanks for your support!''')
        if user.discordid != olddiscordid and user.lichessid == session['oldlichessid']:
            requests.delete(f'''https://discordapp.com/api/guilds/280713822073913354/members/{olddiscordid}/roles/751092271025487942''', headers=headers, data=None)
            requests.put(f'https://discordapp.com/api/guilds/280713822073913354/members/{user.discordid}/roles/751092271025487942', headers=headers, data=None)
            return(f'''Lichess user {session['lichessusername']} was associated with discord user {session['olddiscorduser']} and now is associated with {user.discorduser}. Thanks for your support!''')
        if user.discordid == olddiscordid and user.lichessid != session['oldlichessid']:
            requests.put(f'https://discordapp.com/api/guilds/280713822073913354/members/{user.discordid}/roles/751092271025487942', headers=headers, data=None)
            return(f'''Discord user {session['discorduser']} was associated with Lichess user {session['oldlichessid']} and now is associated with {user.lichessid}. Thanks for your support!''')
    requests.put(f'https://discordapp.com/api/guilds/280713822073913354/members/{user.discordid}/roles/751092271025487942', headers=headers, data=None)
    return(f'''Lichess user {session['lichessusername']} is now associated with {user.discorduser}. Thanks for your support!''')


if __name__ == '__main__':
    app.run(host='0.0.0.0')
