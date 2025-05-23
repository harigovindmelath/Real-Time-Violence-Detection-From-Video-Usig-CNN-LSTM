# -*- coding: utf-8 -*-
"""Realtime-Violenece-Detection.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1cFG6p-D9C-Zl5mvGxRVwDwwnJd74nMm4
"""

import torch.nn as nn

"""##Building LSTM NN"""

class LSTMModel(nn.Module):
    def __init__(self, seq_length, feature_dim, hidden_dim=64):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size=feature_dim, hidden_size=hidden_dim, num_layers=2, batch_first=True)
        self.dropout = nn.Dropout(0.5)
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        x = self.dropout(lstm_out[:, -1, :])
        x = self.fc(x)
        return self.sigmoid(x).squeeze(dim=-1)  # Ensures correct shape

from google.colab import drive
drive.mount('/content/drive')

"""##Setting the paths"""

!nvidia-smi  # Check GPU usage
!free -h  # Check RAM usage

"""###Alert System"""

!pip install pygame

from IPython.display import Audio, display

# Function to play siren (non-blocking)
def play_siren():
    display(Audio("/content/drive/MyDrive/RTVDS/siren.mp3", autoplay=True))

"""##Testing the model"""

import cv2
import torch
import torchvision.transforms as transforms
import numpy as np
from collections import deque
import torchvision.models as models
import torch.nn as nn
from IPython.display import Audio, Image, display

# Load trained model
MODEL_PATH = "/content/drive/MyDrive/RTVDS/violence_detection_model.pth"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = torch.load(MODEL_PATH
                   , weights_only=False)

model.eval()

# Feature extractor
def create_feature_extractor():
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
    model = nn.Sequential(*list(model.children())[:-1])
    return model.eval().to(device)

feature_extractor = create_feature_extractor()

# Preprocessing for frame
def extract_frame_features(frame):
    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((112, 112)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    frame_tensor = transform(frame).unsqueeze(0).to(device)
    with torch.no_grad():
        features = feature_extractor(frame_tensor).squeeze().flatten().cpu().numpy()
    return features[:1280]

# Predict violence
def predict_violence(frame_sequence):
    frame_sequence = torch.tensor(frame_sequence, dtype=torch.float32).unsqueeze(0).to(device)
    with torch.no_grad():
        output = model(frame_sequence)
        return "Violent" if output.item() > 0.5 else "Non-Violent"

# Draw person bounding boxes
def draw_boxes(frame, label):
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    boxes, _ = hog.detectMultiScale(gray, winStride=(4, 4), padding=(8, 8), scale=1.05)
    color = (0, 0, 255) if label == "Violent" else (0, 255, 0)
    for (x, y, w, h) in boxes:
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)
        cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    return frame

# Play siren
def play_siren():
    display(Audio(filename="/content/drive/MyDrive/RTVDS/siren.mp3", autoplay=True))

# Main logic
def violence_snapshot_alert(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []
    features = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame)
        features.append(extract_frame_features(frame_rgb))

    cap.release()

    if len(features) >= 10:
        # Select 10 evenly spaced frames for prediction
        indices = np.linspace(0, len(features)-1, 10, dtype=int)
        selected_features = [features[i] for i in indices]
        label = predict_violence(selected_features)

        if label == "Violent":
            print("🚨 ALERT: Violence detected!")

            mid_index = len(frames) // 2
            alert_frame = draw_boxes(frames[mid_index].copy(), label)

            # Save and display snapshot
            cv2.imwrite("alert_frame.jpg", alert_frame)
            display(Image("alert_frame.jpg"))

            # Play siren
            play_siren()
        else:
            print("✅ Video is non-violent.")
    else:
        print("⚠️ Not enough frames for prediction.")

# Run it
violence_snapshot_alert("/content/drive/MyDrive/RTVDS/test3.mp4")

"""##Evaluatio  of the  model performance"""

import cv2
import torch
import torchvision.transforms as transforms
import numpy as np
from collections import deque
import torchvision.models as models
import torch.nn as nn
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from google.colab.patches import cv2_imshow

# Load trained model
MODEL_PATH = "/content/drive/MyDrive/RTVDS/violence_detection_model.pth"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load trained LSTM model
model = torch.load(MODEL_PATH, map_location=device)
model.eval()

# Load feature extractor (MobileNetV2 without classifier)
def create_feature_extractor():
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
    model = nn.Sequential(*list(model.children())[:-1])  # Remove classification head
    return model.eval().to(device)

feature_extractor = create_feature_extractor()

# Frame preprocessing function
def extract_frame_features(frame):
    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((112, 112)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    frame_tensor = transform(frame).unsqueeze(0).to(device)
    with torch.no_grad():
        features = feature_extractor(frame_tensor).squeeze().flatten().cpu().numpy()
    return features[:1280]  # Ensure 1280 features

# Violence prediction function (returns probability & label)
def predict_violence(frame_sequence):
    frame_sequence = torch.tensor(frame_sequence, dtype=torch.float32).unsqueeze(0).to(device)
    with torch.no_grad():
        output = model(frame_sequence)
        prob = output.item()  # Probability of violence
        print(f"🔍 Prediction Probability: {prob:.4f}")  # Debugging line
        return prob, "Violent" if prob > 0.2 else "Non-Violent"


# Function to evaluate model on test videos
def evaluate_model(test_videos, ground_truth_labels):
    y_true, y_pred = [], []

    for i, video_path in enumerate(test_videos):
        frame_sequence = deque(maxlen=10)  # Store last 10 frames
        cap = cv2.VideoCapture(video_path)

        # Flag to ensure only 1 prediction per video
        prediction_made = False

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_features = extract_frame_features(frame_rgb)
            frame_sequence.append(frame_features)

            if len(frame_sequence) == 10 and not prediction_made:
                prob, label = predict_violence(frame_sequence)
                y_pred.append(1 if label == "Violent" else 0)
                prediction_made = True  # Ensure only one prediction per video

        cap.release()

        # Append actual label for the video
        if prediction_made:
            y_true.append(ground_truth_labels[i])

    # Ensure lists match in length
    assert len(y_true) == len(y_pred), f"Mismatch: y_true={len(y_true)}, y_pred={len(y_pred)}"

    # Compute evaluation metrics
    acc = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)
    print("Ground Truth Labels: ", y_true)
    print("Predicted Labels: ", y_pred)


    print("\n✅ Model Evaluation Results:")
    print(f"🔹 Accuracy: {acc:.4f}")
    print(f"🔹 Precision: {precision:.4f}")
    print(f"🔹 Recall: {recall:.4f}")
    print(f"🔹 F1-score: {f1:.4f}")
    print("🔹 Confusion Matrix:\n", cm)

# 🔹 Define test videos and true labels (1 = Violent, 0 = Non-Violent)
test_videos = ["/content/drive/MyDrive/RTVDS/test.mp4", "/content/drive/MyDrive/RTVDS/test2.mp4"]
ground_truth_labels = [1, 0]  # Example: First video = violent, Second video = non-violent

# Run evaluation
evaluate_model(test_videos, ground_truth_labels)

"""##Unit Testing

"""

import unittest
class TestViolencePrediction(unittest.TestCase):
    def test_predict_violence(self):
        dummy_sequence = np.random.rand(10, 1280)  # Simulated 10-frame sequence
        prob, label = predict_violence(dummy_sequence)  # Unpack tuple
        self.assertIn(label, ["Violent", "Non-Violent"], "Prediction label must be 'Violent' or 'Non-Violent'!")

unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(TestViolencePrediction))

"""##Integration  Testing"""

class TestModelIntegration(unittest.TestCase):
    def test_model_integration(self):
        frame_sequence = deque(maxlen=10)

        # Generate random 10 frames
        for _ in range(10):
            dummy_frame = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)
            features = extract_frame_features(dummy_frame)
            frame_sequence.append(features)

        prob, label = predict_violence(frame_sequence)  # ✅ Unpack tuple correctly
        self.assertIn(label, ["Violent", "Non-Violent"], "Invalid model output!")

unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(TestModelIntegration))

"""##Functional Testing"""

class TestFunctionalPerformance(unittest.TestCase):
    def test_functional_performance(self):
        test_videos = ["/content/drive/MyDrive/RTVDS/test.mp4", "/content/drive/MyDrive/RTVDS/test2.mp4"]
        ground_truth_labels = [1, 0]  # Expected labels

        y_pred = []
        for i, video in enumerate(test_videos):
            frame_sequence = deque(maxlen=10)
            cap = cv2.VideoCapture(video)

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_features = extract_frame_features(frame_rgb)
                frame_sequence.append(frame_features)

                if len(frame_sequence) == 10:
                    prob, label = predict_violence(frame_sequence)
                    print(f"📌 Video {i+1}: Prob={prob:.4f}, Predicted={label}, Actual={ground_truth_labels[i]}")
                    y_pred.append(1 if label == "Violent" else 0)
                    break  # Only one prediction per video

            cap.release()

        print(f"🔍 Final Predictions: {y_pred}")
        self.assertEqual(y_pred, ground_truth_labels, f"Expected {ground_truth_labels}, got {y_pred}")

unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(TestFunctionalPerformance))

"""##Sytem Testing"""

class TestVideoProcessing(unittest.TestCase):
    def test_video_processing(self):
        video_path = "/content/drive/MyDrive/RTVDS/test2.mp4"
        cap = cv2.VideoCapture(video_path)
        self.assertTrue(cap.isOpened(), "Failed to open video file!")

        ret, frame = cap.read()
        self.assertTrue(ret, "Failed to read first frame!")

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        features = extract_frame_features(frame_rgb)
        self.assertEqual(len(features), 1280, "Feature extraction failed!")

        cap.release()

unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(TestVideoProcessing))