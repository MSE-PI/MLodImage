FROM ubuntu:22.04

ENV PYTHONUNBUFFERED=1
ENV GIT_USER=-
ENV GIT_PASSWORD=-

# update and install ssh client
RUN apt update -y && apt install openssh-client -y && apt install python3-pip -y && apt install git -y

COPY ./clone_repo.sh .
RUN chmod +x clone_repo.sh

# clone the repo and launch the trainer script
CMD ["sh", "./clone_repo.sh"]
CMD ["python3", "/app/code/services/model-trainer/trainer.py"]