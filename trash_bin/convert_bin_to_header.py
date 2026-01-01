#!/usr/bin/env python3
"""
BIN 파일을 Arduino U8g2용 헤더 파일로 변환
사용법: python3 convert_bin_to_header.py <input.bin> <output.h> <array_name> [width] [height]
"""

import sys
import os

def bin_to_header(input_path, output_path, array_name, width=64, height=64):
    """
    BIN 파일을 C 헤더 파일로 변환
    """
    try:
        with open(input_path, 'rb') as f:
            data = f.read()
        
        file_size = len(data)
        expected_size = (width * height) // 8  # 1바이트 = 8픽셀
        
        print(f"파일 크기: {file_size} 바이트")
        print(f"예상 크기 (64x64): {expected_size} 바이트")
        
        if file_size == expected_size:
            print("✅ 크기가 정확히 일치합니다!")
            bitmap_data = data
        elif file_size > expected_size:
            print(f"⚠️ 파일이 더 큽니다. 처음 {expected_size}바이트만 사용합니다.")
            bitmap_data = data[:expected_size]
        else:
            print(f"⚠️ 파일이 더 작습니다. 패딩을 추가합니다.")
            bitmap_data = data + b'\x00' * (expected_size - file_size)
        
        # C 헤더 파일 생성
        with open(output_path, 'w') as f:
            f.write(f"// Auto-generated from {os.path.basename(input_path)}\n")
            f.write(f"// Size: {width}x{height} pixels\n")
            f.write(f"#ifndef {array_name.upper()}_H\n")
            f.write(f"#define {array_name.upper()}_H\n\n")
            f.write(f"#include <Arduino.h>\n\n")
            f.write(f"// Width: {width}, Height: {height}\n")
            f.write(f"const unsigned char {array_name}[] PROGMEM = {{\n")
            
            # 바이트 배열 출력 (16바이트씩)
            for i in range(0, len(bitmap_data), 16):
                line = ", ".join([f"0x{bitmap_data[j]:02X}" for j in range(i, min(i+16, len(bitmap_data)))])
                if i + 16 < len(bitmap_data):
                    f.write(f"  {line},\n")
                else:
                    f.write(f"  {line}\n")
            
            f.write("};\n\n")
            f.write(f"#endif // {array_name.upper()}_H\n")
        
        print(f"✅ 변환 완료: {input_path} -> {output_path}")
        print(f"   크기: {width}x{height} 픽셀")
        print(f"   배열 이름: {array_name}")
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("사용법: python3 convert_bin_to_header.py <input.bin> <output.h> <array_name> [width] [height]")
        print("\n예시:")
        print("  python3 convert_bin_to_header.py epd_bitmap_.bin strawberry.h strawberry_bitmap 64 64")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    array_name = sys.argv[3]
    
    width = int(sys.argv[4]) if len(sys.argv) > 4 else 64
    height = int(sys.argv[5]) if len(sys.argv) > 5 else 64
    
    if not os.path.exists(input_file):
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        sys.exit(1)
    
    bin_to_header(input_file, output_file, array_name, width, height)

