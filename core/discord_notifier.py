# -*- coding: utf-8 -*-
"""
Discord 웹훅 알림 모듈
한글 인코딩 문제를 해결하여 Discord로 알림을 전송합니다.
"""
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
from .env_loader import get_env
import logging

# 로거 설정
logger = logging.getLogger(__name__)

class DiscordNotifier:
    """Discord 웹훅을 통한 알림 전송 클래스"""
    
    def __init__(self):
        """Discord 웹훅 URL 로드"""
        self.webhook_url = get_env('DISCORD_WEBHOOK_URL')
        if not self.webhook_url:
            logger.warning("Discord 웹훅 URL이 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        # 알림 전송 이력 관리 (중복 방지 및 주기적 알림 제어)
        self.alert_history = {}  # {case_code: {'last_sent': timestamp, 'count': count}}
        
        # 알림 레벨별 전송 정책
        # 'error': 즉시 전송, 'warning': 1시간마다, 'info': 3시간마다
        self.alert_intervals = {
            'error': 0,      # 즉시 전송 (중복 방지: 5분)
            'warning': 3600,  # 1시간마다
            'info': 10800    # 3시간마다
        }
        
        # 중복 방지 최소 간격 (초)
        self.duplicate_prevention_interval = 300  # 5분
    
    def should_send_alert(self, case_code: str, level: str) -> bool:
        """
        알림을 전송해야 하는지 판단합니다.
        
        Args:
            case_code: 알림 케이스 코드
            level: 알림 레벨 ('error', 'warning', 'info')
        
        Returns:
            전송 여부
        """
        if not self.webhook_url:
            return False
        
        now = datetime.now().timestamp()
        
        # 이전 전송 이력 확인
        if case_code in self.alert_history:
            last_sent = self.alert_history[case_code]['last_sent']
            interval = self.alert_intervals.get(level, 3600)
            
            # 레벨별 전송 간격 체크
            if now - last_sent < interval:
                return False
            
            # 중복 방지: error 레벨도 최소 5분 간격
            if now - last_sent < self.duplicate_prevention_interval:
                return False
        
        return True
    
    def update_alert_history(self, case_code: str):
        """알림 전송 이력 업데이트"""
        now = datetime.now().timestamp()
        if case_code in self.alert_history:
            self.alert_history[case_code]['last_sent'] = now
            self.alert_history[case_code]['count'] += 1
        else:
            self.alert_history[case_code] = {
                'last_sent': now,
                'count': 1
            }
    
    def send_message(self, title: str, message: str, level: str = 'info', 
                     fields: Optional[List[Dict]] = None, 
                     case_code: Optional[str] = None) -> bool:
        """
        Discord 웹훅으로 메시지를 전송합니다.
        
        Args:
            title: 메시지 제목
            message: 메시지 내용
            level: 알림 레벨 ('error', 'warning', 'info')
            fields: 추가 필드 (선택사항)
            case_code: 알림 케이스 코드 (선택사항, 주기적 알림 제어용)
        
        Returns:
            전송 성공 여부
        """
        if not self.webhook_url:
            logger.warning("Discord 웹훅 URL이 설정되지 않아 알림을 전송할 수 없습니다.")
            return False
        
        # 주기적 알림 제어 (case_code가 있는 경우)
        if case_code and not self.should_send_alert(case_code, level):
            logger.debug(f"알림 '{case_code}'는 아직 전송 간격이 지나지 않아 건너뜁니다.")
            return False
        
        # 레벨별 색상 설정
        color_map = {
            'error': 0xff0000,    # 빨간색
            'warning': 0xffaa00,   # 주황색
            'info': 0x00aaff       # 파란색
        }
        color = color_map.get(level, 0x808080)  # 기본값: 회색
        
        # 레벨별 이모지
        emoji_map = {
            'error': '🚨',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        emoji = emoji_map.get(level, '📢')
        
        # Embed 생성
        embed = {
            'title': f"{emoji} {title}",
            'description': message,
            'color': color,
            'timestamp': datetime.utcnow().isoformat(),
            'footer': {
                'text': 'SmartFarm 알림 시스템'
            }
        }
        
        # 추가 필드가 있으면 추가
        if fields:
            embed['fields'] = fields
        
        # 웹훅 페이로드
        payload = {
            'embeds': [embed]
        }
        
        try:
            # 한글 인코딩 문제 해결: JSON 직렬화 시 ensure_ascii=False 사용
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json; charset=utf-8'},
                timeout=10
            )
            
            # 응답 확인
            if response.status_code == 204:
                logger.info(f"Discord 알림 전송 성공: {title}")
                if case_code:
                    self.update_alert_history(case_code)
                return True
            else:
                logger.error(f"Discord 알림 전송 실패: HTTP {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Discord 알림 전송 중 오류 발생: {e}")
            return False
    
    def send_alert(self, alert: Dict) -> bool:
        """
        analyzer.py의 alert 딕셔너리를 Discord로 전송합니다.
        
        Args:
            alert: analyzer.py의 alert 딕셔너리
        
        Returns:
            전송 성공 여부
        """
        level = alert.get('level', 'info')
        title = alert.get('title', '알림')
        message = alert.get('message', '')
        case_code = alert.get('case_code')
        actions = alert.get('actions', [])
        
        # 디버깅: 전송되는 알림 내용 로그 출력
        logger.info(f"[Discord] 📤 알림 전송 시도: [{level}] {title} - {message}")
        
        # 권장 조치사항을 필드로 추가
        fields = []
        if actions:
            actions_text = '\n'.join([f"• {action}" for action in actions])
            fields.append({
                'name': '권장 조치사항',
                'value': actions_text,
                'inline': False
            })
        
        # DLI 정보가 있으면 추가
        if 'dli_info' in alert:
            dli_info = alert['dli_info']
            dli_fields = []
            if 'expected_total' in dli_info:
                dli_fields.append(f"예상 총 DLI: {dli_info['expected_total']:.2f} mol/m²/day")
            if 'target_ratio' in dli_info:
                dli_fields.append(f"목표 달성률: {dli_info['target_ratio']:.1f}%")
            if 'remaining_hours' in dli_info:
                dli_fields.append(f"남은 시간: {dli_info['remaining_hours']}시간")
            
            if dli_fields:
                fields.append({
                    'name': 'DLI 정보',
                    'value': '\n'.join(dli_fields),
                    'inline': False
                })
        
        # 케이스 코드 추가 (디버깅용)
        if case_code:
            fields.append({
                'name': '케이스 코드',
                'value': case_code,
                'inline': True
            })
        
        return self.send_message(title, message, level, fields, case_code)
    
    def send_test_message(self, message: str = "테스트 메시지입니다.") -> bool:
        """
        테스트용 메시지를 전송합니다.
        
        Args:
            message: 테스트 메시지 내용
        
        Returns:
            전송 성공 여부
        """
        return self.send_message(
            title="테스트 알림",
            message=message,
            level='info',
            case_code=None  # 테스트는 주기 제한 없음
        )

# 전역 인스턴스
discord_notifier = DiscordNotifier()

