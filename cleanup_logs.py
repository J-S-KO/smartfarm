#!/usr/bin/env python3
"""
로그 파일 정리 스크립트
최신 로그 형식을 기준으로 형식이 맞지 않는 데이터 삭제
"""
import os
import csv
import glob
from pathlib import Path

# 기준 헤더 (최신 로그 형식)
REFERENCE_HEADER = [
    'Timestamp', 'Temp_C', 'Hum_Pct', 'Soil_Raw', 'Soil_Pct', 'Lux', 
    'VPD_kPa', 'DLI_mol', 'Valve_Status', 'Fan_Status', 'LED_W_Status', 
    'LED_P_Status', 'Curtain_Status', 'Emergency_Stop', 
    'Watering_Count_Today', 'Water_Used_Today_L', 'Note'
]
REFERENCE_COLUMN_COUNT = len(REFERENCE_HEADER)

def check_file_format(filepath):
    """파일 형식 확인 및 정리"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
            if header is None:
                print(f"  ❌ 빈 파일: {filepath}")
                return 'empty'
            
            # 헤더 확인
            if header != REFERENCE_HEADER:
                print(f"  ❌ 헤더 불일치: {filepath}")
                print(f"     기대: {len(REFERENCE_HEADER)} 컬럼")
                print(f"     실제: {len(header)} 컬럼")
                return 'header_mismatch'
            
            # 데이터 행 확인
            valid_rows = [header]  # 헤더는 유지
            invalid_count = 0
            
            for row_num, row in enumerate(reader, start=2):
                if len(row) != REFERENCE_COLUMN_COUNT:
                    invalid_count += 1
                    if invalid_count <= 3:  # 처음 3개만 출력
                        print(f"     행 {row_num}: 컬럼 수 불일치 ({len(row)} != {REFERENCE_COLUMN_COUNT})")
                else:
                    valid_rows.append(row)
            
            if invalid_count > 0:
                print(f"  ⚠️  {invalid_count}개 행 삭제됨")
                # 파일 다시 쓰기
                with open(filepath, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(valid_rows)
                return 'cleaned'
            else:
                print(f"  ✅ 형식 정상")
                return 'valid'
                
    except Exception as e:
        print(f"  ❌ 오류 발생: {filepath} - {e}")
        return 'error'

def main():
    print("=" * 60)
    print("📋 로그 파일 정리 시작")
    print("=" * 60)
    print(f"기준 헤더: {REFERENCE_COLUMN_COUNT}개 컬럼")
    print(f"  {', '.join(REFERENCE_HEADER[:5])}...")
    print()
    
    # 모든 CSV 파일 찾기
    log_dir = Path('logs')
    csv_files = sorted(log_dir.rglob('*.csv'), reverse=True)  # 최신순
    
    print(f"총 {len(csv_files)}개 파일 발견")
    print()
    
    # 파일별 처리
    files_to_delete = []
    files_cleaned = []
    files_valid = []
    
    for filepath in csv_files:
        rel_path = filepath.relative_to(log_dir)
        print(f"📄 {rel_path}")
        
        result = check_file_format(filepath)
        
        if result == 'header_mismatch':
            files_to_delete.append(filepath)
        elif result == 'cleaned':
            files_cleaned.append(filepath)
        elif result == 'valid':
            files_valid.append(filepath)
        elif result == 'empty':
            files_to_delete.append(filepath)
        
        print()
    
    # 삭제할 파일들
    if files_to_delete:
        print("=" * 60)
        print(f"🗑️  삭제할 파일 ({len(files_to_delete)}개):")
        print("=" * 60)
        for f in files_to_delete:
            print(f"  - {f.relative_to(log_dir)}")
        print()
        
        # 자동 삭제 (사용자 요청에 따라)
        print("  → 형식이 맞지 않는 파일들을 자동으로 삭제합니다...")
        for f in files_to_delete:
            f.unlink()
            print(f"  ✅ 삭제됨: {f.relative_to(log_dir)}")
        print()
    
    # 정리된 파일들
    if files_cleaned:
        print("=" * 60)
        print(f"🧹 정리된 파일 ({len(files_cleaned)}개):")
        print("=" * 60)
        for f in files_cleaned:
            print(f"  ✅ {f.relative_to(log_dir)}")
        print()
    
    # 유효한 파일들
    print("=" * 60)
    print(f"✅ 유효한 파일 ({len(files_valid)}개):")
    print("=" * 60)
    for f in files_valid:
        print(f"  ✅ {f.relative_to(log_dir)}")
    print()
    
    # 빈 폴더 확인
    print("=" * 60)
    print("📁 빈 폴더 확인 중...")
    print("=" * 60)
    
    empty_dirs = []
    for month_dir in sorted(log_dir.iterdir()):
        if month_dir.is_dir():
            csv_files_in_dir = list(month_dir.glob('*.csv'))
            if len(csv_files_in_dir) == 0:
                empty_dirs.append(month_dir)
                print(f"  📂 빈 폴더: {month_dir.relative_to(log_dir)}")
    
    if empty_dirs:
        print()
        print(f"⚠️  빈 폴더 {len(empty_dirs)}개 발견:")
        for d in empty_dirs:
            print(f"  - {d.relative_to(log_dir)}")
        print()
        print("  → 사용자 확인 후 삭제하세요.")
        print("  → 수동 삭제 명령: rm -rf logs/[폴더명]")
    else:
        print("  ✅ 빈 폴더 없음")
    
    print()
    print("=" * 60)
    print("✅ 로그 파일 정리 완료!")
    print("=" * 60)

if __name__ == '__main__':
    main()

