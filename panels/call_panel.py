from core.call_audio import audio_to_text

async def fetch_call(panel_id, panel):
    return audio_to_text("call.wav")
