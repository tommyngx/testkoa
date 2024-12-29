import os
import pandas as pd
import argparse

def process_files(folder_path):
    train_path = os.path.join(folder_path, 'train.csv')
    test_path = os.path.join(folder_path, 'test.csv')
    
    if not os.path.exists(train_path) or not os.path.exists(test_path):
        print("train.csv or test.csv not found in the specified folder.")
        return
    
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    
    train_df['split'] = 'TRAIN'
    test_df['split'] = 'TEST'
    
    combined_df = pd.concat([train_df, test_df])
    
    # Remove specified columns
    combined_df = combined_df.drop(columns=['Unnamed: 0', 'raw_file'])
    
    # Fix path and path2 columns
    combined_df['filename'] = combined_df['filename'].str.replace(r'\.jpg$', '', regex=True)
    combined_df['path'] = combined_df['split'] + "/" + combined_df['filename'] + ".jpg"
    combined_df['path2'] = "OAI16/" + combined_df['split'] + "/" + combined_df['KL'].str + "/" + combined_df['filename'] + ".png"
    output_path = os.path.join(folder_path, 'OAI16metadata.csv')
    combined_df.to_csv(output_path, index=False)
    print(f"Combined file saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process train.csv and test.csv files.')
    parser.add_argument('--folder_path', type=str, help='Path to the folder containing train.csv and test.csv')
    
    args = parser.parse_args()
    process_files(args.folder_path)