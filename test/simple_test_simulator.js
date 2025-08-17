// 시뮬레이션 상태
let simulationState = {
    isRunning: false,
    testId: null,
    stats: {
        versionA: { views: 0, purchases: 0 },
        versionB: { views: 0, purchases: 0 }
    },
    autoSimulation: null,
    dashboardUpdateInterval: null
};

// 실시간 상태 업데이트
function updateRealTimeStatus() {
    // 시뮬레이션 상태 업데이트
    const statusElement = document.getElementById('simulationStatus');
    if (statusElement) {
        if (simulationState.isRunning) {
            statusElement.textContent = '실행 중';
            statusElement.style.color = '#38a169';
        } else {
            statusElement.textContent = '대기 중';
            statusElement.style.color = '#718096';
        }
    }
    
    // 총 상호작용 수 업데이트
    const totalElement = document.getElementById('totalInteractions');
    if (totalElement) {
        const total = simulationState.stats.versionA.views + simulationState.stats.versionA.purchases + 
                     simulationState.stats.versionB.views + simulationState.stats.versionB.purchases;
        totalElement.textContent = total;
    }
    
    // 마지막 업데이트 시간
    const lastUpdateElement = document.getElementById('lastUpdate');
    if (lastUpdateElement) {
        lastUpdateElement.textContent = new Date().toLocaleTimeString();
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
            
            tests.forEach(test => {
                const option = document.createElement('option');
                option.value = test.id;
                option.textContent = `${test.name || test.product_name} (ID: ${test.id}) - ${test.status}`;
                select.appendChild(option);
            });
            
            showNotification(`${tests.length}개의 테스트를 불러왔습니다.`, 'info');
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
            document.getElementById('descA').textContent = test.baseline_description || '기존 버전의 상품 설명입니다.';
            document.getElementById('descB').textContent = test.challenger_description || 'AI가 생성한 새로운 버전의 상품 설명입니다.';
            
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
        
        simulationState.isRunning = true;
        document.querySelector('.btn-start').textContent = '시뮬레이션 중지';
        document.querySelector('.btn-start').classList.add('btn-stop');
        
        startAutoSimulation();
        startDashboardUpdates();
        
        // 실시간 상태 업데이트
        updateRealTimeStatus();
        
        showNotification('시뮬레이션이 시작되었습니다! 실시간으로 데이터가 생성되고 대시보드에 반영됩니다.', 'success');
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
    
    if (simulationState.dashboardUpdateInterval) {
        clearInterval(simulationState.dashboardUpdateInterval);
        simulationState.dashboardUpdateInterval = null;
    }
    
    // 실시간 상태 업데이트
    updateRealTimeStatus();
    
    showNotification('시뮬레이션이 중지되었습니다.', 'info');
}

// 자동 시뮬레이션
function startAutoSimulation() {
    simulationState.autoSimulation = setInterval(() => {
        if (!simulationState.isRunning) return;
        
        // 랜덤하게 버전 선택 (50:50)
        const version = Math.random() < 0.5 ? 'A' : 'B';
        
        // 노출 기록
        recordInteraction(version, 'view');
        
        // 일정 확률로 클릭 시뮬레이션 (30% 확률)
        if (Math.random() < 0.3) {
            setTimeout(() => {
                recordInteraction(version, 'click');
                
                // 클릭 후 일정 확률로 구매 시뮬레이션 (20% 확률)
                if (Math.random() < 0.2) {
                    setTimeout(() => {
                        recordInteraction(version, 'purchase');
                    }, Math.random() * 2000 + 1000); // 1-3초 후 구매
                }
            }, Math.random() * 1000 + 500); // 0.5-1.5초 후 클릭
        }
    }, 2000); // 2초마다 새로운 방문자
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
    
    try {
        const response = await fetch('http://localhost:8000/api/abtest/interaction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                test_id: simulationState.testId,
                variant: version === 'A' ? 'baseline' : 'challenger',
                interaction_type: interactionType,
                timestamp: new Date().toISOString()
            })
        });
        
        if (response.ok) {
            // 로컬 통계 업데이트
            if (interactionType === 'view') {
                simulationState.stats[`version${version}`].views++;
            } else if (interactionType === 'purchase') {
                simulationState.stats[`version${version}`].purchases++;
            }
            
            updateStats();
            
            // 상호작용 발생 시 즉시 대시보드 업데이트
            updateDashboardIfOpen();
            
            // 실시간 알림 (구매 시에만)
            if (interactionType === 'purchase') {
                showNotification(`버전 ${version}에서 구매 발생! (테스트 ID: ${simulationState.testId})`, 'success');
            }
        } else {
            console.error('상호작용 기록 실패');
        }
    } catch (error) {
        console.error('상호작용 기록 오류:', error);
    }
}

// 통계 업데이트
function updateStats() {
    const stats = simulationState.stats;
    
    // 기본 통계
    document.getElementById('viewsA').textContent = stats.versionA.views;
    document.getElementById('viewsB').textContent = stats.versionB.views;
    document.getElementById('purchasesA').textContent = stats.versionA.purchases;
    document.getElementById('purchasesB').textContent = stats.versionB.purchases;
    
    // 전환율 계산
    const conversionA = stats.versionA.views > 0 ? (stats.versionA.purchases / stats.versionA.views * 100) : 0;
    const conversionB = stats.versionB.views > 0 ? (stats.versionB.purchases / stats.versionB.views * 100) : 0;
    
    document.getElementById('conversionA').textContent = `${conversionA.toFixed(2)}%`;
    document.getElementById('conversionB').textContent = `${conversionB.toFixed(2)}%`;
    
    // 개선율 계산
    const improvement = conversionA > 0 ? ((conversionB - conversionA) / conversionA * 100) : 0;
    document.getElementById('improvement').textContent = `${improvement.toFixed(2)}%`;
    
    // 통계적 유의성 계산 (간단한 버전)
    const significance = calculateSignificance(stats);
    document.getElementById('significance').textContent = significance;
    
    // 색상 변경으로 승자 표시
    updateWinnerDisplay(conversionA, conversionB);
}

// 통계적 유의성 계산 (간단한 버전)
function calculateSignificance(stats) {
    const n1 = stats.versionA.views;
    const n2 = stats.versionB.views;
    const p1 = stats.versionA.purchases / Math.max(n1, 1);
    const p2 = stats.versionB.purchases / Math.max(n2, 1);
    
    if (n1 < 10 || n2 < 10) {
        return '부족한 데이터';
    }
    
    // 간단한 z-test
    const pooledP = (stats.versionA.purchases + stats.versionB.purchases) / (n1 + n2);
    const se = Math.sqrt(pooledP * (1 - pooledP) * (1/n1 + 1/n2));
    const z = (p2 - p1) / se;
    
    if (Math.abs(z) > 1.96) {
        return '유의함 (95%)';
    } else if (Math.abs(z) > 1.645) {
        return '유의함 (90%)';
    } else {
        return '유의하지 않음';
    }
}

// 승자 표시 업데이트
function updateWinnerDisplay(conversionA, conversionB) {
    const versionACard = document.getElementById('versionA');
    const versionBCard = document.getElementById('versionB');
    
    // 기존 스타일 제거
    versionACard.style.borderColor = '#e2e8f0';
    versionBCard.style.borderColor = '#e2e8f0';
    versionACard.style.backgroundColor = 'white';
    versionBCard.style.backgroundColor = 'white';
    
    // 승자 표시
    if (conversionB > conversionA && conversionA > 0) {
        versionBCard.style.borderColor = '#38a169';
        versionBCard.style.backgroundColor = '#f0fff4';
    } else if (conversionA > conversionB && conversionB > 0) {
        versionACard.style.borderColor = '#38a169';
        versionACard.style.backgroundColor = '#f0fff4';
    }
}

// 시뮬레이션 초기화
function resetSimulation() {
    stopSimulation();
    
    simulationState.stats = {
        versionA: { views: 0, purchases: 0 },
        versionB: { views: 0, purchases: 0 }
    };
    
    updateStats();
    showNotification('시뮬레이션이 초기화되었습니다.', 'info');
}

// 테스트 데이터 초기화
async function resetTestData() {
    if (!confirm('정말로 모든 테스트 데이터를 초기화하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
        return;
    }
    
    try {
        const response = await fetch('http://localhost:8000/api/abtest/cleanup', {
            method: 'DELETE'
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(result.message, 'success');
            resetSimulation();
            loadTestList();
        } else {
            throw new Error('데이터 초기화 실패');
        }
    } catch (error) {
        console.error('데이터 초기화 오류:', error);
        showNotification('데이터 초기화 중 오류가 발생했습니다.', 'error');
    }
}

// 새 테스트 생성
async function generateNewTest() {
    try {
        const productNames = [
            '노트북 Ultra Pro',
            '무선 이어폰 Premium',
            '스마트워치 Elite',
            '태블릿 Pro Max',
            '게이밍 마우스 RGB'
        ];
        
        const descriptions = [
            '최고의 성능을 자랑하는 프리미엄 제품입니다.',
            '혁신적인 기술로 완성된 최신 제품!',
            '사용자 경험을 극대화한 프리미엄 모델입니다.',
            'AI 기술이 적용된 스마트한 제품입니다.',
            '디자인과 기능을 모두 만족하는 완벽한 제품!'
        ];
        
        const randomProduct = productNames[Math.floor(Math.random() * productNames.length)];
        const randomDesc = descriptions[Math.floor(Math.random() * descriptions.length)];
        
        // 제품 정보 업데이트
        document.getElementById('titleA').textContent = randomProduct;
        document.getElementById('titleB').textContent = randomProduct;
        document.getElementById('descA').textContent = randomDesc;
        document.getElementById('descB').textContent = randomDesc.replace(/입니다\.$/, '!').replace(/입니다\.$/, '!');
        
        showNotification('새로운 테스트 제품이 생성되었습니다.', 'success');
    } catch (error) {
        console.error('새 테스트 생성 오류:', error);
        showNotification('새 테스트 생성 중 오류가 발생했습니다.', 'error');
    }
}

// 알림 표시
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// 대시보드 열기
function openDashboard() {
    window.open('dashboard.html', '_blank');
}

// AI 분석 열기
function openAIAnalysis() {
    if (!simulationState.testId) {
        showNotification('먼저 테스트를 선택해주세요.', 'error');
        return;
    }
    window.open(`dashboard.html?testId=${simulationState.testId}&view=analysis`, '_blank');
}

// 테스트 히스토리 열기
function openTestHistory() {
    window.open('dashboard.html?view=history', '_blank');
}

// 키보드 단축키
document.addEventListener('keydown', function(event) {
    switch(event.key) {
        case '1':
            recordInteraction('A', 'view');
            break;
        case '2':
            recordInteraction('B', 'view');
            break;
        case 'q':
            recordInteraction('A', 'click');
            recordInteraction('A', 'purchase');
            break;
        case 'w':
            recordInteraction('B', 'click');
            recordInteraction('B', 'purchase');
            break;
        case 'r':
            resetSimulation();
            break;
        case 's':
            if (!simulationState.isRunning) {
                startSimulation();
            }
            break;
    }
});

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', function() {
    if (simulationState.autoSimulation) {
        clearInterval(simulationState.autoSimulation);
    }
    if (simulationState.dashboardUpdateInterval) {
        clearInterval(simulationState.dashboardUpdateInterval);
    }
});
