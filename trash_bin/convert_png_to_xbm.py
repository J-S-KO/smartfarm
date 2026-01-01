#!/usr/bin/env python3
"""
PNG 이미지를 Arduino U8g2용 XBM 비트맵으로 변환하는 스크립트
사용법: python3 convert_png_to_xbm.py <input.png> <output.h> <array_name>
"""

import sys
from PIL import Image
import os

def png_to_xbm(input_path, output_path, array_name, target_width=None, target_height=None):
    """
    PNG 이미지를 XBM 형식의 C 배열로 변환
    """
    try:
        # 이미지 로드
        img = Image.open(input_path)
        
        # RGBA나 투명도가 있는 경우 처리
        if img.mode in ('RGBA', 'LA', 'P'):
            # 투명 배경을 흰색으로 변환
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # 흑백으로 변환
        img = img.convert('L')
        
        # 크기 조정 (필요한 경우)
        if target_width and target_height:
            img = img.resize((target_width, target_height), Image.LANCZOS)
        
        # 비트맵으로 변환
        width, height = img.size
        pixels = img.load()
        
        # 바이트 배열 생성 (U8g2는 width를 8의 배수로 올림)
        bytes_per_row = (width + 7) // 8
        byte_array = []
        
        # 이미지 통계 확인 (디버깅용)
        min_val = 255
        max_val = 0
        for y in range(height):
            for x in range(width):
                val = pixels[x, y]
                if val < min_val: min_val = val
                if val > max_val: max_val = val
        
        print(f"   픽셀 범위: {min_val} ~ {max_val}")
        
        # 임계값 자동 결정 (중간값 사용)
        threshold = (min_val + max_val) // 2
        if threshold == 0:
            threshold = 128  # 기본값
        print(f"   사용 임계값: {threshold}")
        
        for y in range(height):
            for byte_idx in range(bytes_per_row):
                byte_val = 0
                for bit in range(8):
                    x = byte_idx * 8 + bit
                    if x < width:
                        # 픽셀이 임계값보다 어두우면 1로 설정 (OLED는 1이 켜짐)
                        # 일반적으로 그림은 어두운 부분이므로 1로 설정
                        if pixels[x, y] < threshold:
                            byte_val |= (1 << (7 - bit))
                    # x가 width를 넘어가면 0으로 채움 (패딩)
                byte_array.append(byte_val)
        
        # C 헤더 파일 생성
        with open(output_path, 'w') as f:
            f.write(f"// Auto-generated from {os.path.basename(input_path)}\n")
            f.write(f"// Size: {width}x{height} pixels\n")
            f.write(f"#ifndef {array_name.upper()}_H\n")
            f.write(f"#define {array_name.upper()}_H\n\n")
            f.write(f"#include <Arduino.h>\n\n")
            f.write(f"// Width: {width}, Height: {height}\n")
            f.write(f"const unsigned char {array_name}[] PROGMEM = {{\n")
            
            # 바이트 배열 출력 (16바이트씩) - width, height 제거
            for i in range(0, len(byte_array), 16):
                line = ", ".join([f"0x{byte_array[j]:02X}" for j in range(i, min(i+16, len(byte_array)))])
                if i + 16 < len(byte_array):
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
        return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("사용법: python3 convert_png_to_xbm.py <input.png> <output.h> <array_name> [width] [height]")
        print("\n예시:")
        print("  python3 convert_png_to_xbm.py strawberry.png strawberry.h strawberry_bitmap 64 64")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    array_name = sys.argv[3]
    
    width = int(sys.argv[4]) if len(sys.argv) > 4 else None
    height = int(sys.argv[5]) if len(sys.argv) > 5 else None
    
    if not os.path.exists(input_file):
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        sys.exit(1)
    
    png_to_xbm(input_file, output_file, array_name, width, height)

