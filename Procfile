web: uvicorn app.main:app --host=0.0.0.0 --port=${PORT:-8000}
worker: python -m app.workers.transformation_worker