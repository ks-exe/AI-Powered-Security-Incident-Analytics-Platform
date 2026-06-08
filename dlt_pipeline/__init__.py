"""DLT Ingestion Pipeline.

Loads raw security events from JSONL files into the Bronze layer
with metadata enrichment, dead letter routing, and idempotent operation.
"""
