# main.py
import asyncio
from pathlib import Path

from services.brain import Brain

BASE_DIR = Path(__file__).parent


async def main():
    brain = Brain()

    await brain.start()
    await brain.enqueue()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
