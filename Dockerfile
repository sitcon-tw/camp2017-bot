FROM python:3.6
MAINTAINER Denny Huang

COPY ./requirements.txt /requirements.txt

RUN pip install --no-cache-dir -r /requirements.txt

COPY ./app /app

EXPOSE 5000
WORKDIR /app
ENV FLASK_APP main.py
CMD ["/usr/local/bin/flask", "run", "--host=0.0.0.0"]
