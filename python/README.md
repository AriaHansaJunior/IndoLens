# IndoLens AI Processing Core

This folder contains the Python AI pipeline for **IndoLens**.

## Communication Architecture
Laravel → Process (CLI) → Python → JSON → Laravel

## Module Structure
- `config/`: Configuration and path constants.
- `yolo/`: YOLOv8 face detection logic.
- `facenet/`: FaceNet feature extraction & 128-dimensional embedding generation.
- `recognition/`: Euclidean distance computation & actor matching logic.
- `utils/`: Helper utilities (JSON writers, video frame extraction, overlay renderers).
- `weights/`: Pretrained model weight files.
- `datasets/`: Training & reference face dataset.
- `embeddings/`: Saved face embedding matrices.
- `outputs/`: Processed output files and metadata.
- `temp/`: Temporary processing cache (frames, cropped face patches).

## Standard JSON Output Schema
```json
{
  "status": "success",
  "video": "path/to/video.mp4",
  "actors": [],
  "detections": [],
  "processing_time": 0.0
}
```
