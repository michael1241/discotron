```bash
pip install -r requirements.txt
python discotron.py
```

## Test Docker image locally

```bash
docker build -t discotron  .

docker run -it --rm discotron bash

docker run -it --rm \
    -v $(pwd)/discotron.db:/app/discotron.db \
    -e SECRET_KEY=abc123 \
    -e LICHESS_CLIENT_ID=discotron \
    -e DISCORD_CLIENT_ID=discord-client-id \
    -e DISCORD_CLIENT_SECRET=discord-client-secret \
    -p 5000:5000 \
    discotron
```
