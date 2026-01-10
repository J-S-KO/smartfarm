# -*- coding: utf-8 -*-
"""
환경 변수 로드 유틸리티
.env 파일에서 환경 변수를 읽어옵니다.
"""
import os
from pathlib import Path

def load_env():
    """
    .env 파일에서 환경 변수를 로드합니다.
    .env 파일이 없으면 기본값을 사용합니다.
    보안을 위해 .env 파일의 권한을 600 (소유자만 읽기/쓰기)으로 설정합니다.
    """
    env_file = Path(__file__).parent / '.env'
    
    if env_file.exists():
        # 보안: .env 파일 권한을 600으로 설정 (소유자만 읽기/쓰기)
        try:
            current_mode = env_file.stat().st_mode & 0o777
            if current_mode != 0o600:
                os.chmod(env_file, 0o600)
        except (OSError, PermissionError) as e:
            # 권한 설정 실패해도 파일 읽기는 시도
            pass
        
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 주석이나 빈 줄은 무시
                if not line or line.startswith('#'):
                    continue
                
                # KEY=VALUE 형식 파싱
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 환경 변수에 설정 (이미 있으면 덮어쓰지 않음)
                    if key and value:
                        os.environ.setdefault(key, value)

# 모듈 로드 시 자동으로 .env 파일 읽기
load_env()

def get_env(key: str, default: str = None) -> str:
    """
    환경 변수를 가져옵니다.
    
    Args:
        key: 환경 변수 키
        default: 기본값 (없으면 None)
    
    Returns:
        환경 변수 값 또는 기본값
    """
    return os.environ.get(key, default)

