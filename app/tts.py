"""Priority-based text-to-speech using edge-tts."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import edge_tts

    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    from pydub import AudioSegment
    from pydub.playback import play

    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False


class ActionPriority(IntEnum):
    CONTINUE = 1
    SLOW_DOWN = 2
    TURN_SLIGHT_LEFT = 3
    TURN_SLIGHT_RIGHT = 3
    TURN_LEFT = 3
    TURN_RIGHT = 3
    STOP = 4


@dataclass(order=True)
class TTSRequest:
    priority: int
    timestamp: float
    text: str = field(compare=False)
    action: str = field(compare=False)


class TTSService:
    """Background worker that synthesizes and plays queued speech."""

    def __init__(
        self,
        *,
        voice: str = "en-US-JennyNeural",
        rate: float = 0.5,
        cache_dir: Path | None = None,
    ) -> None:
        self.voice = voice
        self.rate = rate
        self.cache_dir = cache_dir or Path("/tmp/nayan_tts_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._queue: queue.PriorityQueue[TTSRequest] = queue.PriorityQueue()
        self._current: TTSRequest | None = None
        self._interrupt = False
        self._worker: threading.Thread | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_ready(self) -> bool:
        return HAS_EDGE_TTS and HAS_PYDUB

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._worker = threading.Thread(target=self._worker_loop, daemon=True, name="tts-worker")
        self._worker.start()

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        if self._worker is not None:
            self._worker.join(timeout=5)
            self._worker = None

    def speak(self, text: str, action: str) -> None:
        if not self.is_ready:
            logger.warning("TTS dependencies unavailable; skipping speech")
            return

        if not text.strip():
            return

        try:
            priority = ActionPriority[action.upper()].value
        except KeyError:
            priority = ActionPriority.CONTINUE.value

        request = TTSRequest(
            priority=-priority,
            timestamp=time.time(),
            text=text.strip(),
            action=action.upper(),
        )
        self._queue.put(request)

        if priority >= ActionPriority.TURN_LEFT and self._current is not None:
            current_priority = ActionPriority[self._current.action].value
            if priority > current_priority:
                self._interrupt = True

    def _worker_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            while self._running:
                try:
                    request = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                self._current = request
                self._interrupt = False

                try:
                    loop.run_until_complete(self._synthesize_and_play(request))
                except Exception:
                    logger.exception("TTS request failed")
                finally:
                    self._current = None
        finally:
            loop.close()

    async def _synthesize_and_play(self, request: TTSRequest) -> None:
        cache_path = self._cache_path(request.text)

        if not cache_path.exists():
            await asyncio.wait_for(self._synthesize_to_file(request.text, cache_path), timeout=10.0)

        if cache_path.exists():
            self._play_audio(cache_path)

    async def _synthesize_to_file(self, text: str, output_path: Path) -> None:
        communicate = edge_tts.Communicate(text, self.voice, rate=f"{self.rate:+.0%}")

        with output_path.open("wb") as handle:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    handle.write(chunk["data"])

    def _play_audio(self, audio_path: Path) -> None:
        sound = AudioSegment.from_file(audio_path)
        chunk_ms = 500

        for offset in range(0, len(sound), chunk_ms):
            if self._interrupt:
                break
            play(sound[offset : offset + chunk_ms])

    def _cache_path(self, text: str) -> Path:
        digest = hashlib.sha256(f"{text}|{self.voice}|{self.rate}".encode()).hexdigest()
        return self.cache_dir / f"{digest}.mp3"
