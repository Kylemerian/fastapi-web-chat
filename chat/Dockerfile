FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl build-essential libpq-dev

RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /code

COPY pyproject.toml poetry.lock*  /code/

RUN poetry install --no-root --no-interaction --no-ansi

COPY . /code

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "chat.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]