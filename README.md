
# FraudShield AI

**An end-to-end financial fraud intelligence and transaction risk platform.**

FraudShield AI is a portfolio project combining data science, machine learning, explainable AI and backend engineering to support financial transaction fraud detection and investigation.

## Project Objectives

- Detect potentially fraudulent financial transactions.
- Generate transaction-level risk scores.
- Explain predictions using Explainable AI.
- Identify suspicious transaction networks.
- Support fraud alert investigation workflows.
- Monitor data quality and model performance.

## Technology Stack

| Layer | Technology |
|---|---|
| Programming | Python |
| API | FastAPI |
| Database | PostgreSQL |
| Caching | Redis |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn, LightGBM |
| Explainability | SHAP |
| Graph Analytics | NetworkX |
| Dashboard | Streamlit |
| Infrastructure | Docker, Docker Compose |
| Testing | Pytest |
| Version Control | Git, GitHub |

## Current Development Status

- [x] Project structure
- [x] Docker development environment
- [x] PostgreSQL integration
- [x] Redis integration
- [x] FastAPI application
- [x] Health and readiness endpoints
- [x] Automated API tests
- [ ] Transaction data ingestion
- [ ] Data validation and feature engineering
- [ ] Fraud detection models
- [ ] Model explainability
- [ ] Fraud network analysis
- [ ] Investigation dashboard
- [ ] Model monitoring
- [ ] CI/CD pipeline

## Getting Started

### Prerequisites

- Docker Engine
- Docker Compose
- Git

### Installation

Clone the repository and enter the project directory.

Create your environment file:

```bash
cp .env.example .env
```

Configure a secure PostgreSQL password in `.env`.

Start the application:

```bash
docker compose up -d --build
```

Check the services:

```bash
docker compose ps
```

API documentation:

http://localhost:8000/docs

Check API readiness:

```bash
curl http://localhost:8000/ready
```

Run automated tests:

```bash
docker compose exec api pytest tests/ -v
```

## Data and Evaluation

The project will use publicly available datasets with documented provenance and licensing.

Model development will consider:

- Class imbalance
- Temporal train/test splits
- Data leakage prevention
- Precision and recall
- F1-score
- PR-AUC
- Cost-sensitive evaluation

## Responsible Use

FraudShield AI is an educational and portfolio project. It is not connected to a real financial institution and is not intended for production financial decision-making.

## Author

**Sourav Gupta**

GitHub: https://github.com/souravgupta166
