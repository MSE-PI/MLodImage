FROM python:3.10

EXPOSE 8000

LABEL org.opencontainers.image.source = "https://github.com/MSE-PI/MLodImage"

ENV PYTHONUNBUFFERED=1
ENV MINIO_USR=x
ENV MINIO_PWD=x

WORKDIR /app

RUN apt-get update -y  && apt-get install git -y
RUN apt-get install -y ffmpeg

# copy requirements.txt
COPY ./requirements.txt /app/requirements.txt

# install packages from requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# copy all the files
COPY . /app

# launch the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]