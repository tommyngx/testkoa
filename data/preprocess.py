from torchvision import transforms
import yaml
from .augmentations import get_augmentations

def load_config(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def get_transforms(image_size, config_path='config/default.yaml'):
    config = load_config(config_path)
    
    use_augmentations = config['data'].get('use_augmentations', True)
    mean = config['data']['augmentations']['normalize']['mean']
    std = config['data']['augmentations']['normalize']['std']

    if use_augmentations:
        train_transform = get_augmentations(config_path, split='train')
        val_transform = get_augmentations(config_path, split='val')
    else:
        train_transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std)
        ])

        val_transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std)
        ])

    return train_transform, val_transform


