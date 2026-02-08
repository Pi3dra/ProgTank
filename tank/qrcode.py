import cv2
import time
from pyzbar import pyzbar
import paho.mqtt.client as mqtt

BROKER = "192.168.1.76"
TOPIC = "pc/keyboard"

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

client.connect(BROKER, 1883)
client.loop_start()

gst_pipeline = (
    'udpsrc port=5000 caps="application/x-rtp,media=video,encoding-name=H264,payload=96" ! '
    'rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink'
)

cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Failed to open stream")
    exit(1)

print("QR camera running (Q to quit)")

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    detected = False 
    
    for qr in pyzbar.decode(frame):
        data = qr.data.decode("utf-8")

        print(f"QR detected: {data}")
        client.publish(TOPIC, f"QR_CODE:{data}")
        detected = True

        x, y, w, h = qr.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, data, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    if detected:
        time.sleep(1)
        detected = False

    cv2.imshow("QR Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

client.loop_stop()
client.disconnect()

