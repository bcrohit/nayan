# Nayan

AI-powered navigation assistant for visually impaired users — research prototype.

**Phase 1 (current):** walking trajectory estimation from egocentric ( chest-level ) video.

## What it does

1. Reads a walking video ( file or webcam ).
2. Segments walkable surfaces ( road, sidewalk ) with a pretrained SegFormer model ( Cityscapes ).
3. Extracts a corridor centerline and boundary lines from the walkable mask.
4. Smooths the path temporally and overlays it on the video.

Future phases will add obstacle detection, distance estimation, prioritization, and LLM-based explanations on top of this pipeline.

## Architecture

```
video input
    → WalkableRegionDetector   (semantic segmentation)
    → TrajectoryEstimator      (corridor centerline + boundaries)
    → TrajectorySmoother       (temporal EMA)
    → TrajectoryVisualizer     (overlay on frame)
```

Modules are split so later stages can plug in without rewriting Phase 1:

| Module | Role | Future use |
|--------|------|------------|
| `perception/` | Walkable surface detection | Obstacle detection |
| `trajectory/` | Path estimation & smoothing | Distance along path |
| `visualization/` | Frame overlay | Debug / mobile preview |
| `types.py` | Shared dataclasses | LLM context payloads |

## Setup

Requires Python 3.10+. Uses ONNX Runtime by default (no PyTorch install needed).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Optional GPU / PyTorch backend:

```bash
pip install -e ".[torch]"
nayan-trajectory video.mp4 --backend torch --device cuda
```

First run downloads SegFormer ONNX weights (~15 MB) from Hugging Face.

## Usage

Process a video file and show a live preview:

```bash
nayan-trajectory path/to/walking_video.mp4 --display
```

Save annotated output without a window:

```bash
nayan-trajectory path/to/walking_video.mp4 -o output.mp4
```

Webcam ( device index 0 ):

```bash
nayan-trajectory 0 --display
```

Quick test on first 60 frames:

```bash
nayan-trajectory path/to/walking_video.mp4 --max-frames 60 -o preview.mp4
```

### Options

| Flag | Description |
|------|-------------|
| `--display` | Show OpenCV preview window ( default when no `-o` ) |
| `-o`, `--output` | Save annotated MP4 |
| `--max-frames N` | Limit frames processed |
| `--backend onnx` | Segmentation backend (`onnx` default, or `torch`) |
| `--inference-width 512` | Segmentation input size; lower = faster |
| `--device cuda` | Force GPU inference (torch backend, or ONNX CUDA provider) |
| `--no-mask` | Hide green walkable overlay; show trajectory lines only |

Press `q` or `Esc` to quit the preview.

## Visualization legend

- **Green tint** — detected walkable region
- **Green center line** — estimated walking trajectory
- **Orange boundary lines** — corridor edges
- **Orange dot** — estimated vanishing point ( perspective hint )

## Performance notes

- SegFormer-B0 at 512 px typically reaches interactive rates on CPU with ONNX Runtime.
- Use `--backend torch --device cuda` for faster GPU inference when PyTorch is installed.
- The pipeline is single-threaded; batching and TensorRT are future optimizations.

## Project layout

```
src/nayan/
  cli.py                 # CLI entry point
  pipeline.py            # Orchestrates perception → trajectory → viz
  types.py               # Shared data structures
  perception/
    walkable_onnx.py       # SegFormer ONNX walkable-region detector (default)
    walkable_torch.py      # Optional PyTorch SegFormer backend
    walkable_common.py     # Shared Cityscapes class constants
    base.py                # Abstract interfaces (incl. future ObstacleDetector)
  trajectory/
    estimator.py         # Centerline extraction from mask
    smoother.py          # Temporal smoothing
  visualization/
    overlay.py           # Draw trajectory on frame
  video/
    io.py                # Video read / write
```

## Next steps ( not in Phase 1 )

- Obstacle detection intersecting the trajectory corridor
- Monocular depth for distance estimation
- Obstacle prioritization by proximity and path overlap
- LLM / VLM descriptions for navigation feedback
