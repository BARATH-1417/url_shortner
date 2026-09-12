# URL Shortener

A simple URL Shortener built using FastAPI and PostgreSQL.

## Technologies Used

- Python
- FastAPI
- PostgreSQL
- Uvicorn
- Pydantic

## Features

- Convert long URLs into short URLs
- Redirect short URLs to original URLs
- Store URLs in PostgreSQL
- Track URL clicks

## Run Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
