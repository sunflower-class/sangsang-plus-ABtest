// 전역 변수
let currentTestId = null;
let currentTestData = null;

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
        loadCurrentTests()
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
        product_price: parseFloat(formData.get('productPrice')),
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
                            <button onclick="deleteTest(${test.id}, '${test.name.replace(/'/g, "\\'")}')" class="btn-danger" style="background: #e53e3e; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-size: 0.8rem; cursor: pointer; margin-left: 5px;">삭제</button>
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
        if (data.ai_weights) {
            Object.entries(data.ai_weights).forEach(([key, value]) => {
            html += `
                <div class="ai-metric">
                    <div class="ai-metric-label">${key.toUpperCase()}</div>
                    <div class="ai-metric-value">${(value * 100).toFixed(1)}%</div>
                </div>
            `;
            });
        }
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
                            <div class="ai-metric-value confidence-clickable" 
                                 onclick="showConfidenceDetails(${JSON.stringify(variant.confidence_details).replace(/"/g, '&quot;')}, '${variant.variant_name}')" 
                                 style="cursor: pointer; text-decoration: underline;" 
                                 title="클릭하면 신뢰도 계산 세부사항을 볼 수 있습니다">
                                ${(variant.ai_confidence * 100).toFixed(1)}%
                            </div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">CVR (구매전환율)</div>
                            <div class="ai-metric-value">${(variant.cvr * 100).toFixed(2)}%</div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">장바구니 추가율</div>
                            <div class="ai-metric-value">${(variant.cart_add_rate * 100).toFixed(2)}%</div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">장바구니 전환율</div>
                            <div class="ai-metric-value">${(variant.cart_conversion_rate * 100).toFixed(2)}%</div>
                        </div>
                        <div class="ai-metric">
                            <div class="ai-metric-label">매출</div>
                            <div class="ai-metric-value">₩${variant.revenue.toLocaleString()}</div>
                        </div>

                        <div class="ai-metric">
                            <div class="ai-metric-label">클릭수</div>
                            <div class="ai-metric-value">${variant.clicks}</div>
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



// 개별 테스트 삭제
async function deleteTest(testId, testName) {
    if (!confirm(`"${testName}" 테스트를 정말 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`)) {
        return;
    }
    
    try {
        showMessage('테스트를 삭제하는 중...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/test/${testId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showMessage(`테스트 "${testName}"가 성공적으로 삭제되었습니다.`, 'success');
            loadCurrentTests();
        } else {
            const error = await response.json();
            showMessage(`테스트 삭제 실패: ${error.detail}`, 'error');
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
        if (currentTestId) {
            loadAIAnalysis();
        }
    }, 10000); // 10초마다 업데이트 (기존 30초에서 단축)
}

// 수동 새로고침
function manualRefresh() {
    showMessage('데이터를 새로고침하는 중...', 'info');
    
    Promise.all([
        loadCurrentTests()
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

// 신뢰도 계산 세부사항 표시
function showConfidenceDetails(details, variantName) {
    let modalContent = `
        <div style="background: white; padding: 20px; border-radius: 8px; max-width: 600px; margin: 50px auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h3 style="margin-top: 0; color: #2d3748;">${variantName} - 신뢰도 계산 세부사항</h3>
    `;
    
    if (details.calculation_method === 'statistical') {
        modalContent += `
            <div style="background: #f7fafc; padding: 15px; border-radius: 6px; margin: 15px 0;">
                <h4 style="color: #2b6cb0; margin-top: 0;">📊 통계적 신뢰도 계산</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 10px 0;">
                    <div><strong>샘플 크기:</strong> ${details.sample_size}번의 클릭</div>
                    <div><strong>전환율:</strong> ${details.conversion_rate}%</div>
                    <div><strong>표준 오차:</strong> ${details.std_error}</div>
                    <div><strong>오차 한계:</strong> ±${details.margin_of_error}%</div>
                </div>
            </div>
            
            <div style="background: #edf2f7; padding: 15px; border-radius: 6px; margin: 15px 0;">
                <h4 style="color: #2d3748; margin-top: 0;">🧮 계산 과정</h4>
                <div style="margin: 10px 0;">
                    <div><strong>1단계 - 기본 신뢰도:</strong> min(${details.sample_size}/300, 1.0) = ${details.base_confidence}%</div>
                    <div><strong>2단계 - 변동성 보정:</strong> (1 - ${details.margin_of_error/100}) = ${details.variability_factor}%</div>
                    <div><strong>3단계 - 최종 신뢰도:</strong> ${details.base_confidence}% × ${details.variability_factor}% = <strong>${details.final_confidence}%</strong></div>
                </div>
                <div style="background: #bee3f8; padding: 10px; border-radius: 4px; margin-top: 15px;">
                    <strong>📐 공식:</strong> ${details.formula}
                </div>
            </div>
            
            <div style="background: #f0fff4; padding: 15px; border-radius: 6px; margin: 15px 0;">
                <h4 style="color: #22543d; margin-top: 0;">💡 해석</h4>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>샘플이 클수록 신뢰도 증가 (최대 300클릭에서 100%)</li>
                    <li>전환율의 변동성이 클수록 신뢰도 감소</li>
                    <li>95% 신뢰구간을 기준으로 계산</li>
                    <li>최소 10% 신뢰도 보장</li>
                </ul>
            </div>
        `;
    } else {
        modalContent += `
            <div style="background: #fff5f5; padding: 15px; border-radius: 6px; margin: 15px 0;">
                <h4 style="color: #c53030; margin-top: 0;">⚠️ 제한된 신뢰도 (샘플 부족)</h4>
                <div style="margin: 10px 0;">
                    <div><strong>샘플 크기:</strong> ${details.sample_size}번의 클릭</div>
                    <div><strong>선형 신뢰도:</strong> ${details.linear_confidence}%</div>
                </div>
                <div style="background: #fed7d7; padding: 10px; border-radius: 4px; margin-top: 15px;">
                    <strong>📐 공식:</strong> ${details.formula}
                </div>
                <div style="background: #fef5e7; padding: 10px; border-radius: 4px; margin-top: 15px;">
                    <strong>💡 참고:</strong> 신뢰할 만한 통계 분석을 위해서는 최소 30회 이상의 클릭이 필요합니다.
                </div>
            </div>
        `;
    }
    
    modalContent += `
            <div style="text-align: center; margin-top: 20px;">
                <button onclick="closeConfidenceModal()" style="background: #3182ce; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer;">
                    닫기
                </button>
            </div>
        </div>
    `;
    
    // 모달 배경 생성
    const modalOverlay = document.createElement('div');
    modalOverlay.id = 'confidenceModal';
    modalOverlay.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
        background: rgba(0,0,0,0.5); z-index: 10000; overflow-y: auto;
    `;
    modalOverlay.innerHTML = modalContent;
    
    // 배경 클릭시 닫기
    modalOverlay.onclick = (e) => {
        if (e.target === modalOverlay) {
            closeConfidenceModal();
        }
    };
    
    document.body.appendChild(modalOverlay);
}

// 신뢰도 모달 닫기
function closeConfidenceModal() {
    const modal = document.getElementById('confidenceModal');
    if (modal) {
        modal.remove();
    }
}
