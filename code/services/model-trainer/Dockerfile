FROM ubuntu:22.04

ENV PYTHONUNBUFFERED=1

# update and install ssh client
RUN apt update -y && apt install openssh-client -y && apt install python3-pip -y && apt install git -y

# Authorize SSH Host
RUN mkdir -p /root/.ssh && \
    chmod 0700 /root/.ssh && \
    ssh-keyscan github.com > /root/.ssh/known_hosts

# https://gist.github.com/perja12/a3f41046e618f031a65b02e6c17e75d8
# ==> convert key to correct format !!!
ENV SSH_PRIVATE "-"

COPY ./add_key.sh .
RUN chmod +x add_key.sh

RUN touch /root/.ssh/id_rsa
RUN chmod 600 root/.ssh/id_rsa

# add SSH key using shell script
CMD ["sh", "add_key.sh"]

# clone the repo and launch the trainer script
CMD ["git", "clone", "-b", "develop", "git@github.com:MSE-PI/MLodImage.git" , "app"]
CMD ["python3", "/app/code/services/model-trainer/trainer.py"]