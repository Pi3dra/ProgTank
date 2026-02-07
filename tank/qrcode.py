import cv2
from pyzbar import pyzbar

gst_pipeline = (
    'udpsrc port=5000 caps="application/x-rtp,media=video,encoding-name=H264,payload=96" ! '
    'rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink'
)

# Open the video stream
cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Failed to open stream. Check your GStreamer pipeline.")
    exit(1)

print("Streaming... Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    qrcodes = pyzbar.decode(frame)
    for qr in qrcodes:
        data = qr.data.decode('utf-8')
        print(f"QR Code detected: {data}")

        x, y, w, h = qr.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 0), 2)

    # Show frame
    cv2.imshow("QR Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

