# Working Detection Models Bundle (V6 + YOLO)

This folder contains the current working models used by the Flask demo.

## Folder
`d:\Graduation Project\model_bundle_v6_working`

## Included Files
- `violence_detector_v6_production_ts.pt` (TorchScript violence classifier, production runtime file)
- `violence_detector_v6_production_state_dict.pt` (training checkpoint weights)
- `violence_detector_v6_config.json` (model input + threshold profiles)
- `people_detector_yolov8n.pt` (YOLO person detector)
- `violence_test_metrics.json` (internal test set metrics)
- `violence_external_metrics.json` (external holdout metrics)
- `runtime_info_training_machine.json` (hardware/software used for training)

## Model Names and Roles
1. Violence model: **MobileNetV2TemporalAttention V6**
   - Runtime file: `violence_detector_v6_production_ts.pt`
   - Input shape: `[1, 12, 3, 160, 160]`
   - Frame stride: `2`
   - Deploy profile: `balanced`
   - Deploy threshold: `0.315`

2. People detector: **YOLOv8n**
   - Runtime file: `people_detector_yolov8n.pt`
   - Used only for person boxes/counting in the overlay

## Verified Metrics (from this exact V6 run)
Source run: `outputs\mobilenetv2_v6_vigil\RUN_V6_FULL_20260301`

- Internal test (`n=479`, balanced threshold `0.315`):
  - Accuracy: `0.8079`
  - Precision: `0.7552`
  - Recall: `0.9076`
  - F1: `0.8244`
  - ROC-AUC: `0.9072`

- External holdout (`n=60`, balanced threshold `0.315`):
  - Accuracy: `0.8167`
  - Precision: `0.8065`
  - Recall: `0.8333`
  - F1: `0.8197`
  - ROC-AUC: `0.8933`

## SHA256 (integrity)
- `violence_detector_v6_production_ts.pt`: `C20A0C1743A4C6B9746BB2E86A36367C17A0207EF605197D08F13CB3B125A79C`
- `people_detector_yolov8n.pt`: `F59B3D833E2FF32E194B5BB8E08D211DC7C5BDF144B90D2C8412C47CCFC83B36`

## How to use these exact files in Flask
```powershell
$env:VIOLENCE_MODEL_TS='d:\Graduation Project\model_bundle_v6_working\violence_detector_v6_production_ts.pt';
$env:VIOLENCE_EXPORT_CONFIG='d:\Graduation Project\model_bundle_v6_working\violence_detector_v6_config.json';
$env:YOLO_WEIGHTS='d:\Graduation Project\model_bundle_v6_working\people_detector_yolov8n.pt';
$env:TH_PROFILE='balanced';
$env:YOLO_DEVICE='cuda:0';
$env:VIDEO_CODEC_PRIORITY='mp4v';
$env:TRANSCODE_ANNOTATED_TO_H264='1';
& 'd:\Graduation Project\.venv_mobilenet_gpu\Scripts\python.exe' 'd:\Graduation Project\violence-flask\app.py'
```

## Notes
- `balanced` is recommended for demo stability.
- For fewer false alarms, switch to `TH_PROFILE='high_precision'` (lower recall).
- ONNX is not included in this bundle because it was not exported in this run.
