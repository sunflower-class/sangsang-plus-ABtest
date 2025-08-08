import uuid
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from scipy import stats

class TestStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class VariantType(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"

@dataclass
class ProductInfo:
    """상품 기본 정보"""
    product_id: str
    product_name: str
    product_image: str
    product_description: str
    price: float
    category: str
    tags: List[str] = None

@dataclass
class PageVariant:
    """상세페이지 변형 정보"""
    variant_id: str
    variant_type: VariantType
    title: str
    description: str
    layout_type: str  # "grid", "list", "carousel", "hero", "minimal"
    color_scheme: str  # "light", "dark", "colorful", "neutral"
    cta_text: str  # "구매하기", "장바구니 담기", "즉시 구매", "자세히 보기"
    cta_color: str
    cta_position: str  # "top", "middle", "bottom", "floating"
    additional_features: List[str]  # ["리뷰", "배송정보", "관련상품", "Q&A", "스펙"]
    image_style: str  # "original", "enhanced", "minimal", "gallery"
    font_style: str  # "modern", "classic", "bold", "elegant"
    created_at: datetime
    is_active: bool = True

@dataclass
class ABTest:
    """A/B 테스트 정보"""
    test_id: str
    test_name: str
    product_info: ProductInfo
    variants: List[PageVariant]
    status: TestStatus
    start_date: datetime
    end_date: Optional[datetime]
    traffic_split: Dict[str, float]  # variant_id: percentage
    target_metrics: Dict[str, float]  # "ctr": 0.6, "conversion_rate": 0.4
    created_at: datetime
    updated_at: datetime
    description: str = ""

@dataclass
class TestEvent:
    """테스트 이벤트 (노출, 클릭, 전환 등)"""
    event_id: str
    test_id: str
    variant_id: str
    user_id: str
    event_type: str  # "impression", "click", "conversion", "bounce"
    timestamp: datetime
    session_id: str
    user_agent: str = ""
    ip_address: str = ""
    referrer: str = ""
    revenue: float = 0.0
    session_duration: float = 0.0

@dataclass
class TestResult:
    """테스트 결과 집계"""
    test_id: str
    variant_id: str
    variant_type: str
    impressions: int
    clicks: int
    conversions: int
    revenue: float
    ctr: float
    conversion_rate: float
    avg_session_duration: float
    bounce_rate: float
    traffic_percentage: float
    statistical_significance: float = 0.0

class ABTestManager:
    """A/B 테스트 관리자"""
    
    def __init__(self):
        self.tests: Dict[str, ABTest] = {}
        self.events: Dict[str, List[TestEvent]] = {}
        self.user_variants: Dict[str, str] = {}  # user_id: variant_id (일관성 보장)
    
    def create_test(self, test_name: str, product_info: ProductInfo, 
                   variants: List[PageVariant], duration_days: int = 14,
                   target_metrics: Dict[str, float] = None) -> ABTest:
        """새로운 A/B 테스트 생성"""
        test_id = str(uuid.uuid4())
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)
        
        # 기본 트래픽 분할 (균등 분배)
        traffic_split = {}
        for variant in variants:
            traffic_split[variant.variant_id] = 100.0 / len(variants)
        
        # 기본 목표 지표 설정
        if target_metrics is None:
            target_metrics = {"ctr": 0.6, "conversion_rate": 0.4}
        
        test = ABTest(
            test_id=test_id,
            test_name=test_name,
            product_info=product_info,
            variants=variants,
            status=TestStatus.DRAFT,
            start_date=start_date,
            end_date=end_date,
            traffic_split=traffic_split,
            target_metrics=target_metrics,
            created_at=start_date,
            updated_at=start_date
        )
        
        self.tests[test_id] = test
        self.events[test_id] = []
        return test
    
    def start_test(self, test_id: str) -> bool:
        """테스트 시작"""
        if test_id not in self.tests:
            return False
        
        test = self.tests[test_id]
        if test.status == TestStatus.DRAFT:
            test.status = TestStatus.ACTIVE
            test.updated_at = datetime.now()
            return True
        return False
    
    def pause_test(self, test_id: str) -> bool:
        """테스트 일시정지"""
        if test_id not in self.tests:
            return False
        
        test = self.tests[test_id]
        if test.status == TestStatus.ACTIVE:
            test.status = TestStatus.PAUSED
            test.updated_at = datetime.now()
            return True
        return False
    
    def complete_test(self, test_id: str) -> bool:
        """테스트 완료"""
        if test_id not in self.tests:
            return False
        
        test = self.tests[test_id]
        test.status = TestStatus.COMPLETED
        test.end_date = datetime.now()
        test.updated_at = datetime.now()
        return True
    
    def get_variant_for_user(self, test_id: str, user_id: str, session_id: str) -> Optional[PageVariant]:
        """사용자에게 표시할 변형 선택 (일관성 보장)"""
        if test_id not in self.tests:
            return None
        
        test = self.tests[test_id]
        if test.status != TestStatus.ACTIVE:
            return None
        
        # 사용자별 일관된 변형 선택
        user_key = f"{user_id}_{test_id}"
        if user_key not in self.user_variants:
            # 해시 기반 변형 선택
            hash_value = int(hashlib.md5(user_key.encode()).hexdigest(), 16)
            variant_index = hash_value % len(test.variants)
            self.user_variants[user_key] = test.variants[variant_index].variant_id
        
        variant_id = self.user_variants[user_key]
        return next((v for v in test.variants if v.variant_id == variant_id), None)
    
    def record_event(self, test_id: str, variant_id: str, user_id: str, 
                    event_type: str, session_id: str, **kwargs) -> bool:
        """테스트 이벤트 기록"""
        if test_id not in self.tests:
            return False
        
        event = TestEvent(
            event_id=str(uuid.uuid4()),
            test_id=test_id,
            variant_id=variant_id,
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime.now(),
            session_id=session_id,
            **kwargs
        )
        
        self.events[test_id].append(event)
        return True
    
    def get_test_results(self, test_id: str) -> Dict[str, Any]:
        """테스트 결과 집계 및 통계 분석"""
        if test_id not in self.tests or test_id not in self.events:
            return {}
        
        test = self.tests[test_id]
        events = self.events[test_id]
        
        # 변형별 결과 집계
        variant_results = {}
        for variant in test.variants:
            variant_events = [e for e in events if e.variant_id == variant.variant_id]
            
            impressions = len([e for e in variant_events if e.event_type == "impression"])
            clicks = len([e for e in variant_events if e.event_type == "click"])
            conversions = len([e for e in variant_events if e.event_type == "conversion"])
            revenue = sum(e.revenue for e in variant_events if e.event_type == "conversion")
            
            # 세션 지속시간 및 이탈률 계산
            session_durations = [e.session_duration for e in variant_events if e.session_duration > 0]
            avg_session_duration = np.mean(session_durations) if session_durations else 0
            
            bounces = len([e for e in variant_events if e.event_type == "bounce"])
            bounce_rate = (bounces / impressions * 100) if impressions > 0 else 0
            
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
            
            variant_results[variant.variant_id] = TestResult(
                test_id=test_id,
                variant_id=variant.variant_id,
                variant_type=variant.variant_type.value,
                impressions=impressions,
                clicks=clicks,
                conversions=conversions,
                revenue=revenue,
                ctr=round(ctr, 2),
                conversion_rate=round(conversion_rate, 2),
                avg_session_duration=round(avg_session_duration, 2),
                bounce_rate=round(bounce_rate, 2),
                traffic_percentage=test.traffic_split.get(variant.variant_id, 0)
            )
        
        # 통계적 유의성 계산
        if len(variant_results) >= 2:
            self._calculate_statistical_significance(variant_results, events)
        
        # 종합 점수 계산 (목표 지표 기반)
        for variant_id, result in variant_results.items():
            result.statistical_significance = self._calculate_composite_score(result, test.target_metrics)
        
        return {
            "test_id": test_id,
            "test_name": test.test_name,
            "status": test.status.value,
            "start_date": test.start_date.isoformat(),
            "end_date": test.end_date.isoformat() if test.end_date else None,
            "product_info": asdict(test.product_info),
            "variants": {vid: asdict(result) for vid, result in variant_results.items()},
            "total_impressions": sum(r.impressions for r in variant_results.values()),
            "total_clicks": sum(r.clicks for r in variant_results.values()),
            "total_conversions": sum(r.conversions for r in variant_results.values()),
            "total_revenue": sum(r.revenue for r in variant_results.values()),
            "target_metrics": test.target_metrics,
            "winner": self._determine_winner(variant_results, test.target_metrics)
        }
    
    def _calculate_statistical_significance(self, variant_results: Dict[str, TestResult], events: List[TestEvent]):
        """통계적 유의성 계산 (카이제곱 검정)"""
        if len(variant_results) < 2:
            return
        
        # CTR 기반 통계적 유의성 계산
        variant_ids = list(variant_results.keys())
        if len(variant_ids) >= 2:
            # 2x2 분할표 생성 (첫 번째 변형 vs 나머지)
            first_variant = variant_results[variant_ids[0]]
            other_impressions = sum(r.impressions for r in variant_results.values() if r.variant_id != variant_ids[0])
            other_clicks = sum(r.clicks for r in variant_results.values() if r.variant_id != variant_ids[0])
            
            if first_variant.impressions > 0 and other_impressions > 0:
                observed = [[first_variant.clicks, first_variant.impressions - first_variant.clicks],
                           [other_clicks, other_impressions - other_clicks]]
                
                try:
                    chi2, p_value = stats.chi2_contingency(observed)[:2]
                    variant_results[variant_ids[0]].statistical_significance = round(p_value, 4)
                except:
                    variant_results[variant_ids[0]].statistical_significance = 1.0
    
    def _calculate_composite_score(self, result: TestResult, target_metrics: Dict[str, float]) -> float:
        """목표 지표 기반 종합 점수 계산"""
        score = 0.0
        total_weight = sum(target_metrics.values())
        
        if total_weight > 0:
            if "ctr" in target_metrics:
                score += (result.ctr / 100) * (target_metrics["ctr"] / total_weight)
            if "conversion_rate" in target_metrics:
                score += (result.conversion_rate / 100) * (target_metrics["conversion_rate"] / total_weight)
            if "revenue" in target_metrics:
                # 수익 정규화 (예: 1000원을 1.0으로 정규화)
                normalized_revenue = min(result.revenue / 1000, 1.0)
                score += normalized_revenue * (target_metrics["revenue"] / total_weight)
        
        return round(score, 4)
    
    def _determine_winner(self, variant_results: Dict[str, TestResult], target_metrics: Dict[str, float]) -> Optional[str]:
        """승자 결정 (통계적 유의성 고려)"""
        if not variant_results:
            return None
        
        # 종합 점수가 가장 높고 통계적으로 유의한 변형 선택
        best_variant = None
        best_score = -1
        
        for variant_id, result in variant_results.items():
            if result.statistical_significance < 0.05:  # p < 0.05
                if result.statistical_significance > best_score:
                    best_score = result.statistical_significance
                    best_variant = variant_id
        
        return best_variant
    
    def get_all_tests(self) -> List[Dict[str, Any]]:
        """모든 테스트 목록 반환"""
        return [
            {
                "test_id": test.test_id,
                "test_name": test.test_name,
                "status": test.status.value,
                "start_date": test.start_date.isoformat(),
                "end_date": test.end_date.isoformat() if test.end_date else None,
                "variants_count": len(test.variants),
                "created_at": test.created_at.isoformat(),
                "product_name": test.product_info.product_name
            }
            for test in self.tests.values()
        ]
    
    def get_test_events(self, test_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """테스트 이벤트 목록 조회"""
        if test_id not in self.events:
            return []
        
        events = self.events[test_id][-limit:]
        return [
            {
                "event_id": event.event_id,
                "variant_id": event.variant_id,
                "user_id": event.user_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "session_id": event.session_id,
                "revenue": event.revenue
            }
            for event in events
        ]

# 전역 인스턴스
ab_test_manager = ABTestManager()
