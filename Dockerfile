FROM python:3.9

WORKDIR /app

COPY . .

RUN python3 -m pip install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 50053

ENTRYPOINT ["python3", "server.py"]
