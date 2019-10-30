ARG branch

FROM python:3-alpine

WORKDIR /usr/src/app

RUN apk update && apk upgrade && apk add --no-cache git

COPY requirements.txt ./
RUN pip install git+https://github.com/SENERGY-Platform/client-connector-lib.git@${branch}
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir cc-lib
RUN mkdir storage

CMD [ "python", "./client.py"]
