import sounddevice as sd

def get_audio_inputs():
    devices = sd.query_devices()    
    print("Доступные аудиовыходы")
    for i, device in enumerate(devices):
        if device['max_output_channels'] == 2:
            print(f"ID {i}: {device['name']} (Каналов выхода: {device['max_output_channels']})")

def find_vbcable_devices():
    for i, dev in enumerate(sd.query_devices()):
        name = dev["name"]
        hostapi = sd.query_hostapis(dev["hostapi"])["name"]
        max_output_channels = dev["max_output_channels"]
        max_input_channels = dev["max_input_channels"]
        default_samplerate = dev["default_samplerate"]
        if name in "Hi-Fi Cable Input (VB-Audio Hi-Fi Cable)" and hostapi == "Windows WASAPI" and max_output_channels == 2 and max_input_channels == 0 and default_samplerate == 48000.0:
            print(f"Нужный кабель найден: ID {i}")


if __name__ == "__main__":
    find_vbcable_devices()

