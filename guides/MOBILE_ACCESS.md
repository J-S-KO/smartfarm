# 📱 모바일 접속 가이드

## 핸드폰에서 SmartFarm 대시보드 접속하기

### 방법 1: 같은 Wi-Fi 네트워크 (가장 간단)

1. **Raspberry Pi의 IP 주소 확인**
   ```bash
   hostname -I
   ```
   예: `192.168.1.100`

2. **핸드폰이 같은 Wi-Fi에 연결되어 있는지 확인**

3. **핸드폰 브라우저에서 접속**
   ```
   http://192.168.0.11:5000
   ```
   또는
   ```
   http://[RaspberryPi_IP]:5000
   ```

### 방법 2: 외부 네트워크 (집 밖에서 접속)

#### 2-1. 라우터 포트 포워딩 설정

1. **라우터 관리 페이지 접속**
   - 보통 `192.168.1.1` 또는 `192.168.0.1`
   - 라우터 설정 페이지에서 "포트 포워딩" 또는 "Port Forwarding" 메뉴 찾기

2. **포트 포워딩 규칙 추가**
   - **외부 포트**: `8080` (또는 원하는 포트)
   - **내부 IP**: Raspberry Pi IP (예: `192.168.1.100`)
   - **내부 포트**: `5000`
   - **프로토콜**: TCP

3. **공인 IP 확인**
   ```bash
   curl ifconfig.me
   ```
   또는 웹에서 "내 IP 주소" 검색

4. **핸드폰에서 접속**
   ```
   http://[공인IP]:8080
   ```
   예: `http://112.181.243.15:8080`

#### 2-2. 동적 DNS 사용 (IP가 자주 바뀌는 경우)

1. **DDNS 서비스 가입** (예: DuckDNS, No-IP)
2. **도메인 설정** (예: `mysmartfarm.duckdns.org`)
3. **라우터에 DDNS 설정 추가**
4. **핸드폰에서 접속**
   ```
   http://mysmartfarm.duckdns.org:8080
   ```

### 방법 3: SSH 터널링 (가장 안전)

1. **SSH 클라이언트 앱 설치** (Android: JuiceSSH, iOS: Termius)

2. **SSH 터널 설정**
   - 호스트: Raspberry Pi IP
   - 포트: 22
   - 사용자: pi
   - 로컬 포트 포워딩: `5000:localhost:5000`

3. **터널 연결 후 핸드폰 브라우저에서**
   ```
   http://localhost:5000
   ```

## 🔒 보안 주의사항

### 기본 인증
- 기본 비밀번호는 `smartfarm2026`입니다
- 반드시 변경하세요:
  ```bash
  export WEB_PASSWORD=your_secure_password
  python3 web_server.py
  ```

### HTTPS 사용 권장
외부 접속 시 HTTPS 사용을 강력히 권장합니다. 자세한 설정은 `WEB_DASHBOARD_SETUP.md` 참고.

## 🐛 문제 해결

### "연결할 수 없음" 오류

1. **방화벽 확인**
   ```bash
   sudo ufw allow 5000/tcp
   ```

2. **웹서버 실행 확인**
   ```bash
   ps aux | grep web_server
   ```

3. **포트 사용 확인**
   ```bash
   sudo netstat -tlnp | grep 5000
   ```

### 같은 Wi-Fi인데 접속 안 됨

1. **Raspberry Pi와 핸드폰이 같은 네트워크인지 확인**
2. **Raspberry Pi IP 주소 재확인**
3. **라우터의 AP 격리 설정 확인** (일부 라우터는 기기 간 통신을 차단)

## 📱 현재 접속 정보

**로컬 네트워크:**
```
http://[RaspberryPi_IP]:5000
```

**현재 Raspberry Pi IP:** 확인 필요 (`hostname -I`)

**기본 로그인:**
- 사용자명: `admin`
- 비밀번호: `smartfarm2026` (변경 권장)

