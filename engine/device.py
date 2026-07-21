"""Hardware detection: choose the best device and compute type."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def resolve_device(preference: str = "auto") -> tuple[str, str]:
    """Return ``(device, compute_type)`` for WhisperX / faster-whisper.

    * GPU available  -> ``("cuda", "float16")``
    * CPU fallback   -> ``("cpu", "int8")``

    ``preference`` may force ``"cpu"`` or ``"cuda"``; ``"auto"`` probes
    CUDA availability via torch.
    """
    if preference == "cpu":
        return "cpu", "int8"

    try:
        import torch

        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
            if not _torch_supports_device(torch):
                major, minor = torch.cuda.get_device_capability(0)
                logger.warning(
                    "%s (compute capability sm_%d%d) is NOT supported by this "
                    "torch build (%s). Falling back to CPU. To use the GPU, "
                    "install a torch build with matching CUDA kernels, e.g.: "
                    "pip install torch torchaudio --index-url "
                    "https://download.pytorch.org/whl/cu128",
                    gpu,
                    major,
                    minor,
                    torch.__version__,
                )
                return "cpu", "int8"
            logger.info("CUDA available: %s", gpu)
            return "cuda", "float16"
        if preference == "cuda":
            logger.warning("CUDA requested but not available; falling back to CPU.")
    except Exception as exc:  # torch missing or broken CUDA runtime
        logger.warning("Could not probe CUDA (%s); using CPU.", exc)

    return "cpu", "int8"


def _torch_supports_device(torch: object) -> bool:
    """True when the torch build ships kernels for GPU 0's architecture.

    ``torch.cuda.is_available()`` is True even when the card is newer than
    every architecture the wheel was compiled for (e.g. Blackwell sm_120 on
    a cu121 build); actually running a kernel then fails.  Compare the
    device's compute capability against the compiled arch list instead.
    """
    try:
        major, minor = torch.cuda.get_device_capability(0)  # type: ignore[attr-defined]
        capability = major * 10 + minor
        compiled = [
            int(arch.split("_")[1])
            for arch in torch.cuda.get_arch_list()  # type: ignore[attr-defined]
            if arch.startswith("sm_")
        ]
        if not compiled:
            return False
        return capability <= max(compiled)
    except Exception:  # unexpected torch API shape — trust is_available()
        return True


def describe_hardware() -> str:
    """Human-readable one-liner about the compute device in use."""
    device, compute = resolve_device("auto")
    if device == "cuda":
        try:
            import torch

            return f"GPU: {torch.cuda.get_device_name(0)} ({compute})"
        except Exception:
            return f"GPU (CUDA, {compute})"
    return f"CPU ({compute})"
