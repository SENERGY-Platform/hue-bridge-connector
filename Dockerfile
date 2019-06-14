FROM python:3-alpine

WORKDIR /usr/src/app

RUN apk update && apk upgrade && apk add --no-cache git
#RUN git clone https://github.com/SENERGY-Platform/hue-bridge-connector.git .
#RUN git checkout dev

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir cc-lib
RUN touch hue_bridge/bridge.conf

#RUN pip install git+https://github.com/SENERGY-Platform/client-connector-lib.git@dev
#RUN pip install requests rgbxy

CMD [ "python", "./client.py"]
