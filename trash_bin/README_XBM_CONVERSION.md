# PNG를 Arduino XBM 비트맵으로 변환하기

## 📋 준비사항

1. **Python PIL (Pillow) 설치**:
```bash
pip3 install Pillow
```

2. **PNG 파일 준비**:
   - 딸기 이미지: `strawberry.png` (권장 크기: 64x64 픽셀)
   - 상추 이미지: `lettuce.png` (권장 크기: 64x64 픽셀)
   - `images/` 폴더에 저장

## 🔄 변환 방법

### 방법 1: 자동 변환 (권장)

```bash
cd ~/smartfarm/images

# 딸기 변환 (64x64)
python3 ../convert_png_to_xbm.py strawberry.png strawberry.h strawberry_bitmap 64 64

# 상추 변환 (64x64)
python3 ../convert_png_to_xbm.py lettuce.png lettuce.h lettuce_bitmap 64 64
```

### 방법 2: 크기 자동 조정

```bash
# 원본 크기 유지
python3 ../convert_png_to_xbm.py strawberry.png strawberry.h strawberry_bitmap
```

## 📝 생성된 파일

변환 후 다음 파일이 생성됩니다:
- `strawberry.h` - 딸기 비트맵 배열
- `lettuce.h` - 상추 비트맵 배열

## 🔧 아두이노 코드에 포함

1. 생성된 `.h` 파일을 `board_a/` 폴더로 복사:
```bash
cp images/strawberry.h board_a/
cp images/lettuce.h board_a/
```

2. `board_a.ino`에 include 추가:
```cpp
#include "strawberry.h"
#include "lettuce.h"
```

3. 화면보호기 함수 수정:
```cpp
void drawStrawberry(int offsetX, int offsetY) {
  u8g2.drawXBM(0 + offsetX, 0 + offsetY, 64, 64, strawberry_bitmap);
}

void drawLettuce(int offsetX, int offsetY) {
  u8g2.drawXBM(64 + offsetX, 0 + offsetY, 64, 64, lettuce_bitmap);
}
```

## ⚠️ 주의사항

- 이미지는 **흑백**으로 변환됩니다 (임계값: 128)
- 어두운 부분(128 미만)이 OLED에서 **켜짐** (1)
- 밝은 부분(128 이상)이 OLED에서 **꺼짐** (0)
- 메모리 제한: Arduino Uno는 약 2KB SRAM이므로 큰 이미지는 주의

## 🎨 이미지 최적화 팁

1. **크기**: 64x64 픽셀 권장 (각각 절반 화면)
2. **대비**: 명확한 흑백 대비가 좋음
3. **단순화**: 복잡한 디테일보다 단순한 실루엣이 잘 보임

