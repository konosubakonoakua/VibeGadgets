import numpy as np
import struct
import zipfile
import io
import math
from typing import Optional, List, Union


def _format_samplerate(rate: Union[int, float, str]) -> str:
    if isinstance(rate, str):
        return rate.strip()
    if rate >= 1_000_000:
        if rate % 1_000_000 == 0:
            return f"{rate // 1_000_000} MHz"
        else:
            return f"{rate / 1_000_000:.3f} MHz"
    elif rate >= 1000:
        if rate % 1000 == 0:
            return f"{rate // 1000} kHz"
        else:
            return f"{rate / 1000:.3f} kHz"
    else:
        return f"{rate} Hz"


def np2srzip(
    logic: Optional[np.ndarray],
    analog: Optional[np.ndarray],
    sr_file: str,
    samplerate: Union[int, float, str],
    chunk_size: int = 100000,
    digital_names: Optional[List[str]] = None,
    analog_names: Optional[List[str]] = None,
    sigrok_version: str = "0.5.2",
):
    """
    Convert logic + analog arrays to a PulseView compatible srzip file.
    Each analog channel per chunk has its own file.
    Automatically handles analog-only datasets by creating a dummy digital channel.
    """
    num_samples = 0
    num_digital = 0
    num_analog = 0

    if analog is not None:
        num_samples = analog.shape[0]
        num_analog = analog.shape[1]
    if logic is not None:
        num_samples, num_digital = logic.shape
        if analog is not None and analog.shape[0] != num_samples:
            raise ValueError(
                "Logic and analog arrays must have the same number of samples"
            )

    # Handle analog-only: create dummy digital channel
    if (logic is None or num_digital == 0) and num_analog > 0:
        logic = np.zeros((num_samples, 1), dtype=np.uint8)
        num_digital = 1
        digital_names = ["Dummy"]
        print("Added dummy digital channel for analog-only dataset.")

    if digital_names is None:
        digital_names = [f"D{i}" for i in range(num_digital)]
    if analog_names is None and num_analog > 0:
        analog_names = [f"A{i}" for i in range(num_analog)]

    unitsize = math.ceil(num_digital / 8) if num_digital > 0 else 0
    if unitsize > 4:
        print(
            f"Warning: {num_digital} digital channels require {unitsize} bytes/sample, limiting to 4 bytes."
        )
        unitsize = 4

    samplerate_str = _format_samplerate(samplerate)

    # ---------------- Metadata ----------------
    metadata_lines = []
    metadata_lines.append("[global]")
    metadata_lines.append(f"sigrok version={sigrok_version}\n")
    metadata_lines.append("[device 1]")
    metadata_lines.append("capturefile=logic-1")
    metadata_lines.append(f"total probes={num_digital}")
    metadata_lines.append(f"samplerate={samplerate_str}")
    metadata_lines.append(f"total analog={num_analog}")

    for i, name in enumerate(digital_names, 1):
        metadata_lines.append(f"probe{i}={name}")
    for j, name in enumerate(analog_names or [], 1):
        metadata_lines.append(f"analog{num_digital + j}={name}")
    metadata_lines.append(f"unitsize={unitsize}")

    metadata = "\n".join(metadata_lines) + "\n"

    # ---------------- Write srzip ----------------
    with zipfile.ZipFile(sr_file, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("version", "2\n")
        z.writestr("metadata", metadata)

        for chunk_idx in range(0, num_samples, chunk_size):
            chunk_end = min(chunk_idx + chunk_size, num_samples)
            chunk_no = chunk_idx // chunk_size + 1

            # Digital
            if num_digital > 0:
                buf = io.BytesIO()
                for row in logic[chunk_idx:chunk_end]:
                    sample_bytes = bytearray(unitsize)
                    for ch in range(num_digital):
                        if row[ch]:
                            byte_index = ch // 8
                            bit_index = ch % 8
                            if byte_index < unitsize:
                                sample_bytes[byte_index] |= 1 << bit_index
                    buf.write(sample_bytes)
                z.writestr(f"logic-1-{chunk_no}", buf.getvalue())

            # Analog: each channel its own file
            if num_analog > 0:
                for ch in range(num_analog):
                    buf = io.BytesIO()
                    for val in analog[chunk_idx:chunk_end, ch]:
                        buf.write(struct.pack("<f", float(val)))
                    probe_no = num_digital + ch + 1
                    z.writestr(f"analog-1-{probe_no}-{chunk_no}", buf.getvalue())

    print(
        f"Written {sr_file} with {num_samples} samples, "
        f"{num_digital} digital ({unitsize} bytes/sample), {num_analog} analog channels."
    )
