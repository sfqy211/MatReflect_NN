import os
import sys
import subprocess
import glob

import argparse
from compute_median import main as compute_median_main

def main():
    parser = argparse.ArgumentParser(description='Batch process HyperBRDF binary files to fullbin.')
    parser.add_argument('--model', help='Path to the trained model checkpoint (.pt)', default=None)
    args = parser.parse_args()

    # Define paths
    # Assuming this script is in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the trained model checkpoint
    if args.model:
        model_path = os.path.abspath(args.model)
    else:
        # Default guess: results/merl/MERL/checkpoint.pt inside project root
        model_path = os.path.join(project_root, 'results', 'merl', 'MERL', 'checkpoint.pt')
    
    # Data directory containing .binary files
    data_dir = os.path.join(project_root, 'data')
    
    # Check/Create merl_median.binary
    median_file = os.path.join(data_dir, 'merl_median.binary')
    if not os.path.exists(median_file):
        print(f"Notice: {median_file} not found. Generating it now...")
        try:
            # Temporarily change directory if needed, or just run the function
            # compute_median_main assumes 'data' folder is in current cwd or handled correctly.
            # Let's ensure we are in project root
            cwd = os.getcwd()
            os.chdir(project_root)
            compute_median_main()
            os.chdir(cwd)
        except Exception as e:
            print(f"Error generating median file: {e}")
            return
    
    # Output directory for .pt files
    
    # Output directory for .pt files
    pt_output_dir = os.path.join(project_root, 'pt_results')
    
    # Output directory for .fullbin files
    fullbin_output_dir = os.path.join(project_root, 'fullbin_results')
    
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"Error: Model checkpoint not found at {model_path}")
        print("Please update the 'model_path' variable in this script to point to your trained model.")
        return

    
    print("=== HyperBRDF Batch Processing ===")
    print(f"Model: {model_path}")
    print(f"Data: {data_dir}")
    print(f"PT Output: {pt_output_dir}")
    print(f"Fullbin Output: {fullbin_output_dir}")
    print("==================================\n")
    
    # Ensure output directories exist
    os.makedirs(pt_output_dir, exist_ok=True)
    os.makedirs(fullbin_output_dir, exist_ok=True)
    
    # Step 1: Run test.py to generate .pt files
    print("--- Step 1: Generating .pt files from .binary files ---")
    test_script = os.path.join(project_root, 'test.py')
    
    binary_files = glob.glob(os.path.join(data_dir, '*.binary'))
    if not binary_files:
        print(f"Error: No .binary files found in {data_dir}")
        return

    total_files = len(binary_files)
    for i, binary_file in enumerate(binary_files):
        filename = os.path.basename(binary_file)
        print(f"Processing [{i+1}/{total_files}]: {filename}")
        
        # Check if output already exists to skip? (Optional, but good)
        # Output name logic in test.py: mat_name + '.pt'
        mat_name = os.path.splitext(filename)[0]
        output_pt = os.path.join(pt_output_dir, mat_name + '.pt')
        
        if os.path.exists(output_pt):
             print(f"  Skipping (already exists): {output_pt}")
             # Uncomment continue to skip existing files if desired
             # continue 
        
        cmd_test = [
            sys.executable, test_script,
            '--model', model_path,
            '--binary', binary_file,
            '--destdir', pt_output_dir,
            '--dataset', 'MERL'
        ]
        
        try:
            # We suppress output to avoid cluttering unless error occurs
            subprocess.check_call(cmd_test, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print(f"  Failed to process {filename}")
            # We continue to next file
            
    print("Step 1 completed.\n")

    # Step 2: Run pt_to_fullmerl.py to convert .pt files to .fullbin files
    print("--- Step 2: Converting .pt files to .fullbin files ---")
    converter_script = os.path.join(project_root, 'pt_to_fullmerl.py')
    
    # Construct command for pt_to_fullmerl.py
    # python pt_to_fullmerl.py <pts_dir> <dest_dir> --dataset MERL
    cmd_convert = [
        sys.executable, converter_script,
        pt_output_dir,
        fullbin_output_dir,
        '--dataset', 'MERL'
    ]
    
    print(f"Executing: {' '.join(cmd_convert)}")
    try:
        subprocess.check_call(cmd_convert)
        print("Step 2 completed successfully.\n")
    except subprocess.CalledProcessError as e:
        print(f"Step 2 failed with error: {e}")
        return
        
    print(f"Batch processing finished. Final results are in: {fullbin_output_dir}")

if __name__ == "__main__":
    main()
