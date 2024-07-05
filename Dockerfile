#docker stop globalbot
#docker rm globalbot

#docker build --no-cache . -t globalbot-image

#run using bind mount
#docker run --name globalbot --mount type=bind,source="D:\GlobalBot Database",target=/database --restart=unless-stopped globalbot-image

#run using volume
#docker run --name globalbot -v globalbot-db:/database --restart=unless-stopped globalbot-image

FROM python:3.11-slim

COPY .env .
COPY GlobalBot.py .
COPY requirements.txt .

RUN pip install -r requirements.txt

RUN apt-get update
RUN apt-get -y install tesseract-ocr

CMD ["python", "-u", "./GlobalBot.py"]