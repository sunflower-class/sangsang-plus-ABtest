// 브라우저 콘솔 경고 줄이기
(function() {
    'use strict';
    
    // Feature Policy 경고 숨기기
    const originalWarn = console.warn;
    console.warn = function(...args) {
        const message = args.join(' ');
        
        // 특정 경고 메시지 필터링
        const ignoredWarnings = [
            'Unrecognized feature:',
            'ambient-light-sensor',
            'battery',
            'document-domain',
            'layout-animations',
            'legacy-image-formats',
            'oversized-images',
            'vr',
            'wake-lock'
        ];
        
        const shouldIgnore = ignoredWarnings.some(warning => 
            message.includes(warning)
        );
        
        if (!shouldIgnore) {
            originalWarn.apply(console, args);
        }
    };
    
    // Feature Policy 설정
    if ('featurePolicy' in document) {
        try {
            document.featurePolicy.allowsFeature('ambient-light-sensor');
            document.featurePolicy.allowsFeature('battery');
            document.featurePolicy.allowsFeature('document-domain');
            document.featurePolicy.allowsFeature('layout-animations');
            document.featurePolicy.allowsFeature('legacy-image-formats');
            document.featurePolicy.allowsFeature('oversized-images');
            document.featurePolicy.allowsFeature('vr');
            document.featurePolicy.allowsFeature('wake-lock');
        } catch (e) {
            // 무시
        }
    }
    
    // 성능 최적화
    if ('requestIdleCallback' in window) {
        requestIdleCallback(() => {
            // 페이지 로드 후 정리 작업
        });
    }
    
    // 에러 핸들링 개선
    window.addEventListener('error', function(e) {
        // 중요하지 않은 에러는 무시
        if (e.message.includes('Feature Policy') || 
            e.message.includes('Unrecognized feature')) {
            e.preventDefault();
            return false;
        }
    });
    
})();
