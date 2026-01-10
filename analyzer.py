"""
상태 분석 및 액션 제안 모듈
"""
from typing import List, Dict, Optional
from datetime import datetime
import config
import math

class StatusAnalyzer:
    """로그 데이터 기반 상태 분석 및 액션 제안"""
    
    def __init__(self):
        self.alert_counter = 0  # 일련번호 카운터 (세션별로 리셋)
    
    def reset_counter(self):
        """일련번호 카운터 리셋 (새로운 분석 시작 시)"""
        self.alert_counter = 0
    
    def calculate_expected_dli_by_time(self, current_hour: int, current_dli: float, current_lux: float) -> Dict:
        """
        현재 시간대에서 하루 종료까지 예상 DLI 계산
        Args:
            current_hour: 현재 시간 (0-23)
            current_dli: 현재까지 누적된 DLI
            current_lux: 현재 조도
        Returns:
            {
                'expected_total': 예상 총 DLI,
                'target_ratio': 목표 대비 비율,
                'deficit': 부족량,
                'is_on_track': 목표 달성 가능 여부
            }
        """
        # 하루 중 광합성 활성 시간대 (6시 ~ 20시, 14시간)
        active_start_hour = 6
        active_end_hour = 20
        active_hours = active_end_hour - active_start_hour  # 14시간
        
        # 현재 시간이 활성 시간대 밖이면 예측 불가
        if current_hour < active_start_hour:
            return {
                'expected_total': 0.0,
                'target_ratio': 0.0,
                'deficit': config.TARGET_DLI_MIN,
                'is_on_track': False,
                'message': '활성 시간대 전'
            }
        
        if current_hour >= active_end_hour:
            # 이미 하루가 끝났거나 끝나가는 시간
            return {
                'expected_total': current_dli,
                'target_ratio': (current_dli / config.TARGET_DLI_MIN) * 100 if config.TARGET_DLI_MIN > 0 else 0,
                'deficit': max(0, config.TARGET_DLI_MIN - current_dli),
                'is_on_track': current_dli >= config.TARGET_DLI_MIN,
                'message': '활성 시간대 종료'
            }
        
        # 현재까지 경과한 활성 시간
        elapsed_active_hours = current_hour - active_start_hour
        remaining_active_hours = active_end_hour - current_hour
        
        # 현재 시간대의 평균 PPFD 추정 (현재 조도 기반)
        current_ppfd = current_lux * config.LUX_TO_PPFD
        
        # 시간대별 평균 PPFD 추정 (간단한 모델)
        # 정오(12시)를 기준으로 포물선 형태로 가정
        # 최대 PPFD는 정오에, 최소는 활성 시간대 시작/종료 시
        hour_factor = math.sin(math.pi * (current_hour - active_start_hour) / active_hours)
        max_ppfd_estimate = current_ppfd / max(hour_factor, 0.1) if hour_factor > 0 else current_ppfd * 2
        
        # 남은 시간 동안의 예상 DLI 계산
        # 현재 PPFD를 기준으로 남은 시간 동안의 평균 PPFD 추정
        # 정오 이후면 감소, 정오 이전이면 증가 추세
        if current_hour < 12:
            # 오전: 증가 추세
            avg_remaining_ppfd = (current_ppfd + max_ppfd_estimate) / 2
        else:
            # 오후: 감소 추세
            avg_remaining_ppfd = current_ppfd * 0.7  # 점진적 감소
        
        # 남은 시간 동안 예상 DLI (PPFD * 시간(초) / 1,000,000)
        expected_remaining_dli = (avg_remaining_ppfd * remaining_active_hours * 3600) / 1000000.0
        expected_total_dli = current_dli + expected_remaining_dli
        
        # 목표 대비 비율
        target_ratio = (expected_total_dli / config.TARGET_DLI_MIN) * 100 if config.TARGET_DLI_MIN > 0 else 0
        deficit = max(0, config.TARGET_DLI_MIN - expected_total_dli)
        is_on_track = expected_total_dli >= config.TARGET_DLI_MIN * 0.8  # 80% 이상이면 괜찮다고 판단
        
        return {
            'expected_total': expected_total_dli,
            'target_ratio': target_ratio,
            'deficit': deficit,
            'is_on_track': is_on_track,
            'remaining_hours': remaining_active_hours,
            'current_ppfd': current_ppfd,
            'message': f'예상 총 DLI: {expected_total_dli:.2f} mol/m²/day (목표: {config.TARGET_DLI_MIN:.1f})'
        }
    
    def analyze_current_status(self, latest_data: Dict) -> List[Dict]:
        """
        현재 상태 분석 및 액션 제안
        Returns:
            [{
                'id': 일련번호,
                'level': 'warning' | 'error' | 'info',
                'title': 제목,
                'message': 메시지,
                'actions': [액션 리스트]
            }, ...]
        """
        # 매번 분석 시 카운터 리셋 (같은 세션 내에서 일관된 번호 부여)
        self.alert_counter = 0
        alerts = []
        
        if not latest_data:
            return alerts
        
        # 최신 데이터 추출
        try:
            temp = float(latest_data.get('Temp_C', 0))
            hum = float(latest_data.get('Hum_Pct', 0))
            soil = float(latest_data.get('Soil_Pct', 0))
            lux = float(latest_data.get('Lux', 0))
            vpd = float(latest_data.get('VPD_kPa', 0))
            dli = float(latest_data.get('DLI_mol', 0))
            fan = latest_data.get('Fan_Status', 'OFF')
            led_w = latest_data.get('LED_W_Status', 'OFF')
            led_p = latest_data.get('LED_P_Status', 'OFF')
            valve = latest_data.get('Valve_Status', 'OFF')
            curtain = latest_data.get('Curtain_Status', 'CLOSED')
            emergency = latest_data.get('Emergency_Stop', 'False') == 'True'
        except (ValueError, TypeError):
            return alerts
        
        # 센서 데이터 유효성 검사: 0.0 값은 센서가 초기화되지 않았거나 데이터를 읽지 못한 경우
        # 이런 경우 알림을 생성하지 않음 (잘못된 알림 방지)
        if temp == 0.0 and hum == 0.0 and lux == 0.0:
            # 모든 주요 센서가 0.0이면 센서 데이터가 없는 것으로 판단
            return alerts
        
        # 1. 온도 분석 (온도가 0.0이 아닐 때만)
        if temp > 0 and temp < 5:
            self.alert_counter += 1
            alerts.append({
                'id': self.alert_counter,
                'case_code': 'TEMP_CRITICAL_LOW',  # Discord 푸시용 케이스 코드
                'level': 'error',
                'title': '냉해 위험',
                'message': f'온도가 {temp:.1f}°C로 매우 낮습니다. 식물 냉해가 발생할 수 있습니다.',
                'actions': [
                    'LED 조명 켜기 (발열 활용)',
                    '커튼 닫기 (보온)',
                    '팬 작동 중단',
                    '온실 보온 장치 점검'
                ]
            })
        elif temp > 0 and temp < 10:
            self.alert_counter += 1
            alerts.append({
                'id': self.alert_counter,
                'case_code': 'TEMP_LOW',
                'level': 'warning',
                'title': '저온 주의',
                'message': f'온도가 {temp:.1f}°C로 낮습니다. 식물 성장에 불리할 수 있습니다.',
                'actions': [
                    'LED 조명 켜기 (보온)',
                    '커튼 닫기',
                    '온실 보온 상태 확인'
                ]
            })
        elif temp > 0 and temp >= 40:
            self.alert_counter += 1
            alerts.append({
                'id': self.alert_counter,
                'case_code': 'TEMP_CRITICAL_HIGH',  # 즉각 조치 필요
                'level': 'error',
                'title': '고온 위험',
                'message': f'온도가 {temp:.1f}°C로 매우 높습니다. 화재 위험이 있거나 식물이 손상될 수 있습니다.',
                'actions': [
                    '즉시 팬 작동',
                    '커튼 열기 (환기)',
                    'LED 조명 끄기 (발열 감소)',
                    '긴급 환기 시스템 점검',
                    '온도 센서 점검'
                ]
            })
        elif temp > 0 and temp > 35 and temp < 40:
            self.alert_counter += 1
            alerts.append({
                'id': self.alert_counter,
                'case_code': 'TEMP_HIGH',
                'level': 'warning',
                'title': '고온 주의',
                'message': f'온도가 {temp:.1f}°C로 높습니다. 식물 스트레스가 발생할 수 있습니다.',
                'actions': [
                    '팬 작동',
                    '커튼 열기',
                    'LED 조명 밝기 조절'
                ]
            })
        
        # 2. 습도 분석 (습도가 0.0이 아닐 때만)
        if hum > 0 and hum < 20:
            self.alert_counter += 1
            alerts.append({
                'id': self.alert_counter,
                'case_code': 'HUM_LOW',
                'level': 'warning',
                'title': '저습도 주의',
                'message': f'습도가 {hum:.1f}%로 매우 낮습니다. 식물이 건조할 수 있습니다.',
                'actions': [
                    '물주기 고려',
                    '팬 작동 중단',
                    '커튼 닫기 (습도 유지)',
                    '가습기 점검'
                ]
            })
        elif hum > 0 and hum > 95:
            self.alert_counter += 1
            alerts.append({
                'id': self.alert_counter,
                'case_code': 'HUM_HIGH',
                'level': 'warning',
                'title': '고습도 주의',
                'message': f'습도가 {hum:.1f}%로 매우 높습니다. 곰팡이 발생 위험이 있습니다.',
                'actions': [
                    '팬 작동 (환기)',
                    '커튼 열기',
                    'LED 조명 켜기 (습도 감소)',
                    '물주기 중단'
                ]
            })
        
        # 3. 토양습도 분석 (토양습도가 0.0이 아닐 때만)
        if soil > 0 and soil < 10:
            self.alert_counter += 1
            alerts.append({
                'id': self.alert_counter,
                'case_code': 'SOIL_CRITICAL_LOW',  # 즉각 조치 필요
                'level': 'error',
                'title': '토양 건조 위험',
                'message': f'토양습도가 {soil:.1f}%로 매우 낮습니다. 식물이 시들 수 있습니다.',
                'actions': [
                    '즉시 물주기',
                    '토양센서 점검 (센서 오작동 가능성)',
                    '점적스파이크 점검'
                ]
            })
        elif soil > 0 and soil >= 10 and soil < config.SOIL_TRIGGER_PCT:
            self.alert_counter += 1
            alerts.append({
                'id': self.alert_counter,
                'case_code': 'SOIL_LOW',
                'level': 'warning',
                'title': '토양 건조 주의',
                'message': f'토양습도가 {soil:.1f}%로 낮습니다. 물주기가 필요할 수 있습니다.',
                'actions': [
                    '물주기 고려',
                    '토양 상태 확인'
                ]
            })
        
        # 4. VPD 분석 (VPD가 0.0이 아닐 때만, 온도와 습도가 유효할 때만)
        if vpd > 0 and temp > 0 and hum > 0 and vpd < 0.3:
            self.alert_counter += 1
            alerts.append({
                'id': self.alert_counter,
                'case_code': 'VPD_LOW',
                'level': 'warning',
                'title': 'VPD 과낮음',
                'message': f'VPD가 {vpd:.2f} kPa로 매우 낮습니다. 습도가 과도하게 높아 곰팡이 위험이 있습니다.',
                'actions': [
                    '팬 작동 (환기)',
                    '커튼 열기',
                    'LED 조명 켜기 (습도 감소)',
                    '물주기 중단'
                ]
            })
        elif vpd > 0 and temp > 0 and hum > 0 and vpd > 2.5:
            self.alert_counter += 1
            alerts.append({
                'id': self.alert_counter,
                'case_code': 'VPD_HIGH',
                'level': 'warning',
                'title': 'VPD 과높음',
                'message': f'VPD가 {vpd:.2f} kPa로 매우 높습니다. 공기가 과도하게 건조합니다.',
                'actions': [
                    '팬 작동 중단',
                    '커튼 닫기 (습도 유지)',
                    '물주기 고려',
                    '가습기 점검'
                ]
            })
        
        # 5. DLI 분석 (시간대 고려)
        now = datetime.now()
        current_hour = now.hour
        dli_prediction = self.calculate_expected_dli_by_time(current_hour, dli, lux)
        
        # 시간대별 목표 DLI 비율 계산 (현재 시간에서 하루 종료까지 필요한 비율)
        # 예: 오전 8시면 하루의 약 20% 경과, 목표의 20%는 이미 받아야 함
        active_start_hour = 6
        active_end_hour = 20
        if active_start_hour <= current_hour < active_end_hour:
            elapsed_hours = current_hour - active_start_hour
            total_active_hours = active_end_hour - active_start_hour
            expected_progress_ratio = elapsed_hours / total_active_hours  # 0.0 ~ 1.0
            expected_dli_at_this_time = config.TARGET_DLI_MIN * expected_progress_ratio
            
            # 현재 DLI가 시간대별 목표보다 현저히 낮고, 예상 총 DLI도 목표 미달인 경우만 경고
            if dli < expected_dli_at_this_time * 0.7 and not dli_prediction.get('is_on_track', False):
                self.alert_counter += 1
                deficit = dli_prediction.get('deficit', 0)
                expected_total = dli_prediction.get('expected_total', 0)
                target_ratio = dli_prediction.get('target_ratio', 0)
                
                alerts.append({
                    'id': self.alert_counter,
                    'case_code': 'DLI_LOW',
                    'level': 'warning',
                    'title': '일조량 부족 경고',
                    'message': f'현재 DLI: {dli:.2f} mol/m²/day | 예상 총 DLI: {expected_total:.2f} mol/m²/day (목표: {config.TARGET_DLI_MIN:.1f}, 달성률: {target_ratio:.1f}%) | 부족량: {deficit:.2f} mol/m²/day',
                    'actions': [
                        'LED 조명 켜기 (보조 조명)',
                        '커튼 열기 (자연광 확보)',
                        f'남은 시간: {dli_prediction.get("remaining_hours", 0)}시간 동안 LED 보조 필요'
                    ],
                    'dli_info': dli_prediction  # 추가 정보
                })
        elif current_hour >= active_end_hour:
            # 하루 종료 시점: 최종 DLI 확인
            if dli < config.TARGET_DLI_MIN * 0.8:
                self.alert_counter += 1
                alerts.append({
                    'id': self.alert_counter,
                    'case_code': 'DLI_LOW',
                    'level': 'warning',
                    'title': '일조량 목표 미달',
                    'message': f'하루 종료 시점 DLI: {dli:.2f} mol/m²/day (목표: {config.TARGET_DLI_MIN:.1f}, 달성률: {(dli/config.TARGET_DLI_MIN)*100:.1f}%)',
                    'actions': [
                        '내일 LED 조명 시간 연장 고려',
                        '커튼 위치 조정',
                        '조도 센서 점검'
                    ],
                    'dli_info': {'expected_total': dli, 'target_ratio': (dli/config.TARGET_DLI_MIN)*100}
                })
        
        # 6. 센서 이상 감지 (값이 비정상적으로 고정)
        # 이건 통계 데이터가 필요하므로 별도 함수로 처리
        
        # 7. 비상 정지 상태
        if emergency:
            self.alert_counter += 1
            alerts.append({
                'id': self.alert_counter,
                'case_code': 'EMERGENCY_STOP',  # 즉각 조치 필요
                'level': 'error',
                'title': '비상 정지 활성화',
                'message': '시스템이 비상 정지 상태입니다. 모든 구동계가 중단되었습니다.',
                'actions': [
                    '비상 정지 해제 (메뉴 0번)',
                    '시스템 상태 점검',
                    '문제 해결 후 재개'
                ]
            })
        
        return alerts
    
    def analyze_sensor_anomaly(self, data: List[Dict], field: str) -> Optional[Dict]:
        """센서 이상 감지 (값이 고정되어 있거나 비정상적일 때)"""
        if len(data) < 10:  # 최소 데이터 필요
            return None
        
        values = []
        for row in data[-100:]:  # 최근 100개 데이터만 확인
            try:
                val = float(row.get(field, 0))
                values.append(val)
            except (ValueError, TypeError):
                continue
        
        if len(values) < 10:
            return None
        
        # 값의 변화량이 거의 없으면 이상
        value_range = max(values) - min(values)
        avg_value = sum(values) / len(values)
        
        if avg_value > 0 and value_range / avg_value < 0.01:  # 변화량이 1% 미만
            self.alert_counter += 1
            return {
                'id': self.alert_counter,
                'case_code': f'SENSOR_ANOMALY_{field.upper()}',
                'level': 'warning',
                'title': f'{field} 센서 이상 의심',
                'message': f'{field} 값이 거의 변화하지 않습니다. 센서 고장 또는 연결 문제가 의심됩니다.',
                'actions': [
                    '센서 연결 상태 확인',
                    '센서 청소',
                    '센서 교체 고려'
                ]
            }
        
        return None

