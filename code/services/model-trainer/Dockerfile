FROM ubuntu:22.04

ENV PYTHONUNBUFFERED=1
ENV SSH_PRIVATE=""

# update and install ssh client
RUN apt update -y && apt upgrade -y && apt install openssh-client && apt install python3-pip -y

# Authorize SSH Host
RUN mkdir -p /root/.ssh && \
    chmod 0700 /root/.ssh && \
    ssh-keyscan github.com > /root/.ssh/known_hosts

# Add the keys and set permissions
RUN echo "SSH_PRIVATE" > /root/.ssh/id_rsa && \
    chmod 600 /root/.ssh/id_rsa

WORKDIR /app

# install requirements (DVC)
#RUN "pip install dvc"

# copy all the files
COPY . /app

# launch the script
CMD ["python3", "/app/trainer.py"]