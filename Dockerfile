FROM python:3.8-slim-buster

WORKDIR /app

ADD . /app

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y curl

RUN echo 'while ! curl -s http://elasticsearch:9200 > /dev/null; do sleep 1; done' > wait-for-es.sh

EXPOSE 80

CMD /bin/sh wait-for-es.sh && uvicorn main:app --host 0.0.0.0 --port 80