# test_cable.py
import numpy as np
import sounddevice as sd


def find_vbcable_devices():
    print("=== Все VB-Cable / CABLE устройства")
    for i, dev in enumerate(sd.query_devices()):
        name = dev["name"]
        if "CABLE" in name.upper() or "VB-Audio" in name:
            hostapi = sd.query_hostapis(dev["hostapi"])["name"]
            print(f"[{i}] {name}")
            print(f"    hostapi: {hostapi}")
            print(f"    max_output_channels: {dev['max_output_channels']}")
            print(f"    max_input_channels:  {dev['max_input_channels']}")
            print(f"    default_samplerate:  {dev['default_samplerate']}")
            print()


def test_device(device_index, sr, ch):
    duration = 1.0
    tone = 0.3 * np.sin(
        2 * np.pi * 440 * np.linspace(0, duration, int(sr * duration), endpoint=False)
    ).astype(np.float32)

    if ch == 2:
        tone = np.column_stack((tone, tone))

    try:
        with sd.OutputStream(
            samplerate=sr,
            channels=ch,
            dtype="float32",
            device=device_index,
        ) as out:
            out.write(tone)
        print(f"  ✅ OK: sr={sr}, ch={ch}")
    except Exception as e:
        print(f"  ❌ FAIL: sr={sr}, ch={ch} → {type(e).__name__}: {e}")


def main():
    find_vbcable_devices()

    print("=== Тест комбинаций на device 13 ===")
    for sr in [44100, 48000]:
        for ch in [1, 2]:
            test_device(13, sr, ch)

    print("\n=== Инфа по устройству 13 ===")
    dev = sd.query_devices()[13]
    print(f"name: {dev['name']}")
    print(f"hostapi: {sd.query_hostapis(dev['hostapi'])['name']}")
    print(f"max_output_channels: {dev['max_output_channels']}")
    print(f"default_samplerate: {dev['default_samplerate']}")


if __name__ == "__main__":
    main()