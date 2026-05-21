"""
EaseTinker — Python Worker
FastAPI service that wraps the Tinker SDK for fine-tuning orchestration.
"""
import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from schemas import (
    StartJobRequest,
    JobStatusResponse,
    HealthResponse,
    ValidateTinkerKeyRequest,
    ValidateTinkerKeyResponse,
    RecommendRequest,
    RecommendResponse,
)
from job_runner import JobRunner

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("easetinker.worker")

# ─── Config ───────────────────────────────────────────────────────────────────
WORKER_SECRET = os.environ.get("WORKER_SECRET", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# ─── Auth ─────────────────────────────────────────────────────────────────────
security = HTTPBearer()

def verify_secret(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify the shared secret from Next.js."""
    if not WORKER_SECRET:
        raise HTTPException(status_code=500, detail="Worker secret not configured")
    if credentials.credentials != WORKER_SECRET:
        raise HTTPException(status_code=401, detail="Invalid worker secret")
    return credentials.credentials

# ─── App lifecycle ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Worker starting up...")
    app.state.runner = JobRunner(redis_url=REDIS_URL)
    yield
    logger.info("Worker shutting down...")

# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="EaseTinker Worker",
    description="Internal Python worker for Tinker SDK orchestration",
    version="0.1.0",
    docs_url=None,  # Disable in production
    redoc_url=None,
    lifespan=lifespan,
)

# Only allow internal Next.js calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # No external origins
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint (no auth required)."""
    return HealthResponse(status="ok")


# Serialize validation calls: the Tinker SDK reads TINKER_API_KEY from process
# env, so we can't safely run two validations with different keys in parallel.
_tinker_validate_lock = asyncio.Lock()

VALIDATE_TIMEOUT_SECONDS = 20.0


def _enrich_supported_models(models: list[dict]) -> list[dict]:
    """Merge tinker-cookbook metadata into each SDK model entry.

    Cookbook may not know every model the SDK reports (it lags new releases),
    so each lookup is best-effort and falls back to the bare SDK fields.
    """
    try:
        from tinker_cookbook import model_info
    except ImportError:
        logger.warning("tinker_cookbook unavailable; serving unenriched supported_models")
        return models

    enriched: list[dict] = []
    for m in models:
        # SDK field name varies — try the common ones, fall back to "unknown" so
        # ModelMeta.name (required) is always populated.
        name = m.get("model_name") or m.get("name") or m.get("id") or "unknown"
        out = {**m, "name": name}
        try:
            attrs = model_info.get_model_attributes(name)
            out.update(
                organization=attrs.organization,
                version_str=attrs.version_str,
                size_str=attrs.size_str,
                is_chat=attrs.is_chat,
                is_vl=attrs.is_vl,
                recommended_renderer=attrs.recommended_renderers[0]
                if attrs.recommended_renderers else None,
            )
        except Exception as e:
            logger.debug("No cookbook metadata for %s: %s", name, e)
        enriched.append(out)
    return enriched


def _classify_tinker_error(msg: str) -> str:
    """Turn a raw SDK error string into a user-friendly message."""
    low = msg.lower()
    if "billing" in low or "payment" in low or " 402" in msg or "code: 402" in msg:
        return (
            "Your Tinker account has billing paused. Add a payment method at "
            "https://tinker-console.thinkingmachines.ai/billing/balance and try again."
        )
    if " 401" in msg or "unauthorized" in low or "invalid api key" in low:
        return "Tinker rejected the API key as unauthorized. Double-check the key on the Tinker console."
    if " 403" in msg or "forbidden" in low:
        return "Tinker returned 403 Forbidden. The key may not have access to this resource."
    if " 404" in msg:
        return "Tinker endpoint returned 404. Check that the SDK version matches the server."
    return f"Tinker rejected the request: {msg}"


@app.post(
    "/tinker/validate",
    response_model=ValidateTinkerKeyResponse,
    dependencies=[Depends(verify_secret)],
)
async def validate_tinker_key(req: ValidateTinkerKeyRequest):
    """Validate a Tinker API key by querying server capabilities."""
    async with _tinker_validate_lock:
        try:
            import tinker
            os.environ["TINKER_API_KEY"] = req.api_key
            client = tinker.ServiceClient()
            try:
                caps = await asyncio.wait_for(
                    client.get_server_capabilities_async(),
                    timeout=VALIDATE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.warning("Tinker validation timed out after %.0fs", VALIDATE_TIMEOUT_SECONDS)
                return ValidateTinkerKeyResponse(
                    valid=False,
                    error=(
                        f"Timed out talking to Tinker after {int(VALIDATE_TIMEOUT_SECONDS)}s. "
                        "The most common cause is billing paused on the account — "
                        "check https://tinker-console.thinkingmachines.ai/billing/balance"
                    ),
                )
            supported = getattr(caps, "supported_models", None)
            max_batch = getattr(caps, "max_batch_size", None)
            # supported_models items may be pydantic objects — coerce to dict/list,
            # then merge cookbook metadata so the UI can group / badge models.
            if supported is not None:
                try:
                    supported = [
                        m.model_dump() if hasattr(m, "model_dump") else m
                        for m in supported
                    ]
                    supported = _enrich_supported_models(supported)
                except Exception:
                    logger.exception("Failed to normalize supported_models; serving raw SDK output")
            logger.info(f"Tinker key validated, {len(supported) if supported else 0} models")
            return ValidateTinkerKeyResponse(
                valid=True,
                supported_models=supported,
                max_batch_size=max_batch,
            )
        except Exception as e:
            raw = str(e)
            logger.warning(f"Tinker key validation failed: {raw}")
            return ValidateTinkerKeyResponse(valid=False, error=_classify_tinker_error(raw))


@app.post(
    "/tinker/recommend",
    response_model=RecommendResponse,
    dependencies=[Depends(verify_secret)],
)
async def recommend_hyperparams(req: RecommendRequest):
    """Return cookbook-recommended hyperparameters for a base model + LoRA config.

    Each cookbook call is wrapped: uncalibrated or unknown models yield notes
    instead of an error, so the UI can fall back to manual entry gracefully.
    """
    notes: list[str] = []
    lr: float | None = None
    param_count: int | None = None
    renderer: str | None = None

    try:
        from tinker_cookbook import hyperparam_utils, model_info
    except ImportError:
        return RecommendResponse(notes=["tinker_cookbook not installed in worker image"])

    try:
        lr = hyperparam_utils.get_lr(req.base_model, is_lora=True)
    except NotImplementedError as e:
        notes.append(f"Learning rate not calibrated for this model: {e}")
    except Exception as e:
        notes.append(f"Could not compute learning rate: {e}")

    try:
        param_count = hyperparam_utils.get_lora_param_count(
            req.base_model,
            lora_rank=req.lora_rank,
            train_mlp=req.train_mlp,
            train_attn=req.train_attn,
            train_unembed=req.train_unembed,
        )
    except Exception as e:
        notes.append(f"Could not compute LoRA parameter count: {e}")

    try:
        renderer = model_info.get_recommended_renderer_name(req.base_model)
    except Exception as e:
        notes.append(f"Could not determine renderer: {e}")

    return RecommendResponse(
        learning_rate=lr,
        lora_param_count=param_count,
        recommended_renderer=renderer,
        notes=notes,
    )


@app.post("/jobs/start", dependencies=[Depends(verify_secret)])
async def start_job(request: StartJobRequest):
    """
    Start a training job.
    Called by Next.js when user clicks 'Start Training'.
    """
    runner: JobRunner = app.state.runner
    try:
        job_id = await runner.start_job(request)
        logger.info(f"Started job {job_id} for project {request.project_id}")
        return {"job_id": job_id, "status": "started"}
    except Exception as e:
        logger.error(f"Failed to start job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/status", response_model=JobStatusResponse, dependencies=[Depends(verify_secret)])
async def get_job_status(job_id: str):
    """Get current status of a training job."""
    runner: JobRunner = app.state.runner
    status = await runner.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@app.post("/jobs/{job_id}/stop", dependencies=[Depends(verify_secret)])
async def stop_job(job_id: str):
    """Cancel a running training job."""
    runner: JobRunner = app.state.runner
    await runner.stop_job(job_id)
    logger.info(f"Stopped job {job_id}")
    return {"job_id": job_id, "status": "stopping"}
