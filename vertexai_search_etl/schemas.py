"""Schemas for Vertex AI Search ETL utilities."""

from __future__ import annotations

from pydantic import BaseModel


class DatastoreBuildResponse(BaseModel):
    """Summary returned after building a Vertex AI Search NDJSON file."""

    input_path: str
    output_path: str
    written: int
    skipped: int


class DatastoreValidationResponse(BaseModel):
    """Summary returned after validating a Vertex AI Search NDJSON file."""

    jsonl_path: str
    record_count: int


class DatastoreUploadResponse(BaseModel):
    """Summary returned after uploading a Vertex AI Search NDJSON file."""

    jsonl_path: str
    record_count: int
    dry_run: bool
    uploaded: bool
