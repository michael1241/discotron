from discotron import User, app
from tabulate import tabulate

with app.app_context():
    users = User.query.all()

    table_data = []
    for user in users:
        table_data.append([
            user.discorduser,
            user.discordid,
            user.lichessid,
            "✅" if user.lichesspatron else "❌"
        ])
    headers = ["Discord User", "Discord ID", "Lichess ID", "Lichess Patron"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
