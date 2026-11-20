import asyncio
from act.core.llm import LLMClient


async def main():
    client = LLMClient()  # env var подхватится сам
    print(f"URL:  {client.url}")
    print(f"Модель: {client.model}")

    print("\nЗапрос к LLM...")
    async for token in client.stream_ask_generator([
        {"role": "user", "content": "Представься в одном предложении."}
    ]):
        print(token, end="", flush=True)
    print()
    await client.close_stream_client()


if __name__ == "__main__":
    asyncio.run(main())