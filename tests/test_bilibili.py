import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from avatar_pipeline.bilibili import BilibiliDownloader, DownloadError, parse_reference

BV = "BV1Bkh96wE8M"


@pytest.mark.parametrize("value", [BV, f"https://www.bilibili.com/video/{BV}/"])
def test_parse_reference(value):
    assert parse_reference(value) == (BV, 1)


def test_parse_watchlater_and_selected_part():
    assert parse_reference(f"https://www.bilibili.com/list/watchlater?bvid={BV}&p=2") == (BV, 2)


@pytest.mark.parametrize("value", ["https://evil.test/" + BV, BV + "extra", BV + "?p=0"])
def test_reject_invalid_reference(value):
    with pytest.raises(ValueError):
        parse_reference(value)


def test_view_412_falls_back_to_pagelist_without_browser(tmp_path, monkeypatch):
    downloader = BilibiliDownloader(tmp_path)
    calls = []

    def request(url):
        calls.append(url)
        if "/view?" in url:
            raise DownloadError("HTTP 412")
        return {"code": 0, "data": [{"cid": 42, "page": 1, "part": "test", "duration": 79}]}

    monkeypatch.setattr(downloader, "_json", request)
    metadata = downloader.resolve(BV, 1)
    assert metadata["cid"] == 42
    assert metadata["metadata_method"] == "pagelist"
    assert len(calls) == 2
    assert downloader.attempts[0]["status"] == "failed"


def test_selected_part_is_not_silently_replaced_with_first(tmp_path, monkeypatch):
    downloader = BilibiliDownloader(tmp_path)
    monkeypatch.setattr(downloader, "_json", lambda url: {
        "code": 0, "data": {"title": "test", "cid": 11, "pages": [
            {"cid": 11, "page": 1, "duration": 4},
            {"cid": 22, "page": 2, "duration": 8},
        ]},
    })
    assert downloader.resolve(BV, 2)["cid"] == 22


def test_restricted_content_does_not_fall_back(tmp_path, monkeypatch):
    downloader = BilibiliDownloader(tmp_path)
    calls = []

    def request(url):
        calls.append(url)
        return {"code": -404, "message": "not found"}

    monkeypatch.setattr(downloader, "_json", request)
    with pytest.raises(DownloadError, match="restricted"):
        downloader.resolve(BV, 1)
    assert len(calls) == 1


def test_cdn_backup_is_tried_after_primary_failure(tmp_path, monkeypatch):
    downloader = BilibiliDownloader(tmp_path)
    calls = []

    def transfer(url, path):
        calls.append(url)
        if "primary" in url:
            path.write_bytes(b"partial")
            raise DownloadError("HTTP 403")
        path.write_bytes(b"complete")

    monkeypatch.setattr(downloader, "_transfer", transfer)
    path = downloader.download_stream({
        "baseUrl": "https://primary.bilivideo.com/a?token=secret",
        "backupUrl": ["https://backup.bilivideo.com/a?token=secret"],
    }, "video.m4s")
    assert path.read_bytes() == b"complete"
    assert len(calls) == 2
    assert "secret" not in json.dumps(downloader.attempts)


def test_all_failures_write_report_without_opening_browser(tmp_path, monkeypatch):
    downloader = BilibiliDownloader(tmp_path)

    def fail(url):
        raise DownloadError("HTTP 412")

    monkeypatch.setattr(downloader, "_json", fail)
    monkeypatch.setattr(downloader, "_yt_dlp", lambda url: (_ for _ in ()).throw(
        DownloadError("yt-dlp HTTP 412")
    ))
    with pytest.raises(DownloadError, match="non-browser"):
        downloader.download(BV)
    report = json.loads((tmp_path / "download-report.json").read_text())
    assert report["status"] == "failed"
    assert report["browser_started"] is False
    assert [item["method"] for item in report["attempts"]] == [
        "view", "pagelist", "direct", "yt-dlp",
    ]


def test_untracked_existing_media_is_not_overwritten(tmp_path):
    path = tmp_path / "reference.mp4"
    path.write_bytes(b"user media")
    with pytest.raises(DownloadError, match="existing"):
        BilibiliDownloader(tmp_path).download(BV)
    assert path.read_bytes() == b"user media"


def test_probe_rejects_silent_or_truncated_download(tmp_path, monkeypatch):
    downloader = BilibiliDownloader(tmp_path)

    def probe(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, json.dumps({
            "streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
            "format": {"duration": "2"},
        }), "")

    monkeypatch.setattr("avatar_pipeline.bilibili.subprocess.run", probe)
    with pytest.raises(DownloadError, match="audio"):
        downloader.probe(Path("test.mp4"), expected_duration=79)


def test_probe_rejects_truncated_video_even_with_audio(tmp_path, monkeypatch):
    downloader = BilibiliDownloader(tmp_path)
    monkeypatch.setattr("avatar_pipeline.bilibili.subprocess.run", lambda *a, **kw:
        subprocess.CompletedProcess(a, 0, json.dumps({
            "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
            "format": {"duration": "3"},
        }), ""))
    with pytest.raises(DownloadError, match="truncated"):
        downloader.probe(Path("test.mp4"), expected_duration=79)


def test_verified_matching_cache_is_reused(tmp_path, monkeypatch):
    target = tmp_path / "reference.mp4"
    target.write_bytes(b"verified source")
    (tmp_path / "download-report.json").write_text(json.dumps({
        "status": "ok", "bvid": BV, "page": 1,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "metadata": {"duration": 79},
    }))
    downloader = BilibiliDownloader(tmp_path)
    monkeypatch.setattr(downloader, "probe", lambda *a: {})
    monkeypatch.setattr(downloader, "resolve", lambda *a: pytest.fail("cache caused network call"))
    assert downloader.download(BV) == target


def test_corrupt_cache_is_not_reused(tmp_path):
    target = tmp_path / "reference.mp4"
    target.write_bytes(b"corrupt")
    (tmp_path / "download-report.json").write_text(json.dumps({
        "status": "ok", "bvid": BV, "page": 1, "sha256": "old hash",
    }))
    with pytest.raises(DownloadError, match="existing"):
        BilibiliDownloader(tmp_path).download(BV)
    assert target.read_bytes() == b"corrupt"


def test_ytdlp_ignores_user_config_and_cannot_reuse_old_file(tmp_path, monkeypatch):
    existing = tmp_path / "ytdlp-reference.mp4"
    existing.write_bytes(b"unrelated user file")
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("-o") + 1].replace("%(ext)s", "mp4"))
        assert output.parent != tmp_path
        output.write_bytes(b"new download")
        return subprocess.CompletedProcess(command, 0, "", "")

    downloader = BilibiliDownloader(tmp_path)
    monkeypatch.setattr("avatar_pipeline.bilibili.shutil.which", lambda name: name)
    monkeypatch.setattr("avatar_pipeline.bilibili.subprocess.run", run)
    monkeypatch.setattr(downloader, "probe", lambda *a: {})
    path = downloader._yt_dlp(f"https://www.bilibili.com/video/{BV}/")
    assert path.read_bytes() == b"new download"
    assert existing.read_bytes() == b"unrelated user file"
    assert "--ignore-config" in commands[0]


def test_direct_failure_is_recorded_before_ytdlp_success(tmp_path, monkeypatch):
    downloader = BilibiliDownloader(tmp_path)
    metadata = {"cid": 42, "duration": 79}
    monkeypatch.setattr(downloader, "resolve", lambda *a: metadata)
    monkeypatch.setattr(downloader, "_direct", lambda *a: (_ for _ in ()).throw(
        DownloadError("ffmpeg merge exit 1")
    ))
    path = tmp_path / "fallback.mp4"
    path.write_bytes(b"new source")
    monkeypatch.setattr(downloader, "_yt_dlp", lambda *a: path)
    monkeypatch.setattr(downloader, "probe", lambda *a: {})
    assert downloader.download(BV).read_bytes() == b"new source"
    report = json.loads((tmp_path / "download-report.json").read_text())
    assert report["metadata"] == metadata
    assert report["attempts"][0] == {
        "method": "direct", "status": "failed", "detail": "ffmpeg merge exit 1",
    }
    assert report["attempts"][1]["method"] == "yt-dlp"
