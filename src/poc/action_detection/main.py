#!/usr/bin/env python3
"""
Action Detection with Rectangle Tracking

This script detects actions/movement in a video using OpenCV motion detection
and draws a red rectangle that follows the action areas smoothly.

Usage:
    python main.py <input_video> <output_video>
"""

import sys
import cv2
import numpy as np
from typing import Tuple, Optional
import argparse


class ActionTracker:
    def __init__(self, smoothing_factor: float = 0.7, min_area: int = 1000):
        self.smoothing_factor = smoothing_factor
        self.min_area = min_area
        self.prev_center = None
        self.prev_rect_size = None
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=False, varThreshold=50
        )
        
    def detect_motion_center(self, frame: np.ndarray, prev_frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Detect motion and return bounding rectangle (x, y, w, h)"""
        
        # Method 1: Background subtraction
        fg_mask = self.background_subtractor.apply(frame)
        
        # Method 2: Frame differencing
        frame_diff = cv2.absdiff(prev_frame, frame)
        gray_diff = cv2.cvtColor(frame_diff, cv2.COLOR_BGR2GRAY)
        _, thresh_diff = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
        
        # Combine both methods
        combined_mask = cv2.bitwise_or(fg_mask, thresh_diff)
        
        # Morphological operations to clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
            
        # Filter contours by area and merge nearby ones
        valid_contours = [c for c in contours if cv2.contourArea(c) > self.min_area]
        
        if not valid_contours:
            return None
            
        # Get bounding rectangle of all valid contours
        all_points = np.vstack(valid_contours)
        x, y, w, h = cv2.boundingRect(all_points)
        
        return (x, y, w, h)
    
    def smooth_rectangle(self, current_rect: Optional[Tuple[int, int, int, int]]) -> Optional[Tuple[int, int, int, int]]:
        """Apply smoothing to rectangle position and size"""
        if current_rect is None:
            if self.prev_center is None:
                return None
            # Return previous rectangle if no current motion detected
            smooth_w, smooth_h = self.prev_rect_size
            smooth_x = self.prev_center[0] - smooth_w // 2
            smooth_y = self.prev_center[1] - smooth_h // 2
            return (smooth_x, smooth_y, smooth_w, smooth_h)
            
        x, y, w, h = current_rect
        center_x, center_y = x + w // 2, y + h // 2
        
        if self.prev_center is None:
            self.prev_center = (center_x, center_y)
            self.prev_rect_size = (w, h)
        else:
            # Smooth center position
            prev_cx, prev_cy = self.prev_center
            smooth_cx = int(prev_cx * self.smoothing_factor + center_x * (1 - self.smoothing_factor))
            smooth_cy = int(prev_cy * self.smoothing_factor + center_y * (1 - self.smoothing_factor))
            self.prev_center = (smooth_cx, smooth_cy)
            
            # Smooth rectangle size
            prev_w, prev_h = self.prev_rect_size
            smooth_w = int(prev_w * self.smoothing_factor + w * (1 - self.smoothing_factor))
            smooth_h = int(prev_h * self.smoothing_factor + h * (1 - self.smoothing_factor))
            self.prev_rect_size = (smooth_w, smooth_h)
        
        # Convert back to rectangle coordinates
        smooth_w, smooth_h = self.prev_rect_size
        smooth_x = self.prev_center[0] - smooth_w // 2
        smooth_y = self.prev_center[1] - smooth_h // 2
        
        return (smooth_x, smooth_y, smooth_w, smooth_h)


def draw_tracking_rectangle(frame: np.ndarray, rect: Optional[Tuple[int, int, int, int]], 
                          color: Tuple[int, int, int] = (0, 0, 255), thickness: int = 3) -> np.ndarray:
    """Draw red tracking rectangle on frame"""
    if rect is None:
        return frame
        
    x, y, w, h = rect
    
    # Ensure rectangle is within frame bounds
    height, width = frame.shape[:2]
    x = max(0, min(x, width - w))
    y = max(0, min(y, height - h))
    w = min(w, width - x)
    h = min(h, height - y)
    
    # Draw rectangle
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
    
    # Add corner markers for better visibility
    corner_size = 15
    # Top-left corner
    cv2.line(frame, (x, y), (x + corner_size, y), color, thickness + 1)
    cv2.line(frame, (x, y), (x, y + corner_size), color, thickness + 1)
    
    # Top-right corner
    cv2.line(frame, (x + w, y), (x + w - corner_size, y), color, thickness + 1)
    cv2.line(frame, (x + w, y), (x + w, y + corner_size), color, thickness + 1)
    
    # Bottom-left corner
    cv2.line(frame, (x, y + h), (x + corner_size, y + h), color, thickness + 1)
    cv2.line(frame, (x, y + h), (x, y + h - corner_size), color, thickness + 1)
    
    # Bottom-right corner
    cv2.line(frame, (x + w, y + h), (x + w - corner_size, y + h), color, thickness + 1)
    cv2.line(frame, (x + w, y + h), (x + w, y + h - corner_size), color, thickness + 1)
    
    return frame


def process_video(input_path: str, output_path: str):
    """Process video and add action tracking rectangle"""
    
    # Open input video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {input_path}")
        return
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Processing video: {width}x{height} @ {fps}fps, {total_frames} frames")
    
    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Initialize tracker
    tracker = ActionTracker(smoothing_factor=0.7, min_area=500)
    
    # Read first frame
    ret, prev_frame = cap.read()
    if not ret:
        print("Error: Could not read first frame")
        return
    
    frame_count = 0
    
    while True:
        ret, current_frame = cap.read()
        if not ret:
            break
            
        # Detect motion
        motion_rect = tracker.detect_motion_center(current_frame, prev_frame)
        
        # Apply smoothing
        smooth_rect = tracker.smooth_rectangle(motion_rect)
        
        # Draw tracking rectangle
        output_frame = draw_tracking_rectangle(current_frame.copy(), smooth_rect)
        
        # Write frame
        out.write(output_frame)
        
        # Update for next iteration
        prev_frame = current_frame.copy()
        frame_count += 1
        
        # Progress indicator
        if frame_count % 30 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)")
    
    # Cleanup
    cap.release()
    out.release()
    print(f"Video processing complete. Output saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Action detection with rectangle tracking")
    parser.add_argument("input_video", help="Input video file path")
    parser.add_argument("output_video", help="Output video file path")
    parser.add_argument("--smoothing", type=float, default=0.7, 
                       help="Smoothing factor for rectangle movement (0.0-1.0)")
    parser.add_argument("--min-area", type=int, default=500,
                       help="Minimum area for motion detection")
    
    args = parser.parse_args()
    
    # Validate input
    try:
        cap = cv2.VideoCapture(args.input_video)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {args.input_video}")
        cap.release()
    except Exception as e:
        print(f"Error with input video: {e}")
        return 1
    
    # Process video
    try:
        process_video(args.input_video, args.output_video)
        return 0
    except Exception as e:
        print(f"Error processing video: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())