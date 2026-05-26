"""AI/ML background task queue.

Long-running inference and data processing tasks run here, off the request thread.
Results are stored in Celery result backend (Redis) and can be polled by the API.
"""
import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="ml.run_inference",
    bind=True,
    max_retries=2,
    time_limit=300,      # 5 min hard limit
    soft_time_limit=240, # 4 min soft limit — send SIGTERM first
    queue="ml",
)
def run_inference(self, model_name: str, inputs: dict, task_id: str | None = None) -> dict:
    """Run a model inference task and return structured output."""
    try:
        logger.info("ml_inference_start", model=model_name, task_id=task_id)

        # Replace with your actual model inference logic
        result = {
            "model": model_name,
            "inputs": inputs,
            "output": None,  # populate from model
            "task_id": task_id,
        }

        logger.info("ml_inference_complete", model=model_name, task_id=task_id)
        return result
    except Exception as exc:
        logger.error("ml_inference_failed", model=model_name, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="ml.process_document",
    bind=True,
    max_retries=1,
    time_limit=600,
    queue="ml",
)
def process_document(self, file_path: str, processing_type: str) -> dict:
    """Process a document (OCR, embedding, classification, etc.)."""
    try:
        logger.info("ml_document_processing", file=file_path, type=processing_type)
        return {"file": file_path, "type": processing_type, "result": None}
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(name="ml.generate_embeddings", bind=True, max_retries=2, queue="ml")
def generate_embeddings(self, texts: list[str], model: str = "text-embedding-3-small") -> dict:
    """Generate vector embeddings for texts via OpenAI or local model."""
    try:
        from app.config.settings import settings

        if settings.OPENAI_API_KEY:
            from openai import OpenAI

            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.embeddings.create(input=texts, model=model)
            embeddings = [e.embedding for e in response.data]
        else:
            embeddings = []
            logger.warning("embeddings_skipped", reason="OPENAI_API_KEY not set")

        return {"texts": len(texts), "model": model, "embeddings": embeddings}
    except Exception as exc:
        raise self.retry(exc=exc)
