// API 기본 URL
const API_BASE_URL = 'http://localhost:8000';

// 테스트 결과 저장소
let testResults = {
    total: 0,
    passed: 0,
    failed: 0,
    results: {}
};

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    updateSummaryStats();
});

// 모든 테스트 실행
async function runAllTests() {
    clearResults();
    
    const basicTests = [
        testServerHealth,
        testCreateABTest,
        testListABTests,
        testRecordInteraction
    ];
    
    const advancedTests = [
        testAnalytics,
        testResults,
        testLogs,
        testScheduler
    ];
    
    const performanceTests = [
        testBulkData,
        testConcurrentRequests
    ];
    
    const allTests = [...basicTests, ...advancedTests, ...performanceTests];
    
    await runTestSuite(allTests, '모든 테스트');
}

// 기본 테스트만 실행
async function runBasicTests() {
    clearResults();
    
    const basicTests = [
        testServerHealth,
        testCreateABTest,
        testListABTests,
        testRecordInteraction
    ];
    
    await runTestSuite(basicTests, '기본 테스트');
}

// 고급 테스트만 실행
async function runAdvancedTests() {
    clearResults();
    
    const advancedTests = [
        testAnalytics,
        testResults,
        testLogs,
        testScheduler
    ];
    
    await runTestSuite(advancedTests, '고급 테스트');
}

// 테스트 스위트 실행
async function runTestSuite(tests, suiteName) {
    testResults.total = tests.length;
    testResults.passed = 0;
    testResults.failed = 0;
    
    updateSummaryStats();
    updateProgressBar(0);
    
    for (let i = 0; i < tests.length; i++) {
        try {
            await tests[i]();
            testResults.passed++;
        } catch (error) {
            testResults.failed++;
            console.error(`테스트 실패: ${tests[i].name}`, error);
        }
        
        updateSummaryStats();
        updateProgressBar((i + 1) / tests.length * 100);
        
        // 테스트 간 간격
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    showNotification(`${suiteName} 완료: ${testResults.passed}/${testResults.total} 성공`, 
                    testResults.failed === 0 ? 'success' : 'warning');
}

// 서버 상태 확인 테스트
async function testServerHealth() {
    const resultPanel = document.getElementById('healthResult');
    resultPanel.style.display = 'block';
    resultPanel.innerHTML = '테스트 실행 중...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        
        if (response.ok) {
            const data = await response.json();
            resultPanel.innerHTML = `✅ 성공\n\n응답:\n${JSON.stringify(data, null, 2)}`;
            testResults.results['health'] = { status: 'success', data };
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (error) {
        resultPanel.innerHTML = `❌ 실패\n\n오류:\n${error.message}`;
        testResults.results['health'] = { status: 'error', error: error.message };
        throw error;
    }
}

// A/B 테스트 생성 테스트
async function testCreateABTest() {
    const resultPanel = document.getElementById('createResult');
    resultPanel.style.display = 'block';
    resultPanel.innerHTML = '테스트 실행 중...';
    
    try {
        const testData = {
            product_name: `테스트 제품 ${Date.now()}`,
            test_duration_days: 7
        };
        
        const response = await fetch(`${API_BASE_URL}/api/abtest/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(testData)
        });
        
        if (response.ok) {
            const data = await response.json();
            resultPanel.innerHTML = `✅ 성공\n\n요청:\n${JSON.stringify(testData, null, 2)}\n\n응답:\n${JSON.stringify(data, null, 2)}`;
            testResults.results['create'] = { status: 'success', data };
        } else {
            const errorData = await response.json();
            throw new Error(`HTTP ${response.status}: ${errorData.detail || response.statusText}`);
        }
    } catch (error) {
        resultPanel.innerHTML = `❌ 실패\n\n오류:\n${error.message}`;
        testResults.results['create'] = { status: 'error', error: error.message };
        throw error;
    }
}

// 테스트 목록 조회 테스트
async function testListABTests() {
    const resultPanel = document.getElementById('listResult');
    resultPanel.style.display = 'block';
    resultPanel.innerHTML = '테스트 실행 중...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/list`);
        
        if (response.ok) {
            const data = await response.json();
            resultPanel.innerHTML = `✅ 성공\n\n테스트 수: ${data.length}\n\n응답:\n${JSON.stringify(data, null, 2)}`;
            testResults.results['list'] = { status: 'success', data };
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (error) {
        resultPanel.innerHTML = `❌ 실패\n\n오류:\n${error.message}`;
        testResults.results['list'] = { status: 'error', error: error.message };
        throw error;
    }
}

// 상호작용 기록 테스트
async function testRecordInteraction() {
    const resultPanel = document.getElementById('interactionResult');
    resultPanel.style.display = 'block';
    resultPanel.innerHTML = '테스트 실행 중...';
    
    try {
        // 먼저 테스트 목록을 가져와서 활성 테스트 ID를 찾습니다
        const listResponse = await fetch(`${API_BASE_URL}/abtest/list`);
        if (!listResponse.ok) {
            throw new Error('테스트 목록을 가져올 수 없습니다.');
        }
        
        const tests = await listResponse.json();
        const activeTest = tests.find(test => test.status === 'active');
        
        if (!activeTest) {
            // 활성 테스트가 없으면 새로 생성
            const createResponse = await fetch(`${API_BASE_URL}/api/abtest/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_name: '상호작용 테스트',
                    test_duration_days: 1
                })
            });
            
            if (!createResponse.ok) {
                throw new Error('테스트를 생성할 수 없습니다.');
            }
            
            const newTest = await createResponse.json();
            activeTest = { test_id: newTest.test_id };
        }
        
        const interactionData = {
            test_id: activeTest.test_id,
            version: 'A',
            interaction_type: 'view',
            user_id: `test_user_${Date.now()}`
        };
        
        const response = await fetch(`${API_BASE_URL}/api/abtest/interaction`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(interactionData)
        });
        
        if (response.ok) {
            const data = await response.json();
            resultPanel.innerHTML = `✅ 성공\n\n요청:\n${JSON.stringify(interactionData, null, 2)}\n\n응답:\n${JSON.stringify(data, null, 2)}`;
            testResults.results['interaction'] = { status: 'success', data };
        } else {
            const errorData = await response.json();
            throw new Error(`HTTP ${response.status}: ${errorData.detail || response.statusText}`);
        }
    } catch (error) {
        resultPanel.innerHTML = `❌ 실패\n\n오류:\n${error.message}`;
        testResults.results['interaction'] = { status: 'error', error: error.message };
        throw error;
    }
}

// 분석 데이터 조회 테스트
async function testAnalytics() {
    const resultPanel = document.getElementById('analyticsResult');
    resultPanel.style.display = 'block';
    resultPanel.innerHTML = '테스트 실행 중...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/analytics/overview`);
        
        if (response.ok) {
            const data = await response.json();
            resultPanel.innerHTML = `✅ 성공\n\n응답:\n${JSON.stringify(data, null, 2)}`;
            testResults.results['analytics'] = { status: 'success', data };
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (error) {
        resultPanel.innerHTML = `❌ 실패\n\n오류:\n${error.message}`;
        testResults.results['analytics'] = { status: 'error', error: error.message };
        throw error;
    }
}

// 테스트 결과 조회 테스트
async function testResults() {
    const resultPanel = document.getElementById('resultsResult');
    resultPanel.style.display = 'block';
    resultPanel.innerHTML = '테스트 실행 중...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/results`);
        
        if (response.ok) {
            const data = await response.json();
            resultPanel.innerHTML = `✅ 성공\n\n결과 수: ${data.length}\n\n응답:\n${JSON.stringify(data, null, 2)}`;
            testResults.results['results'] = { status: 'success', data };
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (error) {
        resultPanel.innerHTML = `❌ 실패\n\n오류:\n${error.message}`;
        testResults.results['results'] = { status: 'error', error: error.message };
        throw error;
    }
}

// 로그 조회 테스트
async function testLogs() {
    const resultPanel = document.getElementById('logsResult');
    resultPanel.style.display = 'block';
    resultPanel.innerHTML = '테스트 실행 중...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/logs`);
        
        if (response.ok) {
            const data = await response.json();
            resultPanel.innerHTML = `✅ 성공\n\n로그 수: ${data.length}\n\n응답:\n${JSON.stringify(data, null, 2)}`;
            testResults.results['logs'] = { status: 'success', data };
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (error) {
        resultPanel.innerHTML = `❌ 실패\n\n오류:\n${error.message}`;
        testResults.results['logs'] = { status: 'error', error: error.message };
        throw error;
    }
}

// 스케줄러 테스트
async function testScheduler() {
    const resultPanel = document.getElementById('schedulerResult');
    resultPanel.style.display = 'block';
    resultPanel.innerHTML = '테스트 실행 중...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/abtest/scheduler/status`);
        
        if (response.ok) {
            const data = await response.json();
            resultPanel.innerHTML = `✅ 성공\n\n응답:\n${JSON.stringify(data, null, 2)}`;
            testResults.results['scheduler'] = { status: 'success', data };
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (error) {
        resultPanel.innerHTML = `❌ 실패\n\n오류:\n${error.message}`;
        testResults.results['scheduler'] = { status: 'error', error: error.message };
        throw error;
    }
}

// 대량 데이터 생성 테스트
async function testBulkData() {
    const resultPanel = document.getElementById('bulkResult');
    resultPanel.style.display = 'block';
    resultPanel.innerHTML = '테스트 실행 중...';
    
    try {
        // 먼저 테스트를 생성
        const createResponse = await fetch(`${API_BASE_URL}/api/abtest/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_name: '대량 데이터 테스트',
                test_duration_days: 1
            })
        });
        
        if (!createResponse.ok) {
            throw new Error('테스트를 생성할 수 없습니다.');
        }
        
        const test = await createResponse.json();
        const testId = test.test_id;
        
        // 대량의 상호작용 데이터 생성
        const interactions = [];
        const startTime = Date.now();
        
        for (let i = 0; i < 100; i++) {
            const interaction = {
                test_id: testId,
                version: Math.random() < 0.5 ? 'A' : 'B',
                interaction_type: Math.random() < 0.1 ? 'purchase' : 'view',
                user_id: `bulk_user_${i}_${Date.now()}`
            };
            
            interactions.push(interaction);
        }
        
        // 병렬로 요청 전송
        const promises = interactions.map(interaction =>
            fetch(`${API_BASE_URL}/api/abtest/interaction`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(interaction)
            })
        );
        
        const responses = await Promise.all(promises);
        const endTime = Date.now();
        
        const successCount = responses.filter(r => r.ok).length;
        const duration = endTime - startTime;
        
        resultPanel.innerHTML = `✅ 성공\n\n생성된 상호작용: ${interactions.length}\n성공: ${successCount}\n실패: ${interactions.length - successCount}\n소요 시간: ${duration}ms\n평균 응답 시간: ${duration / interactions.length}ms`;
        
        testResults.results['bulk'] = { 
            status: 'success', 
            data: { 
                total: interactions.length, 
                success: successCount, 
                duration: duration 
            } 
        };
    } catch (error) {
        resultPanel.innerHTML = `❌ 실패\n\n오류:\n${error.message}`;
        testResults.results['bulk'] = { status: 'error', error: error.message };
        throw error;
    }
}

// 동시 요청 테스트
async function testConcurrentRequests() {
    const resultPanel = document.getElementById('concurrentResult');
    resultPanel.style.display = 'block';
    resultPanel.innerHTML = '테스트 실행 중...';
    
    try {
        const startTime = Date.now();
        
        // 동시에 여러 API 엔드포인트 호출
        const requests = [
            fetch(`${API_BASE_URL}/health`),
            fetch(`${API_BASE_URL}/api/abtest/list`),
            fetch(`${API_BASE_URL}/api/abtest/analytics/overview`),
            fetch(`${API_BASE_URL}/api/abtest/logs`)
        ];
        
        const responses = await Promise.all(requests);
        const endTime = Date.now();
        
        const successCount = responses.filter(r => r.ok).length;
        const duration = endTime - startTime;
        
        resultPanel.innerHTML = `✅ 성공\n\n동시 요청 수: ${requests.length}\n성공: ${successCount}\n실패: ${requests.length - successCount}\n소요 시간: ${duration}ms`;
        
        testResults.results['concurrent'] = { 
            status: 'success', 
            data: { 
                total: requests.length, 
                success: successCount, 
                duration: duration 
            } 
        };
    } catch (error) {
        resultPanel.innerHTML = `❌ 실패\n\n오류:\n${error.message}`;
        testResults.results['concurrent'] = { status: 'error', error: error.message };
        throw error;
    }
}

// 결과 초기화
function clearResults() {
    testResults = {
        total: 0,
        passed: 0,
        failed: 0,
        results: {}
    };
    
    // 모든 결과 패널 숨기기
    const resultPanels = document.querySelectorAll('.result-panel');
    resultPanels.forEach(panel => {
        panel.style.display = 'none';
        panel.innerHTML = '';
    });
    
    updateSummaryStats();
    updateProgressBar(0);
}

// 요약 통계 업데이트
function updateSummaryStats() {
    document.getElementById('totalTests').textContent = testResults.total;
    document.getElementById('passedTests').textContent = testResults.passed;
    document.getElementById('failedTests').textContent = testResults.failed;
    
    const successRate = testResults.total > 0 ? (testResults.passed / testResults.total * 100) : 0;
    document.getElementById('successRate').textContent = `${successRate.toFixed(1)}%`;
}

// 진행률 바 업데이트
function updateProgressBar(percentage) {
    document.getElementById('progressBar').style.width = `${percentage}%`;
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
