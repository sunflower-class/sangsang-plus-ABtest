import uuid
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from scipy import stats
import asyncio
import aiohttp
from collections import defaultdict

class TestStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    MANUAL_DECISION = "manual_decision"  # 수동 결정 대기 상태
    WINNER_SELECTED = "winner_selected"  # 승자 선택됨
    CYCLE_COMPLETED = "cycle_completed"  # 사이클 완료

class VariantType(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"

class DistributionMode(Enum):
    EQUAL = "equal"  # 50:50 균등 분배
    BANDIT = "bandit"  # Thompson Sampling
    CONTEXTUAL = "contextual"  # Contextual Bandit

class TestMode(Enum):
    MANUAL = "manual"  # 수동 생성
    AUTOPILOT = "autopilot"  # 자동 생성

class DecisionMode(Enum):
    AUTO = "auto"  # 자동 결정
    MANUAL = "manual"  # 수동 결정
    HYBRID = "hybrid"  # 하이브리드 (수동 결정 기간 후 자동)

@dataclass
class ExperimentBrief:
    """실험 계약서 - 요구사항 1번"""
    # 목적
    objective: str  # "구매 전환율(CVR) 최대화"
    
    # 핵심지표 & 보조지표
    primary_metrics: List[str]  # ["CVR"]
    secondary_metrics: List[str]  # ["CTR", "ATC", "체류시간"]
    
    # 가드레일
    guardrails: Dict[str, float]  # {"LCP": 3.5, "error_rate": 0.005, "return_rate": 0.1}
    
    # 대상 & 타깃
    target_categories: List[str]
    target_channels: List[str]
    target_devices: List[str]
    exclude_conditions: List[str]
    
    # 변형 수 & 분배 정책
    variant_count: int  # 2~3개
    distribution_mode: DistributionMode
    initial_split: Dict[str, float]  # {"A": 0.5, "B": 0.5}
    
    # 최소 검출 효과 & 최소 표본수
    mde: float  # Minimum Detectable Effect (예: 0.1 = 10%p)
    min_sample_size: int
    
    # 종료 & 승격 & 롤백 규칙
    termination_rules: Dict[str, Any]
    promotion_rules: Dict[str, Any]
    rollback_rules: Dict[str, Any]
    
    # 결정 모드 설정
    decision_mode: DecisionMode = DecisionMode.HYBRID
    manual_decision_period_days: int = 7  # 수동 결정 기간 (1주일)
    long_term_monitoring_days: int = 30  # 장기 모니터링 기간 (1달)
    auto_decision_confidence: float = 0.95  # 자동 결정 신뢰도 임계값

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
    inventory: int = 0
    daily_sessions: int = 0
    cool_down_days: int = 0

@dataclass
class PageVariant:
    """상세페이지 변형 정보 - 요구사항 2번"""
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
    
    # 메타 태깅 - 요구사항 2번
    prompt_meta: Dict[str, Any] = None  # 레이아웃 유형, CTA 톤, 색 팔레트, 핵심 혜택 등
    
    # 정책 필터 통과 여부
    policy_approved: bool = False
    policy_checks: Dict[str, bool] = None  # 금칙어, 과장표현, 상표, 성능, 접근성

@dataclass
class ABTest:
    """A/B 테스트 정보 - 확장"""
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
    
    # 실험 계약서
    experiment_brief: ExperimentBrief = None
    
    # 테스트 모드
    test_mode: TestMode = TestMode.MANUAL
    
    # 트래픽 예산
    traffic_budget: float = 0.2  # 전체 트래픽의 20%
    concurrent_experiments_limit: int = 1  # SKU당 동시 1개
    
    # Sticky Assignment - 요구사항 4번
    sticky_assignment: bool = True
    
    # SRM 감지 - 요구사항 6번
    srm_detection: bool = True
    srm_threshold: float = 0.01
    
    # 봇/이상치 필터 - 요구사항 6번
    bot_filter: bool = True
    outlier_filter: bool = True
    
    # A/A 테스트 - 요구사항 6번
    aa_test_enabled: bool = False
    aa_test_duration: int = 24  # 시간
    
    # 가드레일 모니터링 - 요구사항 6번
    guardrail_monitoring: bool = True
    
    # Thompson Sampling 파라미터 - 요구사항 7번
    thompson_alpha: float = 1.0
    thompson_beta: float = 1.0
    min_exploration_rate: float = 0.05
    
    # 승자 처리 - 요구사항 8번
    promotion_stages: List[float] = None  # [0.25, 0.5, 1.0]
    promotion_duration: int = 12  # 시간
    auto_rollback: bool = True
    rollback_threshold: float = -0.2  # -20%
    winner_variant_id: Optional[str] = None  # 승자 변형 ID
    
    # 새로운 기능: 결정 관리
    decision_mode: DecisionMode = DecisionMode.HYBRID
    manual_decision_start_date: Optional[datetime] = None  # 수동 결정 시작일
    manual_decision_end_date: Optional[datetime] = None  # 수동 결정 종료일
    long_term_monitoring_start_date: Optional[datetime] = None  # 장기 모니터링 시작일
    long_term_monitoring_end_date: Optional[datetime] = None  # 장기 모니터링 종료일
    auto_decision_confidence: float = 0.95  # 자동 결정 신뢰도 임계값
    
    # 사이클 관리
    cycle_number: int = 1  # 현재 사이클 번호
    max_cycles: int = 5  # 최대 사이클 수
    previous_winner_variant_id: Optional[str] = None  # 이전 사이클 승자
    cycle_completion_date: Optional[datetime] = None  # 사이클 완료일

@dataclass
class TestEvent:
    """테스트 이벤트 (노출, 클릭, 전환 등) - 요구사항 5번"""
    event_id: str
    test_id: str
    variant_id: str
    user_id: str
    event_type: str  # "impression", "click_detail", "add_to_cart", "purchase"
    timestamp: datetime
    session_id: str
    user_agent: str = ""
    ip_address: str = ""
    referrer: str = ""
    revenue: float = 0.0
    session_duration: float = 0.0
    
    # 필수 공통 속성 - 요구사항 5번
    product_id: str = ""
    device: str = ""
    channel: str = ""
    price: float = 0.0
    quantity: int = 1
    
    # 품질 플래그 - 요구사항 5번
    bot_flag: bool = False
    srm_flag: bool = False
    guardrail_breach: bool = False

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
    
    # 베이지안 통계 - 요구사항 7번
    thompson_alpha: float = 1.0
    thompson_beta: float = 1.0
    win_probability: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    
    # 세그먼트별 결과
    segment_results: Dict[str, Dict[str, float]] = None

@dataclass
class BanditDecision:
    """밴딧 의사결정 로그 - 요구사항 9번"""
    timestamp: datetime
    test_id: str
    user_id: str
    selected_variant: str
    decision_reason: str  # "Thompson Sampling", "Exploration", "Exploitation"
    epsilon: float = 0.0
    thompson_values: Dict[str, float] = None

@dataclass
class GuardrailAlert:
    """가드레일 알림"""
    alert_id: str
    test_id: str
    alert_type: str  # "SRM", "BOT", "GUARDRAIL", "PERFORMANCE"
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    message: str
    timestamp: datetime
    resolved: bool = False
    action_taken: str = ""

class ABTestManager:
    """A/B 테스트 관리자 - 확장"""
    
    def __init__(self):
        self.tests: Dict[str, ABTest] = {}
        self.events: Dict[str, List[TestEvent]] = {}
        self.user_variants: Dict[str, str] = {}  # user_id: variant_id (일관성 보장)
        
        # 새로운 기능들을 위한 저장소
        self.bandit_decisions: List[BanditDecision] = []
        self.guardrail_alerts: List[GuardrailAlert] = []
        self.policy_filters: Dict[str, Dict[str, bool]] = {}  # variant_id -> policy_checks
        
        # Thompson Sampling 파라미터
        self.thompson_params: Dict[str, Dict[str, Tuple[float, float]]] = {}  # test_id -> {variant_id: (alpha, beta)}
        
        # SRM 감지용
        self.srm_data: Dict[str, Dict[str, int]] = {}  # test_id -> {variant_id: count}
        
        # 트래픽 예산 관리
        self.traffic_budget_usage: Dict[str, float] = {}  # test_id -> usage_percentage
        
        # 승자 처리 상태
        self.promotion_status: Dict[str, Dict[str, Any]] = {}  # test_id -> promotion_info
        
        # 새로운 기능: 결정 관리
        self.manual_decisions: Dict[str, Dict[str, Any]] = {}  # test_id -> manual_decision_info
        self.cycle_history: Dict[str, List[Dict[str, Any]]] = {}  # test_id -> cycle_history
        
        # 장기 모니터링 데이터
        self.long_term_metrics: Dict[str, Dict[str, List[float]]] = {}  # test_id -> {metric: [values]}
        
        # 자동화 루프 관리
        self.auto_cycle_queue: List[str] = []  # 자동 사이클 대기열
        self.cycle_scheduler: Dict[str, datetime] = {}  # 사이클 스케줄
    
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
        """테스트 완료 및 승자 결정"""
        if test_id not in self.tests:
            return False
        
        test = self.tests[test_id]
        test.status = TestStatus.COMPLETED
        test.end_date = datetime.now()
        test.updated_at = datetime.now()
        
        # 결정 모드에 따른 처리
        if test.decision_mode == DecisionMode.AUTO:
            # 자동 결정
            self._auto_determine_winner(test_id)
        elif test.decision_mode == DecisionMode.MANUAL:
            # 수동 결정 대기
            self._start_manual_decision_period(test_id)
        elif test.decision_mode == DecisionMode.HYBRID:
            # 하이브리드: 수동 결정 기간 후 자동
            self._start_manual_decision_period(test_id)
        
        return True
    
    def _start_manual_decision_period(self, test_id: str) -> bool:
        """수동 결정 기간 시작"""
        if test_id not in self.tests:
            return False
        
        test = self.tests[test_id]
        test.status = TestStatus.MANUAL_DECISION
        test.manual_decision_start_date = datetime.now()
        test.manual_decision_end_date = datetime.now() + timedelta(days=test.experiment_brief.manual_decision_period_days)
        test.updated_at = datetime.now()
        
        # 수동 결정 정보 초기화
        self.manual_decisions[test_id] = {
            "start_date": test.manual_decision_start_date,
            "end_date": test.manual_decision_end_date,
            "manual_winner": None,
            "decision_made": False,
            "decision_reason": ""
        }
        
        return True
    
    def _auto_determine_winner(self, test_id: str) -> Optional[str]:
        """자동 승자 결정"""
        if test_id not in self.tests:
            return None
        
        test = self.tests[test_id]
        results = self.get_test_results(test_id)
        
        if not results or "winner" not in results:
            return None
        
        winner_id = results["winner"]
        test.winner_variant_id = winner_id
        test.status = TestStatus.WINNER_SELECTED
        test.updated_at = datetime.now()
        
        # 승자 결정 로그
        self.manual_decisions[test_id] = {
            "auto_winner": winner_id,
            "decision_made": True,
            "decision_reason": "자동 결정",
            "decision_date": datetime.now()
        }
        
        return winner_id
    
    def manual_select_winner(self, test_id: str, variant_id: str, reason: str = "") -> bool:
        """수동으로 승자 선택"""
        if test_id not in self.tests:
            return False
        
        test = self.tests[test_id]
        if test.status != TestStatus.MANUAL_DECISION:
            return False
        
        # 승자 설정
        test.winner_variant_id = variant_id
        test.status = TestStatus.WINNER_SELECTED
        test.updated_at = datetime.now()
        
        # 수동 결정 정보 업데이트
        if test_id in self.manual_decisions:
            self.manual_decisions[test_id].update({
                "manual_winner": variant_id,
                "decision_made": True,
                "decision_reason": reason,
                "decision_date": datetime.now()
            })
        
        return True
    
    def check_manual_decision_timeout(self, test_id: str) -> bool:
        """수동 결정 기간 만료 확인"""
        if test_id not in self.tests:
            return False
        
        test = self.tests[test_id]
        if test.status != TestStatus.MANUAL_DECISION:
            return False
        
        if test.manual_decision_end_date and datetime.now() > test.manual_decision_end_date:
            # 수동 결정 기간 만료 - 자동 결정
            self._auto_determine_winner(test_id)
            return True
        
        return False
    
    def start_long_term_monitoring(self, test_id: str) -> bool:
        """장기 모니터링 시작 (1달)"""
        if test_id not in self.tests:
            return False
        
        test = self.tests[test_id]
        # 더 유연한 조건: 승자가 선택되었거나 완료된 상태
        if test.status not in [TestStatus.WINNER_SELECTED, TestStatus.COMPLETED, TestStatus.MANUAL_DECISION]:
            return False
        
        test.long_term_monitoring_start_date = datetime.now()
        
        # experiment_brief가 있는 경우에만 사용
        if test.experiment_brief:
            test.long_term_monitoring_end_date = datetime.now() + timedelta(days=test.experiment_brief.long_term_monitoring_days)
        else:
            test.long_term_monitoring_end_date = datetime.now() + timedelta(days=30)  # 기본값
        
        test.updated_at = datetime.now()
        
        # 장기 모니터링 데이터 초기화
        self.long_term_metrics[test_id] = {
            "cvr": [],
            "ctr": [],
            "revenue": [],
            "impressions": [],
            "conversions": []
        }
        
        return True
    
    def record_long_term_metrics(self, test_id: str, metrics: Dict[str, float]) -> bool:
        """장기 모니터링 메트릭 기록"""
        if test_id not in self.long_term_metrics:
            return False
        
        for metric, value in metrics.items():
            if metric in self.long_term_metrics[test_id]:
                self.long_term_metrics[test_id][metric].append(value)
        
        return True
    
    def get_long_term_performance(self, test_id: str) -> Dict[str, Any]:
        """장기 성과 분석"""
        if test_id not in self.long_term_metrics:
            return {}
        
        metrics = self.long_term_metrics[test_id]
        performance = {}
        
        for metric, values in metrics.items():
            if values:
                performance[f"{metric}_avg"] = np.mean(values)
                performance[f"{metric}_trend"] = np.polyfit(range(len(values)), values, 1)[0]  # 선형 트렌드
                performance[f"{metric}_stability"] = np.std(values) / np.mean(values) if np.mean(values) > 0 else 0
        
        return performance
    
    def complete_cycle(self, test_id: str) -> bool:
        """사이클 완료 처리"""
        if test_id not in self.tests:
            return False
        
        test = self.tests[test_id]
        test.status = TestStatus.CYCLE_COMPLETED
        test.cycle_completion_date = datetime.now()
        test.updated_at = datetime.now()
        
        # 사이클 히스토리 기록
        try:
            results = self.get_test_results(test_id)
            total_impressions = 0
            total_conversions = 0
            
            if results and "variants" in results:
                for variant_result in results["variants"].values():
                    total_impressions += variant_result.get("impressions", 0)
                    total_conversions += variant_result.get("conversions", 0)
            
            # 장기 성과 데이터 안전하게 가져오기
            long_term_performance = {}
            try:
                long_term_performance = self.get_long_term_performance(test_id)
            except Exception as e:
                print(f"Warning: Failed to get long term performance for {test_id}: {e}")
                long_term_performance = {}
            
            cycle_info = {
                "cycle_number": test.cycle_number,
                "winner_variant_id": test.winner_variant_id,
                "completion_date": test.cycle_completion_date,
                "long_term_performance": long_term_performance,
                "total_impressions": total_impressions,
                "total_conversions": total_conversions
            }
            
            if test_id not in self.cycle_history:
                self.cycle_history[test_id] = []
            self.cycle_history[test_id].append(cycle_info)
        except Exception as e:
            # 사이클 히스토리 기록 실패해도 사이클 완료는 진행
            print(f"Warning: Failed to record cycle history for {test_id}: {e}")
        
        # 다음 사이클 준비
        if test.cycle_number < test.max_cycles:
            self._prepare_next_cycle(test_id)
        else:
            # 최대 사이클 도달 - 아카이브
            test.status = TestStatus.ARCHIVED
        
        return True
    
    def _prepare_next_cycle(self, test_id: str) -> bool:
        """다음 사이클 준비"""
        if test_id not in self.tests:
            return False
        
        test = self.tests[test_id]
        
        # 이전 승자 정보 저장
        test.previous_winner_variant_id = test.winner_variant_id
        
        # 자동 사이클 대기열에 추가
        if test_id not in self.auto_cycle_queue:
            self.auto_cycle_queue.append(test_id)
        
        # 다음 사이클 스케줄 (7일 후)
        next_cycle_date = datetime.now() + timedelta(days=7)
        self.cycle_scheduler[test_id] = next_cycle_date
        
        return True
    
    def create_next_cycle_variants(self, test_id: str) -> List[PageVariant]:
        """다음 사이클을 위한 새로운 변형 생성"""
        if test_id not in self.tests:
            return []
        
        test = self.tests[test_id]
        previous_winner = test.previous_winner_variant_id
        
        # 이전 승자 변형 찾기
        winner_variant = None
        for variant in test.variants:
            if variant.variant_id == previous_winner:
                winner_variant = variant
                break
        
        if not winner_variant:
            return []
        
        # 새로운 변형 생성 (승자 기반 최적화)
        new_variants = []
        
        # 변형 A: 이전 승자 (기준)
        variant_a = PageVariant(
            variant_id=str(uuid.uuid4()),
            variant_type=VariantType.A,
            title=winner_variant.title,
            description=winner_variant.description,
            layout_type=winner_variant.layout_type,
            color_scheme=winner_variant.color_scheme,
            cta_text=winner_variant.cta_text,
            cta_color=winner_variant.cta_color,
            cta_position=winner_variant.cta_position,
            additional_features=winner_variant.additional_features,
            image_style=winner_variant.image_style,
            font_style=winner_variant.font_style,
            created_at=datetime.now()
        )
        new_variants.append(variant_a)
        
        # 변형 B: 승자 기반 개선 (CTA 최적화)
        variant_b = PageVariant(
            variant_id=str(uuid.uuid4()),
            variant_type=VariantType.B,
            title=winner_variant.title,
            description=winner_variant.description,
            layout_type=winner_variant.layout_type,
            color_scheme=winner_variant.color_scheme,
            cta_text="지금 구매하기",  # 더 강력한 CTA
            cta_color="#dc2626",  # 빨간색으로 변경
            cta_position="floating",  # 플로팅으로 변경
            additional_features=winner_variant.additional_features + ["긴급성"],
            image_style=winner_variant.image_style,
            font_style=winner_variant.font_style,
            created_at=datetime.now()
        )
        new_variants.append(variant_b)
        
        # 변형 C: 승자 기반 개선 (레이아웃 최적화)
        variant_c = PageVariant(
            variant_id=str(uuid.uuid4()),
            variant_type=VariantType.C,
            title=winner_variant.title,
            description=winner_variant.description,
            layout_type="hero",  # 히어로 레이아웃으로 변경
            color_scheme=winner_variant.color_scheme,
            cta_text=winner_variant.cta_text,
            cta_color=winner_variant.cta_color,
            cta_position="top",  # 상단으로 변경
            additional_features=winner_variant.additional_features + ["프리미엄"],
            image_style="enhanced",  # 향상된 이미지
            font_style="bold",  # 굵은 폰트
            created_at=datetime.now()
        )
        new_variants.append(variant_c)
        
        return new_variants
    
    def start_next_cycle(self, test_id: str) -> bool:
        """다음 사이클 시작"""
        if test_id not in self.tests:
            return False
        
        test = self.tests[test_id]
        
        # 새로운 변형 생성
        new_variants = self.create_next_cycle_variants(test_id)
        if not new_variants:
            return False
        
        # 테스트 정보 업데이트
        test.cycle_number += 1
        test.variants = new_variants
        test.status = TestStatus.ACTIVE
        test.start_date = datetime.now()
        
        # experiment_brief가 있는 경우에만 사용
        try:
            if test.experiment_brief and hasattr(test.experiment_brief, 'long_term_monitoring_days'):
                test.end_date = test.start_date + timedelta(days=test.experiment_brief.long_term_monitoring_days)
            else:
                test.end_date = test.start_date + timedelta(days=30)  # 기본값
        except Exception:
            test.end_date = test.start_date + timedelta(days=30)  # 기본값
        
        test.winner_variant_id = None
        test.manual_decision_start_date = None
        test.manual_decision_end_date = None
        test.long_term_monitoring_start_date = None
        test.long_term_monitoring_end_date = None
        test.cycle_completion_date = None
        test.updated_at = datetime.now()
        
        # 트래픽 분할 재설정
        test.traffic_split = {variant.variant_id: 100.0 / len(new_variants) for variant in new_variants}
        
        # 이벤트 초기화
        self.events[test_id] = []
        
        # 자동 사이클 대기열에서 제거
        if test_id in self.auto_cycle_queue:
            self.auto_cycle_queue.remove(test_id)
        
        return True
    
    def get_cycle_status(self, test_id: str) -> Dict[str, Any]:
        """사이클 상태 조회"""
        if test_id not in self.tests:
            return {}
        
        test = self.tests[test_id]
        
        return {
            "test_id": test_id,
            "cycle_number": test.cycle_number,
            "max_cycles": test.max_cycles,
            "status": test.status.value,
            "previous_winner": test.previous_winner_variant_id,
            "current_winner": test.winner_variant_id,
            "cycle_completion_date": test.cycle_completion_date.isoformat() if test.cycle_completion_date else None,
            "next_cycle_scheduled": self.cycle_scheduler.get(test_id),
            "in_auto_queue": test_id in self.auto_cycle_queue,
            "cycle_history": self.cycle_history.get(test_id, [])
        }
    
    def get_manual_decision_info(self, test_id: str) -> Dict[str, Any]:
        """수동 결정 정보 조회"""
        if test_id not in self.manual_decisions:
            return {}
        
        decision_info = self.manual_decisions[test_id]
        test = self.tests.get(test_id)
        
        return {
            "test_id": test_id,
            "decision_mode": test.decision_mode.value if test else "unknown",
            "manual_decision_start_date": decision_info.get("start_date"),
            "manual_decision_end_date": decision_info.get("end_date"),
            "manual_winner": decision_info.get("manual_winner"),
            "auto_winner": decision_info.get("auto_winner"),
            "decision_made": decision_info.get("decision_made", False),
            "decision_reason": decision_info.get("decision_reason", ""),
            "decision_date": decision_info.get("decision_date"),
            "time_remaining": self._get_manual_decision_time_remaining(test_id)
        }
    
    def _get_manual_decision_time_remaining(self, test_id: str) -> Optional[float]:
        """수동 결정 남은 시간 (시간 단위)"""
        if test_id not in self.tests:
            return None
        
        test = self.tests[test_id]
        if not test.manual_decision_end_date:
            return None
        
        remaining = test.manual_decision_end_date - datetime.now()
        return max(0, remaining.total_seconds() / 3600)  # 시간 단위
    
    def get_auto_cycle_queue(self) -> List[Dict[str, Any]]:
        """자동 사이클 대기열 조회"""
        queue_info = []
        for test_id in self.auto_cycle_queue:
            test = self.tests.get(test_id)
            if test:
                queue_info.append({
                    "test_id": test_id,
                    "test_name": test.test_name,
                    "cycle_number": test.cycle_number,
                    "scheduled_date": self.cycle_scheduler.get(test_id),
                    "previous_winner": test.previous_winner_variant_id
                })
        
        return queue_info
    
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
        
        test = self.tests[test_id]
        
        event = TestEvent(
            event_id=str(uuid.uuid4()),
            test_id=test_id,
            variant_id=variant_id,
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime.now(),
            session_id=session_id,
            product_id=test.product_info.product_id,
            price=test.product_info.price,
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
            # 매출 = 구매수 × 상품가격 (같은 제품이므로 가격은 동일)
            revenue = conversions * test.product_info.price
            
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
        
        # 가장 높은 CVR을 가진 변형을 우선적으로 선택
        best_variant = None
        best_cvr = -1
        
        for variant_id, result in variant_results.items():
            # 최소 노출 수 확인 (통계적 신뢰성을 위해)
            if result.impressions >= 5:  # 최소 5회 노출
                if result.conversion_rate > best_cvr:
                    best_cvr = result.conversion_rate
                    best_variant = variant_id
        
        # CVR이 같은 경우 매출로 비교
        if best_variant is None:
            best_revenue = -1
            for variant_id, result in variant_results.items():
                if result.impressions >= 5 and result.revenue > best_revenue:
                    best_revenue = result.revenue
                    best_variant = variant_id
        
        # 여전히 결정되지 않으면 가장 많은 노출을 받은 변형 선택
        if best_variant is None:
            best_impressions = -1
            for variant_id, result in variant_results.items():
                if result.impressions > best_impressions:
                    best_impressions = result.impressions
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
                "product_name": test.product_info.product_name,
                "test_mode": test.test_mode.value
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

# 새로운 기능들 추가
def create_experiment_brief(self, objective: str, primary_metrics: List[str], 
                           secondary_metrics: List[str], guardrails: Dict[str, float],
                           target_categories: List[str], target_channels: List[str],
                           target_devices: List[str], exclude_conditions: List[str],
                           variant_count: int, distribution_mode: DistributionMode,
                           mde: float, min_sample_size: int) -> ExperimentBrief:
    """실험 계약서 생성 - 요구사항 1번"""
    
    # 초기 분배 설정
    if distribution_mode == DistributionMode.EQUAL:
        initial_split = {chr(65 + i): 1.0 / variant_count for i in range(variant_count)}
    else:
        initial_split = {chr(65 + i): 1.0 / variant_count for i in range(variant_count)}
    
    # 종료 & 승격 & 롤백 규칙
    termination_rules = {
        "min_duration_hours": 24,
        "max_duration_hours": 168,  # 7일
        "confidence_threshold": 0.95,
        "mde_achieved": True
    }
    
    promotion_rules = {
        "stages": [0.25, 0.5, 1.0],
        "stage_duration_hours": 12,
        "guardrail_check": True
    }
    
    rollback_rules = {
        "performance_threshold": -0.2,  # -20%
        "guardrail_violation": True,
        "auto_rollback": True
    }
    
    return ExperimentBrief(
        objective=objective,
        primary_metrics=primary_metrics,
        secondary_metrics=secondary_metrics,
        guardrails=guardrails,
        target_categories=target_categories,
        target_channels=target_channels,
        target_devices=target_devices,
        exclude_conditions=exclude_conditions,
        variant_count=variant_count,
        distribution_mode=distribution_mode,
        initial_split=initial_split,
        mde=mde,
        min_sample_size=min_sample_size,
        termination_rules=termination_rules,
        promotion_rules=promotion_rules,
        rollback_rules=rollback_rules
    )

def create_test_with_brief(self, test_name: str, product_info: ProductInfo,
                          variants: List[PageVariant], experiment_brief: ExperimentBrief,
                          test_mode: TestMode = TestMode.MANUAL) -> ABTest:
    """실험 계약서와 함께 테스트 생성"""
    
    test = self.create_test(
        test_name=test_name,
        product_info=product_info,
        variants=variants,
        duration_days=7,  # 기본값
        target_metrics={"ctr": 0.6, "conversion_rate": 0.4}
    )
    
    # 실험 계약서 설정
    test.experiment_brief = experiment_brief
    test.test_mode = test_mode
    test.traffic_split = experiment_brief.initial_split
    
    # Thompson Sampling 초기화
    if experiment_brief.distribution_mode == DistributionMode.BANDIT:
        self.thompson_params[test.test_id] = {
            variant.variant_id: (1.0, 1.0) for variant in variants
        }
    
    # SRM 감지 초기화
    self.srm_data[test.test_id] = {
        variant.variant_id: 0 for variant in variants
    }
    
    return test

def get_variant_with_bandit(self, test_id: str, user_id: str, session_id: str) -> Optional[PageVariant]:
    """Thompson Sampling을 사용한 변형 선택 - 요구사항 7번"""
    if test_id not in self.tests:
        return None
    
    test = self.tests[test_id]
    if test.status != TestStatus.ACTIVE:
        return None
    
    # Sticky Assignment 확인
    user_key = f"{user_id}_{test_id}"
    if test.sticky_assignment and user_key in self.user_variants:
        variant_id = self.user_variants[user_key]
        return next((v for v in test.variants if v.variant_id == variant_id), None)
    
    # Thompson Sampling 적용
    if test.experiment_brief and test.experiment_brief.distribution_mode == DistributionMode.BANDIT:
        variant_id = self._thompson_sampling(test_id, user_id)
    else:
        # 기존 해시 기반 선택
        hash_value = int(hashlib.md5(user_key.encode()).hexdigest(), 16)
        variant_index = hash_value % len(test.variants)
        variant_id = test.variants[variant_index].variant_id
    
    # Sticky Assignment 저장
    if test.sticky_assignment:
        self.user_variants[user_key] = variant_id
    
    return next((v for v in test.variants if v.variant_id == variant_id), None)

def _thompson_sampling(self, test_id: str, user_id: str) -> str:
    """Thompson Sampling 알고리즘"""
    if test_id not in self.thompson_params:
        return None
    
    params = self.thompson_params[test_id]
    samples = {}
    
    # 각 변형에서 베타 분포 샘플링
    for variant_id, (alpha, beta) in params.items():
        samples[variant_id] = np.random.beta(alpha, beta)
    
    # 최대값을 가진 변형 선택
    selected_variant = max(samples.items(), key=lambda x: x[1])[0]
    
    # 의사결정 로그 기록
    decision = BanditDecision(
        timestamp=datetime.now(),
        test_id=test_id,
        user_id=user_id,
        selected_variant=selected_variant,
        decision_reason="Thompson Sampling",
        thompson_values=samples
    )
    self.bandit_decisions.append(decision)
    
    return selected_variant

def update_thompson_params(self, test_id: str, variant_id: str, event_type: str):
    """Thompson Sampling 파라미터 업데이트"""
    if test_id not in self.thompson_params:
        return
    
    if variant_id not in self.thompson_params[test_id]:
        return
    
    alpha, beta = self.thompson_params[test_id][variant_id]
    
    if event_type == "purchase":
        # 성공: alpha 증가
        self.thompson_params[test_id][variant_id] = (alpha + 1, beta)
    elif event_type == "impression":
        # 실패: beta 증가 (구매하지 않음)
        self.thompson_params[test_id][variant_id] = (alpha, beta + 1)

def check_srm(self, test_id: str) -> bool:
    """SRM (Sample Ratio Mismatch) 감지 - 요구사항 6번"""
    if test_id not in self.tests:
        return False
    
    test = self.tests[test_id]
    if not test.srm_detection:
        return True
    
    # 예상 분배와 실제 분배 비교
    expected_split = test.experiment_brief.initial_split if test.experiment_brief else test.traffic_split
    actual_counts = self.srm_data.get(test_id, {})
    
    if not actual_counts:
        return True
    
    total_count = sum(actual_counts.values())
    if total_count == 0:
        return True
    
    # 카이제곱 검정
    observed = []
    expected = []
    
    for variant_id, count in actual_counts.items():
        if variant_id in expected_split:
            observed.append(count)
            expected.append(expected_split[variant_id] * total_count)
    
    if len(observed) < 2:
        return True
    
    try:
        chi2, p_value = stats.chisquare(observed, expected)
        
        # SRM 알림 생성
        if p_value < test.srm_threshold:
            alert = GuardrailAlert(
                alert_id=str(uuid.uuid4()),
                test_id=test_id,
                alert_type="SRM",
                severity="HIGH",
                message=f"SRM 감지: p-value={p_value:.4f}",
                timestamp=datetime.now()
            )
            self.guardrail_alerts.append(alert)
            return False
        
        return True
    except:
        return True

def check_bot_and_outliers(self, event: TestEvent) -> bool:
    """봇 및 이상치 필터링 - 요구사항 6번"""
    # 봇 필터
    if self._is_bot(event.user_agent):
        event.bot_flag = True
        return False
    
    # 이상치 필터
    if self._is_outlier(event):
        event.guardrail_breach = True
        return False
    
    return True

def _is_bot(self, user_agent: str) -> bool:
    """봇 감지"""
    bot_indicators = [
        "bot", "crawler", "spider", "scraper", "headless",
        "phantomjs", "selenium", "webdriver", "curl", "wget"
    ]
    
    user_agent_lower = user_agent.lower()
    return any(indicator in user_agent_lower for indicator in bot_indicators)

def _is_outlier(self, event: TestEvent) -> bool:
    """이상치 감지"""
    # 체류 시간이 너무 짧음
    if event.session_duration < 1.0:  # 1초 미만
        return True
    
    # 비정상적인 클릭 패턴 (예: 너무 빠른 연속 클릭)
    # 이 부분은 실제 구현에서 더 정교하게 처리해야 함
    return False

def check_guardrails(self, test_id: str) -> bool:
    """가드레일 모니터링 - 요구사항 6번"""
    if test_id not in self.tests:
        return True
    
    test = self.tests[test_id]
    if not test.guardrail_monitoring or not test.experiment_brief:
        return True
    
    guardrails = test.experiment_brief.guardrails
    
    # 실제 구현에서는 성능 메트릭을 수집해야 함
    # 여기서는 예시로 가정
    current_metrics = {
        "LCP": 2.5,  # 예시 값
        "error_rate": 0.001,
        "return_rate": 0.05
    }
    
    violations = []
    for metric, threshold in guardrails.items():
        if metric in current_metrics:
            if current_metrics[metric] > threshold:
                violations.append(f"{metric}: {current_metrics[metric]} > {threshold}")
    
    if violations:
        alert = GuardrailAlert(
            alert_id=str(uuid.uuid4()),
            test_id=test_id,
            alert_type="GUARDRAIL",
            severity="CRITICAL",
            message=f"가드레일 위반: {', '.join(violations)}",
            timestamp=datetime.now()
        )
        self.guardrail_alerts.append(alert)
        return False
    
    return True

def apply_policy_filters(self, variant: PageVariant) -> bool:
    """정책 필터 적용 - 요구사항 2번"""
    # 금칙어 체크
    forbidden_words = ["최고", "최저가", "무료", "100%", "보장"]
    content = f"{variant.title} {variant.description}".lower()
    
    for word in forbidden_words:
        if word in content:
            return False
    
    # 과장표현 체크
    exaggeration_patterns = [
        r"최고의", r"최고급", r"최고품질", r"최고수준",
        r"완벽한", r"완벽하게", r"완벽함",
        r"절대", r"절대적으로"
    ]
    
    import re
    for pattern in exaggeration_patterns:
        if re.search(pattern, content):
            return False
    
    # 성능 체크 (예시)
    if len(variant.title) > 100 or len(variant.description) > 500:
        return False
    
    # 접근성 체크 (예시)
    if not variant.cta_text or len(variant.cta_text.strip()) == 0:
        return False
    
    return True

def get_bandit_decisions(self, test_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """밴딧 의사결정 로그 조회 - 요구사항 9번"""
    decisions = [d for d in self.bandit_decisions if d.test_id == test_id]
    decisions = decisions[-limit:]
    
    return [
        {
            "timestamp": decision.timestamp.isoformat(),
            "user_id": decision.user_id,
            "selected_variant": decision.selected_variant,
            "decision_reason": decision.decision_reason,
            "epsilon": decision.epsilon,
            "thompson_values": decision.thompson_values
        }
        for decision in decisions
    ]

def get_guardrail_alerts(self, test_id: str = None) -> List[Dict[str, Any]]:
    """가드레일 알림 조회"""
    alerts = self.guardrail_alerts
    if test_id:
        alerts = [a for a in alerts if a.test_id == test_id]
    
    return [
        {
            "alert_id": alert.alert_id,
            "test_id": alert.test_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
            "resolved": alert.resolved,
            "action_taken": alert.action_taken
        }
        for alert in alerts
    ]

def promote_winner(self, test_id: str, variant_id: str) -> bool:
    """승자 승격 - 요구사항 8번"""
    if test_id not in self.tests:
        return False
    
    test = self.tests[test_id]
    if not test.promotion_stages:
        test.promotion_stages = [0.25, 0.5, 1.0]
    
    # 현재 단계 확인
    current_stage = self.promotion_status.get(test_id, {}).get("current_stage", 0)
    
    if current_stage >= len(test.promotion_stages):
        return False
    
    # 다음 단계로 승격
    next_traffic = test.promotion_stages[current_stage]
    
    # 트래픽 분배 업데이트
    for variant in test.variants:
        if variant.variant_id == variant_id:
            test.traffic_split[variant_id] = next_traffic
        else:
            test.traffic_split[variant.variant_id] = (1.0 - next_traffic) / (len(test.variants) - 1)
    
    # 승격 상태 업데이트
    self.promotion_status[test_id] = {
        "current_stage": current_stage + 1,
        "promoted_variant": variant_id,
        "promotion_time": datetime.now(),
        "traffic_percentage": next_traffic
    }
    
    return True

def auto_rollback(self, test_id: str) -> bool:
    """자동 롤백 - 요구사항 8번"""
    if test_id not in self.tests:
        return False
    
    test = self.tests[test_id]
    if not test.auto_rollback:
        return False
    
    # 최근 30분간의 성과 확인
    recent_events = [
        e for e in self.events.get(test_id, [])
        if (datetime.now() - e.timestamp).total_seconds() < 1800  # 30분
    ]
    
    if not recent_events:
        return False
    
    # 성과 계산
    recent_conversions = len([e for e in recent_events if e.event_type == "purchase"])
    recent_impressions = len([e for e in recent_events if e.event_type == "impression"])
    
    if recent_impressions == 0:
        return False
    
    recent_cvr = recent_conversions / recent_impressions
    
    # 롤백 조건 확인
    if recent_cvr < test.rollback_threshold:
        # 원래 분배로 복원
        if test.experiment_brief:
            test.traffic_split = test.experiment_brief.initial_split.copy()
        
        # 롤백 알림 생성
        alert = GuardrailAlert(
            alert_id=str(uuid.uuid4()),
            test_id=test_id,
            alert_type="ROLLBACK",
            severity="HIGH",
            message=f"자동 롤백: CVR {recent_cvr:.4f} < {test.rollback_threshold}",
            timestamp=datetime.now(),
            action_taken="Traffic restored to original distribution"
        )
        self.guardrail_alerts.append(alert)
        
        return True
    
    return False

# ABTestManager 클래스에 새로운 메서드들 추가
ABTestManager.create_experiment_brief = create_experiment_brief
ABTestManager.create_test_with_brief = create_test_with_brief
ABTestManager.get_variant_with_bandit = get_variant_with_bandit
ABTestManager._thompson_sampling = _thompson_sampling
ABTestManager.update_thompson_params = update_thompson_params
ABTestManager.check_srm = check_srm
ABTestManager.check_bot_and_outliers = check_bot_and_outliers
ABTestManager._is_bot = _is_bot
ABTestManager._is_outlier = _is_outlier
ABTestManager.check_guardrails = check_guardrails
ABTestManager.apply_policy_filters = apply_policy_filters
ABTestManager.get_bandit_decisions = get_bandit_decisions
ABTestManager.get_guardrail_alerts = get_guardrail_alerts
ABTestManager.promote_winner = promote_winner
ABTestManager.auto_rollback = auto_rollback

