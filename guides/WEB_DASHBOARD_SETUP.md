# SmartFarm 웹 대시보드 설정 가이드

## 📋 개요

SmartFarm 시스템의 로그 데이터를 시각화하고 모니터링할 수 있는 웹 대시보드를 제공합니다.

## 🔧 필수 패키지 설치

```bash
cd /home/pi/smartfarm
python3 -m pip install flask flask-cors
```

## 🚀 웹 서버 실행

### 개발 모드 (테스트용)

```bash
cd /home/pi/smartfarm
python3 web_server.py
```

서버가 `http://0.0.0.0:5000`에서 실행됩니다.

### 프로덕션 모드 (systemd 서비스)

1. **서비스 파일 생성**

```bash
sudo nano /etc/systemd/system/smartfarm-web.service
```

다음 내용 추가:

```ini
[Unit]
Description=SmartFarm Web Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/smartfarm
ExecStart=/usr/bin/python3 /home/pi/smartfarm/web_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. **서비스 활성화 및 시작**

```bash
sudo systemctl daemon-reload
sudo systemctl enable smartfarm-web.service
sudo systemctl start smartfarm-web.service
```

3. **서비스 상태 확인**

```bash
sudo systemctl status smartfarm-web.service
```

## 🌐 접속 방법

### 로컬 네트워크 내 접속

1. **Raspberry Pi의 IP 주소 확인**

```bash
hostname -I
```

예: `192.168.1.100`

2. **웹 브라우저에서 접속**

```
http://192.168.1.100:5000
```

### 외부 네트워크에서 접속 (포트 포워딩)

#### 방법 1: 라우터 포트 포워딩 설정

1. **라우터 관리 페이지 접속** (보통 `192.168.1.1`)

2. **포트 포워딩 설정**
   - 외부 포트: `8080` (또는 원하는 포트)
   - 내부 IP: Raspberry Pi IP (예: `192.168.1.100`)
   - 내부 포트: `5000`
   - 프로토콜: TCP

3. **외부에서 접속**

```
http://[공인IP]:8080
```

공인 IP 확인:
```bash
curl ifconfig.me
```

#### 방법 2: SSH 터널링 (보안 권장)

SSH 터널을 통해 안전하게 접속:

```bash
ssh -L 5000:localhost:5000 pi@[RaspberryPi_IP]
```

그 후 로컬 브라우저에서:
```
http://localhost:5000
```

## 🔐 보안 설정

### 기본 인증

기본 사용자명과 비밀번호는 환경변수로 설정할 수 있습니다:

```bash
export WEB_USERNAME=your_username
export WEB_PASSWORD=your_secure_password
python3 web_server.py
```

또는 systemd 서비스 파일에 추가:

```ini
[Service]
Environment="WEB_USERNAME=your_username"
Environment="WEB_PASSWORD=your_secure_password"
```

### HTTPS 설정 (nginx reverse proxy)

1. **nginx 설치**

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

2. **nginx 설정 파일 생성**

```bash
sudo nano /etc/nginx/sites-available/smartfarm
```

다음 내용 추가:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 또는 IP 주소

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **설정 활성화**

```bash
sudo ln -s /etc/nginx/sites-available/smartfarm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

4. **SSL 인증서 발급 (Let's Encrypt)**

```bash
sudo certbot --nginx -d your-domain.com
```

이제 `https://your-domain.com`으로 접속 가능합니다.

## 📱 모바일 접속

웹 대시보드는 반응형 디자인으로 구현되어 있어 모바일 브라우저에서도 정상 작동합니다.

- **안드로이드**: Chrome, Firefox 등
- **iOS**: Safari, Chrome 등

## 🔍 기능 설명

### 1. 현재 상태
- 실시간 센서값 표시 (온도, 습도, 토양습도, 조도, VPD, DLI)

### 2. 데이터 시각화
- 날짜 범위 선택 (동적 막대 바)
- 계열 선택 (체크박스로 표시/숨김)
- Y축 스케일 자동/수동 조정

### 3. 상태 분석 및 권장 사항
- 이상 상태 자동 감지
- 각 상황별 일련번호 부여
- 권장 조치사항 제시

## 🗄️ 데이터베이스 전환 (향후)

현재는 CSV 파일을 읽지만, 향후 MariaDB로 전환할 수 있도록 `data_reader.py`에 추상화 레이어가 구현되어 있습니다.

MariaDB 전환 시:
1. `data_reader.py`의 `MariaDBReader` 클래스 구현
2. `web_server.py`에서 `DataReader()` 대신 `MariaDBReader(connection_string)` 사용

## 🐛 문제 해결

### 포트가 이미 사용 중인 경우

```bash
# 포트 사용 중인 프로세스 확인
sudo lsof -i :5000

# 프로세스 종료
sudo kill -9 [PID]
```

### 방화벽 설정

```bash
# UFW 방화벽 포트 열기
sudo ufw allow 5000/tcp
```

### 로그 확인

```bash
# systemd 서비스 로그
sudo journalctl -u smartfarm-web.service -f
```

## 📝 참고사항

- 웹 서버는 로그 파일만 읽으며, 시스템 제어는 하지 않습니다.
- 기본 비밀번호는 `smartfarm2026`입니다. 반드시 변경하세요.
- 외부 접속 시 HTTPS 사용을 강력히 권장합니다.

