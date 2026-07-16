# Machine Learning Platform

## Overview

The ML module builds predictive models on top of the Gold data warehouse. It provides price predictions, product recommendations, demand forecasting, and anomaly detection, all exposed via a dedicated inference API.

## Model Lifecycle

```text
Gold Layer → Feature Engineering → Feature Store
                                      ↓
                              Training / Experiment Tracking
                                      ↓
                              Model Registry (MLflow)
                                      ↓
                              Inference API
                                      ↓
                              Monitoring & Retraining
```

## Primary Models

| Model              | Description                                  | Algorithm(s)           |
| ------------------ | -------------------------------------------- | ---------------------- |
| Price Prediction   | Predict fair market price                    | XGBoost, LightGBM      |
| Recommendation     | Suggest similar parts (metadata + semantic)  | FAISS, Sentence‑BERT   |
| Demand Forecasting | Forecast listing volume by category/region   | Time‑series models     |
| Anomaly Detection  | Flag suspicious discounts, pricing outliers  | Isolation Forest, LOF  |

## Feature Engineering

Transforms raw attributes (age, mileage, discount ratio, shipping ratio) into model‑ready features. Code in `ml/features/`.

## Experiment Tracking

All experiments are logged to MLflow. Track parameters, metrics, and artifacts. Start the UI:
```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## Inference API

A FastAPI service (`ml/inference/app.py`) serves predictions. Endpoints:
- `POST /predict/price`
- `POST /recommend`
- `POST /anomaly`

The API loads the latest production model from the registry.

## Monitoring

- Prediction latency and error rate
- Data drift via statistical tests
- Alerts when model performance degrades (configurable threshold)

## Retraining

Models are retrained when performance drops or new data volume exceeds a threshold. Airflow DAGs schedule weekly retraining.

## Getting Started

```bash
cd ml
pip install -r requirements.txt
python train.py --model price_prediction
python serve.py
```