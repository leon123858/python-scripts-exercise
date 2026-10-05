"""Recover Unity videos and merge matching audio without re-encoding video."""

import argparse
import base64
import gc
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys
import zlib

from Crypto.Util.strxor import strxor
import lz4.block
import UnityPy
from UnityPy.helpers.ResourceReader import get_resource_data

ROOT = Path(__file__).resolve().parent
AA = ROOT / "Game_Win_Data/StreamingAssets/aa"
DEFAULT_INPUT = AA / "StandaloneWindows64/video_assets_assets/bundles/common/localvideos"
DEFAULT_METADATA = ROOT / "Game_Win_Data/il2cpp_data/Metadata/global-metadata.dat"


def sha256_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def xor_bundle(data, name, mask):
    # Key indexing uses the absolute position, not the offset from byte 40.
    stem = Path(name).stem
    digest = hashlib.sha512(stem.encode("utf-8")).digest()
    length = 32 + len(stem) % 32
    key = bytes(value ^ mask[i % len(mask)] for i, value in enumerate(digest[:length]))
    repeated = (key * ((len(data) + length - 1) // length))[40:len(data)]
    return data[:40] + strxor(data[40:], repeated)


def bundle_info(data):
    if not data.startswith(b"UnityFS\0"):
        raise ValueError("Not a UnityFS bundle")
    version = struct.unpack_from(">I", data, 8)[0]
    pos = data.index(0, 12) + 1
    pos = data.index(0, pos) + 1
    size, compressed, uncompressed, flags = struct.unpack_from(">QIII", data, pos)
    pos += 20
    if version != 8 or flags != 0x243:
        raise ValueError("Unsupported or incorrectly decoded UnityFS header")
    if not 0 < compressed <= 16 * 1024 * 1024 or not 0 < uncompressed <= 64 * 1024 * 1024:
        raise ValueError("Invalid bundle directory sizes")
    aligned = (pos + 15) & ~15
    if data[pos:aligned] != bytes(aligned - pos):
        raise ValueError("Invalid UnityFS header padding")
    info = lz4.block.decompress(data[aligned:aligned + compressed], uncompressed_size=uncompressed)
    if len(info) != uncompressed:
        raise ValueError("Incomplete bundle directory")
    return size, info, (aligned + compressed + 15) & ~15


def discover_mask(metadata_path, sample):
    """Find the initializer through header padding and metadata field boundaries.

    No key is embedded in this tool, persisted, or printed.
    """
    metadata = metadata_path.read_bytes()
    if struct.unpack_from("<II", metadata) != (0xFAB11BAF, 29):
        raise ValueError("Expected IL2CPP metadata version 29")
    table, table_size = struct.unpack_from("<II", metadata, 64)
    values, values_size = struct.unpack_from("<II", metadata, 72)
    if table + table_size > len(metadata) or values + values_size > len(metadata):
        raise ValueError("Invalid metadata section bounds")
    starts = set()
    for pos in range(table, table + table_size, 12):
        index = struct.unpack_from("<iii", metadata, pos)[2]
        if 0 <= index < values_size:
            starts.add(values + index)
    with sample.open("rb") as stream:
        encrypted = stream.read(1024 * 1024)
    digest = hashlib.sha512(sample.stem.encode("utf-8")).digest()
    length = 32 + len(sample.stem) % 32
    segments = []
    start = 50
    while start < 64:
        count = min(64 - start, length - start % length)
        segments.append((count, start))
        start += count
    count, start = max(segments)
    key_index = start % length
    needle = strxor(encrypted[start:start + count], digest[key_index:key_index + count])
    match = metadata.find(needle, values, values + values_size)
    while match >= 0:
        origin = match - key_index
        if origin in starts:
            for mask_size in range(key_index + count, 65):
                mask = metadata[origin:origin + mask_size]
                try:
                    bundle_info(xor_bundle(encrypted, sample.name, mask))
                    return mask
                except (ValueError, IndexError, struct.error, lz4.block.LZ4BlockError):
                    pass
        match = metadata.find(needle, match + 1, values + values_size)
    raise ValueError("No valid XOR initializer found in the supplied metadata")


def catalog_crcs(path):
    catalog = json.loads(path.read_text(encoding="utf-8-sig"))
    data = base64.b64decode(catalog["m_ExtraDataString"])
    crcs = {}
    pos = 0
    while pos < len(data):
        if data[pos] != 7:
            raise ValueError("Unsupported Addressables extra-data object")
        pos += 1
        for _ in range(2):
            size = data[pos]
            pos += 1 + size
        size = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        item = json.loads(data[pos:pos + size].decode("utf-16le"))
        pos += size
        if "m_Hash" in item and "m_Crc" in item:
            crcs[item["m_Hash"]] = item["m_Crc"]
    return crcs


def verify_bundle_crc(data, expected):
    size, info, pos = bundle_info(data)
    if size != len(data):
        raise ValueError("Bundle length does not match its header")
    count = struct.unpack_from(">I", info, 16)[0]
    if 20 + count * 10 > len(info):
        raise ValueError("Invalid block table")
    crc = 0
    for i in range(count):
        raw_size, compressed_size, flags = struct.unpack_from(">IIH", info, 20 + i * 10)
        block = data[pos:pos + compressed_size]
        pos += compressed_size
        if len(block) != compressed_size:
            raise ValueError("Truncated block")
        compression = flags & 0x3F
        if compression in (2, 3):
            block = lz4.block.decompress(block, uncompressed_size=raw_size)
        elif compression != 0:
            raise ValueError("Unsupported block compression")
        if len(block) != raw_size:
            raise ValueError("Block size mismatch")
        crc = zlib.crc32(block, crc)
    if pos != len(data):
        raise ValueError("Unexpected trailing bundle data")
    if crc != expected:
        raise ValueError(f"Bundle CRC mismatch: expected {expected}, got {crc}")
    return crc


def safe_output(output, relative):
    relative = PurePosixPath(str(relative).replace("\\", "/"))
    if relative.is_absolute() or any(p in ("..", ".") or ":" in p for p in relative.parts):
        raise ValueError("Unsafe output path")
    path = (output / Path(*relative.parts)).resolve()
    if not path.is_relative_to(output.resolve()) or path == output.resolve():
        raise ValueError("Output path escapes destination")
    return path


def probe_video(path, ffprobe):
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,sample_rate,channels:format=duration,size",
         "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    if result.returncode or result.stderr.strip():
        raise ValueError(f"ffprobe failed: {result.stderr.strip()[:400]}")
    details = json.loads(result.stdout)
    if not any(s.get("codec_type") == "video" for s in details.get("streams", [])):
        raise ValueError("No video stream found")
    if float(details.get("format", {}).get("duration", 0)) <= 0:
        raise ValueError("Invalid video duration")
    return details


def write_json(path, data):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def reusable(entry, source_hash, output):
    if entry.get("status") != "success" or entry.get("source_sha256") != source_hash:
        return False
    if not entry.get("outputs"):
        return False
    for item in entry["outputs"]:
        path = safe_output(output, item["path"])
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            return False
    return True


def extract_one(bundle, relative, output, mask, expected_crc, ffprobe):
    encrypted = bundle.read_bytes()
    decoded = xor_bundle(encrypted, bundle.name, mask)
    del encrypted
    crc = verify_bundle_crc(decoded, expected_crc)
    environment = UnityPy.load(decoded)
    del decoded
    outputs = []
    paths = set()
    for obj in environment.objects:
        if obj.type.name != "VideoClip":
            continue
        clip = obj.read()
        resource = clip.m_ExternalResources
        payload = get_resource_data(resource.m_Source, obj.assets_file, resource.m_Offset, resource.m_Size)
        if not payload or len(payload) != resource.m_Size:
            raise ValueError("Video resource length mismatch")
        name = PurePosixPath(clip.m_OriginalPath.replace("\\", "/")).name
        if not name:
            name = re.sub(r"_[0-9a-f]+\.bundle$", "", bundle.name)
        destination = safe_output(output, relative.parent / name)
        if destination in paths:
            raise ValueError("Two clips map to the same output name")
        paths.add(destination)
        digest = hashlib.sha256(payload).hexdigest()
        if destination.exists():
            if destination.stat().st_size != len(payload) or sha256_file(destination) != digest:
                raise FileExistsError(f"Existing output differs; move it aside to retry: {destination}")
            details = probe_video(destination, ffprobe)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + ".part")
            try:
                temporary.write_bytes(payload)
                if temporary.stat().st_size != len(payload) or sha256_file(temporary) != digest:
                    raise ValueError("Output verification failed")
                details = probe_video(temporary, ffprobe)
                temporary.rename(destination)
            finally:
                temporary.unlink(missing_ok=True)
        outputs.append({"path": destination.relative_to(output).as_posix(),
                        "bytes": len(payload), "sha256": digest,
                        "clip": clip.m_Name, "original_path": clip.m_OriginalPath,
                        "probe": details})
        del payload
    if not outputs:
        raise ValueError("No VideoClip objects found")
    return {"bundle_crc32": crc, "outputs": outputs}


def finish_audio(args, manifest, output, mask, crcs, ffprobe, ffmpeg, failures=0):
    from audio_pipeline import mux_all
    audio_output = args.audio_output or output.with_name(output.name + "_with_audio")
    report = mux_all(manifest, output, audio_output, args.audio_input, mask, crcs,
                     ffprobe, ffmpeg, sys.modules[__name__], args.duration_policy)
    if failures or report["summary"]["failed"]:
        return 1
    if report["summary"]["missing_audio"] or report["summary"]["needs_sync"]:
        return 2
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=ROOT / "extracted_videos")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--catalog", type=Path, default=AA / "catalog.json")
    parser.add_argument("--audio-input", type=Path, default=AA / "StandaloneWindows64")
    parser.add_argument("--audio-output", type=Path, help="Default: OUTPUT_with_audio alongside the raw output")
    parser.add_argument("--video-only", action="store_true", help="Only extract original silent video resources")
    parser.add_argument("--audio-only", action="store_true", help="Use verified existing raw video outputs; skip extraction")
    parser.add_argument("--duration-policy", choices=("strict", "fit"), default="fit",
                        help="strict: save mismatched stems for review; fit: zero-align, pad/trim audio to video")
    parser.add_argument("--limit", type=int, help="Process only the first N bundles for a sample run")
    args = parser.parse_args(argv)
    source, output = args.input.resolve(), args.output.resolve()
    if args.audio_only and args.video_only:
        parser.error("--audio-only and --video-only are mutually exclusive")
    if output == source or output.is_relative_to(source) or source.is_relative_to(output):
        parser.error("Input and output directories must be separate")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        parser.error("ffprobe is required on PATH to validate exported videos")
    ffmpeg = shutil.which("ffmpeg")
    if not args.video_only and not ffmpeg:
        parser.error("ffmpeg is required to merge and validate audio")
    bundles = sorted(source.rglob("*.bundle"))
    if not bundles:
        parser.error("No .bundle files found")
    selected = bundles[:args.limit] if args.limit else bundles
    manifest_path = output / "manifest.json"
    previous = {}
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old.get("input") != str(source):
            parser.error("Existing manifest belongs to another input directory")
        previous = {e["source"]: e for e in old.get("entries", [])}
    mask = discover_mask(args.metadata, min(bundles, key=lambda p: p.stat().st_size))
    crcs = catalog_crcs(args.catalog)
    if args.audio_only:
        entries = []
        for bundle in selected:
            entry = previous.get(bundle.relative_to(source).as_posix(), {})
            if not reusable(entry, sha256_file(bundle), output):
                parser.error(f"Raw output missing or changed; run without --audio-only: {bundle.name}")
            entries.append(entry)
        manifest = {"total_source_bundles": len(bundles), "entries": entries}
        return finish_audio(args, manifest, output, mask, crcs, ffprobe, ffmpeg)
    print(f"Validated XOR scheme. Processing {len(selected)}/{len(bundles)} bundles.", flush=True)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"version": 1, "input": str(source), "output": str(output),
                "metadata": str(args.metadata.resolve()), "catalog": str(args.catalog.resolve()),
                "total_source_bundles": len(bundles), "selected_bundles": len(selected), "entries": []}
    failures = 0
    for index, bundle in enumerate(selected, 1):
        relative = bundle.relative_to(source)
        entry = {"source": relative.as_posix(), "source_bytes": bundle.stat().st_size}
        action = "exported"
        try:
            source_hash = sha256_file(bundle)
            entry["source_sha256"] = source_hash
            prior = previous.get(entry["source"], {})
            if reusable(prior, source_hash, output):
                entry.update(prior)
                for item in entry["outputs"]:
                    item["probe"] = probe_video(safe_output(output, item["path"]), ffprobe)
                action = "verified existing"
            else:
                bundle_hash = bundle.stem.rsplit("_", 1)[-1]
                if bundle_hash not in crcs:
                    raise ValueError("Bundle CRC missing from Addressables catalog")
                entry.update(extract_one(bundle, relative, output, mask, crcs[bundle_hash], ffprobe))
            entry["status"] = "success"
        except Exception as exc:
            failures += 1
            entry["status"] = "failed"
            entry["error"] = f"{type(exc).__name__}: {exc}"
            action = entry["error"]
        manifest["entries"].append(entry)
        manifest["summary"] = {"processed": index, "successful_bundles": index - failures,
                               "failed_bundles": failures,
                               "videos": sum(len(e.get("outputs", [])) for e in manifest["entries"] if e["status"] == "success"),
                               "complete": index == len(bundles) and not failures}
        # Keep previous checkpoints outside this run's prefix, so --limit or an
        # interrupted verification pass does not discard resumable work.
        cached = dict(previous)
        cached.update({e["source"]: e for e in manifest["entries"]})
        persisted = dict(manifest, entries=[cached[key] for key in sorted(cached)])
        write_json(manifest_path, persisted)
        print(f"[{index}/{len(selected)}] {relative}: {action}", flush=True)
        gc.collect()
    print(json.dumps(manifest["summary"]), flush=True)
    if not args.video_only:
        return finish_audio(args, manifest, output, mask, crcs, ffprobe, ffmpeg, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
