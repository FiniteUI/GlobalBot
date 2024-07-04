#docker build --no-cache . -t globalbot-image

#run using bind mount
#docker run --name globalbot --mount type=bind,source="D:\GlobalBot Database",target=/database --restart=unless-stopped globalbot-image

#run using volume
#helper container to populate volumne, from directory with database
#docker run -v globalbot-db:/database --name helper busybox true
#docker cp . helper:/database
#docker rm helper
#docker run --name globalbot -v globalbot-db:/database --restart=unless-stopped globalbot-image

FROM python:3.11

COPY .env .
COPY GlobalBot.py .
COPY requirements.txt .

RUN pip install -r requirements.txt

CMD ["python", "-u", "./GlobalBot.py"]