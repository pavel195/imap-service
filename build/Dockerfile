FROM python:3.10-slim

RUN adduser web

WORKDIR /app

COPY ./Pipfile .
COPY ./Pipfile.lock .

RUN apt-get update && apt-get install -y vim \
    && python -m pip install --upgrade pip \
	&& pip install -U pip \
    && pip install gunicorn \
    && pip install pipenv \
    && pipenv install --system

COPY . .

RUN chown -R web:web ./
RUN chmod +x ./boot.sh
USER web

EXPOSE 5000
