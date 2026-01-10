// SmartFarm 대시보드 JavaScript

// 전역 변수
let mainChart = null;
let currentData = [];
let compareData = { day1: [], day2: [], day3: [] }; // 일별 비교 데이터 (최근 3일)
let selectedSeries = new Set(); // 기본 활성화는 아래에서 설정
let autoScale = true;
let manualYMin = null;
let manualYMax = null;
let latestDate = null; // 최신 날짜
let compareMode = false; // 일별 비교 모드

// 사용 가능한 데이터 계열 정의 (모두 기본 활성화)
// 순서: 온도,습도 / 토양습도,조도 / VPD, DLI
const dataSeries = {
    'Temp_C': { label: '온도 (°C)', color: 'rgb(255, 99, 132)', group: 1 },
    'Hum_Pct': { label: '습도 (%)', color: 'rgb(54, 162, 235)', group: 1 },
    'Soil_Pct': { label: '토양습도 (%)', color: 'rgb(255, 206, 86)', group: 2 },
    'Lux': { label: '조도 (Lux)', color: 'rgb(75, 192, 192)', group: 2 },
    'VPD_kPa': { label: 'VPD (kPa)', color: 'rgb(153, 102, 255)', group: 3 },
    'DLI_mol': { label: 'DLI (mol/m²/day)', color: 'rgb(255, 159, 64)', group: 3 }
};

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 초기화는 동기적으로 실행
    try {
        // 먼저 업데이트 시간 표시 (즉시)
        updateLastUpdateTime();
        
        initializeChart();
        initializeDateControls();
        initializeHelpModal();
        initializeImageSection();
        initializeActuatorControls();
        
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

// 날짜 컨트롤 초기화
async function initializeDateControls() {
    // 최신 날짜 가져오기
    try {
        const response = await fetch('/api/dates');
        if (response.ok) {
            const result = await response.json();
            if (result.dates && result.dates.length > 0) {
                latestDate = result.dates[result.dates.length - 1]; // 가장 최신 날짜
            }
        }
    } catch (error) {
        console.error('최신 날짜 로드 실패:', error);
    }
    
    // 최근 시간 버튼 이벤트
    document.querySelectorAll('.btn-time[data-hours]').forEach(btn => {
        btn.addEventListener('click', function() {
            const hours = parseInt(this.getAttribute('data-hours'));
            loadRecentData(hours);
        });
    });
    
    // 최근 3일 버튼 이벤트
    const btn3Days = document.getElementById('btn-3days');
    if (btn3Days) {
        btn3Days.addEventListener('click', function() {
            loadRecent3Days();
        });
    }
    
    // 기본으로 최근 1시간 로드
    loadRecentData(1);
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
            aspectRatio: undefined,  // aspectRatio 비활성화하여 컨테이너 높이에 맞춤
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: {
                            size: 14,
                            weight: 'bold'
                        },
                        padding: 15,
                        usePointStyle: true,
                        pointStyle: 'line',
                        filter: function(legendItem, chartData) {
                            // 범례 중복 제거: 같은 라벨은 첫 번째만 표시 (비교 모드가 아닐 때만)
                            if (!compareMode) {
                                const label = legendItem.text;
                                const datasets = chartData.datasets;
                                const firstIndex = datasets.findIndex(d => d.label === label);
                                return legendItem.datasetIndex === firstIndex;
                            }
                            // 비교 모드에서는 모든 데이터셋 표시 (점 스타일로 구분)
                            return true;
                        }
                    },
                    onClick: function(e, legendItem) {
                        const chart = this.chart;
                        
                        // 전체 선택/해제 버튼 처리
                        if (legendItem.isButton) {
                            const datasets = chart.data.datasets;
                            
                            if (legendItem.buttonType === 'selectAll') {
                                // 전체 선택: 모든 데이터셋 표시
                                datasets.forEach((dataset, index) => {
                                    const meta = chart.getDatasetMeta(index);
                                    meta.hidden = false;
                                });
                            } else if (legendItem.buttonType === 'deselectAll') {
                                // 전체 해제: 모든 데이터셋 숨김
                                datasets.forEach((dataset, index) => {
                                    const meta = chart.getDatasetMeta(index);
                                    meta.hidden = true;
                                });
                            }
                            chart.update();
                            return;
                        }
                        
                        // 일반 범례 클릭: 해당 시리즈의 모든 날짜 데이터셋 표시/숨김 토글
                        const clickedLabel = legendItem.text;
                        const datasets = chart.data.datasets;
                        
                        // 같은 라벨을 가진 모든 데이터셋 찾기
                        const indicesToToggle = [];
                        datasets.forEach((dataset, index) => {
                            if (dataset.label === clickedLabel) {
                                indicesToToggle.push(index);
                            }
                        });
                        
                        if (indicesToToggle.length === 0) return;
                        
                        // 첫 번째 데이터셋의 현재 상태 확인
                        const firstIndex = indicesToToggle[0];
                        const firstMeta = chart.getDatasetMeta(firstIndex);
                        const shouldHide = firstMeta.hidden === null ? false : !firstMeta.hidden;
                        
                        // 모든 같은 라벨의 데이터셋을 동시에 토글
                        indicesToToggle.forEach(index => {
                            const meta = chart.getDatasetMeta(index);
                            meta.hidden = shouldHide;
                        });
                        
                        chart.update();
                    },
                    // 전체 선택/해제 버튼을 위한 커스텀 범례 생성
                    generateLabels: function(chart) {
                        const original = Chart.defaults.plugins.legend.labels.generateLabels;
                        const labels = original.call(this, chart);
                        
                        // 전체 선택/해제 버튼 추가
                        labels.unshift({
                            text: '전체 선택',
                            fillStyle: 'transparent',
                            strokeStyle: 'transparent',
                            lineWidth: 0,
                            hidden: false,
                            datasetIndex: -1,  // 특수 인덱스
                            isButton: true,
                            buttonType: 'selectAll'
                        });
                        labels.push({
                            text: '전체 해제',
                            fillStyle: 'transparent',
                            strokeStyle: 'transparent',
                            lineWidth: 0,
                            hidden: false,
                            datasetIndex: -2,  // 특수 인덱스
                            isButton: true,
                            buttonType: 'deselectAll'
                        });
                        
                        return labels;
                    }
                },
                title: {
                    display: true,
                    text: '센서 데이터 시계열 그래프'
                },
                tooltip: {
                    enabled: false  // 툴팁 비활성화
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

// 기본적으로 VPD만 활성화, 나머지는 비활성화 (범례에는 모두 표시)
    Object.keys(dataSeries).forEach(key => {
        if (key === 'VPD_kPa') {  // VPD만 기본 활성화
            selectedSeries.add(key);
        }
        // 나머지는 기본 비활성화 (범례에는 표시되지만 숨김)
    });

// 데이터 샘플링 함수 (성능 최적화)
function sampleData(data, intervalMinutes) {
    if (!data || data.length === 0) return data;
    
    // 간격이 0이면 샘플링 안 함
    if (intervalMinutes <= 0) return data;
    
    const sampled = [];
    let lastSampledTime = null;
    
    data.forEach(row => {
        const rowTime = new Date(row.Timestamp);
        
        if (lastSampledTime === null) {
            // 첫 번째 데이터는 항상 포함
            sampled.push(row);
            lastSampledTime = rowTime;
        } else {
            // 마지막 샘플링 시간으로부터 지정된 간격이 지났는지 확인
            const minutesDiff = (rowTime - lastSampledTime) / (1000 * 60);
            if (minutesDiff >= intervalMinutes) {
                sampled.push(row);
                lastSampledTime = rowTime;
            }
        }
    });
    
    // 마지막 데이터는 항상 포함
    if (sampled.length > 0 && data.length > 0) {
        const lastOriginal = data[data.length - 1];
        const lastSampled = sampled[sampled.length - 1];
        if (lastOriginal.Timestamp !== lastSampled.Timestamp) {
            sampled.push(lastOriginal);
        }
    }
    
    return sampled;
}

// 로딩 인디케이터 표시/숨김
function showLoadingIndicator() {
    const indicator = document.getElementById('loading-indicator');
    if (indicator) {
        indicator.style.display = 'block';
    }
}

function hideLoadingIndicator() {
    const indicator = document.getElementById('loading-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

// 최근 데이터 로드 (시간 기준) - 현재 시각 기준으로 과거 N시간
async function loadRecentData(hours) {
    // 로딩 표시
    showLoadingIndicator();
    
    // 현재 시각 기준으로 계산
    const now = new Date();
    const startTime = new Date(now.getTime() - hours * 60 * 60 * 1000);
    
    // 날짜 범위 계산 (여러 날짜에 걸칠 수 있음)
    const startDateStr = formatDate(startTime);
    const endDateStr = formatDate(now);
    
    try {
        const response = await fetch(`/api/data?start_date=${startDateStr}&end_date=${endDateStr}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        if (result.data && result.data.length > 0) {
            // 시간 필터링 (현재 시각 기준 과거 N시간)
            let filteredData = result.data.filter(row => {
                const rowTime = new Date(row.Timestamp);
                return rowTime >= startTime && rowTime <= now;
            }).sort((a, b) => new Date(a.Timestamp) - new Date(b.Timestamp));
            
            // 중복 제거 (여러 날짜 데이터 처리)
            const seen = new Set();
            filteredData = filteredData.filter(row => {
                const key = row.Timestamp;
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
            
            // 데이터 샘플링 (성능 최적화)
            // 1시간, 3시간: 전체 데이터 (raw)
            // 6시간, 12시간: 1분 간격
            // 24시간: 5분 간격
            let sampleInterval = 0;
            if (hours === 6 || hours === 12) {
                sampleInterval = 1;  // 1분 간격
            } else if (hours === 24) {
                sampleInterval = 5;  // 5분 간격
            }
            
            if (sampleInterval > 0) {
                currentData = sampleData(filteredData, sampleInterval);
            } else {
                currentData = filteredData;
            }
            
            // 일반 모드로 설정
            compareMode = false;
            
            // 비교 모드 시리즈 선택 영역 숨김
            const selector = document.getElementById('compare-series-selector');
            if (selector) {
                selector.style.display = 'none';
            }
            
            updateChart();
        } else {
            alert('해당 시간 범위에 데이터가 없습니다.');
        }
    } catch (error) {
        console.error('데이터 로드 실패:', error);
        alert(`데이터를 불러오는 중 오류가 발생했습니다.\n오류: ${error.message}`);
    } finally {
        // 로딩 숨김
        hideLoadingIndicator();
    }
}

// 최근 3일 데이터 로드 (같은 시간대에 겹쳐서 표시)
async function loadRecent3Days() {
    // 로딩 표시
    showLoadingIndicator();
    
    const today = new Date();
    today.setHours(0, 0, 0, 0); // 오늘 00:00:00
    
    const day3 = new Date(today);
    day3.setDate(day3.getDate() - 2); // 3일 전 00:00:00
    
    const day2 = new Date(today);
    day2.setDate(day2.getDate() - 1); // 어제 00:00:00
    
    const dates = [
        { key: 'day3', date: formatDate(day3), label: 'D-2' },
        { key: 'day2', date: formatDate(day2), label: 'D-1' },
        { key: 'day1', date: formatDate(today), label: '오늘' }
    ];
    
    // 각 날짜의 00:00~23:59 데이터 로드
    compareData = { day1: [], day2: [], day3: [] };
    
    try {
        for (const { key, date } of dates) {
            const response = await fetch(`/api/data?start_date=${date}&end_date=${date}`);
            if (response.ok) {
                const result = await response.json();
                if (result.data) {
                    // 해당 날짜의 전체 데이터 (00:00~23:59)
                    let dayData = result.data
                        .filter(row => {
                            const rowDate = new Date(row.Timestamp);
                            const rowDateStr = formatDate(rowDate);
                            return rowDateStr === date;
                        })
                        .sort((a, b) => new Date(a.Timestamp) - new Date(b.Timestamp));
                    
                    // 3일 데이터는 10분 간격으로 샘플링 (성능 최적화)
                    dayData = sampleData(dayData, 10);
                    
                    compareData[key] = dayData.map(row => ({
                        ...row,
                        timeOnly: new Date(row.Timestamp).toTimeString().slice(0, 5) // HH:MM
                    }));
                }
            }
        }
        
        // 일별 비교 모드로 설정
        compareMode = true;
        
        // 비교 모드 시리즈 선택 영역 표시
        const selector = document.getElementById('compare-series-selector');
        if (selector) {
            selector.style.display = 'block';
        }
        
        // 시리즈 선택 버튼 이벤트 (한 번만 추가)
        document.querySelectorAll('.btn-series').forEach(btn => {
            // 기존 이벤트 리스너 제거 후 추가 (중복 방지)
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);
            
            newBtn.addEventListener('click', function() {
                const seriesKey = this.getAttribute('data-series');
                
                // 선택된 버튼 스타일 업데이트
                document.querySelectorAll('.btn-series').forEach(b => {
                    b.classList.remove('active');
                });
                this.classList.add('active');
                
                // 선택된 시리즈만 활성화
                selectedSeries.clear();
                selectedSeries.add(seriesKey);
                
                // 차트 업데이트
                updateChart();
            });
        });
        
        // 기본으로 VPD 선택
        const vpdBtn = document.querySelector('.btn-series[data-series="VPD_kPa"]');
        if (vpdBtn) {
            vpdBtn.click();
        } else {
            // 버튼이 없으면 직접 설정
            selectedSeries.clear();
            selectedSeries.add('VPD_kPa');
            updateChart();
        }
    } catch (error) {
        console.error('최근 3일 데이터 로드 실패:', error);
        alert(`데이터를 불러오는 중 오류가 발생했습니다.\n오류: ${error.message}`);
    } finally {
        // 로딩 숨김
        hideLoadingIndicator();
    }
}

// 삭제됨: loadCompareData - loadRecent3Days로 대체됨

// 삭제됨: initializeTimeRangeControls 함수 (시간 가로바 기능 제거됨)

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
    
// 삭제됨: initializeScaleControls - Y축 스케일 조정 기능 제거됨

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

// 삭제됨: loadChartData는 loadRecentData로 대체됨

// 차트 업데이트
function updateChart() {
    if (compareMode) {
        // 일별 비교 모드
        updateCompareChart();
    } else {
        // 일반 모드
        updateNormalChart();
    }
}

// 일반 차트 업데이트
function updateNormalChart() {
    if (!currentData || currentData.length === 0) {
        return;
    }
    
    // 라벨 (타임스탬프) - 여러 날짜에 걸친 경우 처리
    const labels = currentData.map(row => {
        const date = new Date(row.Timestamp);
        return date.toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    });
    
    // 데이터셋 생성 (모든 시리즈 포함, 조도는 기본 숨김)
    const datasets = [];
    
    // 모든 시리즈를 순서대로 처리 (조도는 마지막에)
    const seriesOrder = ['Temp_C', 'Hum_Pct', 'Soil_Pct', 'VPD_kPa', 'DLI_mol', 'Lux'];
    
    seriesOrder.forEach(key => {
        const series = dataSeries[key];
        if (!series) return;
        
        const values = currentData.map(row => {
            const val = parseFloat(row[key] || 0);
            return isNaN(val) ? null : val;
        });
        
        // 기본적으로 VPD만 활성화, 나머지는 비활성화
        const isHidden = (key !== 'VPD_kPa');
        
        datasets.push({
            label: series.label,
            data: values,
            borderColor: series.color,
            backgroundColor: series.color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
            borderWidth: 2,
            fill: false,
            tension: 0.1,
            pointRadius: 0,
            pointHoverRadius: 4,
            hidden: isHidden
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

// 일별 비교 차트 업데이트 (최근 3일, 같은 시간대에 겹쳐서 표시)
function updateCompareChart() {
    // 데이터 확인
    if (!compareData || (!compareData.day1 && !compareData.day2 && !compareData.day3)) {
        console.warn('일별 비교 데이터가 없습니다.');
        return;
    }
    
    // 시간대별로 데이터 정렬 (00:00 ~ 23:59, 10분 간격)
    const timeSlots = [];
    for (let h = 0; h < 24; h++) {
        for (let m = 0; m < 60; m += 10) {
            timeSlots.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
        }
    }
    
    const labels = timeSlots;
    const datasets = [];
    
    const dayLabels = {
        day1: '오늘',
        day2: 'D-1',
        day3: 'D-2'
    };
    
    // 날짜별 색상 정의 (시리즈 색상과 무관하게 날짜별로 구분)
    const dayColors = {
        day1: 'rgb(33, 150, 243)',    // 오늘 - 파란색
        day2: 'rgb(76, 175, 80)',     // D-1 - 초록색
        day3: 'rgb(255, 152, 0)'      // D-2 - 주황색
    };
    
    // 활성화된 시리즈만 표시 (한 번에 하나씩만)
    const activeSeries = Array.from(selectedSeries);
    if (activeSeries.length === 0) {
        // 활성화된 시리즈가 없으면 VPD만 표시
        activeSeries.push('VPD_kPa');
    }
    
    // 첫 번째 활성화된 시리즈만 사용 (한 번에 하나씩만)
    const activeKey = activeSeries[0];
    const series = dataSeries[activeKey];
    
    if (!series) {
        console.warn(`시리즈를 찾을 수 없습니다: ${activeKey}`);
        return;
    }
    
    // 각 날짜별로 데이터셋 생성 (날짜별 색상 사용)
    ['day1', 'day2', 'day3'].forEach(dayKey => {
        const dayData = compareData[dayKey] || [];
        const dayLabel = dayLabels[dayKey];
        const dayColor = dayColors[dayKey];
        
        // 시간대별 값 매핑 (같은 시간대에 겹쳐서 표시)
        const values = timeSlots.map(timeSlot => {
            // 해당 시간대에 가장 가까운 데이터 찾기 (±5분 허용)
            const matching = dayData.find(row => {
                const rowTime = row.timeOnly || new Date(row.Timestamp).toTimeString().slice(0, 5);
                const [rowH, rowM] = rowTime.split(':').map(Number);
                const [slotH, slotM] = timeSlot.split(':').map(Number);
                
                // 같은 시간대이고 5분 이내 차이
                if (rowH === slotH && Math.abs(rowM - slotM) <= 5) {
                    return true;
                }
                return false;
            });
            
            if (matching) {
                const val = parseFloat(matching[activeKey] || 0);
            return isNaN(val) ? null : val;
            }
            return null;
        });
        
        // 날짜별 색상으로 표시
        datasets.push({
            label: `${series.label} (${dayLabel})`,  // 시리즈 이름 + 날짜
            data: values,
            borderColor: dayColor,  // 날짜별 색상 사용
            backgroundColor: dayColor.replace('rgb', 'rgba').replace(')', ', 0.1)'),
            borderWidth: 2,
            fill: false,
            tension: 0.1,
            pointRadius: 3,
            pointHoverRadius: 5,
            hidden: false,
            dayKey: dayKey,  // 날짜 키 저장
            dayLabel: dayLabel
        });
    });
    
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
    
    // 범례 설정: 날짜별 색상 범례 추가
    mainChart.options.plugins.legend.display = true;
    mainChart.options.plugins.legend.labels.filter = function(legendItem, chartData) {
        // 날짜 범례만 표시 (시리즈 이름 포함)
        return true;
    };
    
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
    
    // 현재 상태 촬영 버튼
    const captureCurrentBtn = document.getElementById('capture-current-btn');
    if (captureCurrentBtn) {
        captureCurrentBtn.addEventListener('click', async function() {
            // 버튼 비활성화 및 텍스트 변경
            this.disabled = true;
            const originalText = this.textContent;
            this.textContent = '촬영 중...';
            
            try {
                const response = await fetch('/api/camera/capture', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const result = await response.json();
                
                if (result.success) {
                    if (result.image_url) {
                        // 촬영된 이미지 표시
                        currentImage.src = result.image_url;
                        currentImage.style.display = 'block';
                        imagePlaceholder.style.display = 'none';
                        
                        // 날짜와 시간 입력 필드 업데이트
                        const now = new Date();
                        imageDateInput.value = now.toISOString().split('T')[0];
                        await updateImageTimeList(imageDateInput.value);
                        const timeStr = now.toTimeString().slice(0, 5);
                        imageTimeSelect.value = timeStr;
                    } else {
                        imagePlaceholder.textContent = result.message || '촬영 완료 (이미지 확인 중...)';
                        currentImage.style.display = 'none';
                        imagePlaceholder.style.display = 'block';
                    }
                } else {
                    alert(`촬영 실패: ${result.error || '알 수 없는 오류'}`);
                }
            } catch (error) {
                console.error('촬영 요청 실패:', error);
                alert('촬영 요청 중 오류가 발생했습니다.');
            } finally {
                // 버튼 복원
                this.disabled = false;
                this.textContent = originalText;
            }
        });
    }
    
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
                // 메시지가 있으면 표시 (조도 낮음 등)
                if (result.message) {
                    imagePlaceholder.textContent = result.message;
            } else {
                imagePlaceholder.textContent = '사진이 없습니다';
                }
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

// 삭제됨: initializeDiscordTest - Discord 테스트 UI 제거됨 (푸시 기능은 유지)

// 모든 구동계 제어 버튼 초기화
function initializeActuatorControls() {
    // 모든 구동계를 동일한 API로 제어
    const buttons = [
        { id: 'fan-toggle-btn', type: 'fan', status: 'fan-status', card: 'fan-card' },
        { id: 'led-w-toggle-btn', type: 'led_w', status: 'led-w-status', card: 'led-w-card' },
        { id: 'led-p-toggle-btn', type: 'led_p', status: 'led-p-status', card: 'led-p-card' },
        { id: 'valve-toggle-btn', type: 'valve', status: 'valve-status', card: 'valve-card' },
        { id: 'curtain-toggle-btn', type: 'curtain', status: 'curtain-status', card: 'curtain-card' }
    ];
    
    buttons.forEach(btn => {
        initializeToggleButton(btn.id, btn.type, btn.status, btn.card);
    });
}

// 공통 토글 버튼 초기화 함수
function initializeToggleButton(buttonId, actuatorType, statusId, cardId) {
    const toggleBtn = document.getElementById(buttonId);
    if (!toggleBtn) {
        // 디버깅: 실제 DOM 구조 확인
        const card = document.getElementById(cardId);
        if (card) {
            console.warn(`토글 버튼을 찾을 수 없습니다: ${buttonId} (카드는 존재함: ${cardId})`);
            console.log('카드 내용:', card.innerHTML.substring(0, 200));
        } else {
            console.warn(`토글 버튼과 카드를 모두 찾을 수 없습니다: ${buttonId}, ${cardId}`);
        }
        return;
    }
    
    console.log(`✅ 토글 버튼 초기화 완료: ${buttonId}`);
    
    toggleBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        console.log(`${actuatorType} 토글 버튼 클릭됨`);
        
        // 버튼 비활성화
        toggleBtn.disabled = true;
        toggleBtn.textContent = '처리 중...';
        
        try {
            // 모든 구동계는 동일한 API 사용
            console.log(`${actuatorType} 토글 API 호출 중...`);
            const response = await fetch('/api/actuator/toggle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify({ type: actuatorType })
            });
            
            console.log('API 응답 상태:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('API 오류:', response.status, errorText);
                throw new Error(`서버 오류: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('API 응답:', result);
            
            if (result.success) {
                // 상태 업데이트 (즉시 UI 반영)
                const statusEl = document.getElementById(statusId);
                const card = document.getElementById(cardId);
                const newStatus = result.status;
                
                if (statusEl) {
                    statusEl.textContent = newStatus;
                }
                
                // 카드 스타일 업데이트
                if (card) {
                    card.classList.remove('active', 'off');
                    if (newStatus === 'ON' || newStatus === 'OPEN') {
                        card.classList.add('active');
                    } else {
                        card.classList.add('off');
                    }
                }
            } else {
                const errorMsg = result.error || '알 수 없는 오류';
                console.error(`${actuatorType} 제어 실패:`, errorMsg);
                alert(`${actuatorType} 제어 실패: ${errorMsg}`);
            }
        } catch (error) {
            console.error(`${actuatorType} 토글 실패:`, error);
            alert(`${actuatorType} 제어 중 오류가 발생했습니다: ${error.message}`);
        } finally {
            // 버튼 다시 활성화
            toggleBtn.disabled = false;
            toggleBtn.textContent = '토글';
        }
    });
}


