"""
SmartFarm 웹 대시보드 서버
"""
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from datetime import datetime, timedelta
import os
import secrets
from data_reader import DataReader
from analyzer import StatusAnalyzer
import config

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

# 간단한 인증 (환경변수 우선, 없으면 config에서 읽기)
# 실제 운영 시에는 더 강력한 인증 방식 사용 권장
WEB_USERNAME = os.getenv('WEB_USERNAME', config.WEB_USERNAME)
WEB_PASSWORD = os.getenv('WEB_PASSWORD', config.WEB_PASSWORD)

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
    
    if latest_image:
        # 이미지 파일명만 추출
        filename = os.path.basename(latest_image)
        # 월별 폴더 또는 manual 폴더 경로 추출
        rel_path = os.path.relpath(latest_image, config.IMG_DIR)
        return jsonify({
            'image_url': f'/api/image_file/{rel_path.replace(os.sep, "/")}',
            'timestamp': latest_time * 1000  # JavaScript용 밀리초
        })
    
    return jsonify({'image_url': None})

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

if __name__ == '__main__':
    # 개발 모드 (프로덕션에서는 gunicorn 등 사용)
    app.run(host='0.0.0.0', port=5000, debug=False)

