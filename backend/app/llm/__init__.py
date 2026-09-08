"""Runtime LLM access.

`base` defines the provider-neutral interface AKILI programs against. Concrete
providers live beside it and are selected by configuration in `factory`. Nothing
outside this package imports a provider SDK.
"""
