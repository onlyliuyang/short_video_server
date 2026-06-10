import logging
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

_HOMEBREW_BIN_CANDIDATES = (
    "/opt/homebrew/bin",
    "/usr/local/bin",
)


def _resolve_binary(name: str, configured: str) -> str:
    configured_path = Path(configured)
    if configured_path.is_file() and os.access(configured_path, os.X_OK):
        return str(configured_path.resolve())

    found = shutil.which(configured)
    if found:
        return found

    for prefix in _HOMEBREW_BIN_CANDIDATES:
        candidate = Path(prefix) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            logger.info("Auto-detected %s at %s", name, candidate)
            return str(candidate)

    raise RuntimeError(
        f"未找到 {name}。\n"
        f"macOS 请执行: brew install ffmpeg\n"
        f"或在 .env 中设置 {name.upper()}_PATH=/opt/homebrew/bin/{name}"
    )


@lru_cache(maxsize=1)
def _ffmpeg_supports_subtitles_filter(ffmpeg_bin: str) -> bool:
    result = subprocess.run(
        [ffmpeg_bin, "-filters"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and " subtitles " in result.stdout


class FFmpegService:
    SUBTITLE_STYLE = (
        "FontName=Arial,FontSize=22,"
        "PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2"
    )

    def __init__(self) -> None:
        self.ffmpeg = settings.ffmpeg_path
        self.ffprobe = settings.ffprobe_path
        self._resolved = False

    def ensure_available(self) -> None:
        if self._resolved:
            return
        self.ffmpeg = _resolve_binary("ffmpeg", self.ffmpeg)
        self.ffprobe = _resolve_binary("ffprobe", self.ffprobe)
        self._resolved = True
        logger.info("FFmpeg ready: ffmpeg=%s ffprobe=%s", self.ffmpeg, self.ffprobe)

    def _run(self, cmd: list[str], cwd: Path | None = None) -> None:
        logger.info("FFmpeg cmd: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        if result.returncode != 0:
            lines = [ln for ln in (result.stderr or "").splitlines() if ln.strip()]
            tail = "\n".join(lines[-12:]) if lines else "unknown error"
            logger.error("FFmpeg stderr: %s", tail)
            raise RuntimeError(f"FFmpeg failed: {tail}")

    def extract_last_frame(self, video_path: Path, output_path: Path) -> None:
        self.ensure_available()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Extract last frame: %s -> %s", video_path, output_path)
        cmd = [
            self.ffmpeg, "-y",
            "-sseof", "-0.1",
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",
            str(output_path),
        ]
        self._run(cmd)

    def get_duration_ms(self, video_path: Path) -> int:
        self.ensure_available()
        cmd = [
            self.ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return 0
        try:
            return int(float(result.stdout.strip()) * 1000)
        except ValueError:
            return 0

    def get_duration_sec(self, video_path: Path) -> float:
        return self.get_duration_ms(video_path) / 1000.0

    def concat_videos(
        self,
        video_paths: list[Path],
        output_path: Path,
        transition_sec: float = 0.0,
        transition_type: str = "fade",
    ) -> None:
        """拼接视频片段；transition_sec > 0 时使用 xfade dissolve 转场。"""
        self.ensure_available()
        if not video_paths:
            raise ValueError("No videos to concat")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if len(video_paths) == 1 or transition_sec <= 0:
            self._concat_copy(video_paths, output_path)
            return

        durations = [self.get_duration_sec(p) for p in video_paths]
        min_dur = min(durations)
        if transition_sec >= min_dur:
            logger.warning(
                "Transition %.2fs >= shortest clip %.2fs, fallback to hard cut",
                transition_sec, min_dur,
            )
            self._concat_copy(video_paths, output_path)
            return

        self._concat_xfade(video_paths, durations, output_path, transition_sec, transition_type)

    def _concat_copy(self, video_paths: list[Path], output_path: Path) -> None:
        list_file = output_path.parent / "concat_list.txt"
        with open(list_file, "w") as f:
            for p in video_paths:
                f.write(f"file '{p.resolve()}'\n")

        logger.info("Concat (hard cut) %d segments -> %s", len(video_paths), output_path)
        cmd = [
            self.ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path),
        ]
        self._run(cmd)
        list_file.unlink(missing_ok=True)

    def _concat_xfade(
        self,
        video_paths: list[Path],
        durations: list[float],
        output_path: Path,
        transition_sec: float,
        transition_type: str,
    ) -> None:
        n = len(video_paths)
        logger.info(
            "Concat (xfade %s %.2fs) %d segments -> %s durations=%s",
            transition_type, transition_sec, n, output_path,
            [round(d, 2) for d in durations],
        )

        cmd: list[str] = [self.ffmpeg, "-y"]
        for p in video_paths:
            cmd.extend(["-i", str(p)])

        filters: list[str] = []
        prev_label = "0:v"
        accumulated = durations[0]

        for i in range(1, n):
            offset = max(0.0, accumulated - transition_sec)
            out_label = "vout" if i == n - 1 else f"v{i}"
            filters.append(
                f"[{prev_label}][{i}:v]xfade=transition={transition_type}"
                f":duration={transition_sec:.3f}:offset={offset:.3f}[{out_label}]"
            )
            prev_label = out_label
            accumulated += durations[i] - transition_sec

        cmd.extend([
            "-filter_complex", ";".join(filters),
            "-map", "[vout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an",
            "-movflags", "+faststart",
            str(output_path),
        ])
        self._run(cmd)

    def _audio_encode_args(self, output_path: Path) -> list[str]:
        """Pick codec matching container (mp3 must use libmp3lame, not aac)."""
        if output_path.suffix.lower() == ".mp3":
            return ["-c:a", "libmp3lame", "-b:a", "192k"]
        return ["-c:a", "aac", "-b:a", "192k"]

    def mix_audio_timeline(
        self,
        tracks: list[tuple[Path, float]],
        output_path: Path,
        total_duration: float | None = None,
    ) -> None:
        """将多段音频按时间轴偏移后混合（用于分段配音对齐视频）。"""
        self.ensure_available()
        if not tracks:
            raise ValueError("No audio tracks to mix")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if len(tracks) == 1 and tracks[0][1] <= 0 and total_duration is None:
            shutil.copy2(tracks[0][0], output_path)
            return

        cmd: list[str] = [self.ffmpeg, "-y"]
        for path, _ in tracks:
            cmd.extend(["-i", str(path.resolve())])

        filters: list[str] = []
        for i, (_, start_sec) in enumerate(tracks):
            delay_ms = max(0, int(start_sec * 1000))
            filters.append(
                f"[{i}:a]aresample=32000,asetpts=PTS-STARTPTS,adelay={delay_ms}|{delay_ms}[a{i}]"
            )

        labels = "".join(f"[a{i}]" for i in range(len(tracks)))
        if total_duration and total_duration > 0:
            filters.append(
                f"{labels}amix=inputs={len(tracks)}:duration=longest:dropout_transition=0:normalize=0[aout]"
            )
            filters.append(
                f"[aout]apad=whole_dur={total_duration:.3f},atrim=0:{total_duration:.3f}[aout2]"
            )
            map_label = "[aout2]"
        else:
            filters.append(
                f"{labels}amix=inputs={len(tracks)}:duration=longest:dropout_transition=0:normalize=0[aout]"
            )
            map_label = "[aout]"

        cmd.extend([
            "-filter_complex", ";".join(filters),
            "-map", map_label,
            *self._audio_encode_args(output_path),
            str(output_path),
        ])
        logger.info(
            "Mix audio timeline %d tracks -> %s total=%.2fs offsets=%s",
            len(tracks), output_path, total_duration or -1,
            [round(t[1], 2) for t in tracks],
        )
        self._run(cmd)

    @staticmethod
    def segment_start_sec(index: int, segment_duration: int, transition_sec: float) -> float:
        """第 index 段（0-based）在成片时间轴上的起始秒数。"""
        if index <= 0:
            return 0.0
        if transition_sec > 0:
            return index * (segment_duration - transition_sec)
        return index * segment_duration

    @staticmethod
    def expected_video_duration(
        segment_count: int,
        segment_duration: int,
        transition_sec: float,
    ) -> float:
        if segment_count <= 0:
            return 0.0
        if segment_count == 1:
            return float(segment_duration)
        if transition_sec <= 0:
            return float(segment_count * segment_duration)
        return float(segment_count * segment_duration - (segment_count - 1) * transition_sec)

    def merge_audio_video(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        subtitle_path: Path | None = None,
    ) -> None:
        self.ensure_available()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        video_dur = self.get_duration_sec(video_path)
        audio_dur = self.get_duration_sec(audio_path) if audio_path.exists() else 0.0
        logger.info(
            "Merge audio+video -> %s (video=%.2fs audio=%.2fs subtitle=%s)",
            output_path, video_dur, audio_dur, subtitle_path,
        )

        merged_av = output_path.parent / "_merged_av.mp4"
        try:
            # 以视频时长为准：音频不足则补静音，过长则截断；禁止 -shortest 裁切视频
            filter_a = f"[1:a]apad=whole_dur={video_dur:.3f},atrim=0:{video_dur:.3f}[aout]"
            cmd = [
                self.ffmpeg, "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-filter_complex", filter_a,
                "-map", "0:v:0", "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                str(merged_av),
            ]
            self._run(cmd)

            if subtitle_path and subtitle_path.exists():
                if _ffmpeg_supports_subtitles_filter(self.ffmpeg):
                    try:
                        self._burn_subtitles(merged_av, subtitle_path, output_path)
                    except RuntimeError as e:
                        logger.warning("Burn subtitles failed, fallback to soft subs: %s", e)
                        self._mux_soft_subtitles(merged_av, subtitle_path, output_path)
                else:
                    logger.info("FFmpeg has no libass/subtitles filter, using soft subtitles")
                    self._mux_soft_subtitles(merged_av, subtitle_path, output_path)
            else:
                shutil.move(str(merged_av), str(output_path))
                merged_av = output_path
        finally:
            if merged_av.exists() and merged_av != output_path:
                merged_av.unlink(missing_ok=True)

    def _burn_subtitles(self, video_path: Path, subtitle_path: Path, output_path: Path) -> None:
        work_dir = subtitle_path.parent.resolve()
        sub_name = subtitle_path.name
        # FFmpeg filter 中逗号需转义
        style = self.SUBTITLE_STYLE.replace(",", r"\,")
        vf = f"subtitles={sub_name}:force_style='{style}'"
        cmd = [
            self.ffmpeg, "-y",
            "-i", str(video_path.resolve()),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(output_path.resolve()),
        ]
        logger.info("Burn subtitles (hard) cwd=%s", work_dir)
        self._run(cmd, cwd=work_dir)

    def _mux_soft_subtitles(self, video_path: Path, subtitle_path: Path, output_path: Path) -> None:
        """Embed SRT as soft subtitle track (no libass required)."""
        cmd = [
            self.ffmpeg, "-y",
            "-i", str(video_path.resolve()),
            "-i", str(subtitle_path.resolve()),
            "-map", "0:v:0",
            "-map", "0:a:0",
            "-map", "1:0",
            "-c:v", "copy",
            "-c:a", "copy",
            "-c:s", "mov_text",
            "-metadata:s:s:0", "language=chi",
            "-movflags", "+faststart",
            str(output_path.resolve()),
        ]
        logger.info("Mux soft subtitles -> %s", output_path)
        self._run(cmd)

    def generate_srt(
        self,
        segments: list[dict],
        segment_duration: int,
        output_path: Path,
        transition_sec: float = 0.0,
    ) -> None:
        lines: list[str] = []
        for i, seg in enumerate(segments):
            if transition_sec > 0 and i > 0:
                start_sec = i * (segment_duration - transition_sec)
            else:
                start_sec = i * segment_duration
            end_sec = start_sec + segment_duration
            text = seg.get("subtitle") or seg.get("narration", "")
            lines.append(str(i + 1))
            lines.append(f"{self._format_time(start_sec)} --> {self._format_time(end_sec)}")
            lines.append(text)
            lines.append("")
        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(
            "SRT generated: %s (%d entries, transition=%.2fs)",
            output_path, len(segments), transition_sec,
        )

    @staticmethod
    def _format_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


ffmpeg_service = FFmpegService()
