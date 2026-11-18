from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True
)

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True
)

app = FastAPI(
    title="FraudShield AI",
    description="Financial fraud intelligence and transaction risk API",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "application": "FraudShield AI",
        "version": "0.1.0",
        "status": "operational"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/ready")
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        redis_client.ping()

        return {
            "status": "ready",
            "services": {
                "postgresql": "connected",
                "redis": "connected"
            }
        }

    except (SQLAlchemyError, RedisError):
        raise HTTPException(
            status_code=503,
            detail="One or more dependencies are unavailable"
        )


@app.get("/api/v1/info")
def application_info():
    return {
        "name": "FraudShield AI",
        "version": "0.1.0",
        "purpose": "Financial transaction fraud detection",
        "capabilities": [
            "Transaction risk scoring",
            "Fraud network intelligence",
            "Explainable AI",
            "Fraud investigation"
        ]
    }
