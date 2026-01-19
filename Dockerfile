FROM python:3.14.2-alpine3.23

RUN apk add --no-cache \
    bash \
    sqlite

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

CMD ["python", "discotron.py"]
