FROM python:3.11

COPY ./Pipfile* /

RUN pip install --no-cache-dir pipenv && pipenv install

COPY ./app /app

EXPOSE 5000
WORKDIR /app
ENTRYPOINT ["pipenv","run","waitress-serve", "--host=0.0.0.0", "--port=5000", "main:app"]
