"""Harness entry point for m1-d (Qwen3.5-4B conditional-generation QLoRA). Logic: ``qlora.py``."""

from models.m1_catchup.qlora import build_eval_runner

__all__ = ["build_eval_runner"]
