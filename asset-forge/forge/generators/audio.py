"""
AudioCraft AudioGen sound generator.

Requires the `audio` extras group:
    poetry install -E audio

Also requires PyTorch with CUDA:
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

All model weights are downloaded on first use from HuggingFace and cached locally.
Model weights are under CC-BY-NC 4.0 (non-commercial use only).
"""
from __future__ import annotations

from pathlib import Path

from ..config import settings
from ..types.plan import AudioPrompt

try:
    import torch
    import torchaudio
    from audiocraft.models import AudioGen

    _AUDIO_AVAILABLE = True
except ImportError:
    _AUDIO_AVAILABLE = False

_model: "AudioGen | None" = None  # lazy-loaded singleton


def _check_available() -> None:
    if not _AUDIO_AVAILABLE:
        raise RuntimeError(
            "AudioCraft is not installed. "
            "Install it with: poetry install -E audio\n"
            "Then install PyTorch with CUDA:\n"
            "  pip install torch torchaudio --index-url "
            "https://download.pytorch.org/whl/cu121"
        )


def _get_model() -> "AudioGen":
    global _model
    _check_available()
    if _model is None:
        import torch
        from audiocraft.models import AudioGen

        device = settings.audiogen_device
        if device == "cuda" and not torch.cuda.is_available():
            device = "cpu"
        _model = AudioGen.get_pretrained(settings.audiogen_model)
        _model = _model.to(device)  # type: ignore[assignment]
    return _model


def generate_sound(
    audio_prompt: AudioPrompt,
    output_path: Path,
) -> Path:
    """
    Generate a sound effect from an AudioPrompt and save it as a .wav file.

    Args:
        audio_prompt: The prompt spec (text, duration).
        output_path:  Where to save the .wav file.

    Returns:
        Path to the saved .wav file.
    """
    import torch
    import torchaudio

    output_path = Path(output_path).with_suffix(".wav")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = _get_model()
    model.set_generation_params(duration=audio_prompt.duration_seconds)

    with torch.inference_mode():
        wav = model.generate([audio_prompt.prompt])  # shape: (1, 1, samples)

    # wav is (batch, channels, samples); take first item, squeeze batch dim
    audio_tensor = wav[0].cpu()  # (channels, samples) or (samples,)
    if audio_tensor.dim() == 1:
        audio_tensor = audio_tensor.unsqueeze(0)  # ensure (channels, samples)

    torchaudio.save(
        str(output_path),
        audio_tensor,
        model.sample_rate,
        encoding="PCM_S",
        bits_per_sample=16,
    )
    return output_path


def generate_all_sounds(
    audio_prompts: list[AudioPrompt],
    output_dir: Path,
    stem: str,
) -> dict[str, Path]:
    """
    Generate all sounds for a plan and return a role → path mapping.

    Args:
        audio_prompts: List of AudioPrompt objects from the AssetPlan.
        output_dir:    Directory to write .wav files into.
        stem:          Object ID used as filename prefix.

    Returns:
        Dict mapping role (e.g. 'open', 'close', 'ambient') → Path.
    """
    results: dict[str, Path] = {}
    for ap in audio_prompts:
        out = output_dir / f"{stem}_{ap.role}.wav"
        generate_sound(ap, out)
        results[ap.role] = out
    return results
