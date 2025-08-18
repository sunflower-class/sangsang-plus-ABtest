// 전역 변수
let currentTestId = null;
let currentTestData = null;
let performanceChart = null;

// API 기본 URL
const API_BASE_URL = 'http://localhost:8000/api/abtest';

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    startPeriodicUpdates();
    setupMessageListener();
});

// 메시지 리스너 설정 (시뮬레이터와의 통신)
function setupMessageListener() {
    window.addEventListener('message', function(event) {
        if (event.data.type === 'SIMULATION_UPDATE') {
            console.log('시뮬레이터에서 업데이트 수신:', event.data);
            handleSimulationUpdate(event.data);
        }
    });
}

// 시뮬레이터 업데이트 처리
function handleSimulationUpdate(data) {
    console.log('시뮬레이터에서 업데이트 수신:', data);
    
    // 즉시 모든 데이터 새로고침
    Promise.all([
        loadCurrentTests(),
        loadAnalyticsOverview(),
        loadPerformanceData(),
        loadRecentResults(),
        loadLogs()
    ]).then(() => {
        // 특정 테스트가 선택되어 있다면 해당 테스트 정보도 업데이트
        if (data.testId && currentTestId === data.testId) {
            loadAIAnalysis();
            loadWinnerStatus(data.testId);
        }
        
        // 시뮬레이션 상태 표시
        showMessage(`시뮬레이터에서 실시간 데이터 업데이트: 테스트 ${data.testId}`, 'info');
    }).catch(error => {
        console.error('실시간 업데이트 중 오류:', error);
    });
}

// 대시보드 초기화
function initializeDashboard() {
    loadCurrentTests();
    loadAnalyticsOverview();
    loadPerformanceData();
    loadRecentResults();
    loadLogs();
    
    // URL 파라미터 처리
    handleUrlParameters();
}

// URL 파라미터 처리
function handleUrlParameters() {
    const urlParams = new URLSearchParams(window.location.search);
    const testId = urlParams.get('testId');
    const view = urlParams.get('view');
    
    if (testId) {
        currentTestId = parseInt(testId);
        viewTestDetails(currentTestId);
        showMessage(`테스트 ${testId}가 선택되었습니다.`, 'info');
    }
    
    if (view) {
        switch (view) {
            case 'create':
                showCreateTestSection();
                showMessage('새 A/B 테스트 생성 모드입니다.', 'info');
                break;
            case 'analysis':
                showAnalysisSection();
                if (currentTestId) {
                    loadAIAnalysis();
                }
                showMessage('AI 분석 뷰가 로드되었습니다.', 'info');
                break;
            case 'history':
                showHistorySection();
                loadRecentResults();
                showMessage('테스트 히스토리 뷰가 로드되었습니다.', 'info');
                break;
            case 'simulation':
                showMessage('시뮬레이터에서 전환되었습니다. 실시간 데이터를 확인하세요.', 'info');
                break;
        }
    }
}

// 새 테스트 생성 섹션 표시
function showCreateTestSection() {
    // 모든 섹션 숨기기
    hideAllSections();
    
    // 테스트 생성 섹션만 표시
    const createSection = document.querySelector('.card:has(#createImageTestForm)');
    if (createSection) {
        createSection.style.display = 'block';
    }
    
    // 페이지 제목 변경
    document.querySelector('header h1').textContent = '🆕 새 A/B 테스트 생성';
}

// AI 분석 섹션 표시
function showAnalysisSection() {
    // 모든 섹션 숨기기
    hideAllSections();
    
    // AI 분석 관련 섹션들 표시
    const analysisSection = document.querySelector('.card:has(#aiAnalysis)');
    const currentTestsSection = document.querySelector('.card:has(#currentTests)');
    
    if (analysisSection) analysisSection.style.display = 'block';
    if (currentTestsSection) currentTestsSection.style.display = 'block';
    
    // 페이지 제목 변경
    document.querySelector('header h1').textContent = '🧠 AI 분석 결과';
}

// 히스토리 섹션 표시
function showHistorySection() {
    // 모든 섹션 숨기기
    hideAllSections();
    
    // 히스토리 관련 섹션들 표시
    const resultsSection = document.querySelector('.card:has(#recentResults)');
    const logsSection = document.querySelector('.card:has(#logs)');
    const performanceSection = document.querySelector('.card:has(#performanceChart)');
    
    if (resultsSection) resultsSection.style.display = 'block';
    if (logsSection) logsSection.style.display = 'block';
    if (performanceSection) performanceSection.style.display = 'block';
    
    // 페이지 제목 변경
    document.querySelector('header h1').textContent = '📈 테스트 히스토리';
}

// 모든 섹션 숨기기
function hideAllSections() {
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.style.display = 'none';
    });
}

// 모든 섹션 표시 (기본 뷰)
function showAllSections() {
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.style.display = 'block';
    });
    
    // 페이지 제목 복원
    document.querySelector('header h1').textContent = '🤖 AI 기반 A/B 테스트 자동화 플랫폼';
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 이미지 기반 A/B 테스트 생성 폼
    document.getElementById('createImageTestForm').addEventListener('submit', handleCreateImageTest);
    
    // 다음 사이클 생성 폼
    document.getElementById('nextCycleForm').addEventListener('submit', handleNextCycle);
}

// 이미지 기반 A/B 테스트 생성
async function handleCreateImageTest(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const testData = {
        name: formData.get('testName'),
        product_id: formData.get('productId'),
        baseline_image_url: formData.get('baselineImageUrl'),
        challenger_image_url: formData.get('challengerImageUrl'),
        test_duration_days: parseInt(formData.get('testDuration')),
        min_sample_size: parseInt(formData.get('minSampleSize'))
    };
    
    try {
        showMessage('A/B 테스트를 생성하는 중...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/with-images`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(testData)
        });
        
        if (response.ok) {
            const result = await response.json();
            currentTestId = result.id;
            showMessage('A/B 테스트가 성공적으로 생성되었습니다!', 'success');
            event.target.reset();
            loadCurrentTests();
        } else {
            const error = await response.json();
            showMessage(`테스트 생성 실패: ${error.detail}`, 'error');
        }
    } catch (error) {
        showMessage(`오류 발생: ${error.message}`, 'error');
    }
}

// 승자 선택
async function selectWinner(variantType) {
    if (!currentTestId) {
        showMessage('선택할 테스트가 없습니다.', 'error');
        return;
    }
    
    try {
        // 현재 테스트의 버전 정보 가져오기
        const statusResponse = await fetch(`${API_BASE_URL}/test/${currentTestId}/winner-status`);
        const statusData = await statusResponse.json();
        
        let variantId = null;
        if (variantType === 'baseline') {
            variantId = statusData.variants.find(v => v.variant_type === 'baseline')?.id;
        } else {
            variantId = statusData.variants.find(v => v.variant_type === 'challenger')?.id;
        }
        
        if (!variantId) {
            showMessage('버전을 찾을 수 없습니다.', 'error');
            return;
        }
        
        showMessage('승자를 선택하는 중...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/test/${currentTestId}/select-winner/${variantId}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const result = await response.json();
            showMessage(`승자 선택 완료: ${variantType === 'baseline' ? 'A안' : 'B안'}`, 'success');
            hideWinnerSelection();
            showNextCycleForm();
            loadCurrentTests();
        } else {
            const error = await response.json();
            showMessage(`승자 선택 실패: ${error.detail}`, 'error');
        }
    } catch (error) {
        showMessage(`오류 발생: ${error.message}`, 'error');
    }
}

// 다음 사이클 생성
async function handleNextCycle(event) {
    event.preventDefault();
    
    if (!currentTestId) {
        showMessage('이전 테스트가 없습니다.', 'error');
        return;
    }
    
    const formData = new FormData(event.target);
    const cycleData = {
        challenger_image_url: formData.get('newChallengerImageUrl')
    };
    
    try {
        showMessage('다음 테스트 사이클을 생성하는 중...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/test/${currentTestId}/next-cycle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(cycleData)
        });
        
        if (response.ok) {
            const result = await response.json();
            currentTestId = result.new_test_id;
            showMessage(`다음 사이클 생성 완료: ${result.new_test_name}`, 'success');
            event.target.reset();
            hideNextCycleForm();
            loadCurrentTests();
        } else {
            const error = await response.json();
            showMessage(`사이클 생성 실패: ${error.detail}`, 'error');
        }
    } catch (error) {
        showMessage(`오류 발생: ${error.message}`, 'error');
    }
}

// AI 승자 결정 요청
async function requestAIWinnerDetermination(testId) {
    try {
        const response = await fetch(`${API_BASE_URL}/test/${testId}/determine-winner`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const result = await response.json();
            showMessage('AI 승자 결정이 완료되었습니다!', 'success');
            showWinnerSelection(testId);
            loadCurrentTests();
        } else {
            const error = await response.json();
            showMessage(`AI 승자 결정 실패: ${error.detail}`, 'error');
        }
    } catch (error) {
        showMessage(`오류 발생: ${error.message}`, 'error');
    }
}

// 승자 선택 UI 표시
function showWinnerSelection(testId) {
    currentTestId = testId;
    document.getElementById('winnerSelectionCard').style.display = 'block';
    loadWinnerStatus(testId);
}

// 승자 선택 UI 숨기기
function hideWinnerSelection() {
    document.getElementById('winnerSelectionCard').style.display = 'none';
}

// 다음 사이클 폼 표시
function showNextCycleForm() {
    document.getElementById('nextCycleCard').style.display = 'block';
}

// 다음 사이클 폼 숨기기
function hideNextCycleForm() {
    document.getElementById('nextCycleCard').style.display = 'none';
}

// 승자 상태 로드
async function loadWinnerStatus(testId) {
    try {
        const response = await fetch(`${API_BASE_URL}/test/${testId}/winner-status`);
        const data = await response.json();
        
        const aiWinnerInfo = document.getElementById('aiWinnerInfo');
        if (data.ai_winner_id) {
            const aiWinner = data.variants.find(v => v.id === data.ai_winner_id);
            aiWinnerInfo.textContent = `AI가 ${aiWinner.name}을(를) 승자로 결정했습니다. (AI 점수: ${aiWinner.ai_score.toFixed(3)})`;
        } else {
            aiWinnerInfo.textContent = 'AI 승자 결정을 기다리는 중입니다.';
        }
    } catch (error) {
        console.error('승자 상태 로드 실패:', error);
    }
}

// 현재 테스트 목록 로드
async function loadCurrentTests() {
    try {
        const response = await fetch(`${API_BASE_URL}/list`);
        const data = await response.json();
        
        const container = document.getElementById('currentTests');
        
        if (data.tests && data.tests.length > 0) {
            let html = '<div class="test-list">';
            data.tests.forEach(test => {
                const statusClass = getStatusClass(test.status);
                html += `
                    <div class="test-item">
                        <h4>${test.name} <span class="test-status ${statusClass}">${test.status}</span></h4>
                        <p>상품 ID: ${test.product_id}</p>
                        <p>생성일: ${new Date(test.created_at).toLocaleDateString()}</p>
                        <div class="test-actions">
                            <button onclick="viewTestDetails(${test.id})" class="btn-secondary">상세보기</button>
                            ${test.status === 'active' ? `<button onclick="requestAIWinnerDetermination(${test.id})" class="btn-primary">AI 승자 결정</button>` : ''}
                            ${test.status === 'waiting_for_winner_selection' ? `<button onclick="showWinnerSelection(${test.id})" class="btn-winner">승자 선택</button>` : ''}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<p>현재 활성 테스트가 없습니다.</p>';
        }
    } catch (error) {
        console.error('테스트 목록 로드 실패:', error);
        document.getElementById('currentTests').innerHTML = '<p>테스트 목록을 불러오는 중 오류가 발생했습니다.</p>';
    }
}

// AI 분석 결과 로드
async function loadAIAnalysis() {
    if (!currentTestId) {
        document.getElementById('aiAnalysis').innerHTML = '<p>분석할 테스트를 선택하세요.</p>';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/test/${currentTestId}/ai-analysis`);
        const data = await response.json();
        
        const container = document.getElementById('aiAnalysis');
        let html = '<div class="ai-analysis-content">';
        
        // AI 가중치 표시
        html += '<div class="ai-analysis-item">';
        html += '<h4>AI 가중치</h4>';
        html += '<div class="ai-metrics">';
        Object.entries(data.ai_weights).forEach(([key, value]) => {
            html += `
                <div class="ai-metric">
                    <div class="ai-metric-label">${key.toUpperCase()}</div>
                    <div class="ai-metric-value">${(value * 100).toFixed(1)}%</div>
                </div>
            `;
        });
        html += '</div></div>';
        
        // 버전별 분석 결과
        data.variant_analysis.forEach(variant => {
            const scoreClass = getScoreClass(variant.ai_score);
            html += `
                <div class="ai-analysis-item">
                    <h4>${variant.variant_name}</h4>
                    <div class="ai-metrics">
                        <div class="ai-metric">
                            <div class="ai-metric-label">AI 점수</div>
                            <div class="ai-metric-value ${scoreClass}">${variant.ai_score.toFixed(3)}</div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">신뢰도</div>
                            <div class="ai-metric-value">${(variant.ai_confidence * 100).toFixed(1)}%</div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">CVR(상세→구매)</div>
                            <div class="ai-metric-value">${(variant.cvr_detail_to_purchase * 100).toFixed(2)}%</div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">CVR(클릭→구매)</div>
                            <div class="ai-metric-value">${(variant.cvr_click_to_purchase * 100).toFixed(2)}%</div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">장바구니 추가율</div>
                            <div class="ai-metric-value">${(variant.cart_add_rate * 100).toFixed(2)}%</div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">평균 세션시간</div>
                            <div class="ai-metric-value">${variant.avg_session_duration.toFixed(1)}초</div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">상세 조회수</div>
                            <div class="ai-metric-value">${variant.detail_page_views}</div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">이탈률</div>
                            <div class="ai-metric-value">${(variant.bounce_rate * 100).toFixed(1)}%</div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">로드시간</div>
                            <div class="ai-metric-value">${variant.avg_page_load_time.toFixed(2)}초</div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        container.innerHTML = html;
    } catch (error) {
        console.error('AI 분석 로드 실패:', error);
        document.getElementById('aiAnalysis').innerHTML = '<p>AI 분석 데이터를 불러오는 중 오류가 발생했습니다.</p>';
    }
}

// 테스트 상세보기
function viewTestDetails(testId) {
    currentTestId = testId;
    loadAIAnalysis();
    loadWinnerStatus(testId);
}

// 상태별 CSS 클래스 반환
function getStatusClass(status) {
    switch (status) {
        case 'active': return 'status-active';
        case 'waiting_for_winner_selection': return 'status-waiting';
        case 'completed': return 'status-completed';
        default: return '';
    }
}

// 점수별 CSS 클래스 반환
function getScoreClass(score) {
    if (score > 0.7) return 'ai-score-high';
    if (score > 0.4) return 'ai-score-medium';
    return 'ai-score-low';
}

// 메시지 표시
function showMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;
    
    document.body.insertBefore(messageDiv, document.body.firstChild);
    
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

// 기존 함수들 (수정 없이 유지)
async function loadAnalyticsOverview() {
    try {
        const response = await fetch(`${API_BASE_URL}/analytics/overview`);
        const data = await response.json();
        
        document.getElementById('totalTests').textContent = data.total_tests || 0;
        document.getElementById('activeTests').textContent = data.active_tests || 0;
        document.getElementById('totalInteractions').textContent = data.total_interactions || 0;
        document.getElementById('conversionRate').textContent = `${((data.conversion_rate || 0) * 100).toFixed(1)}%`;
        
        // 새로운 지표들 업데이트
        const cartAddRateElement = document.getElementById('cartAddRate');
        if (cartAddRateElement) {
            cartAddRateElement.textContent = `${((data.cart_add_rate || 0) * 100).toFixed(1)}%`;
        }
        
        const totalViewersElement = document.getElementById('totalDetailViewers');
        if (totalViewersElement) {
            totalViewersElement.textContent = data.total_detail_viewers || 0;
        }
        
        const totalRevenueElement = document.getElementById('totalRevenue');
        if (totalRevenueElement) {
            totalRevenueElement.textContent = `${(data.total_revenue || 0).toLocaleString()}원`;
        }
    } catch (error) {
        console.error('분석 개요 로드 실패:', error);
    }
}

async function loadPerformanceData() {
    try {
        const response = await fetch(`${API_BASE_URL}/analytics/performance`);
        const data = await response.json();
        
        if (data.performance && data.performance.length > 0) {
            updatePerformanceChart(data.performance);
        }
    } catch (error) {
        console.error('성과 데이터 로드 실패:', error);
    }
}

function updatePerformanceChart(performanceData) {
    const ctx = document.getElementById('performanceChart').getContext('2d');
    
    if (performanceChart) {
        performanceChart.destroy();
    }
    
    const labels = performanceData.map(item => item.product_name);
    
    // 새로운 지표 데이터
    const baselineCvrDetail = performanceData.map(item => item.baseline_cvr_detail || 0);
    const challengerCvrDetail = performanceData.map(item => item.challenger_cvr_detail || 0);
    const baselineCartRate = performanceData.map(item => item.baseline_cart_rate || 0);
    const challengerCartRate = performanceData.map(item => item.challenger_cart_rate || 0);
    const baselineCvrClick = performanceData.map(item => item.baseline_cvr_click || 0);
    const challengerCvrClick = performanceData.map(item => item.challenger_cvr_click || 0);
    
    performanceChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'A안 CVR (상세→구매)',
                    data: baselineCvrDetail,
                    backgroundColor: 'rgba(54, 162, 235, 0.8)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                },
                {
                    label: 'B안 CVR (상세→구매)',
                    data: challengerCvrDetail,
                    backgroundColor: 'rgba(255, 99, 132, 0.8)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1
                },
                {
                    label: 'A안 CVR (클릭→구매)',
                    data: baselineCvrClick,
                    backgroundColor: 'rgba(75, 192, 192, 0.8)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                },
                {
                    label: 'B안 CVR (클릭→구매)',
                    data: challengerCvrClick,
                    backgroundColor: 'rgba(255, 159, 64, 0.8)',
                    borderColor: 'rgba(255, 159, 64, 1)',
                    borderWidth: 1
                },
                {
                    label: 'A안 장바구니 추가율',
                    data: baselineCartRate,
                    backgroundColor: 'rgba(153, 102, 255, 0.8)',
                    borderColor: 'rgba(153, 102, 255, 1)',
                    borderWidth: 1
                },
                {
                    label: 'B안 장바구니 추가율',
                    data: challengerCartRate,
                    backgroundColor: 'rgba(255, 205, 86, 0.8)',
                    borderColor: 'rgba(255, 205, 86, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return (value * 100).toFixed(1) + '%';
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + (context.parsed.y * 100).toFixed(1) + '%';
                        }
                    }
                }
            },
            // 0값도 표시되도록 설정
            elements: {
                bar: {
                    minBarLength: 2
                }
            }
        }
    });
}

async function loadRecentResults() {
    try {
        const response = await fetch(`${API_BASE_URL}/analytics/performance`);
        const data = await response.json();
        
        const container = document.getElementById('recentResults');
        
        if (data.performance && data.performance.length > 0) {
            let html = '<div class="results-list">';
            data.performance.slice(0, 5).forEach(result => {
                const winnerBadge = result.winner === 'baseline' ? '<span class="badge winner">A안 승</span>' : 
                                  result.winner === 'challenger' ? '<span class="badge winner">B안 승</span>' : 
                                  '<span class="badge tie">무승부</span>';
                
                html += `
                    <div class="result-item">
                        <h4>${result.product_name} ${winnerBadge}</h4>
                        <div class="result-comparison">
                            <div class="variant-stats">
                                <h5>A안 (기존)</h5>
                                <p>상세 조회: ${result.baseline_detail_views} | 클릭: ${result.baseline_clicks} | 구매: ${result.baseline_purchases}</p>
                                <p>장바구니: ${result.baseline_cart_adds} | 평균 세션: ${result.baseline_avg_session}초</p>
                                <p>CVR(상세→구매): ${(result.baseline_cvr_detail * 100).toFixed(1)}% | CVR(클릭→구매): ${(result.baseline_cvr_click * 100).toFixed(1)}%</p>
                                <p>장바구니율: ${(result.baseline_cart_rate * 100).toFixed(1)}% | 이탈률: ${(result.baseline_bounce_rate * 100).toFixed(1)}%</p>
                            </div>
                            <div class="variant-stats">
                                <h5>B안 (AI)</h5>
                                <p>상세 조회: ${result.challenger_detail_views} | 클릭: ${result.challenger_clicks} | 구매: ${result.challenger_purchases}</p>
                                <p>장바구니: ${result.challenger_cart_adds} | 평균 세션: ${result.challenger_avg_session}초</p>
                                <p>CVR(상세→구매): ${(result.challenger_cvr_detail * 100).toFixed(1)}% | CVR(클릭→구매): ${(result.challenger_cvr_click * 100).toFixed(1)}%</p>
                                <p>장바구니율: ${(result.challenger_cart_rate * 100).toFixed(1)}% | 이탈률: ${(result.challenger_bounce_rate * 100).toFixed(1)}%</p>
                            </div>
                        </div>
                        ${result.improvement_rate !== 0 ? `<p class="improvement">CVR 개선율: ${result.improvement_rate > 0 ? '+' : ''}${result.improvement_rate}%</p>` : ''}
                        <div class="performance-metrics">
                            <small>A안 로드시간: ${result.baseline_load_time}초 | B안 로드시간: ${result.challenger_load_time}초</small>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<p>최근 결과가 없습니다.</p>';
        }
    } catch (error) {
        console.error('최근 결과 로드 실패:', error);
        document.getElementById('recentResults').innerHTML = '<p>결과를 불러올 수 없습니다.</p>';
    }
}

async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE_URL}/logs`);
        const data = await response.json();
        
        const container = document.getElementById('logs');
        
        if (data.logs && data.logs.length > 0) {
            let html = '<div class="logs-list">';
            data.logs.slice(0, 10).forEach(log => {
                html += `
                    <div class="log-item">
                        <span class="log-time">${new Date(log.timestamp).toLocaleString()}</span>
                        <span class="log-message">${log.message}</span>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<p>로그가 없습니다.</p>';
        }
    } catch (error) {
        console.error('로그 로드 실패:', error);
        document.getElementById('logs').innerHTML = '<p>로그를 불러오는 중 오류가 발생했습니다.</p>';
    }
}

async function cleanupOldTests() {
    try {
        const response = await fetch(`${API_BASE_URL}/cleanup`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            const result = await response.json();
            showMessage(result.message, 'success');
            loadCurrentTests();
        } else {
            const error = await response.json();
            showMessage(`정리 실패: ${error.detail}`, 'error');
        }
    } catch (error) {
        showMessage(`오류 발생: ${error.message}`, 'error');
    }
}

// 주기적 업데이트
function startPeriodicUpdates() {
    setInterval(() => {
        console.log('주기적 업데이트 실행...');
        loadCurrentTests();
        loadAnalyticsOverview();
        loadPerformanceData();
        if (currentTestId) {
            loadAIAnalysis();
        }
    }, 10000); // 10초마다 업데이트 (기존 30초에서 단축)
}

// 수동 새로고침
function manualRefresh() {
    showMessage('데이터를 새로고침하는 중...', 'info');
    
    Promise.all([
        loadCurrentTests(),
        loadAnalyticsOverview(),
        loadPerformanceData(),
        loadRecentResults(),
        loadLogs()
    ]).then(() => {
        if (currentTestId) {
            loadAIAnalysis();
            loadWinnerStatus(currentTestId);
        }
        showMessage('데이터 새로고침이 완료되었습니다!', 'success');
    }).catch(error => {
        console.error('수동 새로고침 중 오류:', error);
        showMessage('새로고침 중 오류가 발생했습니다.', 'error');
    });
}

