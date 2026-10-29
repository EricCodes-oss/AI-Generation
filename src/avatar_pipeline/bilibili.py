"""Download public Bilibili references without starting or reading a browser."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlencode, urlsplit

API = "https://api.bilibili.com"
REFERER = "https://www.bilibili.com/"
USER_AGENT = "Mozilla/5.0"


class DownloadError(RuntimeError):
    pass


class ContentUnavailable(DownloadError):
    """Do not try alternative methods for inaccessible or restricted content."""


def parse_reference(value: str) -> tuple[str, int]:
    if re.fullmatch(r"BV[0-9A-Za-z]{10}", value):
        return value, 1
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "www.bilibili.com", "bilibili.com", "m.bilibili.com",
    }:
        raise ValueError("expected a Bilibili video URL or BV identifier")
    query = parse_qs(parsed.query)
    match = re.search(r"/video/(BV[0-9A-Za-z]{10})(?:/|$)", parsed.path)
    bvid = match.group(1) if match else query.get("bvid", [""])[0]
    if not re.fullmatch(r"BV[0-9A-Za-z]{10}", bvid):
        raise ValueError("missing or invalid BV identifier")
    page = int(query.get("p", ["1"])[0])
    if page < 1:
        raise ValueError("part number must be positive")
    return bvid, page


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


class BilibiliDownloader:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.attempts: list[dict] = []

    def _record(self, method: str, status: str, detail: str = "") -> None:
        self.attempts.append({"method": method, "status": status, "detail": detail})

    def _curl(self, url: str, output: Path | None = None) -> str:
        command = [
            "curl", "--silent", "--show-error", "--location",
            "--proto", "=https", "--proto-redir", "=https",
            "--connect-timeout", "10", "--max-time", "180" if output else "30",
            "--retry", "1", "--retry-delay", "1",
            "--user-agent", USER_AGENT, "--referer", REFERER,
            "--write-out", "\n%{http_code}",
        ]
        if output:
            command.extend(["--output", str(output)])
        result = subprocess.run([*command, url], capture_output=True, text=True, check=False)
        body, _, status = result.stdout.rpartition("\n")
        if result.returncode or status != "200":
            # Do not persist signed URLs, cookies, or curl's raw error output.
            raise DownloadError(f"curl exit {result.returncode}, HTTP {status or 'unknown'}")
        return body

    def _json(self, url: str) -> dict:
        try:
            payload = json.loads(self._curl(url))
        except ValueError as error:
            raise DownloadError("response was not JSON") from error
        if not isinstance(payload, dict):
            raise DownloadError("invalid API response")
        return payload

    @staticmethod
    def _data(payload: dict):
        code = payload.get("code")
        if code in {-101, -403, -404, -10403, 62002, 62004, 62012}:
            raise ContentUnavailable(f"content unavailable or restricted (API {code})")
        if code != 0 or not payload.get("data"):
            raise DownloadError(f"API returned {code}")
        return payload["data"]

    def resolve(self, bvid: str, page: int) -> dict:
        for method, endpoint in (("view", "/x/web-interface/view"),
                                 ("pagelist", "/x/player/pagelist")):
            try:
                data = self._data(self._json(f"{API}{endpoint}?{urlencode({'bvid': bvid})}"))
                pages = data.get("pages", []) if method == "view" else data
                selected = next((part for part in pages if part.get("page") == page), None)
                if selected is None:
                    raise ContentUnavailable(f"requested part {page} unavailable or restricted")
                metadata = {
                    "bvid": bvid, "page": page, "cid": selected["cid"],
                    "title": data.get("title", "") if method == "view" else selected["part"],
                    "duration": selected.get("duration"), "metadata_method": method,
                }
                self._record(method, "ok")
                return metadata
            except ContentUnavailable:
                self._record(method, "restricted")
                raise
            except (DownloadError, KeyError, TypeError) as error:
                self._record(method, "failed", str(error))
        raise DownloadError("metadata methods exhausted")

    def _transfer(self, url: str, path: Path) -> None:
        self._curl(url, path)
        if not path.stat().st_size:
            raise DownloadError("empty media response")

    def download_stream(self, stream: dict, filename: str) -> Path:
        target = self.output_dir / filename
        if target.exists():
            raise DownloadError(f"existing stream file: {filename}; choose a new output directory")
        urls = [stream.get("baseUrl") or stream.get("base_url")]
        urls.extend(stream.get("backupUrl") or stream.get("backup_url") or [])
        with TemporaryDirectory(prefix="bili-stream-", dir=self.output_dir) as work:
            partial = Path(work) / "stream.part"
            for url in dict.fromkeys(urls):
                if not url or urlsplit(url).scheme != "https":
                    continue
                try:
                    self._transfer(url, partial)
                    partial.rename(target)
                    self._record(filename, "ok", urlsplit(url).hostname or "")
                    return target
                except DownloadError as error:
                    self._record(filename, "failed", str(error))
        raise DownloadError(f"all CDN URLs failed for {filename}")

    def _direct(self, metadata: dict) -> Path:
        params = {"bvid": metadata["bvid"], "cid": metadata["cid"],
                  "qn": 127, "fnval": 4048, "fourk": 1}
        try:
            play = self._data(self._json(f"{API}/x/player/playurl?{urlencode(params)}"))
            if play.get("is_preview") or play.get("isPreview"):
                raise ContentUnavailable("preview-only or restricted stream")
            self._record("playurl", "ok")
        except DownloadError:
            self._record("playurl", "failed")
            raise
        dash = play.get("dash") or {}
        videos, audios = dash.get("video") or [], dash.get("audio") or []
        if not videos or not audios:
            raise DownloadError("no complete DASH audio/video pair")
        video = max(videos, key=lambda item: (
            item["id"], item.get("codecs", "").startswith("avc1"), item.get("bandwidth", 0),
        ))
        audio = max(audios, key=lambda item: item.get("bandwidth", 0))
        video_path = self.download_stream(video, "video.m4s")
        audio_path = self.download_stream(audio, "audio.m4s")
        merged = self.output_dir / "direct.mp4"
        result = subprocess.run([
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
            "-i", str(video_path), "-i", str(audio_path), "-c", "copy",
            "-movflags", "+faststart", str(merged),
        ], capture_output=True, text=True, check=False)
        if result.returncode:
            raise DownloadError(f"ffmpeg merge exit {result.returncode}")
        return merged

    def _yt_dlp(self, url: str) -> Path:
        if not shutil.which("yt-dlp"):
            raise DownloadError("yt-dlp not installed")
        target = self.output_dir / "ytdlp-verified.mp4"
        if target.exists():
            raise DownloadError("existing yt-dlp candidate; choose a new output directory")
        with TemporaryDirectory(prefix="bili-ytdlp-", dir=self.output_dir) as work:
            result = subprocess.run([
                "yt-dlp", "--ignore-config", "--no-playlist", "--no-overwrites",
                "--socket-timeout", "20", "--retries", "1", "--fragment-retries", "1",
                "--merge-output-format", "mp4", "-f",
                "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
                "-o", str(Path(work) / "reference.%(ext)s"), url,
            ], capture_output=True, text=True, check=False)
            path = Path(work) / "reference.mp4"
            if result.returncode or not path.exists():
                raise DownloadError(f"yt-dlp exit {result.returncode}; no verified media")
            self.probe(path)
            path.rename(target)
        return target

    def probe(self, path: Path, expected_duration: float | None = None) -> dict:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_type,codec_name,width,height:format=duration", "-of", "json", str(path),
        ], capture_output=True, text=True, check=False)
        try:
            probe = json.loads(result.stdout)
            streams = probe["streams"]
            duration = float(probe["format"]["duration"])
            if result.returncode or not {"video", "audio"}.issubset(
                {stream.get("codec_type") for stream in streams}
            ):
                raise DownloadError("download missing readable video or audio")
            if duration <= 0 or (expected_duration and
                    abs(duration - expected_duration) > max(1, expected_duration * 0.02)):
                raise DownloadError("download duration does not match source; possibly truncated")
            return probe
        except (KeyError, TypeError, ValueError) as error:
            raise DownloadError("invalid ffprobe result") from error

    def download(self, reference: str) -> Path:
        bvid, page = parse_reference(reference)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / "reference.mp4"
        report_path = self.output_dir / "download-report.json"
        if target.exists():
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                if (report["status"] != "ok" or report["bvid"] != bvid
                        or report["page"] != page or report["sha256"] != _sha256(target)):
                    raise ValueError("cache does not match")
                self.probe(target, report.get("metadata", {}).get("duration"))
                return target
            except (OSError, ValueError, KeyError, DownloadError) as error:
                raise DownloadError("existing media not verified; choose a new output directory") \
                    from error
        url = f"{REFERER}video/{bvid}/?p={page}"
        report = {"source_url": url, "bvid": bvid, "page": page, "status": "failed",
                  "browser_started": False, "attempts": self.attempts,
                  "downloaded_at": datetime.now(UTC).isoformat()}
        metadata = {}
        try:
            try:
                metadata = self.resolve(bvid, page)
                report["metadata"] = metadata
                path = self._direct(metadata)
                probe = self.probe(path, metadata.get("duration"))
            except ContentUnavailable:
                raise
            except DownloadError as error:
                self._record("direct", "failed", str(error))
                try:
                    path = self._yt_dlp(url)
                    probe = self.probe(path, metadata.get("duration"))
                    self._record("yt-dlp", "ok")
                except DownloadError as error:
                    self._record("yt-dlp", "failed", str(error))
                    raise DownloadError(
                        f"all applicable non-browser methods failed; see {report_path}"
                    ) from error
            path.rename(target)
            report.update(status="ok", metadata=metadata, probe=probe, sha256=_sha256(target))
            return target
        finally:
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", help="BV identifier or Bilibili video/watchlater URL")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        path = BilibiliDownloader(args.output_dir).download(args.reference)
    except (ValueError, DownloadError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
