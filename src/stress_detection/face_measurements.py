"""Geometric masks and raw-pixel measurements, not validated quality scores."""

import cv2
import numpy as np

FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
             397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
             172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
EYES = [[33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
        [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]]
MOUTH = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
REGIONS = {"forehead": [10, 338, 337, 336, 9, 107, 108, 109],
           "cheek_image_left": [50, 101, 205, 187, 147, 123],
           "cheek_image_right": [280, 330, 425, 411, 376, 352]}


def polygon_mask(points, shape):
    """Rasterize a polygon with OpenCV's image-boundary clipping; reject degeneracy."""
    height, width = shape
    mask = np.zeros((height, width), np.uint8)
    points = np.asarray(points, dtype=float)
    if (points.ndim != 2 or points.shape[1] != 2 or len(points) < 3
            or not np.isfinite(points).all() or np.abs(points).max(initial=0) > 1_000_000):
        return mask
    vertices = np.rint(points).astype(np.int32)
    if abs(cv2.contourArea(vertices)) < 1:
        return mask
    cv2.fillPoly(mask, [vertices], 255)
    return mask


def bounding_box(xy, width, height):
    low, high = xy.min(axis=0), xy.max(axis=0)
    clipped_low = np.clip(low, [0, 0], [width, height])
    clipped_high = np.clip(high, [0, 0], [width, height])
    box = [*clipped_low.tolist(), *clipped_high.tolist()]
    area = max(0, box[2] - box[0]) * max(0, box[3] - box[1])
    return {"xyxy_pixels": box, "unclipped_xyxy_pixels": [*low.tolist(), *high.tolist()],
            "frame_area_fraction": area / (width * height),
            "clipped": bool(np.any(low != clipped_low) or np.any(high != clipped_high))}


def face_masks(landmarks, shape, exclusion_margin_fraction=0.015):
    height, width = shape
    points = np.asarray(landmarks, dtype=float)
    if points.shape != (478, 3) or not np.isfinite(points).all() or np.abs(points[:, :2]).max() > 4:
        raise ValueError("Expected 478 finite normalized xyz landmarks within supported geometry range")
    xy = points[:, :2] * [width, height]
    box = bounding_box(xy[:468], width, height)
    area = box["frame_area_fraction"] * width * height
    face = polygon_mask(xy[FACE_OVAL], shape)
    exclusion = np.zeros(shape, np.uint8)
    for indices in [*EYES, MOUTH]:
        # Convex hull is intentionally conservative for eyes and mouth.
        hull = cv2.convexHull(np.rint(xy[indices]).astype(np.int32)).reshape(-1, 2)
        exclusion |= polygon_mask(hull, shape)
    radius = max(1, round(exclusion_margin_fraction * np.sqrt(area)))
    exclusion = cv2.dilate(exclusion, np.ones((2 * radius + 1, 2 * radius + 1), np.uint8))
    face = cv2.bitwise_and(face, cv2.bitwise_not(exclusion))
    masks = {name: cv2.bitwise_and(polygon_mask(xy[ids], shape), face) for name, ids in REGIONS.items()}
    return xy, box, face, masks, exclusion


def region_rgb(rgb, mask, min_pixels=32):
    count = int(cv2.countNonZero(mask))
    valid_input = rgb.dtype == np.uint8 and rgb.ndim == 3 and rgb.shape[2] == 3 and rgb.shape[:2] == mask.shape
    if not valid_input or count < min_pixels:
        return {"valid": False, "pixel_count": count, "mean_rgb": None,
                "reason": "invalid_rgb_input" if not valid_input else "insufficient_pixels"}
    return {"valid": True, "pixel_count": count, "mean_rgb": list(cv2.mean(rgb, mask=mask)[:3]), "reason": None}


def quality_measurements(rgb, face_mask, min_pixels=32, dark_threshold=20, saturated_threshold=235):
    count = int(cv2.countNonZero(face_mask))
    if count < min_pixels:
        return {"valid": False, "pixel_count": count, "reason": "insufficient_face_pixels"}
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    values = gray[face_mask != 0]
    interior = cv2.erode(face_mask, np.ones((3, 3), np.uint8)) != 0
    lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=1)
    return {"valid": True, "pixel_count": count, "brightness": float(values.mean()),
            "dark_fraction": float(np.mean(values <= dark_threshold)),
            "saturated_fraction": float(np.mean(values >= saturated_threshold)),
            "laplacian_variance": float(lap[interior].var()) if np.any(interior) else None,
            "sharpness_pixels": int(interior.sum())}


def normalized_motion(previous_xy, xy, previous_box, box, elapsed_seconds):
    if elapsed_seconds <= 0 or not np.isfinite(elapsed_seconds):
        return None
    def size(b):
        return np.sqrt(max(0, b[2] - b[0]) * max(0, b[3] - b[1]))
    scale = (size(previous_box) + size(box)) / 2
    if scale <= 0 or previous_xy.shape != xy.shape:
        return None
    rms = np.sqrt(np.mean(np.sum((xy - previous_xy) ** 2, axis=1)))
    return float(rms / scale / elapsed_seconds)


class SingleFaceTrack:
    """One contiguous geometrically associated track; no automatic reacquisition.

    This is not identity recognition. Once acquired, a missing/multiple face,
    timing fault, or large spatial discontinuity latches the track as lost.
    Later detections are recorded but cannot silently become the selected person.
    """

    def __init__(self, min_iou=0.2, max_center_shift=0.5, max_gap_seconds=0.5):
        self.previous_box = self.previous_time = None
        self.lost = False
        self.min_iou, self.max_center_shift, self.max_gap = min_iou, max_center_shift, max_gap_seconds

    def invalidate(self):
        if self.previous_box is not None:
            self.lost = True

    def accept(self, faces, timestamp, width, height):
        if len(faces) != 1:
            self.invalidate()
            return None, "missing_face" if not faces else "multiple_faces"
        points = np.asarray(faces[0], dtype=float)
        if points.shape != (478, 3) or not np.isfinite(points).all() or np.abs(points[:, :2]).max() > 4:
            self.invalidate()
            return None, "invalid_landmarks"
        box = bounding_box(points[:468, :2] * [width, height], width, height)["xyxy_pixels"]
        if box[2] <= box[0] or box[3] <= box[1]:
            self.invalidate()
            return None, "invalid_face_box"
        if self.lost:
            return None, "track_lost_no_reacquisition"
        if self.previous_box is not None:
            a, b = np.array(self.previous_box), np.array(box)
            intersection = np.maximum(0, np.minimum(a[2:], b[2:]) - np.maximum(a[:2], b[:2])).prod()
            area_a, area_b = np.prod(a[2:] - a[:2]), np.prod(b[2:] - b[:2])
            iou = intersection / max(area_a + area_b - intersection, 1e-12)
            shift = np.linalg.norm((a[:2] + a[2:] - b[:2] - b[2:]) / 2) / np.sqrt(area_a)
            if (timestamp <= self.previous_time or timestamp - self.previous_time > self.max_gap
                    or iou < self.min_iou or shift > self.max_center_shift):
                self.lost = True
                return None, "track_continuity_failed"
        self.previous_box, self.previous_time = box, timestamp
        return points, "tracked"
