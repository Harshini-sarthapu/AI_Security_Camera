"""
Demo Video Generator for AI-Powered Smart Security Camera.
Creates a high-quality MP4 demonstration video with simulated surveillance activities:
1. Person walking across the frame
2. Person entering the designated Restricted Area
3. Person loitering in Sector 1
4. Backpack / Unattended object placed on floor
5. Fast running / abnormal movement

Run this script to generate `demo_video.mp4` ready for instant presentation!
"""

import os
import cv2
import numpy as np

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "demo_video.mp4")
WIDTH, HEIGHT = 640, 480
FPS = 30
TOTAL_SECONDS = 18
TOTAL_FRAMES = TOTAL_SECONDS * FPS


def create_demo_video():
    print(f"[Demo Generator] Creating sample surveillance video ({TOTAL_SECONDS}s at {FPS} FPS)...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(OUTPUT_PATH, fourcc, FPS, (WIDTH, HEIGHT))

    if not out.isOpened():
        print("[Demo Generator ERROR] VideoWriter failed to open.")
        return

    # Restricted area coordinates for reference
    rx1, ry1, rx2, ry2 = int(0.6 * WIDTH), int(0.2 * HEIGHT), int(0.95 * WIDTH), int(0.8 * HEIGHT)

    for f in range(TOTAL_FRAMES):
        t = f / float(FPS)
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

        # Background: Secure facility corridor
        frame[:] = (20, 24, 30)
        # Perspective floor
        cv2.line(frame, (0, 320), (WIDTH, 320), (45, 55, 68), 2)
        for x in range(0, WIDTH + 1, 80):
            cv2.line(frame, (x, 320), (int(x * 1.3 - 80), HEIGHT), (35, 42, 52), 1)

        # Restricted area border markings on floor
        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (25, 30, 40), -1)
        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (0, 0, 180), 1)
        cv2.putText(frame, "SECTOR 1 [RESTRICTED]", (rx1 + 10, ry1 + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 80, 220), 1)

        # Activity Timeline:
        # 0s - 4s: Person 1 walks from left to center
        # 4s - 8s: Person 1 enters restricted area (triggers Unauthorized Entry!)
        # 8s - 14s: Person 1 stays in restricted area > 5s (triggers Loitering!)
        # 6s - 18s: Stationary Backpack on floor (triggers Unattended Object!)
        # 14s - 18s: Person 1 runs quickly across left (triggers Abnormal Movement!)

        # Draw Stationary Backpack (at frame 180 onwards, x=240, y=360)
        if t >= 4.0:
            bx, by = 240, 360
            cv2.rectangle(frame, (bx - 18, by - 22), (bx + 18, by + 10), (30, 100, 200), -1)
            cv2.rectangle(frame, (bx - 10, by - 28), (bx + 10, by - 22), (20, 70, 150), -1)
            cv2.putText(frame, "Backpack", (bx - 26, by + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1)

        # Calculate Person 1 position
        if t < 4.0:
            # Walking towards center
            px = int(80 + (t / 4.0) * 220)
            py = 320
        elif t < 7.5:
            # Walking into restricted zone
            prog = (t - 4.0) / 3.5
            px = int(300 + prog * 180)  # moves inside rx1=384
            py = int(320 - prog * 40)
        elif t < 13.0:
            # Loitering inside restricted zone
            px = int(480 + 10 * np.sin(t * 3))
            py = 280
        else:
            # Running fast to the left
            prog = (t - 13.0) / 5.0
            px = int(480 - prog * 420)
            py = 310

        # Draw Human Figure (Person #1)
        # Head
        cv2.circle(frame, (px, py - 70), 16, (200, 215, 230), -1)
        # Torso
        cv2.rectangle(frame, (px - 18, py - 52), (px + 18, py + 12), (150, 170, 190), -1)
        # Limbs with walking animation
        leg_offset = int(12 * np.sin(t * 10)) if t < 13.0 else int(24 * np.sin(t * 22))
        cv2.line(frame, (px - 10, py + 12), (px - 10 - leg_offset, py + 68), (110, 130, 150), 6)
        cv2.line(frame, (px + 10, py + 12), (px + 10 + leg_offset, py + 68), (110, 130, 150), 6)
        cv2.line(frame, (px - 18, py - 45), (px - 28 + leg_offset, py), (130, 150, 170), 5)
        cv2.line(frame, (px + 18, py - 45), (px + 28 - leg_offset, py), (130, 150, 170), 5)

        # CCTV timestamp and camera watermark
        cv2.putText(frame, f"CAM-01 [CORRIDOR MAIN]  REC", (14, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 230, 118), 1)
        cv2.putText(frame, f"SIMULATION TIME: {t:.1f}s / {TOTAL_SECONDS}s", (WIDTH - 240, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        out.write(frame)

    out.release()
    print(f"[Demo Generator] Successfully generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    create_demo_video()
