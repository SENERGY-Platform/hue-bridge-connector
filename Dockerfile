FROM python:3-alpine

WORKDIR /usr/src/app

RUN apk update && apk upgrade && apk add --no-cache bash git openssh
RUN git clone https://github.com/SENERGY-Platform/hue-bridge-connector.git .
RUN git checkout dev
RUN mkdir cc-lib
RUN touch hue_bridge/bridge.conf

RUN pip install git+https://github.com/SENERGY-Platform/client-connector-lib.git@dev
RUN pip install requests rgbxy

CMD [ "python", "./client.py"]
