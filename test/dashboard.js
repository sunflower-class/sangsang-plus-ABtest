// API 기본 URL
const API_BASE_URL = 'http://localhost:8000';

// 차트 인스턴스
let performanceChart = null;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    startAutoRefresh();
});

// 대시보드 초기화
async function initializeDashboard() {
    try {
        await Promise.all([
            loadCurrentTests(),
            loadMetrics(),
            loadRecentResults(),
            loadLogs(),
            initializeChart()
        ]);
    } catch (error) {
        console.error('대시보드 초기화 오류:', error);
        showNotification('대시보드 로딩 중 오류가 발생했습니다.', 'error');
    }
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 테스트 생성 폼
    const createTestForm = document.getElementById('createTestForm');
    if (createTestForm) {
        createTestForm.addEventListener('submit', handleCreateTest);
    }

    // 새로고침 버튼 (필요시 추가)
    const refreshButton = document.createElement('button');
    refreshButton.textContent = '🔄 새로고침';
    refreshButton.className = 'btn-primary';
    refreshButton.style.marginTop = '10px';
    refreshButton.onclick = initializeDashboard;
    document.querySelector('header').appendChild(refreshButton);
}

// 자동 새로고침 설정
function startAutoRefresh() {
    setInterval(async () => {
        try {
            await Promise.all([
                loadCurrentTests(),
                loadMetrics(),
                loadRecentResults(),
                loadLogs()
            ]);
        } catch (error) {
            console.error('자동 새로고침 오류:', error);
        }
    }, 30000); // 30초마다 새로고침
}

// 테스트 생성 처리
async function handleCreateTest(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const productName = formData.get('productName');
    const testDuration = parseInt(formData.get('testDuration'));
    
    if (!productName.trim()) {
        showNotification('상품명을 입력해주세요.', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_name: productName,
                test_duration_days: testDuration
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification('테스트가 성공적으로 생성되었습니다!', 'success');
            event.target.reset();
            await initializeDashboard(); // 대시보드 새로고침
        } else {
            const error = await response.json();
            showNotification(`테스트 생성 실패: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('테스트 생성 오류:', error);
        showNotification('테스트 생성 중 오류가 발생했습니다.', 'error');
    }
}

// 현재 테스트 현황 로드
async function loadCurrentTests() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/list`);
        if (response.ok) {
            const data = await response.json();
            const tests = data.tests || data; // API 응답 형식에 따라 조정
            
            // tests가 배열인지 확인
            if (!Array.isArray(tests)) {
                console.error('테스트 데이터가 배열이 아닙니다:', tests);
                document.getElementById('currentTests').innerHTML = '<p>테스트 데이터 형식 오류</p>';
                return;
            }
            
            displayCurrentTests(tests);
        } else {
            throw new Error('테스트 목록을 불러올 수 없습니다.');
        }
    } catch (error) {
        console.error('테스트 로드 오류:', error);
        document.getElementById('currentTests').innerHTML = 
            '<p style="color: #e53e3e;">테스트 데이터를 불러올 수 없습니다.</p>';
    }
}

// 테스트 현황 표시
function displayCurrentTests(tests) {
    const container = document.getElementById('currentTests');
    
    if (!tests || tests.length === 0) {
        container.innerHTML = '<p>현재 활성 테스트가 없습니다.</p>';
        return;
    }
    
    const activeTests = tests.filter(test => test.status === 'active');
    const completedTests = tests.filter(test => test.status === 'completed');
    
    let html = '';
    
    if (activeTests.length > 0) {
        html += '<h3>🟢 활성 테스트</h3>';
        activeTests.forEach(test => {
            html += createTestCard(test);
        });
    }
    
    if (completedTests.length > 0) {
        html += '<h3 style="margin-top: 20px;">🔵 완료된 테스트</h3>';
        completedTests.slice(0, 3).forEach(test => {
            html += createTestCard(test);
        });
    }
    
    container.innerHTML = html;
}

// 테스트 카드 생성
function createTestCard(test) {
    const startDate = new Date(test.created_at).toLocaleDateString('ko-KR');
    const endDate = test.end_date ? new Date(test.end_date).toLocaleDateString('ko-KR') : '진행 중';
    
    // API에서 반환하는 필드명에 맞춰 수정
    const testName = test.name || test.product_name || 'Unknown Test';
    
    // A/B 버전 정보 추가
    const versionInfo = `
        <div style="margin: 10px 0; padding: 8px; background: #f7fafc; border-radius: 6px; font-size: 0.9rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span><strong>버전 A (현재):</strong> ${test.baseline_description || '기존 버전'}</span>
                <span style="color: #667eea;">노출: ${test.baseline_impressions || 0} | 구매: ${test.baseline_purchases || 0}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span><strong>버전 B (AI 생성):</strong> ${test.challenger_description || 'AI 생성 버전'}</span>
                <span style="color: #764ba2;">노출: ${test.challenger_impressions || 0} | 구매: ${test.challenger_purchases || 0}</span>
            </div>
        </div>
    `;
    
    return `
        <div class="test-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                <h3>${testName}</h3>
                <button onclick="deleteTest(${test.id}, '${testName}')" 
                        style="background: #e53e3e; color: white; border: none; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; cursor: pointer;">
                    삭제
                </button>
            </div>
            <div style="margin-bottom: 10px;">
                <span class="status-badge status-${test.status}">${getStatusText(test.status)}</span>
                <span style="margin-left: 10px; color: #718096; font-size: 0.9rem;">
                    ${startDate} ~ ${endDate}
                </span>
            </div>
            ${versionInfo}
            <div class="test-stats">
                <div class="test-stat">
                    <div class="value">${test.total_impressions || 0}</div>
                    <div class="label">총 노출</div>
                </div>
                <div class="test-stat">
                    <div class="value">${test.total_clicks || 0}</div>
                    <div class="label">총 클릭</div>
                </div>
                <div class="test-stat">
                    <div class="value">${test.total_purchases || 0}</div>
                    <div class="label">총 구매</div>
                </div>
            </div>
            ${test.winner ? `<p style="margin-top: 10px; color: #38a169; font-weight: 600;">🏆 승자: ${test.winner}</p>` : ''}
        </div>
    `;
}

// 상태 텍스트 변환
function getStatusText(status) {
    const statusMap = {
        'active': '활성',
        'completed': '완료',
        'paused': '일시정지'
    };
    return statusMap[status] || status;
}

// 메트릭 로드
async function loadMetrics() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/analytics/overview`);
        if (response.ok) {
            const metrics = await response.json();
            displayMetrics(metrics);
        } else {
            throw new Error('메트릭을 불러올 수 없습니다.');
        }
    } catch (error) {
        console.error('메트릭 로드 오류:', error);
        // 기본값 표시
        displayMetrics({
            total_tests: 0,
            active_tests: 0,
            total_interactions: 0,
            conversion_rate: 0
        });
    }
}

// 메트릭 표시
function displayMetrics(metrics) {
    document.getElementById('totalTests').textContent = metrics.total_tests || 0;
    document.getElementById('activeTests').textContent = metrics.active_tests || 0;
    document.getElementById('totalInteractions').textContent = metrics.total_interactions || 0;
    document.getElementById('conversionRate').textContent = `${(metrics.conversion_rate || 0).toFixed(2)}%`;
}

// 최근 결과 로드
async function loadRecentResults() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/results`);
        if (response.ok) {
            const data = await response.json();
            const results = data.results || data; // API 응답 형식에 따라 조정
            
            // results가 배열인지 확인
            if (!Array.isArray(results)) {
                console.error('결과 데이터가 배열이 아닙니다:', results);
                document.getElementById('recentResults').innerHTML = '<p>결과 데이터 형식 오류</p>';
                return;
            }
            
            displayRecentResults(results);
        } else {
            throw new Error('결과를 불러올 수 없습니다.');
        }
    } catch (error) {
        console.error('결과 로드 오류:', error);
        document.getElementById('recentResults').innerHTML = 
            '<p style="color: #e53e3e;">결과 데이터를 불러올 수 없습니다.</p>';
    }
}

// 최근 결과 표시
function displayRecentResults(results) {
    const container = document.getElementById('recentResults');
    
    if (!results || results.length === 0) {
        container.innerHTML = '<p>완료된 테스트 결과가 없습니다.</p>';
        return;
    }
    
    let html = '<div style="display: grid; gap: 15px;">';
    results.slice(0, 5).forEach(result => {
        const testName = result.test_id || `테스트 ${result.id}`;
        const createdDate = result.created_at ? new Date(result.created_at).toLocaleDateString('ko-KR') : 'N/A';
        const winner = result.winner_variant_id ? `버전 ${result.winner_variant_id}` : '결정되지 않음';
        const confidence = result.confidence_level ? `${(result.confidence_level * 100).toFixed(1)}%` : 'N/A';
        
        html += `
            <div class="test-card">
                <h3>${testName}</h3>
                <p><strong>테스트 ID:</strong> ${result.test_id}</p>
                <p><strong>생성일:</strong> ${createdDate}</p>
                <p><strong>승자:</strong> ${winner}</p>
                <p><strong>승자 점수:</strong> ${result.winner_score ? result.winner_score.toFixed(2) : 'N/A'}</p>
                <p><strong>신뢰도:</strong> ${confidence}</p>
                <p><strong>총 노출:</strong> ${result.total_impressions || 0}</p>
                <p><strong>총 구매:</strong> ${result.total_purchases || 0}</p>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

// 로그 로드
async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/logs`);
        if (response.ok) {
            const data = await response.json();
            const logs = data.logs || data; // API 응답 형식에 따라 조정
            
            // logs가 배열인지 확인
            if (!Array.isArray(logs)) {
                console.error('로그 데이터가 배열이 아닙니다:', logs);
                document.getElementById('logs').innerHTML = '<p>로그 데이터 형식 오류</p>';
                return;
            }
            
            displayLogs(logs);
        } else {
            throw new Error('로그를 불러올 수 없습니다.');
        }
    } catch (error) {
        console.error('로그 로드 오류:', error);
        document.getElementById('logs').innerHTML = 
            '<p style="color: #e53e3e;">로그를 불러올 수 없습니다.</p>';
    }
}

// 로그 표시
function displayLogs(logs) {
    const container = document.getElementById('logs');
    
    if (!logs || logs.length === 0) {
        container.innerHTML = '<p>로그가 없습니다.</p>';
        return;
    }
    
    let html = '';
    logs.slice(-20).reverse().forEach(log => {
        const timestamp = new Date(log.timestamp).toLocaleTimeString('ko-KR');
        const levelClass = `log-level-${log.level}`;
        
        html += `
            <div class="log-entry">
                <span class="log-timestamp">${timestamp}</span>
                <span class="log-message ${levelClass}">${log.message}</span>
            </div>
        `;
    });
    
    container.innerHTML = html;
    container.scrollTop = container.scrollHeight; // 최신 로그로 스크롤
}

// 차트 초기화
async function initializeChart() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/analytics/performance`);
        if (response.ok) {
            const data = await response.json();
            const performanceData = data.performance || data; // API 응답 형식에 따라 조정
            
            // performanceData가 배열인지 확인
            if (!Array.isArray(performanceData)) {
                console.error('성과 데이터가 배열이 아닙니다:', performanceData);
                createPerformanceChart([]); // 빈 차트 생성
                return;
            }
            
            createPerformanceChart(performanceData);
        } else {
            throw new Error('성과 데이터를 불러올 수 없습니다.');
        }
    } catch (error) {
        console.error('차트 초기화 오류:', error);
        createPerformanceChart([]); // 빈 차트 생성
    }
}

// 성과 차트 생성
function createPerformanceChart(data) {
    const canvas = document.getElementById('performanceChart');
    const ctx = canvas.getContext('2d');
    
    // 캔버스 높이 강제 설정
    canvas.style.height = '400px';
    canvas.style.maxHeight = '400px';
    
    // 기존 차트가 있으면 완전히 제거
    if (performanceChart) {
        performanceChart.destroy();
        performanceChart = null;
    }
    
    // 데이터가 없으면 빈 차트 생성
    if (!data || data.length === 0) {
        const emptyChartData = {
            labels: ['데이터 없음'],
            datasets: [
                {
                    label: '전환율 (%)',
                    data: [0],
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 2,
                    tension: 0.1
                },
                {
                    label: '클릭률 (%)',
                    data: [0],
                    backgroundColor: 'rgba(118, 75, 162, 0.2)',
                    borderColor: 'rgba(118, 75, 162, 1)',
                    borderWidth: 2,
                    tension: 0.1
                }
            ]
        };
        
        performanceChart = new Chart(ctx, {
            type: 'line',
            data: emptyChartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: '테스트별 성과 비교 (데이터 없음)'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '비율 (%)'
                        }
                    }
                },
                layout: {
                    padding: {
                        top: 20,
                        bottom: 20
                    }
                }
            }
        });
        return;
    }
    
    const chartData = {
        labels: data.map(item => item.product_name || 'Unknown'),
        datasets: [
            {
                label: '전환율 (%)',
                data: data.map(item => item.conversion_rate || 0),
                backgroundColor: 'rgba(102, 126, 234, 0.2)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 2,
                tension: 0.1
            },
            {
                label: '클릭률 (%)',
                data: data.map(item => item.click_rate || 0),
                backgroundColor: 'rgba(118, 75, 162, 0.2)',
                borderColor: 'rgba(118, 75, 162, 1)',
                borderWidth: 2,
                tension: 0.1
            }
        ]
    };
    
    performanceChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: '테스트별 성과 비교'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '비율 (%)'
                    }
                }
            },
            layout: {
                padding: {
                    top: 20,
                    bottom: 20
                }
            }
        }
    });
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

// 유틸리티 함수: 날짜 포맷팅
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 유틸리티 함수: 숫자 포맷팅
function formatNumber(num) {
    return new Intl.NumberFormat('ko-KR').format(num);
}

// 유틸리티 함수: 퍼센트 포맷팅
function formatPercentage(num) {
    return `${(num * 100).toFixed(2)}%`;
}

// 테스트 삭제 함수
async function deleteTest(testId, testName) {
    if (!confirm(`테스트 "${testName}" (ID: ${testId})를 완전히 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없으며, 모든 관련 데이터가 삭제됩니다.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/test/${testId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(result.message, 'success');
            
            // 테스트 목록 새로고침
            await loadCurrentTests();
            await initializeChart();
        } else {
            throw new Error('테스트 삭제 실패');
        }
    } catch (error) {
        console.error('테스트 삭제 오류:', error);
        showNotification('테스트 삭제 중 오류가 발생했습니다.', 'error');
    }
}

// 오래된 테스트 정리 함수
async function cleanupOldTests() {
    if (!confirm('7일 이상 된 완료된 테스트들을 정리하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/cleanup`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(result.message, 'success');
            
            // 테스트 목록 새로고침
            await loadCurrentTests();
            await initializeChart();
        } else {
            throw new Error('테스트 정리 실패');
        }
    } catch (error) {
        console.error('테스트 정리 오류:', error);
        showNotification('테스트 정리 중 오류가 발생했습니다.', 'error');
    }
}
