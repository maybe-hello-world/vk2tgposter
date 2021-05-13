FROM python:3.9-slim

MAINTAINER Kell <maybe.hello.world@gmail.com>

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py bot.py
COPY Telebot429Wrapper.py Telebot429Wrapper.py

CMD ["python", "./bot.py"]