"""Image utilities: perceptual hashing (dHash) used by the Visual Counterfeit Signal Agent.

dHash ("difference hash") shrinks an image to 17x16 grayscale and records whether each pixel is
brighter than its right neighbour. Visually identical images (resized, re-compressed, brightness
shifted) end up with nearly identical 256-bit hashes, so a small Hamming distance means "same photo".
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def dhash(path: str | Path, hash_size: int = 16) -> int:
    img = Image.open(path).convert("L").resize((hash_size + 1, hash_size), Image.LANCZOS)
    px = np.asarray(img, dtype=np.int16)
    diff = px[:, 1:] > px[:, :-1]
    value = 0
    for bit in diff.flatten():
        value = (value << 1) | int(bit)
    return value


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def similarity(a: int, b: int, bits: int = 256) -> float:
    """1.0 = identical hash, 0.0 = completely different."""
    return 1 - hamming(a, b) / bits
