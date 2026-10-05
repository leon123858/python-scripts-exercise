"""Match this game's role/other AudioClips and mux playable videos."""

import gc
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import UnityPy

PIPELINE_VERSION = 1


class NeedsSync(ValueError):
    def __init__(self, message, tracks, differences, files):
        super().__init__(message)
        self.tracks = tracks
        self.differences = differences
        self.files = files


def index_audio(directory):
    if not directory.is_dir():
        raise ValueError(f"Audio source directory does not exist: {directory}")
    result = {}
    for path in sorted(directory.glob("sound_assets_*.bundle")):
        match = re.fullmatch(r"sound_assets_(.+)_(role|other)_([0-9a-f]+)\.bundle", path.name)
        if not match:
            continue
        name, kind, _ = match.groups()
        if kind in result.setdefault(name, {}):
            raise ValueError(f"Ambiguous audio bundles for {name}_{kind}")
        result[name][kind] = path
    return result


def match_audio(clip, index):
    # Chat videos and their accompanying audio use different explicit prefixes.
    key = re.sub(r"^chat_video_", "chat_audio_", clip)
    return [(kind, path) for kind, path in sorted(index.get(key, {}).items())]


def audio_samples(path, kind, work, mask, crcs, core):
    decoded = core.xor_bundle(path.read_bytes(), path.name, mask)
    crc = core.verify_bundle_crc(decoded, crcs[path.stem.rsplit("_", 1)[-1]])
    env = UnityPy.load(decoded)
    clips = [obj.read() for obj in env.objects if obj.type.name == "AudioClip"]
    if len(clips) != 1:
        raise ValueError(f"Expected one AudioClip in {path.name}, found {len(clips)}")
    clip = clips[0]
    expected_name = path.name[len("sound_assets_"):].rsplit("_", 1)[0]
    if clip.m_Name != expected_name:
        raise ValueError(f"AudioClip name does not match bundle: {path.name}")
    samples = clip.samples
    if len(samples) != 1:
        raise ValueError(f"Expected one decoded sample in {path.name}")
    name, payload = next(iter(samples.items()))
    if not payload:
        raise ValueError(f"Empty AudioClip: {path.name}")
    output = work / (kind + Path(name).suffix)
    output.write_bytes(payload)
    details = {"kind": kind, "source": str(path.resolve()),
               "source_sha256": core.sha256_file(path), "bundle_crc32": crc,
               "clip": clip.m_Name, "duration": clip.m_Length,
               "channels": clip.m_Channels, "sample_rate": clip.m_Frequency,
               "decoded_sha256": hashlib.sha256(payload).hexdigest()}
    return output, details


def mux_command(ffmpeg, video, tracks, destination, duration):
    command = [ffmpeg, "-hide_banner", "-v", "error", "-nostdin", "-y", "-i", str(video)]
    for track in tracks:
        command.extend(["-i", str(track)])
    # Both full-length stems start at zero. Keep unity gain; a latency-compensated
    # limiter prevents clipping when stems overlap, without a normalization boost.
    inputs = "".join(f"[{i}:a:0]" for i in range(1, len(tracks) + 1))
    graph = (inputs + f"amix=inputs={len(tracks)}:duration=longest:normalize=0,"
             "alimiter=limit=0.95:level=0:latency=1,apad,"
             f"atrim=duration={duration:.9f},asetpts=PTS-STARTPTS[mixed]")
    command.extend(["-filter_complex", graph, "-map", "0:v:0", "-map", "[mixed]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-map_metadata", "0", "-movflags", "+faststart", "-f", "mp4", str(destination)])
    return command


def run_checked(command):
    result = subprocess.run(command, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=600)
    if result.returncode or result.stderr.strip():
        raise ValueError(f"FFmpeg failed: {result.stderr.strip()[:600]}")
    return result.stdout


def validate_mux(path, original_probe, ffprobe, ffmpeg, core):
    probe = core.probe_video(path, ffprobe)
    if not any(s.get("codec_type") == "audio" for s in probe["streams"]):
        raise ValueError("Muxed file has no audio stream")
    original_video = next(s for s in original_probe["streams"] if s.get("codec_type") == "video")
    output_video = next(s for s in probe["streams"] if s.get("codec_type") == "video")
    for field in ("codec_name", "width", "height"):
        if output_video.get(field) != original_video.get(field):
            raise ValueError(f"Video {field} changed during mux")
    if abs(float(probe["format"]["duration"]) - float(original_probe["format"]["duration"])) > 0.15:
        raise ValueError("Muxed duration differs from original video")
    run_checked([ffmpeg, "-v", "error", "-nostdin", "-xerror", "-i", str(path),
                 "-map", "0:a:0", "-f", "null", "-"])
    return probe


def write_summary(report, destination):
    summary = report["summary"]
    lines = ["Audio restoration result", f"Voiced videos: {summary['videos_with_audio']}",
             f"Missing audio: {summary['missing_audio']}", f"Failed: {summary['failed']}",
             "", "No matching audio (original silent video remains in the raw directory):"]
    lines.extend(e["path"] for e in report["entries"] if e["status"] == "missing_audio")
    lines.extend(["", "Audio duration adjusted to video (seconds: audio minus video):"])
    lines.extend(f"{e['path']}: {e['duration_differences']}" for e in report["entries"] if e.get("duration_adjusted"))
    lines.extend(["", "Errors / synchronization review:"])
    lines.extend(f"{e['path']}: {e.get('error', e.get('reason'))}" for e in report["entries"]
                 if e["status"] in ("failed", "needs_sync"))
    (destination / "audio_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def mux_all(raw_manifest, raw_output, destination, audio_root, mask, crcs, ffprobe, ffmpeg, core,
            duration_policy="fit"):
    destination = destination.resolve()
    for source in (raw_output.resolve(), audio_root.resolve()):
        if destination == source or destination.is_relative_to(source) or source.is_relative_to(destination):
            raise ValueError("Audio output must be separate from original media and source assets")
    index = index_audio(audio_root)
    if not index:
        raise ValueError("No role/other audio bundles found in the audio source directory")
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "manifest.json"
    previous = {}
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old.get("raw_input") != str(raw_output.resolve()):
            raise ValueError("Audio manifest belongs to a different video directory")
        previous = {e["path"]: e for e in old.get("entries", [])}
    videos = [o for e in raw_manifest["entries"] if e["status"] == "success" for o in e["outputs"]]
    report = {"version": PIPELINE_VERSION, "raw_input": str(raw_output.resolve()),
              "audio_input": str(audio_root.resolve()), "output": str(destination),
              "duration_policy": duration_policy,
              "mix": "zero-aligned role + other, unity gain, peak limiter, AAC 192k; video stream copy",
              "entries": []}
    work_root = destination / ".work"
    work_root.mkdir(exist_ok=True)
    for number, video in enumerate(videos, 1):
        entry = {"path": video["path"], "clip": video["clip"], "raw_sha256": video["sha256"],
                 "duration_policy": duration_policy}
        tracks = match_audio(video["clip"], index)
        target = core.safe_output(destination, video["path"])
        original = core.safe_output(raw_output, video["path"])
        try:
            if not tracks:
                # Do not copy a silent file into the directory advertised as voiced.
                entry.update(status="missing_audio", reason="No matching role/other AudioClip bundles", original=str(original))
            else:
                signature = [{"kind": kind, "source": str(path.resolve()), "sha256": core.sha256_file(path)}
                             for kind, path in tracks]
                entry["audio_sources"] = signature
                prior = previous.get(video["path"], {})
                can_resume = (prior.get("status") == "success" and prior.get("pipeline_version") == PIPELINE_VERSION
                              and prior.get("raw_sha256") == video["sha256"] and prior.get("audio_sources") == signature
                              and target.is_file() and core.sha256_file(target) == prior.get("sha256"))
                if can_resume:
                    entry.update(prior)
                    core.probe_video(target, ffprobe)
                    action = "verified existing audio"
                else:
                    if target.exists():
                        raise FileExistsError(f"Existing voiced output differs; move it aside to retry: {target}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with tempfile.TemporaryDirectory(dir=work_root) as temporary:
                        work = Path(temporary)
                        samples, details = [], []
                        for kind, path in tracks:
                            sample, detail = audio_samples(path, kind, work, mask, crcs, core)
                            samples.append(sample)
                            details.append(detail)
                        duration = float(video["probe"]["format"]["duration"])
                        differences = [round(t["duration"] - duration, 6) for t in details]
                        # Small encoder/frame differences are expected; larger ones
                        # require investigation instead of silently shifting tracks.
                        mismatch = any(abs(difference) > 0.5 for difference in differences)
                        if mismatch and duration_policy == "strict":
                            review = core.safe_output(destination, Path("_audio_review") / Path(video["path"]).with_suffix(""))
                            review.mkdir(parents=True, exist_ok=True)
                            review_files = []
                            for sample, detail in zip(samples, details):
                                saved = review / sample.name
                                if saved.exists() and core.sha256_file(saved) != detail["decoded_sha256"]:
                                    raise FileExistsError(f"Different existing review audio: {saved}")
                                if not saved.exists():
                                    shutil.copyfile(sample, saved)
                                if core.sha256_file(saved) != detail["decoded_sha256"]:
                                    raise ValueError("Review audio copy failed verification")
                                review_files.append(saved.relative_to(destination).as_posix())
                            raise NeedsSync(f"Audio/video duration mismatch needs review: {differences}",
                                            details, differences, review_files)
                        part = work / "muxed.mp4"
                        run_checked(mux_command(ffmpeg, original, samples, part, duration))
                        probe = validate_mux(part, video["probe"], ffprobe, ffmpeg, core)
                        digest = core.sha256_file(part)
                        size = part.stat().st_size
                        # Copy out of TemporaryDirectory before renaming: on
                        # Windows its private ACL must not follow the final file.
                        staged = target.with_name(target.name + ".part")
                        try:
                            shutil.copyfile(part, staged)
                            if core.sha256_file(staged) != digest:
                                raise ValueError("Final audio output copy failed verification")
                            staged.rename(target)
                        finally:
                            staged.unlink(missing_ok=True)
                    entry.update(status="success", pipeline_version=PIPELINE_VERSION,
                                 audio_tracks=details, duration_differences=differences,
                                 duration_adjusted=mismatch,
                                 sha256=digest, bytes=size, probe=probe)
                    action = "audio merged and decoded successfully"
                entry["status"] = "success"
        except NeedsSync as exc:
            entry.update(status="needs_sync", reason=str(exc), audio_tracks=exc.tracks,
                         duration_differences=exc.differences, review_audio=exc.files, original=str(original))
        except Exception as exc:
            entry.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        report["entries"].append(entry)
        successes = sum(e["status"] == "success" for e in report["entries"])
        missing = sum(e["status"] == "missing_audio" for e in report["entries"])
        failed = sum(e["status"] == "failed" for e in report["entries"])
        needs_sync = sum(e["status"] == "needs_sync" for e in report["entries"])
        report["summary"] = {"processed": number, "videos_with_audio": successes,
                             "missing_audio": missing, "needs_sync": needs_sync, "failed": failed,
                             "complete": number == raw_manifest["total_source_bundles"] and missing == failed == needs_sync == 0}
        cached = dict(previous)
        cached.update({e["path"]: e for e in report["entries"]})
        persisted = dict(report, entries=[cached[key] for key in sorted(cached)])
        core.write_json(manifest_path, persisted)
        message = action if entry["status"] == "success" else entry.get("error", entry.get("reason"))
        print(f"[audio {number}/{len(videos)}] {video['path']}: {message}", flush=True)
        gc.collect()
    if not any(work_root.iterdir()):
        work_root.rmdir()
    write_summary(report, destination)
    print("Audio summary: " + json.dumps(report["summary"]), flush=True)
    return report
