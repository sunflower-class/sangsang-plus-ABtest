// 시뮬레이션 상태
let simulationState = {
    isRunning: false,
    testId: null,
    testInfo: null,
    stats: {
        versionA: { 
            clicks: 0, 
            cart_additions: 0, 
            purchases: 0, 
            cart_purchases: 0, 
            direct_purchases: 0, 
            errors: 0, 
            page_loads: 0, 
            total_page_load_time: 0 
        },
        versionB: { 
            clicks: 0, 
            cart_additions: 0, 
            purchases: 0, 
            cart_purchases: 0, 
            direct_purchases: 0, 
            errors: 0, 
            page_loads: 0, 
            total_page_load_time: 0 
        }
    },
    autoSimulation: null,
    batchProcessor: null,
    dashboardUpdateInterval: null,
    currentSpeed: 'fast', // 기본 속도
    performanceMetrics: {
        lastInteractionTime: Date.now(),
        totalInteractions: 0,
        serverErrors: 0,
        lastTPS: 0,
        tpsHistory: []
    },
    speedSettings: {
        slow: { interval: 4000, visitors: [1, 2], delays: { click: [500, 1500], purchase: [1000, 3000] } },
        normal: { interval: 2000, visitors: [1, 3], delays: { click: [300, 800], purchase: [500, 1500] } },
        fast: { interval: 800, visitors: [1, 3], delays: { click: [100, 400], purchase: [200, 700] } },
        turbo: { interval: 300, visitors: [2, 5], delays: { click: [50, 200], purchase: [100, 300] } }
    }
};

// 실시간 상태 업데이트
function updateRealTimeStatus() {
    // 시뮬레이션 상태 업데이트
    const statusElement = document.getElementById('simulationStatus');
    if (statusElement) {
        if (simulationState.isRunning) {
            const speedConfig = simulationState.speedSettings[simulationState.currentSpeed];
            const estimatedVPM = Math.round(60000 / speedConfig.interval * 2.5);
            statusElement.textContent = `실행 중 (${simulationState.currentSpeed.toUpperCase()}, ~${estimatedVPM}/분)`;
            statusElement.style.color = '#38a169';
        } else {
            statusElement.textContent = '대기 중';
            statusElement.style.color = '#718096';
        }
    }
    
    // 대시보드 연결 상태 체크
    checkDashboardConnection();
    
    // 총 상호작용 수 업데이트
    const totalElement = document.getElementById('totalInteractions');
    if (totalElement) {
        const total = simulationState.stats.versionA.clicks + simulationState.stats.versionA.cart_additions + simulationState.stats.versionA.purchases + simulationState.stats.versionA.errors + simulationState.stats.versionA.page_loads +
                     simulationState.stats.versionB.clicks + simulationState.stats.versionB.cart_additions + simulationState.stats.versionB.purchases + simulationState.stats.versionB.errors + simulationState.stats.versionB.page_loads;
        totalElement.textContent = total;
    }
    
    // TPS 업데이트
    updateTPSDisplay();
    
    // 서버 응답 상태 업데이트
    updateServerResponseStatus();
    
    // 마지막 업데이트 시간
    const lastUpdateElement = document.getElementById('lastUpdate');
    if (lastUpdateElement) {
        lastUpdateElement.textContent = new Date().toLocaleTimeString();
    }
}

// TPS 계산 및 표시
function updateTPSDisplay() {
    const tpsElement = document.getElementById('transactionsPerSecond');
    if (tpsElement) {
        tpsElement.textContent = simulationState.performanceMetrics.lastTPS.toFixed(1);
        
        // TPS에 따른 색상 변경
        if (simulationState.performanceMetrics.lastTPS > 10) {
            tpsElement.style.color = '#38a169'; // 높음 - 녹색
        } else if (simulationState.performanceMetrics.lastTPS > 5) {
            tpsElement.style.color = '#d69e2e'; // 중간 - 노랑
        } else {
            tpsElement.style.color = '#667eea'; // 낮음 - 파랑
        }
    }
}

// 서버 응답 상태 업데이트
function updateServerResponseStatus() {
    const serverElement = document.getElementById('serverResponse');
    if (serverElement) {
        const errorRate = simulationState.performanceMetrics.serverErrors / Math.max(simulationState.performanceMetrics.totalInteractions, 1);
        
        if (errorRate === 0) {
            serverElement.textContent = '정상';
            serverElement.style.color = '#38a169';
        } else if (errorRate < 0.05) {
            serverElement.textContent = '경고';
            serverElement.style.color = '#d69e2e';
        } else {
            serverElement.textContent = '오류';
            serverElement.style.color = '#e53e3e';
        }
    }
}

// 대시보드 연결 상태 체크
async function checkDashboardConnection() {
    const dashboardElement = document.getElementById('dashboardConnection');
    if (!dashboardElement) return;
    
    try {
        const response = await fetch('http://localhost:8000/api/abtest/', {
            method: 'GET',
            timeout: 3000
        });
        
        if (response.ok) {
            dashboardElement.textContent = '연결됨';
            dashboardElement.style.color = '#38a169';
        } else {
            dashboardElement.textContent = '연결 실패';
            dashboardElement.style.color = '#e53e3e';
        }
    } catch (error) {
        dashboardElement.textContent = '연결 안됨';
        dashboardElement.style.color = '#e53e3e';
    }
}

// 성능 메트릭 업데이트
function updatePerformanceMetrics(success = true) {
    const now = Date.now();
    simulationState.performanceMetrics.totalInteractions++;
    
    if (!success) {
        simulationState.performanceMetrics.serverErrors++;
    }
    
    // TPS 계산 (5초 간격으로)
    const timeDiff = now - simulationState.performanceMetrics.lastInteractionTime;
    if (timeDiff >= 5000) { // 5초마다 TPS 재계산
        const newTPS = simulationState.performanceMetrics.totalInteractions / (timeDiff / 1000);
        simulationState.performanceMetrics.lastTPS = newTPS;
        simulationState.performanceMetrics.tpsHistory.push(newTPS);
        
        // 히스토리 크기 제한 (최대 20개)
        if (simulationState.performanceMetrics.tpsHistory.length > 20) {
            simulationState.performanceMetrics.tpsHistory.shift();
        }
        
        // 리셋
        simulationState.performanceMetrics.lastInteractionTime = now;
        simulationState.performanceMetrics.totalInteractions = 0;
    }
}

// 대시보드 연결 상태 확인
function checkDashboardConnection() {
    const connectionElement = document.getElementById('dashboardConnection');
    if (connectionElement) {
        try {
            // 대시보드가 열려있는지 확인
            if (window.opener && window.opener.location.href.includes('dashboard.html')) {
                connectionElement.textContent = '연결됨';
                connectionElement.style.color = '#38a169';
            } else {
                connectionElement.textContent = '연결 안됨';
                connectionElement.style.color = '#e53e3e';
            }
        } catch (error) {
            connectionElement.textContent = '연결 안됨';
            connectionElement.style.color = '#e53e3e';
        }
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    updateStats();
    loadTestList();
    
    // 테스트 선택 이벤트 리스너 추가
    const testSelect = document.getElementById('testSelect');
    if (testSelect) {
        testSelect.addEventListener('change', function() {
            const selectedTestId = this.value;
            const selectedOption = this.options[this.selectedIndex];
            
            // 완료된 테스트는 선택할 수 없음
            if (selectedOption && selectedOption.disabled) {
                showNotification('완료된 테스트는 선택할 수 없습니다. 활성 테스트를 선택해주세요.', 'error');
                this.value = ''; // 선택 해제
                simulationState.testId = null;
                return;
            }
            
            if (selectedTestId) {
                loadSelectedTestInfo(selectedTestId);
                simulationState.testId = parseInt(selectedTestId);
            }
        });
    }
    
    // 실시간 상태 업데이트 시작
    setInterval(() => {
        updateRealTimeStatus();
        checkDashboardConnection();
    }, 1000); // 1초마다 상태 업데이트
    
    showNotification('시뮬레이터가 준비되었습니다. 테스트를 선택하고 "시뮬레이션 시작" 버튼을 클릭하세요.', 'info');
});

// 테스트 목록 로드
async function loadTestList() {
    try {
        const response = await fetch('http://localhost:8000/api/abtest/list');
        if (response.ok) {
            const data = await response.json();
            const tests = data.tests || data;
            const select = document.getElementById('testSelect');
            
            if (!select) {
                console.error('testSelect 요소를 찾을 수 없습니다.');
                return;
            }
            
            select.innerHTML = '<option value="">테스트를 선택하세요...</option>';
            
            if (!Array.isArray(tests)) {
                console.error('테스트 데이터가 배열이 아닙니다:', tests);
                showNotification('테스트 데이터 형식 오류', 'error');
                return;
            }
            
            let activeTestCount = 0;
            let completedTestCount = 0;
            
            tests.forEach(test => {
                const option = document.createElement('option');
                option.value = test.id;
                
                // 완료된 테스트는 비활성화
                if (test.status === 'completed' || test.status === 'COMPLETED') {
                    option.disabled = true;
                    option.textContent = `${test.name || test.product_name} (ID: ${test.id}) - 완료됨 (선택 불가)`;
                    completedTestCount++;
                } else {
                    option.textContent = `${test.name || test.product_name} (ID: ${test.id}) - ${test.status}`;
                    activeTestCount++;
                }
                
                select.appendChild(option);
            });
            
            showNotification(`${activeTestCount}개의 활성 테스트, ${completedTestCount}개의 완료된 테스트를 불러왔습니다.`, 'info');
        } else {
            throw new Error('테스트 목록을 불러올 수 없습니다.');
        }
    } catch (error) {
        console.error('테스트 목록 로드 오류:', error);
        showNotification('테스트 목록을 불러오는 중 오류가 발생했습니다.', 'error');
    }
}

// 이미지 URL 정보 업데이트
function updateImageInfo(test) {
    const imageAUrlElement = document.getElementById('imageAUrl');
    const imageBUrlElement = document.getElementById('imageBUrl');
    
    if (imageAUrlElement) {
        imageAUrlElement.textContent = test.baseline_image_url || '이미지 없음';
        if (test.baseline_image_url) {
            imageAUrlElement.style.color = '#38a169';
        } else {
            imageAUrlElement.style.color = '#e53e3e';
        }
    }
    
    if (imageBUrlElement) {
        imageBUrlElement.textContent = test.challenger_image_url || '이미지 없음';
        if (test.challenger_image_url) {
            imageBUrlElement.style.color = '#38a169';
        } else {
            imageBUrlElement.style.color = '#e53e3e';
        }
    }
}

// 선택된 테스트 정보 로드
async function loadSelectedTestInfo(testId) {
    if (!testId) return;
    
    try {
        const response = await fetch(`http://localhost:8000/api/abtest/test/${testId}`);
        if (response.ok) {
            const test = await response.json();
            
            // 테스트 정보를 화면에 표시
            document.getElementById('titleA').textContent = test.product_name || '상품 A';
            document.getElementById('titleB').textContent = test.product_name || '상품 B';
            
            // 버전별 설명 업데이트
            document.getElementById('descA').textContent = test.baseline_description || 'A안 - AI가 생성한 상품 설명입니다.';
            document.getElementById('descB').textContent = test.challenger_description || 'B안 - AI가 생성한 상품 설명입니다.';
            
            // 가격 정보 업데이트
            document.getElementById('priceA').textContent = `₩${test.baseline_price || '1,200,000'}`;
            document.getElementById('priceB').textContent = `₩${test.challenger_price || '1,200,000'}`;
            
            // 이미지 URL 정보 업데이트
            updateImageInfo(test);
            
            // 실제 이미지 URL 설정
            if (test.baseline_image_url) {
                const imageA = document.querySelector('#versionA .product-image');
                imageA.innerHTML = `<img src="${test.baseline_image_url}" alt="A안 이미지" style="width: 100%; height: 100%; object-fit: cover; border-radius: 10px;" onerror="this.parentElement.innerHTML='📱';">`;
            } else {
                const imageA = document.querySelector('#versionA .product-image');
                imageA.innerHTML = '📱';
            }
            
            if (test.challenger_image_url) {
                const imageB = document.querySelector('#versionB .product-image');
                imageB.innerHTML = `<img src="${test.challenger_image_url}" alt="B안 이미지" style="width: 100%; height: 100%; object-fit: cover; border-radius: 10px;" onerror="this.parentElement.innerHTML='📱';">`;
            } else {
                const imageB = document.querySelector('#versionB .product-image');
                imageB.innerHTML = '📱';
            }
            
            showNotification(`테스트 "${test.name || test.product_name}" 정보를 로드했습니다.`, 'info');
        }
    } catch (error) {
        console.error('테스트 정보 로드 오류:', error);
        showNotification('테스트 정보를 불러오는 중 오류가 발생했습니다.', 'error');
    }
}

// 시뮬레이션 시작/중지 토글
function startSimulation() {
    if (simulationState.isRunning) {
        stopSimulation();
    } else {
        if (!simulationState.testId) {
            showNotification('먼저 테스트를 선택해주세요.', 'error');
            return;
        }
        
        // 선택된 테스트가 완료된 상태인지 확인
        const testSelect = document.getElementById('testSelect');
        const selectedOption = testSelect.options[testSelect.selectedIndex];
        if (selectedOption && selectedOption.disabled) {
            showNotification('완료된 테스트는 시뮬레이션할 수 없습니다. 활성 테스트를 선택해주세요.', 'error');
            return;
        }
        
        simulationState.isRunning = true;
        
        // 버튼 상태 업데이트 (안전하게 처리)
        const startBtn = document.querySelector('.btn-start');
        if (startBtn) {
            startBtn.textContent = '시뮬레이션 중지';
            startBtn.classList.add('btn-stop');
        }
        
        // 버튼 상태 업데이트
        updateSimulationButtons();
        
        startAutoSimulation();
        startDashboardUpdates();
        
        // 실시간 상태 업데이트
        updateRealTimeStatus();
        
        const speedConfig = simulationState.speedSettings[simulationState.currentSpeed];
        const estimatedVPM = Math.round(60000 / speedConfig.interval * 2.5);
        showNotification(`🚀 ${simulationState.currentSpeed.toUpperCase()} 모드로 시뮬레이션 시작! 예상 분당 방문자: ${estimatedVPM}명`, 'success');
    }
}

// 시뮬레이션 중지
function stopSimulation() {
    simulationState.isRunning = false;
    document.querySelector('.btn-start').textContent = '시뮬레이션 시작';
    document.querySelector('.btn-start').classList.remove('btn-stop');
    
    if (simulationState.autoSimulation) {
        clearInterval(simulationState.autoSimulation);
        simulationState.autoSimulation = null;
    }
    
    if (simulationState.batchProcessor) {
        clearInterval(simulationState.batchProcessor);
        simulationState.batchProcessor = null;
    }
    
    if (simulationState.dashboardUpdateInterval) {
        clearInterval(simulationState.dashboardUpdateInterval);
        simulationState.dashboardUpdateInterval = null;
    }
    
    // 실시간 상태 업데이트
    updateRealTimeStatus();
    
    showNotification('시뮬레이션이 중지되었습니다.', 'info');
}

// 자동 시뮬레이션 (동적 속도 조절)
function startAutoSimulation() {
    // 배치 처리를 위한 큐
    let interactionQueue = [];
    let batchCounter = 0;
    
    // 현재 속도 설정 가져오기
    const speedConfig = simulationState.speedSettings[simulationState.currentSpeed];
    
    // 동적 속도로 방문자 생성
    simulationState.autoSimulation = setInterval(() => {
        if (!simulationState.isRunning) return;
        
        // 방문자 수 범위에서 랜덤 선택
        const [minVisitors, maxVisitors] = speedConfig.visitors;
        const visitorCount = Math.floor(Math.random() * (maxVisitors - minVisitors + 1)) + minVisitors;
        
        for (let i = 0; i < visitorCount; i++) {
            // 각 방문자별로 약간의 시간차를 두고 처리
            setTimeout(() => {
                simulateVisitor(speedConfig);
            }, i * (speedConfig.interval / visitorCount / 4)); // 균등 분산
        }
    }, speedConfig.interval); // 설정된 간격으로 방문자 그룹 생성
    
    // 배치 처리용 타이머 (서버 부하 감소)
    simulationState.batchProcessor = setInterval(() => {
        if (interactionQueue.length > 0) {
            processBatch(interactionQueue.splice(0)); // 큐 비우기
        }
    }, 2000); // 2초마다 배치 처리 (리소스 부족 방지)
    
    function simulateVisitor(speedConfig) {
        if (!simulationState.isRunning) return;
        
        // 랜덤하게 버전 선택 (50:50)
        const version = Math.random() < 0.5 ? 'A' : 'B';
        
        // 방문자 타입별 행동 패턴 (더 현실적)
        const visitorType = getVisitorType();
        const behavior = getVisitorBehavior(visitorType);
        
        // 즉시 노출 기록 (배치 큐에 추가)
        addToQueue(version, 'view');
        
        // 클릭 확률 (방문자 타입별 차등)
        if (Math.random() < behavior.clickRate) {
            const [clickMin, clickMax] = speedConfig.delays.click;
            setTimeout(() => {
                addToQueue(version, 'click');
                
                // 구매 확률 (클릭한 사람 중)
                if (Math.random() < behavior.purchaseRate) {
                    const [purchaseMin, purchaseMax] = speedConfig.delays.purchase;
                    setTimeout(() => {
                        addToQueue(version, 'purchase');
                    }, Math.random() * (purchaseMax - purchaseMin) + purchaseMin);
                }
            }, Math.random() * (clickMax - clickMin) + clickMin);
        }
    }
    
    function getVisitorType() {
        const rand = Math.random();
        if (rand < 0.6) return 'casual';      // 60% - 일반 방문자
        if (rand < 0.85) return 'interested'; // 25% - 관심 있는 방문자  
        return 'buyer';                       // 15% - 구매 의향 높은 방문자
    }
    
    function getVisitorBehavior(type) {
        const behaviors = {
            casual: { clickRate: 0.15, purchaseRate: 0.05 },     // 낮은 참여도
            interested: { clickRate: 0.45, purchaseRate: 0.25 }, // 중간 참여도
            buyer: { clickRate: 0.80, purchaseRate: 0.60 }       // 높은 참여도
        };
        return behaviors[type];
    }
    
    function addToQueue(version, interactionType) {
        // 로컬 통계 즉시 업데이트 (UI 반응성)
        if (interactionType === 'view') {
            simulationState.stats[`version${version}`].views++;
        } else if (interactionType === 'click') {
            simulationState.stats[`version${version}`].clicks++;
        } else if (interactionType === 'purchase') {
            simulationState.stats[`version${version}`].purchases++;
        }
        
        // 성능 메트릭 업데이트
        updatePerformanceMetrics(true);
        
        // 서버 전송용 큐에 추가
        interactionQueue.push({
            version: version,
            type: interactionType,
            timestamp: Date.now()
        });
        
        // UI 업데이트 (15번에 1번으로 빈도 증가 - 고속 모드 대응)
        batchCounter++;
        if (batchCounter % 15 === 0) {
            updateStats();
            updateDashboardIfOpen();
        }
    }
    
    async function processBatch(batch) {
        if (batch.length === 0) return;
        
        // 같은 타입끼리 그룹화하여 효율적 처리
        const grouped = batch.reduce((acc, item) => {
            const key = `${item.version}-${item.type}`;
            acc[key] = (acc[key] || 0) + 1;
            return acc;
        }, {});
        
        // 그룹별로 순차 처리 (서버 부하 분산)
        for (const [key, count] of Object.entries(grouped)) {
            const [version, type] = key.split('-');
            
            // 여러 번 발생한 같은 상호작용을 한 번에 처리
            for (let i = 0; i < count; i++) {
                try {
                    await recordInteractionToServer(version, type);
                    updatePerformanceMetrics(true); // 성공
                    await new Promise(resolve => setTimeout(resolve, 100)); // 100ms로 증가 (리소스 부족 방지)
                } catch (error) {
                    updatePerformanceMetrics(false); // 실패
                    if (error.message.includes('ERR_INSUFFICIENT_RESOURCES')) {
                        console.warn('리소스 부족으로 인한 요청 실패. 잠시 후 재시도됩니다.');
                    } else {
                        console.warn('배치 처리 중 오류 (계속 진행):', error.message);
                    }
                }
            }
        }
    }
    

}

// 대시보드 실시간 업데이트 시작
function startDashboardUpdates() {
    simulationState.dashboardUpdateInterval = setInterval(() => {
        if (!simulationState.isRunning) return;
        
        // 대시보드가 열려있다면 실시간 업데이트
        updateDashboardIfOpen();
    }, 2000); // 2초마다 대시보드 업데이트 (기존 5초에서 단축)
}

// 대시보드가 열려있다면 업데이트
function updateDashboardIfOpen() {
    // 부모 창이나 다른 창에서 대시보드가 열려있는지 확인
    try {
        // 부모 창이 있고 대시보드인 경우
        if (window.opener && window.opener.location.href.includes('dashboard.html')) {
            window.opener.postMessage({
                type: 'SIMULATION_UPDATE',
                testId: simulationState.testId,
                stats: simulationState.stats
            }, '*');
        }
        
        // 같은 창에서 대시보드가 열려있는 경우 (iframe 등)
        if (window.parent && window.parent !== window) {
            window.parent.postMessage({
                type: 'SIMULATION_UPDATE',
                testId: simulationState.testId,
                stats: simulationState.stats
            }, '*');
        }
    } catch (error) {
        // 다른 도메인이나 보안 정책으로 인한 오류는 무시
        console.log('대시보드 업데이트 중 오류 (무시됨):', error.message);
    }
}

// 상호작용 기록
async function recordInteraction(version, interactionType) {
    if (!simulationState.isRunning || !simulationState.testId) {
        showNotification('시뮬레이션이 실행되지 않았습니다.', 'error');
        return;
    }
    
    const stats = simulationState.stats[`version${version}`];
    
    // 새로운 지표 시스템 검증 로직
    if (interactionType === 'add_to_cart' && stats.clicks === 0) {
        showNotification('클릭 없이는 장바구니에 추가할 수 없습니다. 먼저 클릭 버튼을 클릭하세요.', 'warning');
        return;
    }
    
    // 구매 시 직접구매 vs 장바구니구매 구분
    if (interactionType === 'purchase') {
        if (stats.clicks === 0) {
            showNotification('클릭 없이는 구매할 수 없습니다. 먼저 클릭 버튼을 클릭하세요.', 'warning');
        return;
    }
    
        // 장바구니에 상품이 있는 경우 구매 유형 선택
        if (stats.cart_additions > 0) {
            const userChoice = confirm('장바구니에서 구매하시겠습니까?\n\n확인: 장바구니 구매\n취소: 직접 구매');
            if (userChoice) {
                await recordInteractionWithMetadata(version, interactionType, { purchase_type: 'from_cart' });
        return;
            }
    }
    
        // 직접 구매
        await recordInteractionWithMetadata(version, interactionType, { purchase_type: 'direct' });
        return;
    }

    // 가드레일 지표 (오류, 페이지 로드)는 제한 없음
    if (interactionType === 'error' || interactionType === 'page_load') {
        await recordSimpleInteraction(version, interactionType);
        return;
    }

    // 일반적인 상호작용 처리
    await recordSimpleInteraction(version, interactionType);
}

// 메타데이터가 있는 상호작용 기록
async function recordInteractionWithMetadata(version, interactionType, metadata = {}) {
    const stats = simulationState.stats[`version${version}`];
    
    try {
        // 서버에 전송
        await recordInteractionToServerWithMetadata(version, interactionType, metadata);
        
        // 로컬 상태 업데이트
        updateLocalStats(version, interactionType, metadata);
        
        // UI 업데이트
        updateStats();
        updateRealTimeStatus();
        
        showNotification(`${version} 버전 ${getInteractionDisplayName(interactionType)} 완료!`, 'success');
        
    } catch (error) {
        console.error('상호작용 기록 실패:', error);
        showNotification('상호작용 기록에 실패했습니다.', 'error');
    }
}

// 일반 상호작용 기록
async function recordSimpleInteraction(version, interactionType) {
    try {
        // 서버에 전송
        await recordInteractionToServer(version, interactionType);
        
        // 로컬 상태 업데이트
        updateLocalStats(version, interactionType);
        
        // UI 업데이트
        updateStats();
        updateRealTimeStatus();
        
        showNotification(`${version} 버전 ${getInteractionDisplayName(interactionType)} 완료!`, 'success');
        
    } catch (error) {
        console.error('상호작용 기록 실패:', error);
        showNotification('상호작용 기록에 실패했습니다.', 'error');
    }
}

// 로컬 통계 업데이트
function updateLocalStats(version, interactionType, metadata = {}) {
    const stats = simulationState.stats[`version${version}`];
    
    // 상호작용 타입별 매핑
    if (interactionType === 'click') {
        stats.clicks++;
    } else if (interactionType === 'add_to_cart') {
        stats.cart_additions++;
    } else if (interactionType === 'purchase') {
        stats.purchases++;
        
        // 구매 타입별 세분화
        if (metadata.purchase_type === 'from_cart') {
            stats.cart_purchases++;
        } else {
            stats.direct_purchases++;
        }
    } else if (interactionType === 'error') {
        stats.errors++;
    } else if (interactionType === 'page_load') {
        stats.page_loads++;
        // 페이지 로드 시간 시뮬레이션
        const loadTime = Math.random() * 2000 + 500; // 500ms ~ 2500ms
        stats.total_page_load_time += loadTime;
    }
}

// 상호작용 표시명 반환
function getInteractionDisplayName(interactionType) {
    const displayNames = {
        'click': '클릭',
        'add_to_cart': '장바구니 추가',
        'purchase': '구매',
        'error': '오류',
        'page_load': '페이지 로드'
    };
    return displayNames[interactionType] || interactionType;
}

// 메타데이터와 함께 서버로 전송
async function recordInteractionToServerWithMetadata(version, interactionType, metadata = {}) {
    const response = await fetch('http://localhost:8000/api/abtest/interaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            test_id: simulationState.testId,
            variant: version === 'A' ? 'baseline' : 'challenger',
            interaction_type: interactionType,
            metadata: metadata,
            timestamp: new Date().toISOString()
        })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
}

// 기본 서버 전송 함수
async function recordInteractionToServer(version, interactionType) {
    if (!simulationState.testId) return;
    
    try {
        const response = await fetch('http://localhost:8000/api/abtest/interaction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                test_id: simulationState.testId,
                variant: version === 'A' ? 'baseline' : 'challenger',
                interaction_type: interactionType,
                timestamp: new Date().toISOString()
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        throw error;
    }
}


// 통계 업데이트
function updateStats() {
    const stats = simulationState.stats;
    
    // 핵심 지표 - 기본 카운트
    updateElementIfExists('clicksA', stats.versionA.clicks);
    updateElementIfExists('clicksB', stats.versionB.clicks);
    updateElementIfExists('purchasesA', stats.versionA.purchases);
    updateElementIfExists('purchasesB', stats.versionB.purchases);
    
    // 핵심 지표 - CVR (구매전환율: 구매수/클릭수)
    const cvrA = stats.versionA.clicks > 0 ? (stats.versionA.purchases / stats.versionA.clicks * 100) : 0;
    const cvrB = stats.versionB.clicks > 0 ? (stats.versionB.purchases / stats.versionB.clicks * 100) : 0;
    updateElementIfExists('cvrA', `${cvrA.toFixed(2)}%`);
    updateElementIfExists('cvrB', `${cvrB.toFixed(2)}%`);
    
    // 보조 지표 - 장바구니 관련
    updateElementIfExists('cartAdditionsA', stats.versionA.cart_additions);
    updateElementIfExists('cartAdditionsB', stats.versionB.cart_additions);
    
    // 보조 지표 - 장바구니 추가율 (장바구니 추가수/클릭수)
    const cartAddRateA = stats.versionA.clicks > 0 ? (stats.versionA.cart_additions / stats.versionA.clicks * 100) : 0;
    const cartAddRateB = stats.versionB.clicks > 0 ? (stats.versionB.cart_additions / stats.versionB.clicks * 100) : 0;
    updateElementIfExists('cartAddRateA', `${cartAddRateA.toFixed(2)}%`);
    updateElementIfExists('cartAddRateB', `${cartAddRateB.toFixed(2)}%`);
    
    // 보조 지표 - 장바구니 CVR (장바구니 구매수/장바구니 추가수)
    const cartCvrA = stats.versionA.cart_additions > 0 ? Math.min((stats.versionA.cart_purchases / stats.versionA.cart_additions * 100), 100) : 0;
    const cartCvrB = stats.versionB.cart_additions > 0 ? Math.min((stats.versionB.cart_purchases / stats.versionB.cart_additions * 100), 100) : 0;
    updateElementIfExists('cartCvrA', `${cartCvrA.toFixed(2)}%`);
    updateElementIfExists('cartCvrB', `${cartCvrB.toFixed(2)}%`);
    
    // 보조 지표 - 매출 (현재 테스트의 상품 가격 활용)
    const productPrice = simulationState.testInfo?.product_price || 1200000;
    const revenueA = stats.versionA.purchases * productPrice;
    const revenueB = stats.versionB.purchases * productPrice;
    updateElementIfExists('revenueA', formatCurrency(revenueA));
    updateElementIfExists('revenueB', formatCurrency(revenueB));
    
    // 가드레일 지표 - 오류 관련
    updateElementIfExists('errorsA', stats.versionA.errors);
    updateElementIfExists('errorsB', stats.versionB.errors);
    
    // 가드레일 지표 - 오류율 (오류수/총상호작용수)
    const totalInteractionsA = stats.versionA.clicks + stats.versionA.cart_additions + stats.versionA.purchases + stats.versionA.errors + stats.versionA.page_loads;
    const totalInteractionsB = stats.versionB.clicks + stats.versionB.cart_additions + stats.versionB.purchases + stats.versionB.errors + stats.versionB.page_loads;
    const errorRateA = totalInteractionsA > 0 ? (stats.versionA.errors / totalInteractionsA * 100) : 0;
    const errorRateB = totalInteractionsB > 0 ? (stats.versionB.errors / totalInteractionsB * 100) : 0;
    updateElementIfExists('errorRateA', `${errorRateA.toFixed(2)}%`);
    updateElementIfExists('errorRateB', `${errorRateB.toFixed(2)}%`);
    
    // 가드레일 지표 - 평균 페이지 로드 시간
    const avgLoadTimeA = stats.versionA.page_loads > 0 ? (stats.versionA.total_page_load_time / stats.versionA.page_loads) : 0;
    const avgLoadTimeB = stats.versionB.page_loads > 0 ? (stats.versionB.total_page_load_time / stats.versionB.page_loads) : 0;
    updateElementIfExists('avgLoadTimeA', `${Math.round(avgLoadTimeA)}ms`);
    updateElementIfExists('avgLoadTimeB', `${Math.round(avgLoadTimeB)}ms`);
}

// 안전한 DOM 업데이트 함수
function updateElementIfExists(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

// 통화 포맷팅 함수
function formatCurrency(amount) {
    return new Intl.NumberFormat('ko-KR', {
        style: 'currency',
        currency: 'KRW',
        minimumFractionDigits: 0
    }).format(amount);
}

// 누락된 함수들 추가
function openDashboard() {
    window.open('/test/dashboard.html', '_blank');
}

function openAIAnalysis() {
    if (!simulationState.testId) {
        showNotification('먼저 시뮬레이션을 시작하세요.', 'warning');
        return;
    }
    window.open(`/test/dashboard.html#ai-analysis-${simulationState.testId}`, '_blank');
}

function openTestHistory() {
    window.open('/test/dashboard.html#history', '_blank');
}

// 알림 표시 함수
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // 스타일 설정
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
        z-index: 10000;
        max-width: 300px;
        word-wrap: break-word;
    `;
    
    // 타입별 색상
    switch(type) {
        case 'success':
            notification.style.backgroundColor = '#28a745';
            break;
        case 'error':
            notification.style.backgroundColor = '#dc3545';
            break;
        case 'warning':
            notification.style.backgroundColor = '#ffc107';
            notification.style.color = '#212529';
            break;
        default:
            notification.style.backgroundColor = '#17a2b8';
    }
    
    document.body.appendChild(notification);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// 시뮬레이션 버튼 상태 업데이트
function updateSimulationButtons() {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    if (simulationState.isRunning) {
        if (startBtn) startBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'inline-block';
    } else {
        if (startBtn) startBtn.style.display = 'inline-block';
        if (stopBtn) stopBtn.style.display = 'none';
    }
}

// 자동 시뮬레이션 시작
function startAutoSimulation() {
    if (simulationState.autoSimulation) {
        clearInterval(simulationState.autoSimulation);
    }
    
    const speedConfig = simulationState.speedSettings[simulationState.currentSpeed];
    console.log('🚀 자동 시뮬레이션 시작:', speedConfig);
    
    simulationState.autoSimulation = setInterval(() => {
        if (!simulationState.isRunning) {
            console.log('❌ 시뮬레이션이 중지됨, 자동 시뮬레이션 종료');
            clearInterval(simulationState.autoSimulation);
            return;
        }
        
        console.log('👥 방문자 그룹 생성 중...');
        
        // 랜덤하게 방문자 수 결정
        const visitorsCount = Math.floor(Math.random() * (speedConfig.visitors[1] - speedConfig.visitors[0] + 1)) + speedConfig.visitors[0];
        
        for (let i = 0; i < visitorsCount; i++) {
            // 50% 확률로 버전 A 또는 B 선택
            const version = Math.random() < 0.5 ? 'A' : 'B';
            
            // 지연 시간 후 방문자 시뮬레이션 실행
            setTimeout(() => {
                simulateVisitor(version);
            }, Math.random() * speedConfig.interval);
        }
    }, speedConfig.interval);
}

// 단일 방문자 시뮬레이션
async function simulateVisitor(version) {
    if (!simulationState.isRunning) return;
    
    try {
        // 1. 페이지 로드 (100% 확률)
        await simulateInteraction(version, 'page_load');
        await delay(100, 300);
        
        // 2. 클릭 (70% 확률)
        if (Math.random() < 0.7) {
            await simulateInteraction(version, 'click');
            await delay(200, 800);
            
            // 3-a. 장바구니 추가 (30% 확률)
            if (Math.random() < 0.3) {
                await simulateInteraction(version, 'add_to_cart');
                await delay(300, 1000);
                
                // 4-a. 장바구니에서 구매 (40% 확률)
                if (Math.random() < 0.4) {
                    await simulateInteractionWithMetadata(version, 'purchase', { purchase_type: 'from_cart' });
                }
            } else {
                // 3-b. 직접 구매 (15% 확률)
                if (Math.random() < 0.15) {
                    await simulateInteractionWithMetadata(version, 'purchase', { purchase_type: 'direct' });
                }
            }
        }
        
        // 5. 오류 (2% 확률)
        if (Math.random() < 0.02) {
            await simulateInteraction(version, 'error');
        }
        
    } catch (error) {
        console.error('방문자 시뮬레이션 오류:', error);
    }
}

// 시뮬레이션 상호작용 실행
async function simulateInteraction(version, interactionType) {
    try {
        // 로컬 상태 업데이트
        updateLocalStats(version, interactionType);
        
        // 서버에 전송
        await recordInteractionToServer(version, interactionType);
        
        // UI 업데이트 (성능상 일부 생략)
        if (Math.random() < 0.1) { // 10% 확률로만 UI 업데이트
            updateStats();
        }
        
    } catch (error) {
        console.error('상호작용 시뮬레이션 실패:', error);
    }
}

// 메타데이터가 있는 시뮬레이션 상호작용
async function simulateInteractionWithMetadata(version, interactionType, metadata = {}) {
    try {
        // 로컬 상태 업데이트
        updateLocalStats(version, interactionType, metadata);
        
        // 서버에 전송
        await recordInteractionToServerWithMetadata(version, interactionType, metadata);
        
        // UI 업데이트 (성능상 일부 생략)
        if (Math.random() < 0.1) { // 10% 확률로만 UI 업데이트
            updateStats();
        }
        
    } catch (error) {
        console.error('상호작용 시뮬레이션 실패:', error);
    }
}

// 지연 함수
function delay(min, max) {
    const ms = Math.random() * (max - min) + min;
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 시뮬레이션 속도 변경
function changeSimulationSpeed() {
    const speedControl = document.getElementById('speedControl');
    if (!speedControl) return;
    
    const newSpeed = speedControl.value;
    simulationState.currentSpeed = newSpeed;
    
    console.log('속도 변경:', newSpeed);
    
    // 실행 중이면 재시작
    if (simulationState.isRunning) {
        if (simulationState.autoSimulation) {
            clearInterval(simulationState.autoSimulation);
            simulationState.autoSimulation = null;
        }
        
        // 새로운 속도로 재시작
        startAutoSimulation();
        
        const speedConfig = simulationState.speedSettings[newSpeed];
        const estimatedVPM = Math.round(60000 / speedConfig.interval * 2.5);
        showNotification(`🚀 새로운 속도로 재시작! 예상 분당 방문자: ${estimatedVPM}명`, 'success');
    }
}

// 시뮬레이션 초기화
function resetSimulation() {
    // 시뮬레이션 중지
    if (simulationState.isRunning) {
        simulationState.isRunning = false;
        
        // 자동 시뮬레이션 중지
        if (simulationState.autoSimulation) {
            clearInterval(simulationState.autoSimulation);
            simulationState.autoSimulation = null;
        }
    }
    
    // 통계 초기화
    simulationState.stats = {
        versionA: { 
            clicks: 0, 
            cart_additions: 0, 
            purchases: 0, 
            cart_purchases: 0, 
            direct_purchases: 0, 
            errors: 0, 
            page_loads: 0, 
            total_page_load_time: 0 
        },
        versionB: { 
            clicks: 0, 
            cart_additions: 0, 
            purchases: 0, 
            cart_purchases: 0, 
            direct_purchases: 0, 
            errors: 0, 
            page_loads: 0, 
            total_page_load_time: 0 
        }
    };
    
    // 성능 메트릭 초기화
    simulationState.performanceMetrics = {
        lastInteractionTime: Date.now(),
        totalInteractions: 0,
        serverErrors: 0,
        lastTPS: 0,
        tpsHistory: []
    };
    
    // 상태 초기화
    simulationState.testId = null;
    simulationState.testInfo = null;
    simulationState.isRunning = false;
    
    // UI 업데이트
    updateStats();
    updateRealTimeStatus();
    updateSimulationButtons();
    
    showNotification('시뮬레이션이 초기화되었습니다.', 'success');
}

// 시뮬레이션 중지
function stopSimulation() {
    if (!simulationState.isRunning) {
        showNotification('시뮬레이션이 실행 중이 아닙니다.', 'warning');
        return;
    }
    
    simulationState.isRunning = false;
    
    // 자동 시뮬레이션 중지
    if (simulationState.autoSimulation) {
        clearInterval(simulationState.autoSimulation);
        simulationState.autoSimulation = null;
    }
    
    // 대시보드 업데이트 중지
    if (simulationState.dashboardUpdateInterval) {
        clearInterval(simulationState.dashboardUpdateInterval);
        simulationState.dashboardUpdateInterval = null;
    }
    
    // 버튼 상태 업데이트
    updateSimulationButtons();
    
    // 실시간 상태 업데이트
    updateRealTimeStatus();
    
    showNotification('시뮬레이션이 중지되었습니다.', 'info');
}

// 대시보드 실시간 업데이트 시작
function startDashboardUpdates() {
    simulationState.dashboardUpdateInterval = setInterval(() => {
        if (!simulationState.isRunning) return;
        
        // 대시보드가 열려있다면 실시간 업데이트
        updateDashboardIfOpen();
    }, 2000); // 2초마다 대시보드 업데이트
}

// 대시보드가 열려있다면 업데이트
function updateDashboardIfOpen() {
    try {
        // 부모 창이 있고 대시보드인 경우
        if (window.opener && window.opener.location.href.includes('dashboard.html')) {
            window.opener.postMessage({
                type: 'SIMULATION_UPDATE',
                testId: simulationState.testId,
                stats: simulationState.stats
            }, '*');
        }
        
        // iframe 내부에서 실행되는 경우
        if (window.parent && window.parent !== window) {
            window.parent.postMessage({
                type: 'SIMULATION_UPDATE',
                testId: simulationState.testId,
                stats: simulationState.stats
            }, '*');
        }
    } catch (error) {
        // 다른 도메인이나 보안 정책으로 인한 오류는 무시
        console.log('대시보드 업데이트 중 오류 (무시됨):', error.message);
    }
}

