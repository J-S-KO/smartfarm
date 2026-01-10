"""
데이터 읽기 모듈 (CSV → MariaDB 전환 대비 추상화)
"""
import os
import csv
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import config

class DataReader:
    """CSV 파일 기반 데이터 읽기 (향후 MariaDB로 전환 가능)"""
    
    def __init__(self):
        self.log_dir = config.LOG_DIR
    
    def get_available_dates(self) -> List[str]:
        """사용 가능한 날짜 목록 반환 (YYYY-MM-DD 형식)"""
        dates = set()
        
        # 월별 폴더 검색
        month_patterns = os.path.join(self.log_dir, "*/smartfarm_log_*.csv")
        for filepath in glob.glob(month_patterns):
            # 파일명에서 날짜 추출: smartfarm_log_YYYY-MM-DD.csv
            filename = os.path.basename(filepath)
            if filename.startswith("smartfarm_log_") and filename.endswith(".csv"):
                date_str = filename.replace("smartfarm_log_", "").replace(".csv", "")
                try:
                    # 날짜 형식 검증
                    datetime.strptime(date_str, "%Y-%m-%d")
                    dates.add(date_str)
                except ValueError:
                    continue
        
        return sorted(list(dates), reverse=True)  # 최신순 정렬
    
    def read_log_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        지정된 날짜 범위의 로그 데이터 읽기
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
        Returns:
            로그 데이터 리스트 (딕셔너리 형태)
        """
        data = []
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # 날짜 범위 내의 모든 날짜 생성
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            month_dir = current_dt.strftime("%Y-%m")
            
            # 로그 파일 경로
            log_file = os.path.join(self.log_dir, month_dir, f"smartfarm_log_{date_str}.csv")
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # None 키 제거 (CSV 마지막 빈 컬럼 처리)
                        if None in row:
                            del row[None]
                        
                        # 타임스탬프 파싱
                        try:
                            timestamp = datetime.strptime(row['Timestamp'], "%Y-%m-%d %H:%M:%S")
                            row['_timestamp'] = timestamp  # 내부 사용
                            row['_date'] = date_str
                            data.append(row)
                        except (ValueError, KeyError) as e:
                            continue
            
            current_dt += timedelta(days=1)
        
        # 타임스탬프 기준 정렬
        data.sort(key=lambda x: x.get('_timestamp', datetime.min))
        return data
    
    def get_latest_data(self, limit: int = 1) -> Optional[Dict]:
        """최신 데이터 반환"""
        dates = self.get_available_dates()
        if not dates:
            return None
        
        # 최신 날짜의 데이터 읽기
        latest_date = dates[0]
        data = self.read_log_data(latest_date, latest_date)
        
        if data:
            return data[-limit:] if limit == 1 else data[-limit:]
        return None
    
    def get_statistics(self, start_date: str, end_date: str) -> Dict:
        """통계 정보 계산"""
        data = self.read_log_data(start_date, end_date)
        if not data:
            return {}
        
        # 숫자 필드 추출
        numeric_fields = ['Temp_C', 'Hum_Pct', 'Soil_Pct', 'Lux', 'VPD_kPa', 'DLI_mol']
        stats = {}
        
        for field in numeric_fields:
            values = []
            for row in data:
                try:
                    val = float(row.get(field, 0))
                    if val > 0:  # 유효한 값만
                        values.append(val)
                except (ValueError, TypeError):
                    continue
            
            if values:
                stats[field] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'count': len(values)
                }
        
        return stats

# 향후 MariaDB 전환을 위한 인터페이스 (현재는 미구현)
class MariaDBReader(DataReader):
    """MariaDB 기반 데이터 읽기 (향후 구현)"""
    
    def __init__(self, connection_string: str):
        # super().__init__()  # CSV는 사용 안 함
        self.conn_string = connection_string
        # TODO: MariaDB 연결 설정
    
    def read_log_data(self, start_date: str, end_date: str) -> List[Dict]:
        # TODO: MariaDB 쿼리 구현
        pass

