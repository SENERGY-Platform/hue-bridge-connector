FROM python:3-alpine

WORKDIR /usr/src/app

RUN apk update && apk upgrade && apk add --no-cache git

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir cc-lib
RUN touch hue_bridge/bridge.conf

CMD [ "python", "./client.py"]
