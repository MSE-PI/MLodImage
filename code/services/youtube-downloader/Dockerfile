FROM python:3.10

EXPOSE 8000

LABEL org.opencontainers.image.source = "https://github.com/MSE-PI/MLodImage"

ENV PYTHONUNBUFFERED=1
ENV MINIO_USR=x
ENV MINIO_PWD=x

WORKDIR /app

# copy requirements.txt
COPY ./requirements.txt /app/requirements.txt

# install packages from requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# replace cipher.py file in pytube library to fix regex error https://github.com/pytube/pytube/pull/1646
COPY ./cipher.py /usr/local/lib/python3.10/site-packages/pytube/cipher.py

# copy all the files
COPY . /app

# launch the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
