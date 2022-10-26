FROM python:3.9-slim

RUN apt-get -y update && apt-get install -y ffmpeg && apt-get install tzdata -y

COPY . /app
WORKDIR /app

RUN pip install pipenv==2021.5.29
RUN pipenv install --system --skip-lock

CMD ["python", "bot/main.py"]
