"""Harness entry point for m1-c (Phi-4-mini-instruct QLoRA). Logic lives in ``qlora.py``."""

from models.m1_catchup.qlora import build_eval_runner

__all__ = ["build_eval_runner"]
