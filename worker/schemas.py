"""
Pydantic schemas for the EaseTinker worker API.
"""
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ValidateTinkerKeyRequest(BaseModel):
    api_key: str = Field(..., description="Tinker API key to validate")


class ModelMeta(BaseModel):
    """SDK-reported model entry enriched with tinker-cookbook metadata when available."""
    model_config = ConfigDict(extra="allow")  # preserve SDK passthrough fields

    name: str
    organization: Optional[str] = None
    version_str: Optional[str] = None
    size_str: Optional[str] = None
    is_chat: Optional[bool] = None
    is_vl: Optional[bool] = None
    recommended_renderer: Optional[str] = None


class ValidateTinkerKeyResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
    supported_models: Optional[list[ModelMeta]] = None
    max_batch_size: Optional[int] = None


class RecommendRequest(BaseModel):
    base_model: str = Field(..., description="HuggingFace-style model id, e.g. 'meta-llama/Llama-3.1-8B'")
    lora_rank: int = Field(default=32, ge=1, le=256)
    train_mlp: bool = True
    train_attn: bool = True
    train_unembed: bool = True


class RecommendResponse(BaseModel):
    learning_rate: Optional[float] = None
    lora_param_count: Optional[int] = None
    recommended_renderer: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class StartJobRequest(BaseModel):
    job_id: str = Field(..., description="Database job ID from Next.js")
    project_id: str
    tinker_api_key: str = Field(..., description="Decrypted Tinker API key")
    base_model: str = Field(..., example="Qwen/Qwen3-8B")
    lora_rank: int = Field(default=32, ge=1, le=256)
    learning_rate: float = Field(default=1e-4, gt=0)
    epochs: int = Field(default=3, ge=1, le=100)
    batch_size: int = Field(default=4, ge=1, le=64)
    loss_function: str = Field(default="cross_entropy")
    training_data: list[dict] = Field(..., description="List of {prompt, completion} dicts")


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    current_epoch: Optional[int] = None
    current_loss: Optional[float] = None
    checkpoint_path: Optional[str] = None
    error_msg: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
