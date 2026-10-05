import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import audio_pipeline as audio
import main


class AudioTests(unittest.TestCase):
    def test_exact_mapping_and_chat_alias(self):
        index = {"video_10": {"role": Path("role.bundle"), "other": Path("other.bundle")},
                 "chat_audio_1": {"other": Path("chat.bundle")}}
        self.assertEqual([kind for kind, _ in audio.match_audio("video_10", index)], ["other", "role"])
        self.assertEqual(audio.match_audio("chat_video_1", index), [("other", Path("chat.bundle"))])
        self.assertEqual(audio.match_audio("video_1", index), [])

    def test_index_rejects_ambiguous_tracks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for suffix in ("abcd", "ef01"):
                (root / f"sound_assets_video_10_role_{suffix}.bundle").touch()
            with self.assertRaisesRegex(ValueError, "Ambiguous"):
                audio.index_audio(root)

    def test_mix_command_copies_video_and_maps_both_stems(self):
        command = audio.mux_command("ffmpeg", Path("video.mp4"), [Path("a.wav"), Path("b.wav")], Path("out.mp4"), 4)
        graph = command[command.index("-filter_complex") + 1]
        self.assertIn("[1:a:0][2:a:0]amix=inputs=2", graph)
        self.assertIn("normalize=0", graph)
        self.assertIn("latency=1", graph)
        self.assertEqual(command[command.index("-c:v") + 1], "copy")

    def test_missing_audio_is_reported_without_copying_silent_video(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw, assets, output = root / "raw", root / "assets", root / "voiced"
            raw.mkdir()
            assets.mkdir()
            (assets / "sound_assets_unrelated_other_abcd.bundle").touch()
            manifest = {"total_source_bundles": 1, "entries": [{"status": "success", "outputs": [
                {"path": "missing.mp4", "clip": "missing", "sha256": "source"}]}]}
            result = audio.mux_all(manifest, raw, output, assets, b"mask", {}, "ffprobe", "ffmpeg", main)
            self.assertEqual(result["summary"]["missing_audio"], 1)
            self.assertFalse(result["summary"]["complete"])
            self.assertFalse((output / "missing.mp4").exists())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools required")
    def test_real_mux_preserves_video_and_decodes_audio(self):
        ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "video.mp4"
            audio.run_checked([ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=64x64:r=30:d=1",
                               "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)])
            tracks = []
            for frequency in (440, 880):
                path = root / f"{frequency}.wav"
                duration = 0.95 if frequency == 440 else 1.7
                audio.run_checked([ffmpeg, "-v", "error", "-f", "lavfi", "-i",
                                   f"sine=frequency={frequency}:duration={duration}:sample_rate=22050", str(path)])
                tracks.append(path)
            output = root / "voiced.mp4"
            audio.run_checked(audio.mux_command(ffmpeg, video, tracks, output, 1))
            probe = audio.validate_mux(output, main.probe_video(video, ffprobe), ffprobe, ffmpeg, main)
            self.assertTrue(any(s.get("codec_name") == "aac" for s in probe["streams"]))
            def video_hash(path):
                return audio.run_checked([ffmpeg, "-v", "error", "-i", str(path), "-map", "0:v:0",
                                          "-c", "copy", "-f", "hash", "-hash", "sha256", "-"])
            self.assertEqual(video_hash(video), video_hash(output))
            pcm = subprocess.run([ffmpeg, "-v", "error", "-i", str(output), "-map", "0:a:0",
                                  "-f", "s16le", "-"], capture_output=True, check=True).stdout
            self.assertTrue(any(pcm), "Decoded audio must contain nonzero samples")


if __name__ == "__main__":
    unittest.main()
