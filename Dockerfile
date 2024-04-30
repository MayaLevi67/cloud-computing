FROM python:3.9-slim

# set the working directory in the container
WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PORT=8000

CMD flask run --host=0.0.0.0 --port=$PORT
