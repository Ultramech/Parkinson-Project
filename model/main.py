import os
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from imutils import paths
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import VGG16
from tensorflow.keras.layers import AveragePooling2D, Dropout, Flatten, Dense, Input
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical
import os 

# --- CONFIGURATION ---
# UPDATE THIS PATH to match the folder name you uploaded
# For example, if your folder is named 'dataset', change this to 'dataset'
DATASET_PATH = "dataset"
INIT_LR = 1e-4
EPOCHS = 50  # Reduced for testing; increase to 50 or 100 for final training
BS = 8


def load_data(dataset_path):
    print(f"[INFO] loading images from {dataset_path}...")
    imagePaths = list(paths.list_images(dataset_path))
    data = []
    labels = []

    if not imagePaths:
        raise ValueError(f"No images found in '{dataset_path}'. Please check your folder structure.")

    for imagePath in imagePaths:
        # Extract the class label from the filename
        label = imagePath.split(os.path.sep)[-2]

        # Load the image, swap color channels, and resize it to 224x224
        image = cv2.imread(imagePath)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (224, 224))

        data.append(image)
        labels.append(label)

    # Convert to NumPy arrays and scale pixel intensities to [0, 1]
    data = np.array(data) / 255.0
    labels = np.array(labels)

    return data, labels


def build_model():
    print("[INFO] compiling model...")
    # Load VGG16 network, ensuring the head FC layer sets are left off
    baseModel = VGG16(weights="imagenet", include_top=False, input_tensor=Input(shape=(224, 224, 3)))

    # Construct the head of the model that will be placed on top of the base
    headModel = baseModel.output
    headModel = AveragePooling2D(pool_size=(4, 4))(headModel)
    headModel = Flatten(name="flatten")(headModel)
    headModel = Dense(64, activation="relu")(headModel)
    headModel = Dropout(0.5)(headModel)
    headModel = Dense(2, activation="softmax")(headModel)  # Assuming 2 classes: Healthy vs Parkinson's

    # Place the head FC model on top of the base model
    model = Model(inputs=baseModel.input, outputs=headModel)

    # Loop over all layers in the base model and freeze them so they will not be updated
    for layer in baseModel.layers:
        layer.trainable = False

    opt = Adam(learning_rate=INIT_LR)
    model.compile(loss="binary_crossentropy", optimizer=opt, metrics=["accuracy"])
    return model


def plot_history(H, epochs):
    print("[INFO] plotting training history...")
    plt.style.use("ggplot")
    plt.figure()
    plt.plot(np.arange(0, epochs), H.history["loss"], label="train_loss")
    plt.plot(np.arange(0, epochs), H.history["val_loss"], label="val_loss")
    plt.plot(np.arange(0, epochs), H.history["accuracy"], label="train_acc")
    plt.plot(np.arange(0, epochs), H.history["val_accuracy"], label="val_acc")
    plt.title("Training Loss and Accuracy")
    plt.xlabel("Epoch #")
    plt.ylabel("Loss/Accuracy")
    plt.legend(loc="lower left")
    plt.savefig("plot.png")  # Saves the plot to your project folder
    plt.show()  # Opens a window with the graph


if __name__ == "__main__":
    # 1. Load Data
    try:
        data, labels = load_data(DATASET_PATH)
    except Exception as e:
        print(e)
        exit()

    # 2. Encode Labels
    lb = LabelEncoder()
    labels = lb.fit_transform(labels)
    labels = to_categorical(labels)

    # 3. Split Data
    (trainX, testX, trainY, testY) = train_test_split(data, labels,
                                                      test_size=0.20, stratify=labels, random_state=42)

    # 4. Data Augmentation
    aug = ImageDataGenerator(
        rotation_range=20,
        zoom_range=0.15,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.15,
        horizontal_flip=True,
        fill_mode="nearest")

    # 5. Build and Train Model
    model = build_model()

    print("[INFO] training head...")
    H = model.fit(
        aug.flow(trainX, trainY, batch_size=BS),
        steps_per_epoch=len(trainX) // BS,
        validation_data=(testX, testY),
        validation_steps=len(testX) // BS,
        epochs=EPOCHS)

    # 6. Evaluate
    print("[INFO] evaluating network...")
    predIdxs = model.predict(testX, batch_size=BS)
    predIdxs = np.argmax(predIdxs, axis=1)

    print(classification_report(testY.argmax(axis=1), predIdxs,
                                target_names=lb.classes_))

    # 7. Save Model and Plot
    print("[INFO] saving model...")
    # model.save("parkinsons_detector.model")

    os.makedirs("model", exist_ok=True)
    # model.save("model/parkinsons_detector.model")

    model.save("model/parkinsons_detector.keras")


    plot_history(H, EPOCHS)
    print("Done! Check 'parkinsons_detector.model' and 'plot.png' in your project folder.")