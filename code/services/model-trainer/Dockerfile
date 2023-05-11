FROM ubuntu:22.04

ENV GIT_REPO git@github.com:MSE-PI/MLodImage.git

ENV PYTHONUNBUFFERED=1

# update and install ssh client
RUN apt update -y && apt install openssh-client -y && apt install python3-pip -y && apt install git -y

# Authorize SSH Host
RUN mkdir -p /root/.ssh && \
    chmod 0700 /root/.ssh && \
    ssh-keyscan github.com > /root/.ssh/known_hosts

ADD ./id_rsa /root/.ssh/id_rsa

# Add the keys and set permissions
RUN chmod 600 /root/.ssh/id_rsa

# launch the script
CMD ["cat", "/root/.ssh/id_rsa"]
#CMD ["git", "clone", "-b", "train-model", "git@github.com:MSE-PI/MLodImage.git" , "app"]
#CMD ["python3", "/app/code/services/model-trainer/trainer.py"]