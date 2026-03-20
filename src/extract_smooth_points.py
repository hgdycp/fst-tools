import os
import sys
import scipy.io
import numpy as np
from datetime import datetime


def extract_smooth_points(mat_file, output_file=None):
    if not os.path.exists(mat_file):
        print(f"\n错误: 文件 '{mat_file}' 不存在!")
        return False
    
    print(f"\n正在加载文件: {mat_file}")
    
    try:
        data = scipy.io.loadmat(mat_file)
    except Exception as e:
        print(f"错误: 无法加载.mat文件 - {e}")
        return False
    
    if 'trackList' not in data:
        print("错误: 文件中未找到 'trackList' 变量!")
        return False
    
    track_list = data['trackList']
    print(f"成功加载数据，共 {track_list.shape[1]} 条轨迹")
    
    if output_file is None:
        base_name = os.path.splitext(os.path.basename(mat_file))[0]
        output_file = f"{base_name}_smoothPoints.txt"
    
    output_path = os.path.abspath(output_file)
    print(f"\n正在生成输出文件: {output_path}")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            
            total_tracks = track_list.shape[1]
            total_points = 0
            
            for track_idx in range(total_tracks):
                track = track_list[0, track_idx]
                
                if 'smoothPointList' not in track.dtype.names:
                    continue
                
                BatchNum = track['BatchNo'][0]
                smooth_list = track['smoothPointList']
                num_points = smooth_list.shape[1]
                total_points += num_points
                
                
                if num_points > 0:
                    first_point = smooth_list[0, 0]
                    point_fields = first_point.dtype.names
                    
                    
                    for point_idx in range(num_points):
                        point = smooth_list[0, point_idx]
                        
                        values = []
                        values.append(f"{BatchNum}")
                        for field in point_fields:
                            val = point[field]
                            if isinstance(val, np.ndarray):
                                if val.size == 1:
                                    val = val.item()
                                    if isinstance(val, float):
                                        values.append(f"{val:.8f}")
                                    else:
                                        values.append(f"{val}")
                                else:
                                    values.append(f"数组({val.shape})")
                            else:
                                values.append(f"{val}")
                        
                        f.write(", ".join(values))
                        f.write("\n")
                
        return True
        
    except Exception as e:
        print(f"错误: 写入文件时失败 - {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    default_file = 'track_20251210172235.mat'
    
    mat_file = None
    output_file = None
    
    if len(sys.argv) > 1:
        mat_file = sys.argv[1]
        if len(sys.argv) > 2:
            output_file = sys.argv[2]
    else:
        print(f"\n未指定输入文件，使用默认文件: {default_file}")
        mat_file = default_file
    
    success = extract_smooth_points(mat_file, output_file)
    
    print("\n按任意键退出...")
    try:
        input()
    except:
        pass
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
