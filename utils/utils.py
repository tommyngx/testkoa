import numpy as np
import cv2

def generate_gradcam2(model, image, target_layer):
    model.eval()
    if image.dim() == 3:
        image = image.unsqueeze(0)
    image.requires_grad = True

    activations = []
    gradients = []

    # Hook to capture activations
    def forward_hook(module, input, output):
        activations.append(output)

    # Hook to capture gradients
    def backward_hook(module, grad_input, grad_output):
        gradients.append(grad_output[0])  # Gradients w.r.t. activations

    # Register hooks
    forward_handle = target_layer.register_forward_hook(forward_hook)
    backward_handle = target_layer.register_full_backward_hook(backward_hook)

    # Forward pass
    output = model(image)
    forward_handle.remove()

    # Backward pass
    score = output[:, output.max(1)[-1]]
    model.zero_grad()
    score.backward(retain_graph=True)
    backward_handle.remove()

    # Retrieve activations and gradients
    activations = activations[0].detach()  # Shape: [batch_size, num_patches, embedding_dim]
    gradients = gradients[0].detach()  # Shape: [batch_size, num_patches, embedding_dim]

    # Debugging: Log shapes
    #with open('tensor_shapes.txt', "w") as f:
    #    f.write(f"Activations shape: {activations.shape}\n")
    #    f.write(f"Gradients shape: {gradients.shape}\n")

    if activations.dim() == 4:  # CNN-based models
        pooled_gradients = torch.mean(gradients, dim=[0, 2, 3])
        for i in range(min(activations.shape[1], pooled_gradients.shape[0])):
            activations[:, i, :, :] *= pooled_gradients[i]
        heatmap = torch.mean(activations, dim=1).squeeze()

    elif activations.dim() == 3:  # ViT models
        # Exclude class token (first patch)
        activations = activations[:, 1:, :]  # Remove class token
        gradients = gradients[:, 1:, :]  # Remove class token

        # Calculate pooled_gradients
        pooled_gradients = torch.mean(gradients, dim=1, keepdim=True)  # Average across patches
        pooled_gradients = pooled_gradients.expand_as(activations)  # Match activations shape

        # Debugging: Log pooled_gradients shape
        #with open('tensor_shapes.txt', "a") as f:
        #    f.write(f"Pooled gradients shape after adjustment: {pooled_gradients.shape}\n")

        # Calculate heatmap for ViT models
        heatmap = torch.sum(activations * pooled_gradients, dim=-1)  # [batch_size, num_patches]

        # Reshape heatmap to spatial dimensions
        grid_size = int(np.sqrt(heatmap.size(1)))  # Compute grid size (e.g., 14x14)
        heatmap = heatmap.view(activations.size(0), grid_size, grid_size)  # Reshape to [batch_size, height, width]

    else:
        raise ValueError("Unexpected activations dimensions.")

    # Post-process heatmap
    heatmap = F.relu(heatmap)
    heatmap /= torch.max(heatmap)

    heatmap = heatmap.cpu().numpy()  # Move to CPU before converting to NumPy
    heatmap = cv2.resize(heatmap[0], (image.shape[2], image.shape[3]))  # Resize first batch
    heatmap = np.uint8(255 * heatmap)
    heatmap = 255 - heatmap

    heatmap_colored = np.stack([heatmap] * 3, axis=-1)
    return heatmap_colored


def blue_to_gray_np(image: np.ndarray) -> np.ndarray:
    """
    Convert blue areas in an image (NumPy array) to gray.
    
    Args:
        image (np.ndarray): Input image in BGR format as a NumPy array.
    
    Returns:
        np.ndarray: Processed image with blue areas converted to gray.
    """
    if image is None:
        raise ValueError("Input image is None.")
    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError("Input image must be a 3-channel color image (BGR).")
    
    # Convert to HSV for easier color range detection
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Define the blue range in HSV (adjust values if needed)
    lower_blue = np.array([100, 50, 50])  # Hue: 100-140, Saturation/Value: 50-255
    upper_blue = np.array([140, 255, 255])
    
    # Create a mask for blue areas
    blue_mask = cv2.inRange(hsv_image, lower_blue, upper_blue)
    
    # Create a grayscale version of the image
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Convert grayscale to 3-channel image to match the input format
    gray_3_channel = cv2.merge([gray_image, gray_image, gray_image])
    
    # Replace blue areas with the corresponding grayscale pixels
    result = np.where(blue_mask[:, :, None] == 255, gray_3_channel, image)
    return result

def red_to_gray_np(image: np.ndarray) -> np.ndarray:
    """
    Convert red areas in an image (NumPy array) to gray.
    
    Args:
        image (np.ndarray): Input image in BGR format as a NumPy array.
    
    Returns:
        np.ndarray: Processed image with red areas converted to gray.
    """
    if image is None:
        raise ValueError("Input image is None.")
    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError("Input image must be a 3-channel color image (BGR).")
    
    # Convert to HSV for easier color range detection
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Define the red range in HSV
    # Red in HSV often spans two ranges due to hue wrap-around (0-10 and 170-180)
    lower_red1 = np.array([0, 50, 50])    # Lower red range 1
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])  # Lower red range 2
    upper_red2 = np.array([180, 255, 255])
    
    # Create masks for both red ranges and combine them
    red_mask1 = cv2.inRange(hsv_image, lower_red1, upper_red1)
    red_mask2 = cv2.inRange(hsv_image, lower_red2, upper_red2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    
    # Create a grayscale version of the image
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Convert grayscale to 3-channel image to match the input format
    gray_3_channel = cv2.merge([gray_image, gray_image, gray_image])
    
    # Replace red areas with the corresponding grayscale pixels
    result = np.where(red_mask[:, :, None] == 255, gray_3_channel, image)
    return result

def red_to_0_np(image: np.ndarray) -> np.ndarray:
    """
    Convert red areas in an image (NumPy array) to black.
    
    Args:
        image (np.ndarray): Input image in BGR format as a NumPy array.
    
    Returns:
        np.ndarray: Processed image with red areas turned to black.
    """
    if image is None:
        raise ValueError("Input image is None.")
    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError("Input image must be a 3-channel color image (BGR).")
    
    # Convert to HSV for easier color range detection
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Define the red range in HSV
    # Red in HSV often spans two ranges due to hue wrap-around (0-10 and 170-180)
    lower_red1 = np.array([0, 50, 50])    # Lower red range 1
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])  # Lower red range 2
    upper_red2 = np.array([180, 255, 255])
    
    # Create masks for both red ranges and combine them
    red_mask1 = cv2.inRange(hsv_image, lower_red1, upper_red1)
    red_mask2 = cv2.inRange(hsv_image, lower_red2, upper_red2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    
    # Create a black image to replace red areas
    black_image = np.zeros_like(image)
    
    # Replace red areas with black
    result = np.where(red_mask[:, :, None] == 255, black_image, image)
    return result


def generate_gradcam_ori(model, image, target_layer):
    model.eval()
    if image.dim() == 3:
        image = image.unsqueeze(0)
    image.requires_grad = True

    features = []
    def hook_fn(module, input, output):
        features.append(output)

    handle = target_layer.register_forward_hook(hook_fn)
    output = model(image)
    handle.remove()

    score = output[:, output.max(1)[-1]]
    score.backward()

    gradients = image.grad.data
    activations = features[0].detach()

    with open('tensor_shapes.txt', "w") as f:
        f.write(f"Activations shape: {activations[0].shape}\n")
        #f.write(f"Pooled gradients shape: {pooled_gradients.shape}\n")
    
    if activations.dim() == 4:  # CNN-based models
        pooled_gradients = torch.mean(gradients, dim=[0, 2, 3])
        for i in range(min(activations.shape[1], pooled_gradients.shape[0])):
            activations[:, i, :, :] *= pooled_gradients[i]
        heatmap = torch.mean(activations, dim=1).squeeze()

    elif activations.dim() == 3:  # ViT models with activations shaped [batch_size, num_patches, embedding_dim]
        # Debugging: Log activations and gradients shape
        with open('tensor_shapes.txt', "a") as f:
            f.write(f"Activations shape: {activations.shape}\n")
            f.write(f"Gradients shape before adjustment: {gradients.shape}\n")

        # Handle CNN-like gradients
        if gradients.dim() == 4:  # [batch_size, channels, height, width]
            gradients = torch.mean(gradients, dim=[2, 3])  # Average spatially to reduce to [batch_size, channels]

        # Ensure gradients match activations shape
        if gradients.dim() == 2:  # [batch_size, embedding_dim]
            gradients = gradients.unsqueeze(1).expand(activations.size(0), activations.size(1), gradients.size(1))  # Expand to [batch_size, num_patches, embedding_dim]
        elif gradients.dim() == 3 and gradients.size(1) == 1:  # [batch_size, 1, embedding_dim]
            gradients = gradients.expand(activations.size(0), activations.size(1), gradients.size(2))  # Expand to [batch_size, num_patches, embedding_dim]
        elif gradients.dim() == 3 and gradients.size(2) == 224:  # [batch_size, channels, height]
            gradients = torch.mean(gradients, dim=1, keepdim=True)  # Average across channels to reduce to [batch_size, 1, height]
            gradients = gradients.expand(activations.size(0), activations.size(1), activations.size(2))  # Match activations shape [batch_size, num_patches, embedding_dim]
        elif gradients.dim() == 3 and gradients.size(2) == 3:  # [batch_size, channels, 3]
            gradients = torch.mean(gradients, dim=2, keepdim=True)  # Average across channels to reduce to [batch_size, channels, 1]
            gradients = gradients.expand(activations.size(0), activations.size(1), activations.size(2))  # Match activations shape [batch_size, num_patches, embedding_dim]
        else:
            raise ValueError(f"Unexpected gradients dimensions: {gradients.dim()}")

        # Compute pooled gradients
        pooled_gradients = torch.mean(gradients, dim=1, keepdim=True)  # Shape: [batch_size, 1, embedding_dim]
        pooled_gradients = pooled_gradients.expand(activations.size(0), activations.size(1), activations.size(2))  # Match activations shape [batch_size, num_patches, embedding_dim]

        # Calculate weighted activations
        weighted_activations = activations * pooled_gradients  # Element-wise multiplication

        # Generate heatmap by summing across the embedding dimension
        heatmap = torch.sum(weighted_activations, dim=-1).squeeze()  # Shape: [batch_size, num_patches]

        # Reshape heatmap to spatial dimensions (square grid)
        grid_size = int(np.sqrt(heatmap.size(0)))  # Compute grid size (e.g., 14x14 for 196 patches)
        heatmap = heatmap.view(grid_size, grid_size)  # Shape: [grid_size, grid_size]

        # Debugging: Log heatmap shape
        with open('tensor_shapes.txt', "a") as f:
            f.write(f"Heatmap shape: {heatmap.shape}\n")

    else:
            raise ValueError(f"Unexpected activations dimensions: {activations.dim()}") 

    heatmap = F.relu(heatmap)
    heatmap /= torch.max(heatmap)

    heatmap = heatmap.cpu().numpy()  # Move to CPU before converting to NumPy
    heatmap = cv2.resize(heatmap, (image.shape[2], image.shape[3]))
    heatmap = np.uint8(255 * heatmap)
    heatmap = 255 - heatmap

    heatmap_colored = np.stack([heatmap] * 3, axis=-1)
    return heatmap_colored #heatmap