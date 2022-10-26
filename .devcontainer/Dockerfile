ARG VARIANT="3.9"
FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}

RUN apt-get -y update && apt-get install -y ffmpeg && apt-get install tzdata -y

COPY Pipfile* /tmp/pip-tmp/
RUN cd /tmp/pip-tmp && pip install pipenv==2021.5.29 \
 && pipenv install --dev --deploy --system --ignore-pipfile --skip-lock