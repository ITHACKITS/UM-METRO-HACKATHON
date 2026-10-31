"""TUAI Sigap pest-decoder tests."""

from __future__ import annotations

import numpy as np

from app.sigap.models.pest import PestAdapter


def test_yolo11_raw_output_decode_and_classwise_nms(tmp_path):
    adapter = PestAdapter(tmp_path / "model.onnx", candidate_threshold=0.05)
    # 102 IP102 classes + 4 xywh channels, in common [1, channels, anchors] layout.
    output = np.zeros((1, 106, 200), dtype=np.float32)
    output[0, 0:4, 10] = [320, 320, 120, 100]
    output[0, 4 + 7, 10] = 0.8
    output[0, 0:4, 11] = [322, 320, 120, 100]
    output[0, 4 + 7, 11] = 0.7
    output[0, 0:4, 20] = [100, 120, 40, 50]
    output[0, 4 + 4, 20] = 0.65

    detections = adapter._decode_raw(
        output, original_size=(640, 640), scale=1.0, pad_x=0, pad_y=0
    )
    assert [item.class_id for item in detections] == [7, 4]
    assert detections[0].score == np.float32(0.8)
    assert detections[0].bbox.x_min == 260
    assert detections[0].bbox.y_max == 370


def test_postprocessed_output_filters_unsupported_classes(tmp_path):
    adapter = PestAdapter(tmp_path / "model.onnx", candidate_threshold=0.1)
    output = np.asarray(
        [
            [10, 20, 100, 120, 0.9, 0],
            [50, 50, 80, 80, 0.99, 99],
        ],
        dtype=np.float32,
    )
    detections = adapter._decode_raw(
        output, original_size=(640, 640), scale=1.0, pad_x=0, pad_y=0
    )
    assert len(detections) == 1
    assert detections[0].class_id == 0


def test_channel_first_postprocessed_output_is_transposed(tmp_path):
    adapter = PestAdapter(tmp_path / "model.onnx", candidate_threshold=0.1)
    output = np.zeros((1, 6, 20), dtype=np.float32)
    output[0, :, 3] = [10, 20, 100, 120, 0.9, 4]

    detections = adapter._decode_raw(
        output, original_size=(640, 640), scale=1.0, pad_x=0, pad_y=0
    )

    assert len(detections) == 1
    assert detections[0].class_id == 4

