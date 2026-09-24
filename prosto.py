import asyncio
import sounddevice as sd
import numpy as np
from scipy.signal import resample_poly
from kokoro_onnx import Kokoro

kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")

VB_INDEX = 17
TARGET_SR = 48000
TARGET_CH = 2

async def main():
    stream = kokoro.create_stream(
        text="Первое предложение. Второе предложение идёт за ним. Третье тоже тут.",
        voice="af_heart",
        speed=1.0,
        lang="ru"
    )

    with sd.OutputStream(samplerate=TARGET_SR, channels=TARGET_CH, dtype='float32', device=VB_INDEX) as out:
        async for chunk in stream:
            audio, sr = chunk  # (np.ndarray, int)
            # audio: (N,) float32 @ 24000 Hz mono
            audio = resample_poly(audio, 2, 1)  # 24k -> 48k
            audio = np.column_stack((audio, audio))  # mono -> stereo
            out.write(audio.astype(np.float32))

asyncio.run(main())