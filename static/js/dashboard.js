// SmartFarm 대시보드 JavaScript

// 전역 변수
let mainChart = null;
let currentData = [];
let selectedSeries = new Set();
let autoScale = true;
let manualYMin = null;
let manualYMax = null;
let timeFilterStart = null;
let timeFilterEnd = null;

// 사용 가능한 데이터 계열 정의 (기본적으로 모두 해제)
// 순서: 온도,습도 / 토양습도,조도 / VPD, DLI
const dataSeries = {
    'Temp_C': { label: '온도 (°C)', color: 'rgb(255, 99, 132)', enabled: false, group: 1 },
    'Hum_Pct': { label: '습도 (%)', color: 'rgb(54, 162, 235)', enabled: false, group: 1 },
    'Soil_Pct': { label: '토양습도 (%)', color: 'rgb(255, 206, 86)', enabled: false, group: 2 },
    'Lux': { label: '조도 (Lux)', color: 'rgb(75, 192, 192)', enabled: false, group: 2 },
    'VPD_kPa': { label: 'VPD (kPa)', color: 'rgb(153, 102, 255)', enabled: false, group: 3 },
    'DLI_mol': { label: 'DLI (mol/m²/day)', color: 'rgb(255, 159, 64)', enabled: false, group: 3 }
};

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 초기화는 동기적으로 실행
    try {
        // 먼저 업데이트 시간 표시 (즉시)
        updateLastUpdateTime();
        
        initializeDateInputs();
        initializeChart();
        initializeSeriesCheckboxes();
        initializeScaleControls();
        initializeTimeRangeControls();
        initializeHelpModal();
        initializeImageSection();
        
        // 데이터 로드는 비동기로 실행
        loadLatestData();
        loadAlerts();
        
        // 주기적 업데이트 (30초마다)
        setInterval(() => {
            loadLatestData();
            loadAlerts();
        }, 30000);
    } catch (error) {
        console.error('초기화 중 오류 발생:', error);
        // 최소한 업데이트 시간은 표시
        updateLastUpdateTime();
    }
});

// 날짜 입력 초기화
function initializeDateInputs() {
    const today = new Date();
    // 기본값: 오늘 날짜 (2026-01-02 기준)
    const defaultDate = new Date('2026-01-02');
    
    document.getElementById('end-date').value = formatDate(today);
    document.getElementById('start-date').value = formatDate(defaultDate);
    
    // 데이터 로드 버튼
    document.getElementById('load-data-btn').addEventListener('click', loadChartData);
    document.getElementById('reset-date-btn').addEventListener('click', () => {
        const defaultDate = new Date('2026-01-02');
        document.getElementById('end-date').value = formatDate(today);
        document.getElementById('start-date').value = formatDate(defaultDate);
        loadChartData();
    });
    
    // 초기 데이터 로드
    loadChartData();
}

// 날짜 포맷 (YYYY-MM-DD)
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// 차트 초기화
function initializeChart() {
    const ctx = document.getElementById('main-chart').getContext('2d');
    
    mainChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: '센서 데이터 시계열 그래프'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: '시간'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: '값'
                    },
                    beginAtZero: false
                }
            }
        }
    });
}

// 계열 체크박스 초기화
function initializeSeriesCheckboxes() {
    const container = document.getElementById('series-checkboxes');
    const applyBtn = document.getElementById('apply-series-btn');
    
    if (!container) {
        console.error('series-checkboxes 컨테이너를 찾을 수 없습니다.');
        return;
    }
    
    if (!applyBtn) {
        console.error('apply-series-btn 버튼을 찾을 수 없습니다.');
        return;
    }
    
    // 컨테이너 초기화
    container.innerHTML = '';
    
    // 모든 체크박스 생성
    Object.keys(dataSeries).forEach(key => {
        const series = dataSeries[key];
        const label = document.createElement('label');
        label.innerHTML = `
            <input type="checkbox" data-series="${key}" ${series.enabled ? 'checked' : ''}>
            <span>${series.label}</span>
        `;
        
        const checkbox = label.querySelector('input');
        checkbox.addEventListener('change', function() {
            // 체크박스 변경 시 즉시 업데이트하지 않음 (적용 버튼 대기)
        });
        
        if (series.enabled) {
            selectedSeries.add(key);
        }
        
        container.appendChild(label);
    });
    
    // 적용 버튼 이벤트
    applyBtn.addEventListener('click', function() {
        // 모든 체크박스 상태 확인하여 selectedSeries 업데이트
        selectedSeries.clear();
        container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            if (checkbox.checked) {
                selectedSeries.add(checkbox.getAttribute('data-series'));
            }
        });
        updateChart();
    });
}

// 시간 범위 컨트롤 초기화 (양쪽 조절 가능한 슬라이더)
function initializeTimeRangeControls() {
    const timeStartInput = document.getElementById('time-start');
    const timeEndInput = document.getElementById('time-end');
    const timeRangeStartSlider = document.getElementById('time-range-start');
    const timeRangeEndSlider = document.getElementById('time-range-end');
    const applyTimeBtn = document.getElementById('apply-time-btn');
    const sliderContainer = document.querySelector('.dual-range-container');
    
    if (!sliderContainer) {
        console.error('dual-range-container를 찾을 수 없습니다.');
        return;
    }
    
    if (!timeRangeStartSlider || !timeRangeEndSlider) {
        console.error('시간 범위 슬라이더를 찾을 수 없습니다.');
        return;
    }
    
    // 기존 툴팁 제거 (중복 방지)
    const existingTooltips = sliderContainer.querySelectorAll('.range-tooltip');
    existingTooltips.forEach(tooltip => tooltip.remove());
    
    // 노브 위쪽에 표시할 요소 생성
    const startTooltip = document.createElement('div');
    startTooltip.className = 'range-tooltip range-tooltip-start';
    startTooltip.textContent = '00:00';
    sliderContainer.appendChild(startTooltip);
    
    const endTooltip = document.createElement('div');
    endTooltip.className = 'range-tooltip range-tooltip-end';
    endTooltip.textContent = '23:59';
    sliderContainer.appendChild(endTooltip);
    
    // 데이터의 시작/끝 시간 표시 업데이트
    function updateDataRangeLabels() {
        if (!currentData || currentData.length === 0) return;
        
        const firstTime = new Date(currentData[0].Timestamp);
        const lastTime = new Date(currentData[currentData.length - 1].Timestamp);
        
        document.getElementById('time-range-min').textContent = firstTime.toTimeString().slice(0, 5);
        document.getElementById('time-range-max').textContent = lastTime.toTimeString().slice(0, 5);
    }
    
    // 시작 슬라이더 업데이트 함수
    function updateStartSlider() {
        if (!currentData || currentData.length === 0) {
            // 데이터가 없어도 툴팁은 표시
            if (startTooltip && timeRangeStartSlider) {
                const startValue = parseInt(timeRangeStartSlider.value) || 0;
                const percentage = (startValue / 100) * 100;
                startTooltip.textContent = `${Math.floor(percentage / 4.17)}:${String(Math.floor((percentage % 4.17) * 14.4)).padStart(2, '0')}`;
                updateTooltipPosition(startTooltip, timeRangeStartSlider);
            }
            return;
        }
        
        const startValue = parseInt(timeRangeStartSlider.value);
        const endValue = parseInt(timeRangeEndSlider.value);
        
        // 시작값이 종료값보다 크면 제한
        if (startValue >= endValue) {
            timeRangeStartSlider.value = Math.max(0, endValue - 1);
            return updateStartSlider();
        }
        
        const dataLength = currentData.length;
        const startIdx = Math.floor((startValue / 100) * dataLength);
        
        if (startIdx < dataLength) {
            const startTime = new Date(currentData[startIdx].Timestamp);
            const startTimeStr = startTime.toTimeString().slice(0, 5);
            
            // 시간 입력 필드 업데이트
            if (timeStartInput) {
                timeStartInput.value = startTimeStr;
            }
            
            // 노브 위쪽 툴팁 업데이트
            if (startTooltip) {
                startTooltip.textContent = startTimeStr;
                updateTooltipPosition(startTooltip, timeRangeStartSlider);
            }
        }
    }
    
    // 종료 슬라이더 업데이트 함수
    function updateEndSlider() {
        if (!currentData || currentData.length === 0) {
            // 데이터가 없어도 툴팁은 표시
            if (endTooltip && timeRangeEndSlider) {
                const endValue = parseInt(timeRangeEndSlider.value) || 100;
                const percentage = (endValue / 100) * 100;
                endTooltip.textContent = `${Math.floor(percentage / 4.17)}:${String(Math.floor((percentage % 4.17) * 14.4)).padStart(2, '0')}`;
                updateTooltipPosition(endTooltip, timeRangeEndSlider);
            }
            return;
        }
        
        const startValue = parseInt(timeRangeStartSlider.value);
        const endValue = parseInt(timeRangeEndSlider.value);
        
        // 종료값이 시작값보다 작으면 제한
        if (endValue <= startValue) {
            timeRangeEndSlider.value = Math.min(100, startValue + 1);
            return updateEndSlider();
        }
        
        const dataLength = currentData.length;
        const endIdx = Math.floor((endValue / 100) * dataLength);
        
        if (endIdx < dataLength) {
            const endTime = new Date(currentData[endIdx].Timestamp);
            const endTimeStr = endTime.toTimeString().slice(0, 5);
            
            // 시간 입력 필드 업데이트
            if (timeEndInput) {
                timeEndInput.value = endTimeStr;
            }
            
            // 노브 위쪽 툴팁 업데이트
            if (endTooltip) {
                endTooltip.textContent = endTimeStr;
                updateTooltipPosition(endTooltip, timeRangeEndSlider);
            }
        }
    }
    
    // 툴팁 위치 업데이트
    function updateTooltipPosition(tooltip, slider) {
        const sliderRect = slider.getBoundingClientRect();
        const containerRect = sliderContainer.getBoundingClientRect();
        const value = parseInt(slider.value);
        const min = parseInt(slider.min);
        const max = parseInt(slider.max);
        const percentage = ((value - min) / (max - min)) * 100;
        
        const tooltipLeft = (percentage / 100) * containerRect.width;
        tooltip.style.left = `${tooltipLeft}px`;
        tooltip.style.transform = 'translateX(-50%)';
    }
    
    // 슬라이더 이벤트 (각각 독립적으로 처리)
    if (timeRangeStartSlider && timeRangeEndSlider) {
        timeRangeStartSlider.addEventListener('input', updateStartSlider);
        timeRangeEndSlider.addEventListener('input', updateEndSlider);
        
        // 초기 툴팁 위치 설정
        setTimeout(() => {
            updateStartSlider();
            updateEndSlider();
        }, 100);
        
        // 슬라이더 크기 변경 시에도 툴팁 위치 업데이트
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                updateTooltipPosition(startTooltip, timeRangeStartSlider);
                updateTooltipPosition(endTooltip, timeRangeEndSlider);
            }, 100);
        });
    }
    
    // 시간 입력 이벤트
    timeStartInput.addEventListener('change', function() {
        // 시간 입력 시 슬라이더 업데이트는 하지 않음 (수동 입력은 적용 버튼 필요)
    });
    
    timeEndInput.addEventListener('change', function() {
        // 시간 입력 시 슬라이더 업데이트는 하지 않음 (수동 입력은 적용 버튼 필요)
    });
    
    // 적용 버튼
    applyTimeBtn.addEventListener('click', function() {
        const startTime = timeStartInput.value;
        const endTime = timeEndInput.value;
        
        // 데이터에서 해당 시간 찾아서 슬라이더 위치 업데이트
        if (currentData && currentData.length > 0) {
            const startTimeObj = new Date(`2000-01-01T${startTime}`);
            const endTimeObj = new Date(`2000-01-01T${endTime}`);
            
            let startIdx = 0;
            let endIdx = currentData.length - 1;
            
            currentData.forEach((row, idx) => {
                const rowTime = new Date(row.Timestamp);
                const rowTimeOnly = new Date(`2000-01-01T${rowTime.toTimeString().slice(0, 5)}`);
                
                if (rowTimeOnly <= startTimeObj) {
                    startIdx = idx;
                }
                if (rowTimeOnly <= endTimeObj) {
                    endIdx = idx;
                }
            });
            
            const dataLength = currentData.length;
            timeRangeStartSlider.value = Math.floor((startIdx / dataLength) * 100);
            timeRangeEndSlider.value = Math.floor((endIdx / dataLength) * 100);
            
            updateStartSlider();
            updateEndSlider();
        }
        
        timeFilterStart = startTime;
        timeFilterEnd = endTime;
        updateChart();
    });
    
    // 전역 함수로 내보내기 (loadChartData에서 호출)
    window.updateTimeRangeLabels = updateDataRangeLabels;
    window.updateTimeRangeSliders = function() {
        updateStartSlider();
        updateEndSlider();
    };
}

// Y축 범위 계산 (데이터 기반) - 전역 함수로 이동
function calculateYRange() {
    if (!currentData || currentData.length === 0) return { min: 0, max: 100 };
    
    let min = Infinity;
    let max = -Infinity;
    
    selectedSeries.forEach(key => {
        currentData.forEach(row => {
            const val = parseFloat(row[key] || 0);
            if (!isNaN(val)) {
                min = Math.min(min, val);
                max = Math.max(max, val);
            }
        });
    });
    
    if (min === Infinity) return { min: 0, max: 100 };
    
    // 여유 공간 추가
    const range = max - min;
    min = min - range * 0.1;
    max = max + range * 0.1;
    
    return { min, max };
}

// 슬라이더 범위 설정 - 전역 함수로 이동
function updateSliderRange() {
    const yMinSlider = document.getElementById('y-min-slider');
    const yMaxSlider = document.getElementById('y-max-slider');
    const yMinInput = document.getElementById('y-min');
    const yMaxInput = document.getElementById('y-max');
    
    if (!yMinSlider || !yMaxSlider || !yMinInput || !yMaxInput) return;
    
    const range = calculateYRange();
    yMinSlider.min = Math.floor(range.min);
    yMinSlider.max = Math.floor(range.max);
    yMaxSlider.min = Math.floor(range.min);
    yMaxSlider.max = Math.floor(range.max);
    yMinSlider.value = Math.floor(range.min);
    yMaxSlider.value = Math.floor(range.max);
    yMinInput.value = range.min.toFixed(1);
    yMaxInput.value = range.max.toFixed(1);
    document.getElementById('y-min-value').textContent = range.min.toFixed(1);
    document.getElementById('y-max-value').textContent = range.max.toFixed(1);
}

// 스케일 컨트롤 초기화
function initializeScaleControls() {
    const autoScaleCheckbox = document.getElementById('auto-scale');
    const manualInputs = document.getElementById('manual-scale-inputs');
    const yMinInput = document.getElementById('y-min');
    const yMaxInput = document.getElementById('y-max');
    const yMinSlider = document.getElementById('y-min-slider');
    const yMaxSlider = document.getElementById('y-max-slider');
    
    autoScaleCheckbox.addEventListener('change', function() {
        autoScale = this.checked;
        manualInputs.style.display = autoScale ? 'none' : 'block';
        if (!autoScale) {
            updateSliderRange();
        }
        updateChart();
    });
    
    // Y축 최소값 슬라이더
    yMinSlider.addEventListener('input', function() {
        const value = parseFloat(this.value);
        yMinInput.value = value.toFixed(1);
        document.getElementById('y-min-value').textContent = value.toFixed(1);
    });
    
    // Y축 최대값 슬라이더
    yMaxSlider.addEventListener('input', function() {
        const value = parseFloat(this.value);
        yMaxInput.value = value.toFixed(1);
        document.getElementById('y-max-value').textContent = value.toFixed(1);
    });
    
    // 입력 필드 변경
    yMinInput.addEventListener('change', function() {
        const value = parseFloat(this.value);
        if (!isNaN(value)) {
            yMinSlider.value = value;
            document.getElementById('y-min-value').textContent = value.toFixed(1);
        }
    });
    
    yMaxInput.addEventListener('change', function() {
        const value = parseFloat(this.value);
        if (!isNaN(value)) {
            yMaxSlider.value = value;
            document.getElementById('y-max-value').textContent = value.toFixed(1);
        }
    });
    
    // 적용 버튼
    document.getElementById('apply-scale-btn').addEventListener('click', function() {
        const yMin = parseFloat(yMinInput.value);
        const yMax = parseFloat(yMaxInput.value);
        
        if (!isNaN(yMin) && !isNaN(yMax) && yMin < yMax) {
            manualYMin = yMin;
            manualYMax = yMax;
            autoScale = false;
            autoScaleCheckbox.checked = false;
            manualInputs.style.display = 'block';
            updateChart();
        } else {
            alert('올바른 최소값과 최대값을 입력해주세요.');
        }
    });
    
    // 데이터 로드 시 슬라이더 범위 업데이트는 loadChartData 함수 내에서 처리
}

// 최신 데이터 로드
async function loadLatestData() {
    try {
        const response = await fetch('/api/latest');
        
        if (!response.ok) {
            if (response.status === 401) {
                // 인증 오류 - 로그인 페이지로 리다이렉트
                window.location.href = '/login';
                return;
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        if (result.data) {
            updateCurrentStatus(result.data);
        }
        
        // 성공 여부와 관계없이 업데이트 시간은 항상 표시
        updateLastUpdateTime();
    } catch (error) {
        console.error('최신 데이터 로드 실패:', error);
        // 에러가 발생해도 업데이트 시간은 표시
        updateLastUpdateTime();
    }
}

// 현재 상태 업데이트
function updateCurrentStatus(data) {
    // 센서값
    document.getElementById('temp-value').textContent = parseFloat(data.Temp_C || 0).toFixed(1);
    document.getElementById('hum-value').textContent = parseFloat(data.Hum_Pct || 0).toFixed(1);
    document.getElementById('soil-value').textContent = parseFloat(data.Soil_Pct || 0).toFixed(1);
    document.getElementById('lux-value').textContent = parseInt(data.Lux || 0).toLocaleString();
    document.getElementById('vpd-value').textContent = parseFloat(data.VPD_kPa || 0).toFixed(2);
    
    // DLI 표시 (목표 대비 진행률 포함)
    const dli = parseFloat(data.DLI_mol || 0);
    const targetDli = 12.0; // TARGET_DLI_MIN
    const dliProgress = (dli / targetDli) * 100;
    const dliDisplay = dli.toFixed(2) + ` (${dliProgress.toFixed(1)}%)`;
    document.getElementById('dli-value').textContent = dliDisplay;
    
    // 구동계 상태
    updateActuatorStatus('fan', data.Fan_Status || 'OFF');
    updateActuatorStatus('led-w', data.LED_W_Status || 'OFF');
    updateActuatorStatus('led-p', data.LED_P_Status || 'OFF');
    updateActuatorStatus('valve', data.Valve_Status || 'OFF');
    updateActuatorStatus('curtain', data.Curtain_Status || 'CLOSED');
    updateActuatorStatus('emergency', data.Emergency_Stop === 'True' || data.Emergency_Stop === true ? 'ON' : 'OFF');
}

// 구동계 상태 업데이트
function updateActuatorStatus(type, status) {
    const card = document.getElementById(`${type}-card`);
    const statusEl = document.getElementById(`${type}-status`);
    
    if (!card || !statusEl) return;
    
    // 상태 텍스트
    const statusText = status === 'ON' ? 'ON' : (status === 'OPEN' ? 'OPEN' : (status === 'CLOSED' ? 'CLOSED' : 'OFF'));
    statusEl.textContent = statusText;
    
    // 카드 스타일 업데이트
    card.classList.remove('active', 'off');
    if (status === 'ON' || status === 'OPEN') {
        card.classList.add('active');
    } else {
        card.classList.add('off');
    }
}

// 마지막 업데이트 시간
function updateLastUpdateTime() {
    try {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('ko-KR');
        const updateElement = document.getElementById('last-update');
        if (updateElement) {
            updateElement.textContent = `마지막 업데이트: ${timeStr}`;
        } else {
            console.warn('last-update 요소를 찾을 수 없습니다.');
        }
    } catch (error) {
        console.error('업데이트 시간 표시 실패:', error);
    }
}

// 차트 데이터 로드
async function loadChartData() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    if (!startDate || !endDate) {
        alert('시작 날짜와 종료 날짜를 선택해주세요.');
        return;
    }
    
    try {
        const response = await fetch(`/api/data?start_date=${startDate}&end_date=${endDate}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        if (result.data) {
            currentData = result.data;
            
            // 시간 범위 슬라이더 업데이트
            if (currentData && currentData.length > 0) {
                const timeRangeStartSlider = document.getElementById('time-range-start');
                const timeRangeEndSlider = document.getElementById('time-range-end');
                
                if (timeRangeStartSlider && timeRangeEndSlider) {
                    timeRangeStartSlider.value = 0;
                    timeRangeEndSlider.value = 100;
                }
                
                // 데이터 로드 후 시간 범위 라벨 및 슬라이더 업데이트
                if (typeof window.updateTimeRangeLabels === 'function') {
                    window.updateTimeRangeLabels();
                }
                if (typeof window.updateTimeRangeSliders === 'function') {
                    window.updateTimeRangeSliders();
                }
            }
            
            // Y축 슬라이더 범위 업데이트
            if (!autoScale) {
                updateSliderRange();
            }
            
            updateChart();
        }
    } catch (error) {
        console.error('차트 데이터 로드 실패:', error);
        console.error('오류 상세:', error.message, error.stack);
        alert(`데이터를 불러오는 중 오류가 발생했습니다.\n오류: ${error.message}\n\n브라우저 콘솔(F12)에서 자세한 정보를 확인하세요.`);
    }
}

// 차트 업데이트
function updateChart() {
    if (!currentData || currentData.length === 0) {
        return;
    }
    
    // 시간 필터 적용
    let filteredData = currentData;
    if (timeFilterStart && timeFilterEnd) {
        filteredData = currentData.filter(row => {
            const rowTime = new Date(row.Timestamp).toTimeString().slice(0, 5);
            return rowTime >= timeFilterStart && rowTime <= timeFilterEnd;
        });
    }
    
    if (filteredData.length === 0) {
        filteredData = currentData; // 필터 결과가 없으면 전체 데이터 사용
    }
    
    // 라벨 (타임스탬프)
    const labels = filteredData.map(row => {
        const date = new Date(row.Timestamp);
        return date.toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    });
    
    // 데이터셋 생성
    const datasets = [];
    
    selectedSeries.forEach(key => {
        const series = dataSeries[key];
        if (!series) return;
        
        const values = filteredData.map(row => {
            const val = parseFloat(row[key] || 0);
            return isNaN(val) ? null : val;
        });
        
        datasets.push({
            label: series.label,
            data: values,
            borderColor: series.color,
            backgroundColor: series.color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
            borderWidth: 2,
            fill: false,
            tension: 0.1,
            pointRadius: 0,  // 점 제거, 선만 표시
            pointHoverRadius: 4  // 호버 시에만 점 표시
        });
    });
    
    // 차트 업데이트
    mainChart.data.labels = labels;
    mainChart.data.datasets = datasets;
    
    // Y축 스케일 설정
    if (!autoScale && manualYMin !== null && manualYMax !== null) {
        mainChart.options.scales.y.min = manualYMin;
        mainChart.options.scales.y.max = manualYMax;
    } else {
        mainChart.options.scales.y.min = undefined;
        mainChart.options.scales.y.max = undefined;
    }
    
    mainChart.update();
}

// 알림 로드
async function loadAlerts() {
    try {
        const response = await fetch('/api/alerts');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.alerts) {
            displayAlerts(result.alerts);
        } else {
            // 알림이 없어도 빈 배열로 표시
            displayAlerts([]);
        }
    } catch (error) {
        console.error('경고 메시지 로드 실패:', error);
        // 에러 발생 시 빈 알림 표시 (정상 작동 메시지)
        displayAlerts([]);
    }
}

// 알림 표시
function displayAlerts(alerts) {
    const container = document.getElementById('alerts-container');
    
    if (alerts.length === 0) {
        container.innerHTML = `
            <div class="status-ok-card">
                <div class="status-icon">✅</div>
                <div class="status-title">모든 시스템 정상 작동 중</div>
                <div class="status-message">현재 이상 상태가 감지되지 않았습니다. 모든 센서와 구동계가 정상적으로 작동하고 있습니다.</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = alerts.map(alert => {
        const actionsHtml = alert.actions.map(action => `<li>${action}</li>`).join('');
        const caseCode = alert.case_code ? `<span class="help-case-code">${alert.case_code}</span>` : '';
        
        // DLI 정보가 있으면 추가 표시
        let dliInfoHtml = '';
        if (alert.dli_info) {
            const dliInfo = alert.dli_info;
            const progressBar = dliInfo.target_ratio ? `
                <div style="margin-top: 12px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 0.9em;">
                        <span>목표 달성률: ${dliInfo.target_ratio.toFixed(1)}%</span>
                        <span>${dliInfo.is_on_track ? '✅ 목표 달성 가능' : '⚠️ 목표 달성 어려움'}</span>
                    </div>
                    <div style="width: 100%; height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden;">
                        <div style="width: ${Math.min(dliInfo.target_ratio, 100)}%; height: 100%; background: ${dliInfo.is_on_track ? '#4caf50' : '#ff9800'}; transition: width 0.3s;"></div>
                    </div>
                    ${dliInfo.remaining_hours ? `<div style="margin-top: 4px; font-size: 0.85em; color: #666;">남은 활성 시간: ${dliInfo.remaining_hours}시간</div>` : ''}
                </div>
            ` : '';
            dliInfoHtml = progressBar;
        }
        
        return `
            <div class="alert-card ${alert.level}">
                <div class="alert-header">
                    <div class="alert-title">${alert.title}</div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        ${caseCode}
                        <div class="alert-id">#${alert.id}</div>
                    </div>
                </div>
                <div class="alert-message">${alert.message}</div>
                ${dliInfoHtml}
                <div class="alert-actions">
                    <h4>권장 조치사항:</h4>
                    <ul>${actionsHtml}</ul>
                </div>
            </div>
        `;
    }).join('');
}

// Help 모달 초기화
function initializeHelpModal() {
    const helpBtn = document.getElementById('help-btn');
    const modal = document.getElementById('help-modal');
    const closeBtn = document.querySelector('.modal-close');
    
    // Help 버튼 클릭
    helpBtn.addEventListener('click', function() {
        modal.style.display = 'block';
        loadHelpCases();
    });
    
    // 닫기 버튼
    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    // 모달 외부 클릭 시 닫기
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Help 케이스 목록 로드
function loadHelpCases() {
    const container = document.getElementById('help-cases-list');
    
    // 모든 경고 케이스 정의 (Discord 푸시용 케이스 코드 포함)
    const allCases = [
        {
            case_code: 'TEMP_CRITICAL_LOW',
            level: 'error',
            title: '냉해 위험',
            description: '온도가 5°C 미만으로 매우 낮습니다. 식물 냉해가 발생할 수 있습니다. 즉각 조치 필요.',
            push_priority: 'high'
        },
        {
            case_code: 'TEMP_LOW',
            level: 'warning',
            title: '저온 주의',
            description: '온도가 10°C 미만으로 낮습니다. 식물 성장에 불리할 수 있습니다.',
            push_priority: 'medium'
        },
        {
            case_code: 'TEMP_CRITICAL_HIGH',
            level: 'error',
            title: '고온 위험',
            description: '온도가 40°C 초과로 매우 높습니다. 화재 위험이 있거나 식물이 손상될 수 있습니다. 즉각 조치 필요.',
            push_priority: 'high'
        },
        {
            case_code: 'TEMP_HIGH',
            level: 'warning',
            title: '고온 주의',
            description: '온도가 35°C 초과로 높습니다. 식물 스트레스가 발생할 수 있습니다.',
            push_priority: 'medium'
        },
        {
            case_code: 'HUM_LOW',
            level: 'warning',
            title: '저습도 주의',
            description: '습도가 20% 미만으로 매우 낮습니다. 식물이 건조할 수 있습니다.',
            push_priority: 'medium'
        },
        {
            case_code: 'HUM_HIGH',
            level: 'warning',
            title: '고습도 주의',
            description: '습도가 95% 초과로 매우 높습니다. 곰팡이 발생 위험이 있습니다.',
            push_priority: 'medium'
        },
        {
            case_code: 'SOIL_CRITICAL_LOW',
            level: 'error',
            title: '토양 건조 위험',
            description: '토양습도가 10% 미만으로 매우 낮습니다. 식물이 시들 수 있습니다. 즉각 조치 필요.',
            push_priority: 'high'
        },
        {
            case_code: 'SOIL_LOW',
            level: 'warning',
            title: '토양 건조 주의',
            description: '토양습도가 설정값 미만으로 낮습니다. 물주기가 필요할 수 있습니다.',
            push_priority: 'medium'
        },
        {
            case_code: 'VPD_LOW',
            level: 'warning',
            title: 'VPD 과낮음',
            description: 'VPD가 0.3 kPa 미만으로 매우 낮습니다. 습도가 과도하게 높아 곰팡이 위험이 있습니다.',
            push_priority: 'medium'
        },
        {
            case_code: 'VPD_HIGH',
            level: 'warning',
            title: 'VPD 과높음',
            description: 'VPD가 2.5 kPa 초과로 매우 높습니다. 공기가 과도하게 건조합니다.',
            push_priority: 'medium'
        },
        {
            case_code: 'DLI_LOW',
            level: 'warning',
            title: '일조량 부족',
            description: 'DLI가 목표치의 절반 미만입니다. 식물 성장이 저하될 수 있습니다.',
            push_priority: 'low'
        },
        {
            case_code: 'EMERGENCY_STOP',
            level: 'error',
            title: '비상 정지 활성화',
            description: '시스템이 비상 정지 상태입니다. 모든 구동계가 중단되었습니다. 즉각 조치 필요.',
            push_priority: 'high'
        },
        {
            case_code: 'SENSOR_ANOMALY_*',
            level: 'warning',
            title: '센서 이상 의심',
            description: '센서 값이 거의 변화하지 않습니다. 센서 고장 또는 연결 문제가 의심됩니다.',
            push_priority: 'medium'
        }
    ];
    
    container.innerHTML = allCases.map(caseItem => {
        const priorityBadge = caseItem.push_priority === 'high' ? 
            '<span style="background: #f44336; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 8px;">즉각 조치</span>' :
            caseItem.push_priority === 'medium' ?
            '<span style="background: #ff9800; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 8px;">주의</span>' :
            '<span style="background: #2196f3; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 8px;">정보</span>';
        
        return `
            <div class="help-case-item ${caseItem.level}">
                <div class="help-case-header">
                    <div class="help-case-title">${caseItem.title}${priorityBadge}</div>
                    <div class="help-case-code">${caseItem.case_code}</div>
                </div>
                <div class="help-case-description">${caseItem.description}</div>
            </div>
        `;
    }).join('');
}

// 이미지 섹션 초기화
function initializeImageSection() {
    const imageDateInput = document.getElementById('image-date');
    const imageTimeSelect = document.getElementById('image-time');
    const loadImageBtn = document.getElementById('load-image-btn');
    const currentImage = document.getElementById('current-image');
    const imagePlaceholder = document.getElementById('image-placeholder');
    
    // 오늘 날짜를 기본값으로 설정
    const today = new Date();
    imageDateInput.value = today.toISOString().split('T')[0];
    
    // 최신 사진 로드
    loadLatestImage();
    
    // 날짜 변경 시 시간 목록 업데이트
    imageDateInput.addEventListener('change', async function() {
        await updateImageTimeList(this.value);
    });
    
    // 사진 로드 버튼
    loadImageBtn.addEventListener('click', async function() {
        const date = imageDateInput.value;
        const time = imageTimeSelect.value;
        await loadImage(date, time);
    });
    
    // 최신 사진 로드 함수
    async function loadLatestImage() {
        try {
            const response = await fetch('/api/latest_image');
            const result = await response.json();
            if (result.image_url) {
                currentImage.src = result.image_url;
                currentImage.style.display = 'block';
                imagePlaceholder.style.display = 'none';
                
                // 날짜와 시간 입력 필드 업데이트
                const timestamp = result.timestamp;
                if (timestamp) {
                    const date = new Date(timestamp);
                    imageDateInput.value = date.toISOString().split('T')[0];
                    await updateImageTimeList(imageDateInput.value);
                    // 해당 시간 선택
                    const timeStr = date.toTimeString().slice(0, 5);
                    imageTimeSelect.value = timeStr;
                }
            } else {
                imagePlaceholder.textContent = '사진이 없습니다';
                currentImage.style.display = 'none';
                imagePlaceholder.style.display = 'block';
            }
        } catch (error) {
            console.error('최신 사진 로드 실패:', error);
            imagePlaceholder.textContent = '사진을 불러올 수 없습니다';
        }
    }
    
    // 특정 날짜/시간의 사진 로드
    async function loadImage(date, time) {
        try {
            const url = time ? `/api/image?date=${date}&time=${time}` : `/api/image?date=${date}`;
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.image_url) {
                currentImage.src = result.image_url;
                currentImage.style.display = 'block';
                imagePlaceholder.style.display = 'none';
            } else {
                imagePlaceholder.textContent = '해당 시간의 사진이 없습니다';
                currentImage.style.display = 'none';
                imagePlaceholder.style.display = 'block';
            }
        } catch (error) {
            console.error('사진 로드 실패:', error);
            imagePlaceholder.textContent = '사진을 불러올 수 없습니다';
        }
    }
    
    // 특정 날짜의 사용 가능한 시간 목록 업데이트
    async function updateImageTimeList(date) {
        try {
            const response = await fetch(`/api/image_times?date=${date}`);
            const result = await response.json();
            
            imageTimeSelect.innerHTML = '<option value="">최신 사진</option>';
            if (result.times && result.times.length > 0) {
                result.times.forEach(time => {
                    const option = document.createElement('option');
                    option.value = time;
                    option.textContent = time;
                    imageTimeSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('시간 목록 로드 실패:', error);
        }
    }
}


