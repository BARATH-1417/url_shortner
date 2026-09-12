from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
import psycopg2
import os
import string
import random


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL is not configured in .env")


# =========================================================
# CREATE FASTAPI APP
# =========================================================

app = FastAPI(
    title="Cloud URL Shortener",
    description="URL Shortener using FastAPI and PostgreSQL",
    version="1.0.0"
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    return psycopg2.connect(DATABASE_URL)


# =========================================================
# CREATE DATABASE TABLE
# =========================================================

def create_table():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY,
            original_url TEXT NOT NULL,
            short_code VARCHAR(10) UNIQUE NOT NULL,
            clicks INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    cursor.close()
    conn.close()


# Create table when application starts
create_table()


# =========================================================
# REQUEST MODEL
# =========================================================

class URLRequest(BaseModel):
    url: HttpUrl


# =========================================================
# GENERATE UNIQUE SHORT CODE
# =========================================================

def generate_short_code(length=6):

    characters = string.ascii_letters + string.digits

    while True:

        short_code = "".join(
            random.choices(characters, k=length)
        )

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id
            FROM urls
            WHERE short_code = %s
            """,
            (short_code,)
        )

        result = cursor.fetchone()

        cursor.close()
        conn.close()

        # If code doesn't already exist
        if result is None:
            return short_code


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "message": "Cloud URL Shortener is running",
        "status": "success"
    }


# =========================================================
# CREATE SHORT URL
# =========================================================

@app.post("/shorten")
def shorten_url(data: URLRequest):

    original_url = str(data.url)

    # Generate unique code
    short_code = generate_short_code()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO urls (original_url, short_code)
        VALUES (%s, %s)
        RETURNING id
        """,
        (original_url, short_code)
    )

    url_id = cursor.fetchone()[0]

    conn.commit()

    cursor.close()
    conn.close()

    return {
        "id": url_id,
        "original_url": original_url,
        "short_code": short_code,
        "short_url": f"http://127.0.0.1:8000/{short_code}"
    }


# =========================================================
# REDIRECT SHORT URL
# =========================================================

@app.get("/{short_code}")
def redirect_url(short_code: str):

    conn = get_connection()
    cursor = conn.cursor()

    # Find original URL
    cursor.execute(
        """
        SELECT original_url
        FROM urls
        WHERE short_code = %s
        """,
        (short_code,)
    )

    result = cursor.fetchone()

    if result is None:

        cursor.close()
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Short URL not found"
        )

    original_url = result[0]

    # Increase click count
    cursor.execute(
        """
        UPDATE urls
        SET clicks = clicks + 1
        WHERE short_code = %s
        """,
        (short_code,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    # Redirect user
    return RedirectResponse(
        url=original_url,
        status_code=307
    )


# =========================================================
# GET URL STATISTICS
# =========================================================

@app.get("/stats/{short_code}")
def get_statistics(short_code: str):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            original_url,
            short_code,
            clicks,
            created_at
        FROM urls
        WHERE short_code = %s
        """,
        (short_code,)
    )

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Short URL not found"
        )

    return {
        "id": result[0],
        "original_url": result[1],
        "short_code": result[2],
        "clicks": result[3],
        "created_at": result[4]
    }


# =========================================================
# GET ALL URLS
# =========================================================

@app.get("/urls/all")
def get_all_urls():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            original_url,
            short_code,
            clicks,
            created_at
        FROM urls
        ORDER BY id DESC
        """
    )

    results = cursor.fetchall()

    cursor.close()
    conn.close()

    urls = []

    for row in results:

        urls.append({
            "id": row[0],
            "original_url": row[1],
            "short_code": row[2],
            "short_url": f"http://127.0.0.1:8000/{row[2]}",
            "clicks": row[3],
            "created_at": row[4]
        })

    return {
        "total_urls": len(urls),
        "urls": urls
    }


# =========================================================
# DELETE SHORT URL
# =========================================================

@app.delete("/delete/{short_code}")
def delete_url(short_code: str):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM urls
        WHERE short_code = %s
        RETURNING id
        """,
        (short_code,)
    )

    result = cursor.fetchone()

    conn.commit()

    cursor.close()
    conn.close()

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Short URL not found"
        )

    return {
        "message": "Short URL deleted successfully",
        "short_code": short_code
    }