import os
import argparse
import pandas as pd
import cv2
import yaml
from tqdm import tqdm
import random
import shutil

def load_config(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def load_metadata(metadata_csv):
    return pd.read_csv(metadata_csv)

def parse_filename(filename, data_name):
    if data_name == 'CGMH':
        parts = filename.split('_')
        age = parts[0]
        kl_value = parts[1]
        knee_side = parts[2][0]
        return age, kl_value, knee_side
    else:
        parts = filename.split('P2')
        age = parts[0]
        rest = parts[1].split('KNEE')
        sex_id = rest[0]
        knee_side = rest[1].split('_')[1][0]
        return age, sex_id, knee_side

def get_kl_value(row, knee_side):
    if knee_side == 'L':
        return row['KL_Left']
    elif knee_side == 'R':
        return row['KL_Right']
    else:
        return None

def generate_dataset(input_folder, metadata_csv, output_dir, data_name, seed):
    random.seed(seed)
    metadata = load_metadata(metadata_csv)
    
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    train_dir = os.path.join(output_dir, 'TRAIN')
    test_dir = os.path.join(output_dir, 'TEST')
    for kl in range(5):
        os.makedirs(os.path.join(train_dir, str(kl)), exist_ok=True)
        os.makedirs(os.path.join(test_dir, str(kl)), exist_ok=True)
        os.makedirs(os.path.join(output_dir, str(kl)), exist_ok=True)
    
    metaraw_data = []
    id_split = {}

    for image_name in tqdm(os.listdir(input_folder), desc="Processing images"):
        if image_name.endswith(('.jpg', '.jpeg', '.png')):
            if data_name == 'CGMH':
                age, kl_value, knee_side = parse_filename(image_name, data_name)
                new_name = f"{age}_{kl_value}_{knee_side}.png"
                kl_output_dir = os.path.join(output_dir, str(kl_value))
                cv2.imwrite(os.path.join(kl_output_dir, new_name), cv2.imread(os.path.join(input_folder, image_name)))
                
                # Save in TRAIN and TEST folders
                cv2.imwrite(os.path.join(train_dir, str(kl_value), new_name), cv2.imread(os.path.join(input_folder, image_name)))
                cv2.imwrite(os.path.join(test_dir, str(kl_value), new_name), cv2.imread(os.path.join(input_folder, image_name)))
                
                metaraw_data.append({
                    'data': data_name,
                    'ID': new_name,
                    'KL': kl_value,
                    'path': f"{data_name}/{kl_value}/{new_name}",
                    'split': 'TRAIN',
                    'path_relative': f"{data_name}/TRAIN/{kl_value}/{new_name}"
                })
                metaraw_data.append({
                    'data': data_name,
                    'ID': new_name,
                    'KL': kl_value,
                    'path': f"{data_name}/{kl_value}/{new_name}",
                    'split': 'TEST',
                    'path_relative': f"{data_name}/TEST/{kl_value}/{new_name}"
                })
            else:
                age, sex_id, knee_side = parse_filename(image_name, data_name)
                id_value = sex_id[1:]
                sex = sex_id[0]
                
                if id_value == 'NoID':
                    continue
                
                row = metadata[(metadata['ID'] == int(id_value)) & (metadata['Sex'] == sex)]
                if not row.empty:
                    kl_value = get_kl_value(row.iloc[0], knee_side)
                    if kl_value is not None:
                        img = cv2.imread(os.path.join(input_folder, image_name))
                        new_name = f"{age}P2{sex}{id_value}{knee_side}{kl_value}.png"
                        
                        if id_value not in id_split:
                            id_split[id_value] = 'TRAIN' if random.random() < 0.8 else 'TEST'
                        
                        split = id_split[id_value]
                        kl_output_dir = os.path.join(output_dir, split, str(kl_value))
                        cv2.imwrite(os.path.join(kl_output_dir, new_name), img)
                        
                        # Save a copy in the KL folder outside of TRAIN and TEST
                        cv2.imwrite(os.path.join(output_dir, str(kl_value), new_name), img)
                        
                        metaraw_data.append({
                            'data': data_name,
                            'ID': new_name,
                            'KL': kl_value,
                            'path': f"{data_name}/{kl_value}/{new_name}",
                            'split': split,
                            'path_relative': f"{data_name}/{split}/{kl_value}/{new_name}"
                        })
    
    metaraw_df = pd.DataFrame(metaraw_data)
    metaraw_df.to_csv(os.path.join(output_dir, 'metadata.csv'), index=False)

def main(input_folder, metadata_csv, data_name, config='default.yaml', seed=2024):
    config_path = os.path.join('config', config)
    config = load_config(config_path)
    output_dir = os.path.join(config['output_dir'], 'yolo', 'runs', data_name)
    
    generate_dataset(input_folder, metadata_csv, output_dir, data_name, seed)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dataset based on metadata and image files")
    parser.add_argument('--input_folder', type=str, required=True, help='Path to the input folder containing images')
    parser.add_argument('--metadata_csv', type=str, required=True, help='Path to the metadata CSV file')
    parser.add_argument('--data_name', type=str, required=True, help='Name of the dataset')
    parser.add_argument('--config', type=str, default='default.yaml', help='Name of the configuration file')
    parser.add_argument('--seed', type=int, default=2024, help='Random seed for splitting the dataset')
    args = parser.parse_args()
    
    main(args.input_folder, args.metadata_csv, args.data_name, args.config, args.seed)
