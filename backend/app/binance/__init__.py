"""AKILI's own Binance Agentic MCP integration — behind an adapter boundary.

Phase 6.2: AKILI can *start* its own OAuth authorization with Binance, as an
independent public client identified by its Client ID Metadata Document. It
does not yet receive the callback, exchange a code, store a token, open an MCP
session, or read any account data.

AKILI never uses, reads, or proxies any other application's Binance
authorization (including Claude Code's). Everything here is AKILI's own.
"""
