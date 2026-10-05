import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib
from Crypto.Util.strxor import strxor

import lz4.block

import main


def make_bundle(payload):
    info = bytes(16) + struct.pack(">I", 1)
    info += struct.pack(">IIH", len(payload), len(payload), 0)
    info += struct.pack(">I", 0)
    compressed = lz4.block.compress(info, store_size=False)
    prefix = b"UnityFS\0" + struct.pack(">I", 8) + b"5.x.x\0" + b"2022.3.10f1\0"
    block_start = (64 + len(compressed) + 15) & ~15
    header = prefix + struct.pack(">QIII", block_start + len(payload), len(compressed), len(info), 0x243)
    data = header + bytes(64 - len(header)) + compressed
    return data + bytes(block_start - len(data)) + payload


class ExtractionTests(unittest.TestCase):
    def test_xor_key_wraps_at_64_character_stems(self):
        name = "a" * 64 + ".bundle"
        mask = b"test-mask"
        payload = bytes(range(256))
        digest = hashlib.sha512(("a" * 64).encode()).digest()
        key = bytes(v ^ mask[i % len(mask)] for i, v in enumerate(digest[:32]))
        expected = payload[:40] + strxor(payload[40:], (key * 8)[40:])
        self.assertEqual(main.xor_bundle(payload, name, mask), expected)

    def test_crc_detects_payload_damage(self):
        payload = b"original movie bytes" * 100
        data = make_bundle(payload)
        crc = zlib.crc32(payload)
        self.assertEqual(main.verify_bundle_crc(data, crc), crc)
        damaged = data[:-1] + bytes([data[-1] ^ 1])
        with self.assertRaisesRegex(ValueError, "CRC mismatch"):
            main.verify_bundle_crc(damaged, crc)

    def test_truncated_bundle_fails(self):
        with self.assertRaisesRegex(ValueError, "length"):
            main.verify_bundle_crc(make_bundle(b"movie")[:-1], 0)

    def test_metadata_discovery_and_decryption(self):
        mask = bytes(range(1, 36))
        name = "video_905_2.mp4_" + "a" * 32 + ".bundle"
        clear = make_bundle(b"movie" * 100)
        encrypted = main.xor_bundle(clear, name, mask)
        self.assertEqual(clear[:40], encrypted[:40])
        self.assertNotEqual(clear[40:], encrypted[40:])
        metadata = bytearray(512)
        struct.pack_into("<II", metadata, 0, 0xFAB11BAF, 29)
        struct.pack_into("<II", metadata, 64, 256, 12)
        struct.pack_into("<II", metadata, 72, 300, 100)
        struct.pack_into("<iii", metadata, 256, 0, 0, 0)
        metadata[300:335] = mask
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            meta = root / "metadata.dat"
            sample = root / name
            meta.write_bytes(metadata)
            sample.write_bytes(encrypted)
            recovered = main.discover_mask(meta, sample)
            self.assertEqual(main.xor_bundle(encrypted, name, recovered), clear)

    def test_paths_stay_inside_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.assertEqual(main.safe_output(root, "story/video.mp4"), root / "story/video.mp4")
            for name in ["../escape.mp4", "/escape.mp4", "C:/escape.mp4", "story/../../escape.mp4"]:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    main.safe_output(root, name)

    def test_resume_rejects_same_size_corruption_and_changed_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "video.mp4"
            path.write_bytes(b"original")
            entry = {"status": "success", "source_sha256": "source",
                     "outputs": [{"path": "video.mp4", "bytes": 8,
                                  "sha256": hashlib.sha256(b"original").hexdigest()}]}
            self.assertTrue(main.reusable(entry, "source", root))
            self.assertFalse(main.reusable(entry, "different", root))
            path.write_bytes(b"modified")
            self.assertFalse(main.reusable(entry, "source", root))

    def test_probe_rejects_missing_video(self):
        with patch("main.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stderr = ""
            run.return_value.stdout = '{"streams": [], "format": {"duration": "1"}}'
            with self.assertRaisesRegex(ValueError, "No video"):
                main.probe_video(Path("sample.mp4"), "ffprobe")


if __name__ == "__main__":
    unittest.main()
