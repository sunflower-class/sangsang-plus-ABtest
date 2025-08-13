/**
 * 실제 서비스 연동을 위한 JavaScript 추적 코드
 * 웹사이트에 이 코드를 삽입하면 자동으로 A/B 테스트 이벤트를 추적합니다.
 */

class ABTestTracker {
    constructor(config = {}) {
        this.apiUrl = config.apiUrl || 'http://localhost:5001';
        this.testId = config.testId;
        this.userId = config.userId || this.generateUserId();
        this.sessionId = config.sessionId || this.generateSessionId();
        this.trackingEnabled = true;
        
        // 이벤트 큐
        this.eventQueue = [];
        this.isProcessing = false;
        
        // 초기화
        this.init();
    }
    
    /**
     * 추적기 초기화
     */
    init() {
        if (!this.testId) {
            console.warn('ABTestTracker: testId가 설정되지 않았습니다.');
            return;
        }
        
        // 페이지 로드 시 노출 이벤트 자동 기록
        this.recordImpression();
        
        // 클릭 이벤트 리스너 등록
        this.setupClickTracking();
        
        // 구매 이벤트 리스너 등록
        this.setupPurchaseTracking();
        
        // 페이지 언로드 시 큐된 이벤트 전송
        window.addEventListener('beforeunload', () => {
            this.flushEventQueue();
        });
        
        console.log('ABTestTracker 초기화 완료');
    }
    
    /**
     * 사용자 ID 생성
     */
    generateUserId() {
        let userId = localStorage.getItem('ab_test_user_id');
        if (!userId) {
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('ab_test_user_id', userId);
        }
        return userId;
    }
    
    /**
     * 세션 ID 생성
     */
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * 클릭 이벤트 추적 설정
     */
    setupClickTracking() {
        document.addEventListener('click', (event) => {
            const target = event.target;
            
            // 버튼 클릭 추적
            if (target.tagName === 'BUTTON' || target.closest('button')) {
                this.recordClick('button_click', {
                    button_text: target.textContent || target.innerText,
                    button_id: target.id,
                    button_class: target.className
                });
            }
            
            // 링크 클릭 추적
            if (target.tagName === 'A' || target.closest('a')) {
                this.recordClick('link_click', {
                    link_url: target.href,
                    link_text: target.textContent || target.innerText
                });
            }
            
            // 구매 버튼 클릭 추적
            if (this.isPurchaseButton(target)) {
                this.recordClick('purchase_button_click', {
                    button_text: target.textContent || target.innerText,
                    product_id: this.getProductId(),
                    product_price: this.getProductPrice()
                });
            }
        });
    }
    
    /**
     * 구매 이벤트 추적 설정
     */
    setupPurchaseTracking() {
        // 구매 완료 페이지에서 자동으로 구매 이벤트 기록
        if (this.isPurchaseCompletePage()) {
            this.recordPurchase({
                product_id: this.getProductId(),
                product_price: this.getProductPrice(),
                order_id: this.getOrderId()
            });
        }
        
        // 구매 완료 이벤트 리스너 (SPA 등에서 사용)
        window.addEventListener('purchaseComplete', (event) => {
            this.recordPurchase({
                product_id: event.detail.productId,
                product_price: event.detail.price,
                order_id: event.detail.orderId
            });
        });
    }
    
    /**
     * 노출 이벤트 기록
     */
    recordImpression(data = {}) {
        this.recordEvent('impression', data);
    }
    
    /**
     * 클릭 이벤트 기록
     */
    recordClick(clickType, data = {}) {
        this.recordEvent('click', {
            click_type: clickType,
            ...data
        });
    }
    
    /**
     * 장바구니 추가 이벤트 기록
     */
    recordAddToCart(data = {}) {
        this.recordEvent('add_to_cart', data);
    }
    
    /**
     * 구매 이벤트 기록
     */
    recordPurchase(data = {}) {
        this.recordEvent('purchase', {
            revenue: data.product_price || 0,
            product_id: data.product_id,
            order_id: data.order_id,
            ...data
        });
    }
    
    /**
     * 이벤트 기록 (공통)
     */
    recordEvent(eventType, data = {}) {
        if (!this.trackingEnabled || !this.testId) {
            return;
        }
        
        // 변형 ID 가져오기
        this.getVariantId().then(variantId => {
            const eventData = {
                test_id: this.testId,
                variant_id: variantId,
                user_id: this.userId,
                session_id: this.sessionId,
                event_type: eventType,
                page_url: window.location.href,
                referrer: document.referrer,
                user_agent: navigator.userAgent,
                ip_address: this.getClientIP(),
                ...data
            };
            
            // 이벤트 큐에 추가
            this.eventQueue.push(eventData);
            
            // 큐 처리
            this.processEventQueue();
        }).catch(error => {
            console.error('ABTestTracker: 변형 ID 가져오기 실패:', error);
        });
    }
    
    /**
     * 변형 ID 가져오기
     */
    async getVariantId() {
        try {
            const response = await fetch(`${this.apiUrl}/api/abtest/${this.testId}/variant/${this.userId}`);
            const data = await response.json();
            return data.variant.variant_id;
        } catch (error) {
            console.error('ABTestTracker: 변형 ID 가져오기 실패:', error);
            return null;
        }
    }
    
    /**
     * 이벤트 큐 처리
     */
    async processEventQueue() {
        if (this.isProcessing || this.eventQueue.length === 0) {
            return;
        }
        
        this.isProcessing = true;
        
        try {
            const eventData = this.eventQueue.shift();
            
            const response = await fetch(`${this.apiUrl}/api/abtest/real-time/event`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(eventData)
            });
            
            if (!response.ok) {
                console.error('ABTestTracker: 이벤트 전송 실패:', response.status);
                // 실패한 이벤트를 다시 큐에 추가
                this.eventQueue.unshift(eventData);
            }
        } catch (error) {
            console.error('ABTestTracker: 이벤트 처리 실패:', error);
        } finally {
            this.isProcessing = false;
            
            // 큐에 남은 이벤트가 있으면 계속 처리
            if (this.eventQueue.length > 0) {
                setTimeout(() => this.processEventQueue(), 100);
            }
        }
    }
    
    /**
     * 이벤트 큐 비우기
     */
    flushEventQueue() {
        while (this.eventQueue.length > 0) {
            this.processEventQueue();
        }
    }
    
    /**
     * 클라이언트 IP 주소 가져오기 (대략적)
     */
    getClientIP() {
        // 실제로는 서버에서 IP를 전달받아야 함
        return 'unknown';
    }
    
    /**
     * 구매 버튼인지 확인
     */
    isPurchaseButton(element) {
        const text = (element.textContent || element.innerText || '').toLowerCase();
        const keywords = ['구매', '결제', '주문', 'buy', 'purchase', 'checkout', 'order'];
        return keywords.some(keyword => text.includes(keyword));
    }
    
    /**
     * 구매 완료 페이지인지 확인
     */
    isPurchaseCompletePage() {
        const url = window.location.href.toLowerCase();
        const keywords = ['complete', 'success', 'thank', 'confirm', '완료', '성공', '감사'];
        return keywords.some(keyword => url.includes(keyword));
    }
    
    /**
     * 상품 ID 가져오기
     */
    getProductId() {
        // 페이지에서 상품 ID 추출 (실제 구현 필요)
        const metaTag = document.querySelector('meta[name="product-id"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        
        // URL에서 상품 ID 추출
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('product_id') || urlParams.get('id');
    }
    
    /**
     * 상품 가격 가져오기
     */
    getProductPrice() {
        // 페이지에서 상품 가격 추출 (실제 구현 필요)
        const metaTag = document.querySelector('meta[name="product-price"]');
        if (metaTag) {
            return parseFloat(metaTag.getAttribute('content'));
        }
        
        // 가격 요소에서 추출
        const priceElement = document.querySelector('.price, .product-price, [data-price]');
        if (priceElement) {
            const priceText = priceElement.textContent.replace(/[^\d]/g, '');
            return parseFloat(priceText);
        }
        
        return 0;
    }
    
    /**
     * 주문 ID 가져오기
     */
    getOrderId() {
        // URL에서 주문 ID 추출
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('order_id') || urlParams.get('orderId');
    }
    
    /**
     * 추적 활성화/비활성화
     */
    setTrackingEnabled(enabled) {
        this.trackingEnabled = enabled;
    }
    
    /**
     * 수동 이벤트 기록
     */
    trackCustomEvent(eventType, data = {}) {
        this.recordEvent(eventType, data);
    }
}

// 전역 객체로 노출
window.ABTestTracker = ABTestTracker;

// 사용 예시:
/*
// 1. 추적기 초기화
const tracker = new ABTestTracker({
    apiUrl: 'http://localhost:5001',
    testId: 'your-test-id-here',
    userId: 'user-123', // 선택적
    sessionId: 'session-456' // 선택적
});

// 2. 수동 이벤트 기록
tracker.trackCustomEvent('custom_action', {
    action_name: 'product_view',
    product_category: 'electronics'
});

// 3. 구매 완료 이벤트 (SPA에서)
window.dispatchEvent(new CustomEvent('purchaseComplete', {
    detail: {
        productId: 'prod-123',
        price: 50000,
        orderId: 'order-456'
    }
}));
*/

// 자동 초기화 (HTML에서 설정된 경우)
document.addEventListener('DOMContentLoaded', () => {
    const testId = document.querySelector('meta[name="ab-test-id"]')?.getAttribute('content');
    if (testId) {
        window.abTestTracker = new ABTestTracker({
            testId: testId
        });
    }
});

