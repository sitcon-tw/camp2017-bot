FROM python:3.11

RUN curl -sSL https://install.python-poetry.org/ | python3 -

ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root
COPY ./app /app

EXPOSE 5000
WORKDIR /app
ENTRYPOINT ["poetry", "run","waitress-serve", "--host=0.0.0.0", "--port=5000", "main:app"]
