import os
import glob
import numpy as np
from utils import fastmerl

def main():
    # 获取项目全局的 BRDF 目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, '..', 'data', 'inputs', 'brdfs')
    
    # 输出文件仍放在 HyperBRDF/data 下作为内部引用
    output_dir = os.environ.get("HB_MEDIAN_OUTPUT_DIR") or os.path.join(current_dir, 'data')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'merl_median.binary')
    
    if os.path.exists(output_file):
        print(f"{output_file} already exists. Skipping.")
        return

    print(f"Computing median BRDF from: {data_dir}")
    files = glob.glob(os.path.join(data_dir, '*.binary'))
    files = [f for f in files if 'median' not in f] # Exclude any median file if present
    
    if not files:
        print("No binary files found in data directory.")
        return

    print(f"Found {len(files)} files.")
    
    # Load all BRDFs
    brdfs = []
    for i, f in enumerate(files):
        print(f"Loading [{i+1}/{len(files)}]: {os.path.basename(f)}")
        try:
            m = fastmerl.Merl(f)
            # m.brdf is a tuple/list. Convert to numpy.
            # brdf_np is already created in __init__
            brdfs.append(m.brdf_np)
        except Exception as e:
            print(f"Error loading {f}: {e}")
            
    if not brdfs:
        print("No valid BRDFs loaded.")
        return
        
    print("Stacking arrays...")
    # shape: (N, 3*90*90*180)
    all_brdfs = np.stack(brdfs)
    
    print("Computing median...")
    median_brdf = np.median(all_brdfs, axis=0)
    
    print("Saving merl_median.binary...")
    # Create a Merl object to use for saving
    # We can reuse the last one loaded
    m_out = fastmerl.Merl(files[0])
    m_out.brdf = tuple(median_brdf)
    m_out.write_merl_file(output_file)
    
    print("Done.")

if __name__ == "__main__":
    main()
