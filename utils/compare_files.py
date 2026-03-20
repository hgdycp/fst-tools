import difflib

def compare_files(file1_path, file2_path):
    with open(file1_path, 'r', encoding='utf-8') as f1, open(file2_path, 'r', encoding='utf-8') as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()
    
    print(f"文件1 ({file1_path}) 行数: {len(lines1)}")
    print(f"文件2 ({file2_path}) 行数: {len(lines2)}")
    
    if len(lines1) != len(lines2):
        print("[!] 警告：两个文件行数不同！")
    
    # 使用difflib进行差异比较
    diff = list(difflib.unified_diff(lines1, lines2, fromfile=file1_path, tofile=file2_path, lineterm=''))
    
    if not diff:
        print("\n[OK] 两个文件完全相同！")
        return
    
    print("\n📊 发现差异：")
    print('\n'.join(diff[:100]))  # 只显示前100行差异
    if len(diff) > 100:
        print(f"\n... (还有 {len(diff)-100} 行差异未显示)")

if __name__ == "__main__":
    file1 = r"c:\Users\aa\Desktop\调试工具\完成工具\track_random.a3h"
    file2 = r"c:\Users\aa\Desktop\调试工具\完成工具\track_random copy.a3h"
    compare_files(file1, file2)