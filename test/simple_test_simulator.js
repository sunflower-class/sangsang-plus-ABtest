// 시뮬레이션 상태
let simulationState = {
    isRunning: false,
    testId: null,
    stats: {
        versionA: { views: 0, purchases: 0 },
        versionB: { views: 0, purchases: 0 }
    },
    autoSimulation: null
};

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
                simulationState.testId = parseInt(selectedTestId); // 전역 변수에 저장
            }
        });
    }
    
    showNotification('시뮬레이터가 준비되었습니다. 테스트를 선택하고 "시뮬레이션 시작" 버튼을 클릭하세요.', 'info');
});

// 테스트 목록 로드
async function loadTestList() {
    try {
        const response = await fetch('http://localhost:8000/api/abtest/list');
        if (response.ok) {
            const data = await response.json();
            const tests = data.tests || data; // API 응답 형식에 따라 조정
            const select = document.getElementById('testSelect');
            
            // 요소가 존재하는지 확인
            if (!select) {
                console.error('testSelect 요소를 찾을 수 없습니다.');
                return;
            }
            
            // 기존 옵션 제거 (첫 번째 옵션 제외)
            select.innerHTML = '<option value="">테스트를 선택하세요...</option>';
            
            // tests가 배열인지 확인
            if (!Array.isArray(tests)) {
                console.error('테스트 데이터가 배열이 아닙니다:', tests);
                showNotification('테스트 데이터 형식 오류', 'error');
                return;
            }
            
            // 테스트 목록 추가
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
            
            // 버전별 설명 업데이트 (실제로는 AI 생성된 내용이어야 함)
            document.getElementById('descA').textContent = test.baseline_description || '기존 버전의 상품 설명입니다.';
            document.getElementById('descB').textContent = test.challenger_description || 'AI가 생성한 새로운 버전의 상품 설명입니다.';
            
            // 가격 정보 업데이트
            document.getElementById('priceA').textContent = `₩${test.baseline_price || '1,200,000'}`;
            document.getElementById('priceB').textContent = `₩${test.challenger_price || '1,200,000'}`;
            
            showNotification(`테스트 "${test.name || test.product_name}" 정보를 로드했습니다.`, 'info');
        }
    } catch (error) {
        console.error('테스트 정보 로드 오류:', error);
        showNotification('테스트 정보를 불러오는 중 오류가 발생했습니다.', 'error');
    }
}

// 시뮬레이션 시작
async function startSimulation() {
    if (simulationState.isRunning) {
        showNotification('시뮬레이션이 이미 실행 중입니다.', 'info');
        return;
    }
    
    // 선택된 테스트 확인
    const selectedTestId = document.getElementById('testSelect').value;
    if (!selectedTestId) {
        showNotification('시뮬레이션할 테스트를 선택해주세요.', 'error');
        return;
    }
    
    try {
        simulationState.testId = parseInt(selectedTestId);
        simulationState.isRunning = true;
        
        // 선택된 테스트 정보 가져오기
        const listResponse = await fetch('http://localhost:8000/api/abtest/list');
        if (listResponse.ok) {
            const data = await listResponse.json();
            const tests = data.tests || data; // API 응답 형식에 따라 조정
            const selectedTest = tests.find(test => test.id === simulationState.testId);
            
            if (selectedTest) {
                showNotification(`시뮬레이션이 시작되었습니다! (테스트: ${selectedTest.name}, ID: ${simulationState.testId})`, 'success');
                
                // 자동 시뮬레이션 시작
                startAutoSimulation();
                
                // 버튼 상태 변경
                document.querySelector('.btn-start').textContent = '시뮬레이션 중...';
                document.querySelector('.btn-start').disabled = true;
            } else {
                throw new Error('선택된 테스트를 찾을 수 없습니다');
            }
        } else {
            throw new Error('테스트 목록 조회 실패');
        }
    } catch (error) {
        console.error('시뮬레이션 시작 오류:', error);
        showNotification('시뮬레이션 시작 중 오류가 발생했습니다.', 'error');
    }
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
    const totalA = stats.versionA.views;
    const totalB = stats.versionB.views;
    const purchasesA = stats.versionA.purchases;
    const purchasesB = stats.versionB.purchases;
    
    if (totalA < 10 || totalB < 10) {
        return '데이터 부족';
    }
    
    const rateA = purchasesA / totalA;
    const rateB = purchasesB / totalB;
    
    // 간단한 z-test
    const pooledRate = (purchasesA + purchasesB) / (totalA + totalB);
    const standardError = Math.sqrt(pooledRate * (1 - pooledRate) * (1/totalA + 1/totalB));
    const zScore = Math.abs(rateB - rateA) / standardError;
    
    if (zScore > 1.96) {
        return '유의함 (95%)';
    } else if (zScore > 1.645) {
        return '유의함 (90%)';
    } else {
        return '유의하지 않음';
    }
}

// 승자 표시 업데이트
function updateWinnerDisplay(conversionA, conversionB) {
    const cardA = document.getElementById('versionA');
    const cardB = document.getElementById('versionB');
    
    // 기존 스타일 제거
    cardA.style.borderColor = '#e2e8f0';
    cardB.style.borderColor = '#e2e8f0';
    cardA.style.backgroundColor = 'white';
    cardB.style.backgroundColor = 'white';
    
    if (conversionB > conversionA && conversionA > 0) {
        cardB.style.borderColor = '#38a169';
        cardB.style.backgroundColor = '#f0fff4';
    } else if (conversionA > conversionB && conversionB > 0) {
        cardA.style.borderColor = '#38a169';
        cardA.style.backgroundColor = '#f0fff4';
    }
}

// 시뮬레이션 초기화
function resetSimulation() {
    simulationState.isRunning = false;
    simulationState.testId = null;
    simulationState.stats = {
        versionA: { views: 0, purchases: 0 },
        versionB: { views: 0, purchases: 0 }
    };
    
    if (simulationState.autoSimulation) {
        clearInterval(simulationState.autoSimulation);
        simulationState.autoSimulation = null;
    }
    
    updateStats();
    
    // 버튼 상태 복원
    document.querySelector('.btn-start').textContent = '시뮬레이션 시작';
    document.querySelector('.btn-start').disabled = false;
    
    // 카드 스타일 초기화
    document.getElementById('versionA').style.borderColor = '#e2e8f0';
    document.getElementById('versionB').style.borderColor = '#e2e8f0';
    document.getElementById('versionA').style.backgroundColor = 'white';
    document.getElementById('versionB').style.backgroundColor = 'white';
    
    showNotification('시뮬레이션이 초기화되었습니다.', 'info');
}

// 테스트 데이터 초기화 (데이터베이스에서 해당 테스트의 상호작용 데이터 삭제)
async function resetTestData() {
    const selectedTestId = document.getElementById('testSelect').value;
    if (!selectedTestId) {
        showNotification('초기화할 테스트를 선택해주세요.', 'error');
        return;
    }
    
    if (!confirm(`테스트 ID ${selectedTestId}의 모든 상호작용 데이터를 삭제하시겠습니까?`)) {
        return;
    }
    
    try {
        const response = await fetch(`http://localhost:8000/api/abtest/test/${selectedTestId}/reset`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            showNotification(`테스트 ID ${selectedTestId}의 데이터가 초기화되었습니다.`, 'success');
            resetSimulation(); // 로컬 통계도 초기화
        } else {
            throw new Error('데이터 초기화 실패');
        }
    } catch (error) {
        console.error('테스트 데이터 초기화 오류:', error);
        showNotification('테스트 데이터 초기화 중 오류가 발생했습니다.', 'error');
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
    
    // 3초 후 자동 제거
    setTimeout(() => {
        notification.remove();
    }, 3000);
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
});
