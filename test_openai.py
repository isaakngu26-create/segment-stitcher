#!/usr/bin/env python3
"""Test script to verify OpenAI client initialization."""
import os
from openai import OpenAI

# Test 1: Check if API key is available
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print("✓ OPENAI_API_KEY environment variable is set")
else:
    print("✗ OPENAI_API_KEY environment variable is NOT set")
    print("  Set it with: export OPENAI_API_KEY=sk-...")

# Test 2: Try to initialize the client
try:
    client = OpenAI(api_key=api_key or "test-key")
    print("✓ OpenAI client initialized successfully")
except Exception as e:
    print(f"✗ Error initializing OpenAI client: {e}")

# Test 3: Check reconciler module imports
try:
    from src.reconciliation.llm_reconciler import reconcile_segments, FUNCTION_SCHEMA
    print("✓ Reconciler module imports successfully")
    print(f"  Function schema has keys: {list(FUNCTION_SCHEMA.keys())}")
except Exception as e:
    print(f"✗ Error importing reconciler module: {e}")

print("\nDone!")
