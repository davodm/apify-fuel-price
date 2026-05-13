# Apify Python Actor base image (includes runtime conventions for the platform).
# See: https://docs.apify.com/sdk/python/docs/overview
FROM apify/actor-python:3.12

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

CMD ["python", "-m", "src.main"]
