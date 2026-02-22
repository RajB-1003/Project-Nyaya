import asyncio
from web_fetcher import fetch_government_context

async def test():
    for intent in ["RTI", "Domestic Violence", "Divorce"]:
        ctx, sources = await fetch_government_context(intent)
        source_label = "WEB+RAG" if ctx else "RAG (fallback)"
        print(f"\n=== {intent} ===")
        print(f"context_source: {source_label}")
        print(f"Sources used: {sources}")
        print(f"Content chars: {len(ctx)}")
        if ctx:
            print(f"Preview (first 200 chars): {ctx[:200]}")

asyncio.run(test())
