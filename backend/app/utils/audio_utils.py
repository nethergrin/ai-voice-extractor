import struct


def pcm_to_wav(pcm_data: bytes, sample_rate: int, channels: int, bit_depth: int) -> bytes:
    """
    Convert raw PCM data to WAV format.

    Args:
        pcm_data: Raw PCM bytes
        sample_rate: Sample rate in Hz (e.g., 16000)
        channels: Number of audio channels (e.g., 1 for mono)
        bit_depth: Bits per sample (e.g., 16)

    Returns:
        Complete WAV file as bytes
    """
    num_samples = len(pcm_data) // (channels * bit_depth // 8)
    byte_rate = sample_rate * channels * bit_depth // 8
    block_align = channels * bit_depth // 8
    subchunk2_size = len(pcm_data)
    chunk_size = 36 + subchunk2_size

    wav_header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        chunk_size,
        b'WAVE',
        b'fmt ',
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bit_depth,
        b'data',
        subchunk2_size,
    )

    return wav_header + pcm_data
