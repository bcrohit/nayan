from __future__ import annotations

import argparse
import sys
import time

import cv2

from nayan.perception import create_walkable_detector
from nayan.pipeline import TrajectoryPipeline
from nayan.trajectory.estimator import TrajectoryEstimator
from nayan.trajectory.smoother import TrajectorySmoother
from nayan.video.io import VideoSource, VideoWriter
from nayan.visualization.overlay import TrajectoryVisualizer


def _parse_source(value: str) -> str | int:
    if value.isdigit():
        return int(value)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Nayan Phase 1 — estimate and visualize walking trajectory from egocentric video.",
    )
    parser.add_argument(
        "input",
        type=_parse_source,
        help="Path to input video file, or webcam index (e.g. 0).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Optional path to save annotated output video (.mp4).",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Show live preview window.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Process at most this many frames (useful for quick tests).",
    )
    parser.add_argument(
        "--backend",
        choices=("onnx", "torch"),
        default="onnx",
        help="Segmentation backend (default: onnx — no PyTorch required).",
    )
    parser.add_argument(
        "--inference-width",
        type=int,
        default=512,
        help="Segmentation input size in pixels (lower = faster).",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Torch device for segmentation model (default: cuda if available else cpu).",
    )
    parser.add_argument(
        "--no-mask",
        action="store_true",
        help="Hide walkable-region overlay; show trajectory lines only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    display = args.display or args.output is None
    if not display and args.output is None:
        print("Nothing to do: provide --output and/or --display.", file=sys.stderr)
        return 1

    print(f"Loading walkable-region model ({args.backend}, first run downloads weights)...")
    detector = create_walkable_detector(
        backend=args.backend,
        inference_size=args.inference_width,
        device=args.device,
    )

    pipeline = TrajectoryPipeline(
        walkable_detector=detector,
        trajectory_estimator=TrajectoryEstimator(),
        smoother=TrajectorySmoother(),
        visualizer=TrajectoryVisualizer(show_walkable_mask=not args.no_mask),
    )

    source = VideoSource(path=args.input, max_frames=args.max_frames)
    source.open()

    writer: VideoWriter | None = None
    if args.output:
        writer = VideoWriter(
            path=args.output,
            fps=source.fps,
            frame_size=(source.width, source.height),
        )

    frame_times: list[float] = []
    processed = 0

    try:
        for result in pipeline.run(source):
            processed += 1
            frame_times.append(time.perf_counter())

            if len(frame_times) > 1:
                dt = frame_times[-1] - frame_times[-2]
                fps = 1.0 / dt if dt > 0 else 0.0
                label = f"FPS: {fps:.1f}  frame: {result.context.index}"
                cv2.putText(
                    result.frame,
                    label,
                    (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

            if writer is not None:
                writer.write(result.frame)

            if display:
                cv2.imshow("Nayan — Walking Trajectory", result.frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
    finally:
        if writer is not None:
            writer.close()
        cv2.destroyAllWindows()

    if processed == 0:
        print("No frames processed.", file=sys.stderr)
        return 1

    if len(frame_times) > 1:
        elapsed = frame_times[-1] - frame_times[0]
        avg_fps = (processed - 1) / elapsed if elapsed > 0 else 0.0
        print(f"Processed {processed} frames, avg {avg_fps:.1f} FPS")

    if args.output:
        print(f"Saved annotated video to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
