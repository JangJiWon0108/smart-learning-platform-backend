from __future__ import annotations

from .properties import Settings


def get_adk_model(settings: Settings, *, purpose: str) -> str:
    match purpose:
        case "intent":
            return settings.GEMINI_MODEL_TYPE
        case "solver":
            return settings.GEMINI_MODEL_TYPE_SOLVER
        case "curator":
            return settings.GEMINI_MODEL_TYPE_CURATOR
        case "tracer":
            return settings.GEMINI_MODEL_TYPE_TRACER
        case _:
            return settings.GEMINI_MODEL_TYPE
