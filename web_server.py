# -*- coding: utf-8 -*-
"""
SmartFarm 웹 대시보드 서버
"""
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from datetime import datetime, timedelta
import os
import secrets
import threading
import time
from data_reader import DataReader
from analyzer import StatusAnalyzer
import config
from env_loader import get_env
from discord_notifier import discord_notifier
# automation.py의 send_cmd 함수 import (시리얼 통신 공통 함수)
try:
    from automation import send_cmd
except ImportError:
    # automation.py를 import할 수 없는 경우를 위한 fallback 함수
    def send_cmd(ser, lock, cmd):
        """시리얼 명령 전송 (fallback)"""
        if not ser or not ser.is_open:
            return False
        with lock:
            try:
                ser.write((cmd + '\n').encode())
                ser.flush()
                time.sleep(0.1)
                return True
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"시리얼 명령 전송 실패: {e}")
                return False

# Flask-CORS는 선택적 (없어도 동작)
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # 세션 보안을 위한 시크릿 키
if CORS_AVAILABLE:
    CORS(app)  # CORS 허용 (필요시)

# 데이터 읽기 및 분석 모듈
data_reader = DataReader()
analyzer = StatusAnalyzer()

# 전역 변수: 시리얼 통신 및 상태
sys_state = {}
ser_b = None
ser_b_lock = threading.Lock()
state_lock = threading.Lock()
camera_thread = None

def init_web_server(state_dict, serial_b, serial_b_lock, state_lock_obj, cam_thread=None):
    """웹 서버 초기화 (main.py에서 호출)"""
    global sys_state, ser_b, ser_b_lock, state_lock, camera_thread
    sys_state = state_dict
    ser_b = serial_b
    ser_b_lock = serial_b_lock  # 중요: 시리얼 포트 락 공유
    state_lock = state_lock_obj
    camera_thread = cam_thread
    import logging
    logging.getLogger(__name__).info(f"[Web] 웹 서버 초기화 완료: ser_b={ser_b is not None}, ser_b_lock={ser_b_lock is not None}, state_lock={state_lock is not None}")

def init_serial_connection():
    """독립 실행 시 시리얼 포트 초기화"""
    global ser_b, sys_state, ser_b_lock, state_lock
    
    import logging
    logger = logging.getLogger(__name__)
    
    if ser_b and ser_b.is_open and sys_state and ser_b_lock and state_lock:
        return True  # 이미 연결됨
    
    try:
        import serial
        
        # Lock 객체가 없으면 생성
        if not ser_b_lock:
            ser_b_lock = threading.Lock()
        if not state_lock:
            state_lock = threading.Lock()
        
        # 시리얼 포트 연결
        if not ser_b or not ser_b.is_open:
            try:
                ser_b = serial.Serial(config.PORT_B, config.BAUD_RATE, timeout=1)
                time.sleep(2)  # 아두이노 재부팅 대기
                ser_b.reset_input_buffer()
                ser_b.reset_output_buffer()
                logger.info(f"[init_serial] ✅ 시리얼 포트 연결 성공: {config.PORT_B}")
            except serial.SerialException as e:
                logger.error(f"[init_serial] ❌ 시리얼 포트 연결 실패: {e}")
                ser_b = None
                return False
        
        # 초기 상태 설정 (없을 때만)
        if not sys_state:
            sys_state = {
                'fan_status': 'OFF',
                'valve_status': 'OFF',
                'led_w_status': 'OFF',
                'led_p_status': 'OFF',
                'curtain_status': 'CLOSED',
                'emergency_stop': False,
                'lux': 0
            }
        return True
    except Exception as e:
        logger.error(f"[init_serial] ❌ 시리얼 포트 연결 실패: {e}")
        import traceback
        logger.error(f"[init_serial] 트레이스백:\n{traceback.format_exc()}")
        return False

def init_camera_thread():
    """독립 실행 시 카메라 스레드 초기화"""
    global camera_thread, sys_state, state_lock, ser_b, ser_b_lock
    
    if camera_thread and camera_thread.is_alive():
        return True  # 이미 실행 중
    
    try:
        import camera
        
        # sys_state와 state_lock이 없으면 초기화
        if not sys_state:
            sys_state = {
                'lux': 0,
                'led_w_status': 'OFF'
            }
        if not state_lock:
            state_lock = threading.Lock()
        
        # 시리얼 포트가 없으면 초기화 시도
        if not ser_b or not ser_b.is_open:
            init_serial_connection()
        
        # 카메라 스레드 생성 및 시작 (ser_b, ser_b_lock 전달)
        camera_thread = camera.CameraThread(sys_state, state_lock, ser_b, ser_b_lock)
        camera_thread.daemon = True
        camera_thread.start()
        
        import logging
        logging.getLogger(__name__).info("카메라 스레드 초기화 성공")
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"카메라 스레드 초기화 실패: {e}")
        return False

# 인증 정보 로드 (.env 파일에서 필수)
WEB_USERNAME = get_env('WEB_USERNAME')
WEB_PASSWORD = get_env('WEB_PASSWORD')

# .env 파일에 인증 정보가 없으면 에러
if not WEB_USERNAME or not WEB_PASSWORD:
    import sys
    print("=" * 60)
    print("❌ 오류: 웹 대시보드 인증 정보가 설정되지 않았습니다!")
    print("=" * 60)
    print("다음 단계를 따라주세요:")
    print("1. 프로젝트 루트에 .env 파일을 생성하세요")
    print("2. .env 파일에 다음 내용을 추가하세요:")
    print("   WEB_USERNAME=your_username")
    print("   WEB_PASSWORD=your_secure_password")
    print("=" * 60)
    sys.exit(1)

def check_auth(username, password):
    """인증 확인"""
    return username == WEB_USERNAME and password == WEB_PASSWORD

@app.route('/')
def index():
    """메인 대시보드 페이지"""
    if 'authenticated' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if check_auth(username, password):
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='사용자명 또는 비밀번호가 올바르지 않습니다.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """로그아웃"""
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/api/dates')
def api_dates():
    """사용 가능한 날짜 목록 API"""
    if 'authenticated' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    dates = data_reader.get_available_dates()
    return jsonify({'dates': dates})

@app.route('/api/data')
def api_data():
    """로그 데이터 API"""
    if 'authenticated' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    if not start_date or not end_date:
        # 기본값: 2026-01-02부터 오늘까지
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = '2026-01-02'  # 데이터가 있는 첫 날짜
    
    try:
        data = data_reader.read_log_data(start_date, end_date)
        
        # JSON 직렬화 가능하도록 변환
        result = []
        for row in data:
            clean_row = {}
            for key, value in row.items():
                if key.startswith('_'):  # 내부 필드 제외
                    continue
                try:
                    # 숫자 변환 시도
                    if value is None or value == '':
                        clean_row[key] = None
                    elif '.' in str(value):
                        clean_row[key] = float(value)
                    else:
                        clean_row[key] = int(value)
                except (ValueError, TypeError):
                    clean_row[key] = str(value) if value is not None else ''
            result.append(clean_row)
        
        return jsonify({'data': result, 'start_date': start_date, 'end_date': end_date})
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        print(f"[Web Server] 데이터 읽기 오류: {error_msg}")
        print(traceback_str)
        return jsonify({'error': error_msg, 'data': []}), 500

@app.route('/api/latest')
def api_latest():
    """최신 데이터 API"""
    if 'authenticated' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    latest = data_reader.get_latest_data(limit=1)
    if latest:
        latest = latest[0] if isinstance(latest, list) else latest
        # 내부 필드 제거
        clean_data = {k: v for k, v in latest.items() if not k.startswith('_')}
        
        # 구동계 상태는 sys_state에서 직접 읽어오기 (CSV보다 정확)
        # CSV는 주기적으로 기록되므로 실시간 상태와 다를 수 있음
        if sys_state and state_lock:
            with state_lock:
                # LED 상태는 sys_state에서 우선 읽기
                if 'led_w_status' in sys_state:
                    clean_data['LED_W_Status'] = sys_state['led_w_status']
                if 'led_p_status' in sys_state:
                    clean_data['LED_P_Status'] = sys_state['led_p_status']
                # 팬, 밸브, 커튼 상태도 sys_state에서 우선 읽기
                if 'fan_status' in sys_state:
                    clean_data['Fan_Status'] = sys_state['fan_status']
                if 'valve_status' in sys_state:
                    clean_data['Valve_Status'] = sys_state['valve_status']
                if 'curtain_status' in sys_state:
                    clean_data['Curtain_Status'] = sys_state['curtain_status']
        
        return jsonify({'data': clean_data})
    return jsonify({'data': None})

@app.route('/api/alerts')
def api_alerts():
    """상태 분석 및 알림 API"""
    if 'authenticated' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    latest = data_reader.get_latest_data(limit=1)
    if latest:
        latest = latest[0] if isinstance(latest, list) else latest
        alerts = analyzer.analyze_current_status(latest)
        
        # Discord 알림 전송 (각 알림에 대해)
        for alert in alerts:
            try:
                discord_notifier.send_alert(alert)
            except Exception as e:
                # Discord 전송 실패해도 웹 대시보드는 정상 작동해야 함
                import logging
                logging.getLogger(__name__).error(f"Discord 알림 전송 실패: {e}")
        
        return jsonify({'alerts': alerts})
    return jsonify({'alerts': []})

@app.route('/api/statistics')
def api_statistics():
    """통계 정보 API"""
    if 'authenticated' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    if not start_date or not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    stats = data_reader.get_statistics(start_date, end_date)
    return jsonify({'statistics': stats})

@app.route('/api/latest_image')
def api_latest_image():
    """가장 최근 이미지 API"""
    if 'authenticated' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    import glob
    from pathlib import Path
    
    # images 폴더에서 가장 최근 이미지 찾기
    image_dir = config.IMG_DIR
    image_patterns = [
        os.path.join(image_dir, '**', '*.jpg'),
        os.path.join(image_dir, '**', '*.jpeg'),
        os.path.join(image_dir, '**', '*.png')
    ]
    
    latest_image = None
    latest_time = 0
    
    for pattern in image_patterns:
        for img_path in glob.glob(pattern, recursive=True):
            try:
                mtime = os.path.getmtime(img_path)
                if mtime > latest_time:
                    latest_time = mtime
                    latest_image = img_path
            except OSError:
                continue
    
    # 현재 시간으로부터 30분 전 시간 계산
    now = datetime.now()
    thirty_min_ago = now - timedelta(minutes=30)
    thirty_min_ago_timestamp = thirty_min_ago.timestamp()
    
    # 최근 이미지가 30분 전보다 오래된 경우 조도 낮음 메시지 반환
    if latest_image and latest_time < thirty_min_ago_timestamp:
        return jsonify({
            'image_url': None,
            'message': '조도가 낮아 사진 촬영이 진행되지 않았습니다.',
            'timestamp': latest_time * 1000 if latest_time > 0 else None
        })
    
    if latest_image:
        # 이미지 파일명만 추출
        filename = os.path.basename(latest_image)
        # 월별 폴더 또는 manual 폴더 경로 추출
        rel_path = os.path.relpath(latest_image, config.IMG_DIR)
        return jsonify({
            'image_url': f'/api/image_file/{rel_path.replace(os.sep, "/")}',
            'timestamp': latest_time * 1000,  # JavaScript용 밀리초
            'message': None
        })
    
    return jsonify({
        'image_url': None,
        'message': '사진이 없습니다.',
        'timestamp': None
    })

@app.route('/api/image')
def api_image():
    """특정 날짜/시간의 이미지 API"""
    if 'authenticated' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    date = request.args.get('date', '')
    time = request.args.get('time', '')
    
    if not date:
        return jsonify({'error': '날짜가 필요합니다'}), 400
    
    import glob
    from datetime import datetime
    
    # 날짜 파싱
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        year_month = date_obj.strftime('%Y-%m')
    except ValueError:
        return jsonify({'error': '잘못된 날짜 형식'}), 400
    
    # 이미지 파일명 패턴 생성
    if time:
        # 특정 시간: YYYY-MM-DD_HH-MM-SS_Auto.jpg
        time_str = time.replace(':', '-')
        pattern = f"{date}_{time_str}*"
    else:
        # 해당 날짜의 모든 이미지 중 가장 최근 것
        pattern = f"{date}_*"
    
    # 이미지 검색
    search_paths = [
        os.path.join(config.IMG_DIR, year_month, pattern),
        os.path.join(config.IMG_DIR, 'manual', pattern)
    ]
    
    found_images = []
    for search_path in search_paths:
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            full_pattern = search_path.replace('*', ext)
            found_images.extend(glob.glob(full_pattern))
    
    if found_images:
        # 가장 최근 이미지 선택
        latest_image = max(found_images, key=os.path.getmtime)
        rel_path = os.path.relpath(latest_image, config.IMG_DIR)
        return jsonify({
            'image_url': f'/api/image_file/{rel_path.replace(os.sep, "/")}'
        })
    
    return jsonify({'image_url': None})

@app.route('/api/image_times')
def api_image_times():
    """특정 날짜의 사용 가능한 시간 목록 API"""
    if 'authenticated' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    date = request.args.get('date', '')
    if not date:
        return jsonify({'error': '날짜가 필요합니다'}), 400
    
    import glob
    from datetime import datetime
    
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        year_month = date_obj.strftime('%Y-%m')
    except ValueError:
        return jsonify({'error': '잘못된 날짜 형식'}), 400
    
    # 해당 날짜의 모든 이미지 찾기
    pattern = f"{date}_*"
    search_paths = [
        os.path.join(config.IMG_DIR, year_month, pattern),
        os.path.join(config.IMG_DIR, 'manual', pattern)
    ]
    
    times = set()
    for search_path in search_paths:
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            full_pattern = search_path.replace('*', ext)
            for img_path in glob.glob(full_pattern):
                filename = os.path.basename(img_path)
                # 파일명에서 시간 추출: YYYY-MM-DD_HH-MM-SS_Auto.jpg
                parts = filename.split('_')
                if len(parts) >= 2:
                    time_str = parts[1]  # HH-MM-SS
                    time_formatted = time_str.replace('-', ':')[:5]  # HH:MM
                    times.add(time_formatted)
    
    return jsonify({'times': sorted(list(times))})

@app.route('/api/image_file/<path:filename>')
def serve_image(filename):
    """이미지 파일 서빙"""
    if 'authenticated' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    from flask import send_from_directory
    # images 폴더에서 파일 찾기
    image_path = os.path.join(config.IMG_DIR, filename)
    if os.path.exists(image_path):
        # 파일이 있는 폴더와 파일명 분리
        dir_path = os.path.dirname(image_path)
        file_name = os.path.basename(image_path)
        return send_from_directory(dir_path, file_name)
    return jsonify({'error': 'Image not found'}), 404

@app.route('/api/discord/test', methods=['POST'])
def api_discord_test():
    """Discord 알림 테스트 엔드포인트"""
    if 'authenticated' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    message = data.get('message', '테스트 메시지입니다. 한글 인코딩 테스트: 🌿 스마트팜 알림 시스템')
    level = data.get('level', 'info')  # 'error', 'warning', 'info'
    
    # 레벨 검증
    if level not in ['error', 'warning', 'info']:
        level = 'info'
    
    try:
        success = discord_notifier.send_test_message(message)
        if success:
            return jsonify({
                'success': True,
                'message': 'Discord 알림이 성공적으로 전송되었습니다.',
                'level': level
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Discord 알림 전송에 실패했습니다. 웹훅 URL을 확인하세요.',
                'level': level
            }), 500
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Discord 테스트 알림 전송 중 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'오류 발생: {str(e)}',
            'level': level
        }), 500

@app.route('/api/actuator/toggle', methods=['POST'])
def api_actuator_toggle():
    """구동계 ON/OFF 토글 API (팬, LED, 밸브, 커튼)"""
    if 'authenticated' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    import logging
    logger = logging.getLogger(__name__)
    
    # 시스템 초기화 확인 및 시도
    if not sys_state or not ser_b_lock or not state_lock:
        if not init_serial_connection():
            return jsonify({
                'success': False, 
                'error': '시스템 초기화 실패. Board B가 연결되어 있는지 확인하세요.'
            }), 503
    
    # 시리얼 연결 확인 및 초기화 시도
    if not ser_b or not ser_b.is_open:
        if not init_serial_connection():
            return jsonify({
                'success': False, 
                'error': '시리얼 포트 연결 실패. Board B가 연결되어 있는지 확인하세요.'
            }), 503
    
    data = request.get_json() or {}
    actuator_type = data.get('type', '').lower()
    
    if not actuator_type:
        return jsonify({'success': False, 'error': '구동계 타입이 필요합니다'}), 400
    
    try:
        with state_lock:
            if actuator_type == 'fan':
                current_status = sys_state.get('fan_status', 'OFF')
                status_key = 'fan_status'
                if current_status == 'OFF':
                    cmd = 'FAN_ON'
                    new_status = 'ON'
                else:
                    cmd = 'FAN_OFF'
                    new_status = 'OFF'
            elif actuator_type == 'led_w':
                current_status = sys_state.get('led_w_status', 'OFF')
                status_key = 'led_w_status'
                if current_status == 'OFF':
                    cmd = 'LED_ON'  # 즉시 ON (페이드 없음, 수동 제어용)
                    new_status = 'ON'
                else:
                    cmd = 'LED_OFF'  # 즉시 OFF (페이드 없음, 수동 제어용)
                    new_status = 'OFF'
            elif actuator_type == 'led_p':
                current_status = sys_state.get('led_p_status', 'OFF')
                status_key = 'led_p_status'
                if current_status == 'OFF':
                    cmd = 'PURPLE_ON'  # 즉시 ON (페이드 없음, 수동 제어용)
                    new_status = 'ON'
                else:
                    cmd = 'PURPLE_OFF'  # 즉시 OFF (페이드 없음, 수동 제어용)
                    new_status = 'OFF'
            elif actuator_type == 'valve':
                current_status = sys_state.get('valve_status', 'OFF')
                status_key = 'valve_status'
                cmd = 'M1'  # 밸브 토글 명령
                new_status = 'ON' if current_status == 'OFF' else 'OFF'
            elif actuator_type == 'curtain':
                current_status = sys_state.get('curtain_status', 'CLOSED')
                status_key = 'curtain_status'
                if current_status == 'CLOSED':
                    cmd = f'CURTAIN_OPEN:{config.CURTAIN_STEPS_OPEN}'
                    new_status = 'OPEN'
                else:
                    cmd = f'CURTAIN_CLOSE:{config.CURTAIN_STEPS_CLOSE}'
                    new_status = 'CLOSED'
            else:
                return jsonify({'success': False, 'error': f'지원하지 않는 구동계 타입: {actuator_type}'}), 400
        
        # 시리얼 명령 전송 (send_cmd 함수 사용 - automation.py와 동일한 로직)
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[Web] 📤 {actuator_type} 명령 전송: {cmd}")
        
        # send_cmd 호출 전 상태 확인
        if not ser_b:
            logger.error(f"[Web] ❌ 시리얼 포트가 초기화되지 않았습니다.")
            return jsonify({
                'success': False,
                'error': '시리얼 포트가 초기화되지 않았습니다'
            }), 503
        
        if not ser_b.is_open:
            logger.error(f"[Web] ❌ 시리얼 포트가 열려있지 않습니다.")
            return jsonify({
                'success': False,
                'error': '시리얼 포트가 열려있지 않습니다'
            }), 503
        
        # send_cmd 함수 사용 (automation.py와 동일한 로직)
        success = send_cmd(ser_b, ser_b_lock, cmd, caller_info=f"[Web] {actuator_type}")
        
        if success:
            # 상태 업데이트 (시리얼 통신 성공 시에만)
            with state_lock:
                old_status = sys_state.get(status_key, 'UNKNOWN')
                sys_state[status_key] = new_status
                
                # 수동 제어 플래그 설정 (automation.py가 덮어쓰지 않도록)
                if actuator_type in ['led_w', 'led_p']:
                    # 수동 제어 후 5분 동안 자동 제어 무시 (1시간은 너무 김)
                    sys_state[f'{actuator_type}_manual_override'] = time.time() + 300
                    logger.info(f"[Web] ✅ {actuator_type} 수동 제어 플래그 설정 (5분간 자동 제어 무시)")
                
                logger.info(f"[Web] ✅ {actuator_type} 토글 성공: {cmd} → {new_status} (sys_state 업데이트: {old_status} → {new_status})")
            
            return jsonify({
                'success': True,
                'actuator_type': actuator_type,
                'status': new_status,
                'message': f'{actuator_type}가 {new_status}로 변경되었습니다.'
            })
        else:
            logger.error(f"[Web] ❌ {actuator_type} 토글 실패: {cmd} 전송 실패")
            
            return jsonify({
                'success': False,
                'error': '구동계 제어 명령 전송 실패'
            }), 500
            
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"구동계 토글 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'오류 발생: {str(e)}'
        }), 500

@app.route('/api/camera/capture', methods=['POST'])
def api_camera_capture():
    """수동 카메라 촬영 API"""
    if 'authenticated' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    global camera_thread
    
    # 카메라 스레드가 없거나 실행 중이 아니면 초기화 시도
    if not camera_thread or not camera_thread.is_alive():
        if not init_camera_thread():
            return jsonify({
                'success': False,
                'error': '카메라 스레드를 초기화할 수 없습니다. 카메라가 연결되어 있는지 확인하세요.'
            }), 503
    
    try:
        # 수동 촬영 트리거
        camera_thread.trigger_manual_capture()
        
        # 촬영 완료 대기 (최대 5초)
        max_wait = 5
        wait_interval = 0.5
        waited = 0
        
        while waited < max_wait:
            if not camera_thread.force_capture:  # 촬영 완료 (플래그가 False로 변경됨)
                break
            time.sleep(wait_interval)
            waited += wait_interval
        
        # 최신 이미지 찾기 (manual 폴더에서)
        import glob
        manual_dir = os.path.join(config.IMG_DIR, 'manual')
        if os.path.exists(manual_dir):
            pattern = os.path.join(manual_dir, '*.jpg')
            images = glob.glob(pattern)
            if images:
                # 가장 최근 이미지
                latest = max(images, key=os.path.getmtime)
                rel_path = os.path.relpath(latest, config.IMG_DIR)
                return jsonify({
                    'success': True,
                    'image_url': f'/api/image_file/{rel_path.replace(os.sep, "/")}',
                    'message': '촬영 완료'
                })
        
        return jsonify({
            'success': True,
            'message': '촬영 요청 완료 (이미지 확인 중...)'
        })
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"카메라 촬영 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'촬영 중 오류 발생: {str(e)}'
        }), 500

if __name__ == '__main__':
    # 로깅 설정 (독립 실행 시)
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('smartfarm.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("=" * 70)
    logger.info("웹 서버 독립 실행 모드")
    logger.info("=" * 70)
    
    # 독립 실행 시 시리얼 포트 및 카메라 스레드 초기화 시도
    logger.info("시리얼 포트 초기화 시도...")
    if init_serial_connection():
        logger.info(f"✅ 시리얼 포트 초기화 성공: ser_b={ser_b}, is_open={ser_b.is_open if ser_b else False}")
    else:
        logger.error("❌ 시리얼 포트 초기화 실패 - main.py가 실행 중이면 시리얼 포트 충돌 가능")
    
    logger.info("카메라 스레드 초기화 시도...")
    if init_camera_thread():
        logger.info("✅ 카메라 스레드 초기화 성공")
    else:
        logger.warning("⚠️ 카메라 스레드 초기화 실패")
    
    logger.info("웹 서버 시작...")
    # 개발 모드 (프로덕션에서는 gunicorn 등 사용)
    app.run(host='0.0.0.0', port=5000, debug=False)

