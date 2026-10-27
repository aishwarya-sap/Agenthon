"""Pytest fixtures shared across all tests."""
import os

# Force mock mode for all tests — no credentials, no SAP, no AI Core
os.environ["IBD_TESTING"] = "1"
os.environ["AGENT_AUTH_MODE"] = "mock"
