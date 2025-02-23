import os
import argparse
import cv2
from ultralytics import YOLO
from ultralytics.solutions import heatmap
from ultralytics import solutions
from ultralytics.solutions.heatmap import Heatmap
import yaml
from tqdm import tqdm
from datetime import datetime
import random
import numpy as np
import torch
from torchvision import models, transforms
from torch.autograd import Function

def load_config(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def load_random_image(dataset_location, dataX):
    if dataX == 'CGMH':
        subfolders = [os.path.join(dataset_location, str(i)) for i in range(5)]
        images = [os.path.join(subfolder, img) for subfolder in subfolders for img in os.listdir(subfolder) if img.endswith(('.jpg', '.jpeg', '.png'))]
    else:
        images = [os.path.join(dataset_location, img) for img in os.listdir(dataset_location) if img.endswith(('.jpg', '.jpeg', '.png'))]
    
    if not images:
        raise FileNotFoundError("No images found in the dataset location.")
    
    random_image = random.choice(images)
    img = cv2.imread(random_image)
    return img, random_image

def load_image_paths(dataset_location, dataX):
    if dataX == 'CGMH':
        subfolders = [os.path.join(dataset_location, str(i)) for i in range(5)]
        images = [os.path.join(subfolder, img) for subfolder in subfolders for img in os.listdir(subfolder) if img.endswith(('.jpg', '.jpeg', '.png'))]
    else:
        images = [os.path.join(dataset_location, img) for img in os.listdir(dataset_location) if img.endswith(('.jpg', '.jpeg', '.png'))]
    
    if not images:
        raise FileNotFoundError("No images found in the dataset location.")
    return images

class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self.hook_layers()

    def hook_layers(self):
        def forward_hook(module, input, output):
            self.activations = output

        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0]

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_backward_hook(backward_hook)

    def generate_heatmap(self, input_image, class_idx):
        self.model.zero_grad()
        output = self.model(input_image)
        target = output[0][class_idx]
        target.backward()

        gradients = self.gradients[0]
        activations = self.activations[0]
        weights = torch.mean(gradients, dim=(1, 2), keepdim=True)
        heatmap = torch.sum(weights * activations, dim=0).cpu().detach().numpy()
        heatmap = np.maximum(heatmap, 0)
        heatmap = cv2.resize(heatmap, (input_image.shape[3], input_image.shape[2]))
        heatmap = heatmap - np.min(heatmap)
        heatmap = heatmap / np.max(heatmap)
        return heatmap

def create_heatmap_image(model_path, img):
    print("Loading YOLO model...")
    # Load the YOLO model
    model = YOLO(model_path)
    
    print("Performing detection on the image...")
    # Perform detection on the image
    results = model(img, verbose=False)
    
    print("Generating heatmap based on detection results...")
    # Create an empty heatmap
    heatmap_img = np.zeros_like(img)
    
    # Load a pre-trained model for Grad-CAM
    gradcam_model = models.resnet50(pretrained=True)
    gradcam = GradCAM(gradcam_model, gradcam_model.layer4[2])
    
    # Preprocess the image for Grad-CAM
    preprocess = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    input_tensor = preprocess(img).unsqueeze(0)
    
    # Iterate over the detection results and generate Grad-CAM heatmaps
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].int().tolist()
            class_idx = int(box.cls)
            heatmap = gradcam.generate_heatmap(input_tensor, class_idx)
            heatmap = cv2.applyColorMap(np.uint8(255 * heatmap), cv2.COLORMAP_JET)
            heatmap = cv2.resize(heatmap, (x2 - x1, y2 - y1))
            heatmap_img[y1:y2, x1:x2] = heatmap
    
    print("Heatmap image created successfully.")
    return heatmap_img

def save_combined_image(input_img, detected_img, heatmap_img, output_path):
    combined_img = np.hstack((input_img, detected_img, heatmap_img))
    cv2.imwrite(output_path, combined_img)

def process_images(dataset_location, model, model_path, output_dir, source_type, dataX):
    if source_type == 'random':
        img, image_path = load_random_image(dataset_location, dataX)
        results = model(img, verbose=False)
        detected_img = results[0].plot()
        heatmap_img = create_heatmap_image(model_path, img)
        #heatmap_img = results[0].plot()
        
        output_path = os.path.join(output_dir, os.path.basename(image_path))
        save_combined_image(img, detected_img, heatmap_img, output_path)
        
        # Print output
        print(f"Image path: {image_path}")
        print("Saved combined image to:", output_path)
    else:
        image_paths = load_image_paths(dataset_location, dataX)
        for image_path in tqdm(image_paths, desc="Processing images", total=len(image_paths)):
            img = cv2.imread(image_path)
            results = model(img, verbose=False)
            detected_img = results[0].plot()
            heatmap_img = create_heatmap_image(model_path, img)
            
            output_path = os.path.join(output_dir, os.path.basename(image_path))
            save_combined_image(img, detected_img, heatmap_img, output_path)

def main(dataset_location, model_path, source_type, dataX='VOS', config_path='config/default.yaml'):
    config = load_config(config_path)
    folder_name = os.path.basename(dataset_location) + "_" + datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join(config['output_dir'], 'yolo', 'runs', 'heatmaps', folder_name)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Load model
    model = YOLO(model_path)
    
    # Process images
    process_images(dataset_location, model, model_path, output_dir, source_type, dataX)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predict using a YOLO model on images from the dataset and save combined images with input, detected, and heatmap")
    parser.add_argument('--dataset_location', type=str, required=True, help='Path to the dataset location')
    parser.add_argument('--model', type=str, required=True, help='Path to the YOLO model file')
    parser.add_argument('--source_type', type=str, choices=['random', 'folder'], default='random', help='Source type: random image or whole folder')
    parser.add_argument('--dataX', type=str, default='VOS', help='Data source identifier')
    parser.add_argument('--config', type=str, default='config/default.yaml', help='Path to the configuration file')
    args = parser.parse_args()
    
    main(args.dataset_location, args.model, args.source_type, args.dataX, args.config)
