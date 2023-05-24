FROM ubuntu:22.04

ENV PYTHONUNBUFFERED=1
ENV GIT_USER=-
ENV GIT_PASSWORD=-

# update and install ssh client
RUN apt update -y && apt install python3-pip -y && apt install git -y && apt install -y gettext

# install python dependencies
COPY ./requirements.txt .

RUN pip3 install -r requirements.txt

COPY ./train.sh .
RUN chmod +x train.sh

# launch the training script
CMD sh ./train.sh