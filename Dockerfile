FROM python:3-slim

MAINTAINER Kell <maybe.hello.world@gmail.com>

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py bot.py

CMD ["python", "./bot.py"]