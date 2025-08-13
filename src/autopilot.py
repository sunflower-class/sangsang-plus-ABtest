#!/usr/bin/env python3
"""
자동 생성기(Autopilot) 및 스케줄러
요구사항 3번: 실험 생성 방식 (수동 vs 자동)
요구사항 11번: 자동화 루프
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import random
import json
import logging
import threading
import uuid

from ab_test_manager import (
    ABTestManager, ProductInfo, PageVariant, VariantType, 
    ExperimentBrief, DistributionMode, TestMode, TestStatus, DecisionMode
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('autopilot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ProductCandidate:
    """자동 생성 후보 상품"""
    product_id: str
    product_name: str
    daily_sessions: int
    inventory: int
    last_experiment_date: Optional[datetime]
    cool_down_days: int
    category: str
    price: float
    priority_score: float = 0.0

class AutopilotConfig:
    """자동 생성 설정"""
    def __init__(
        self,
        enabled: bool = True,
        check_interval_hours: int = 24,
        cycle_check_interval_hours: int = 6,
        auto_cycle_enabled: bool = True,
        manual_decision_timeout_hours: int = 168,  # 7일
        long_term_monitoring_enabled: bool = True,
        test_mode: bool = False,  # 테스트 모드 추가
        max_concurrent_experiments: int = 5,
        max_traffic_usage: float = 0.2,
        min_daily_sessions: int = 100,
        min_inventory: int = 10,
        cool_down_days: int = 7,
        experiment_duration_days: int = 14
    ):
        self.enabled = enabled
        self.check_interval_hours = check_interval_hours
        self.cycle_check_interval_hours = cycle_check_interval_hours
        self.auto_cycle_enabled = auto_cycle_enabled
        self.manual_decision_timeout_hours = manual_decision_timeout_hours
        self.long_term_monitoring_enabled = long_term_monitoring_enabled
        self.test_mode = test_mode
        self.max_concurrent_experiments = max_concurrent_experiments
        self.max_traffic_usage = max_traffic_usage
        self.min_daily_sessions = min_daily_sessions
        self.min_inventory = min_inventory
        self.cool_down_days = cool_down_days
        self.experiment_duration_days = experiment_duration_days
        
        # 테스트 모드일 때 시간 간격 단축
        if self.test_mode:
            self.check_interval_hours = 1  # 1시간
            self.cycle_check_interval_hours = 1  # 1시간
            self.manual_decision_timeout_hours = 1  # 1시간

class CycleManager:
    """사이클 관리자 - 완전한 AB 테스트 루프 관리"""
    
    def __init__(self, ab_test_manager: ABTestManager, config: AutopilotConfig):
        self.ab_test_manager = ab_test_manager
        self.config = config
        self.is_running = False
        self.cycle_thread = None
    
    def start(self):
        """사이클 관리자 시작"""
        if self.is_running:
            return
        
        self.is_running = True
        self.cycle_thread = threading.Thread(target=self._run_cycle_manager, daemon=True)
        self.cycle_thread.start()
        logger.info("사이클 관리자 시작됨")
    
    def stop(self):
        """사이클 관리자 중지"""
        self.is_running = False
        if self.cycle_thread:
            self.cycle_thread.join()
        logger.info("사이클 관리자 중지됨")
    
    def _run_cycle_manager(self):
        """사이클 관리자 메인 루프"""
        while self.is_running:
            try:
                self._check_manual_decision_timeouts()
                self._check_long_term_monitoring()
                self._process_auto_cycle_queue()
                self._check_completed_tests()
                
                # 6시간마다 체크
                time.sleep(self.config.cycle_check_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"사이클 관리자 오류: {e}")
                time.sleep(300)  # 5분 후 재시도
    
    def _check_manual_decision_timeouts(self):
        """수동 결정 타임아웃 체크"""
        for test_id in list(self.ab_test_manager.tests.keys()):
            test = self.ab_test_manager.tests[test_id]
            if test.status == TestStatus.MANUAL_DECISION:
                if self.ab_test_manager.check_manual_decision_timeout(test_id):
                    logger.info(f"테스트 {test_id} 수동 결정 타임아웃 - 자동 결정 실행")
    
    def _check_long_term_monitoring(self):
        """장기 모니터링 체크"""
        if not self.config.long_term_monitoring_enabled:
            return
        
        for test_id in list(self.ab_test_manager.tests.keys()):
            test = self.ab_test_manager.tests[test_id]
            if test.status == TestStatus.WINNER_SELECTED:
                # 승자 선택 후 장기 모니터링 시작
                if not test.long_term_monitoring_start_date:
                    self.ab_test_manager.start_long_term_monitoring(test_id)
                    logger.info(f"테스트 {test_id} 장기 모니터링 시작")
                
                # 장기 모니터링 완료 체크
                elif (test.long_term_monitoring_end_date and 
                      datetime.now() > test.long_term_monitoring_end_date):
                    # 장기 모니터링 완료 - 사이클 완료
                    self.ab_test_manager.complete_cycle(test_id)
                    logger.info(f"테스트 {test_id} 장기 모니터링 완료 - 사이클 완료")
    
    def _process_auto_cycle_queue(self):
        """자동 사이클 대기열 처리"""
        if not self.config.auto_cycle_enabled:
            return
        
        current_time = datetime.now()
        queue = self.ab_test_manager.get_auto_cycle_queue()
        
        for item in queue:
            test_id = item["test_id"]
            scheduled_date = self.ab_test_manager.cycle_scheduler.get(test_id)
            
            if scheduled_date and current_time >= scheduled_date:
                # 스케줄된 시간 도달 - 다음 사이클 시작
                if self.ab_test_manager.start_next_cycle(test_id):
                    logger.info(f"테스트 {test_id} 다음 사이클 시작")
                else:
                    logger.error(f"테스트 {test_id} 다음 사이클 시작 실패")
    
    def _check_completed_tests(self):
        """완료된 테스트 체크"""
        for test_id in list(self.ab_test_manager.tests.keys()):
            test = self.ab_test_manager.tests[test_id]
            
            # 테스트 완료 조건 체크
            if test.status == TestStatus.ACTIVE and test.end_date:
                if datetime.now() > test.end_date:
                    # 테스트 기간 만료 - 완료 처리
                    self.ab_test_manager.complete_test(test_id)
                    logger.info(f"테스트 {test_id} 기간 만료 - 완료 처리")

class VariantGenerator:
    """변형 자동 생성기 - 요구사항 2번"""
    
    def __init__(self):
        self.layout_types = ["grid", "list", "carousel", "hero", "minimal"]
        self.color_schemes = ["light", "dark", "colorful", "neutral"]
        self.cta_texts = ["구매하기", "장바구니 담기", "즉시 구매", "자세히 보기", "지금 주문"]
        self.cta_colors = ["#007bff", "#28a745", "#dc3545", "#ffc107", "#17a2b8"]
        self.cta_positions = ["top", "middle", "bottom", "floating"]
        self.additional_features = [
            ["리뷰", "배송정보"],
            ["관련상품", "Q&A"],
            ["스펙", "리뷰"],
            ["배송정보", "스펙"],
            ["Q&A", "관련상품"]
        ]
        self.image_styles = ["original", "enhanced", "minimal", "gallery"]
        self.font_styles = ["modern", "classic", "bold", "elegant"]
        
        # 성공 패턴 데이터베이스 (실제로는 DB에서 관리)
        self.success_patterns = {
            "electronics": {
                "layout_type": "grid",
                "cta_text": "즉시 구매",
                "color_scheme": "dark",
                "features": ["스펙", "리뷰"]
            },
            "fashion": {
                "layout_type": "carousel",
                "cta_text": "장바구니 담기",
                "color_scheme": "colorful",
                "features": ["관련상품", "리뷰"]
            }
        }
    
    def generate_variants(self, product_info: ProductInfo, variant_count: int = 3) -> List[PageVariant]:
        """상품 정보를 기반으로 변형 자동 생성"""
        variants = []
        
        # 기본 변형 (A) - 현재 페이지와 유사
        base_variant = self._create_base_variant(product_info, VariantType.A)
        variants.append(base_variant)
        
        # 변형 B, C 생성
        for i in range(1, min(variant_count, 4)):
            variant_type = VariantType(chr(65 + i))
            variant = self._create_optimized_variant(product_info, variant_type, i)
            variants.append(variant)
        
        return variants
    
    def _create_base_variant(self, product_info: ProductInfo, variant_type: VariantType) -> PageVariant:
        """기본 변형 생성"""
        return PageVariant(
            variant_id=str(uuid.uuid4()),
            variant_type=variant_type,
            title=product_info.product_name,
            description=product_info.product_description,
            layout_type="grid",
            color_scheme="light",
            cta_text="구매하기",
            cta_color="#007bff",
            cta_position="bottom",
            additional_features=["리뷰", "배송정보"],
            image_style="original",
            font_style="modern",
            created_at=datetime.now()
        )
    
    def _create_optimized_variant(self, product_info: ProductInfo, variant_type: VariantType, index: int) -> PageVariant:
        """최적화된 변형 생성"""
        # 카테고리별 성공 패턴 적용
        category_pattern = self.success_patterns.get(product_info.category.lower(), {})
        
        return PageVariant(
            variant_id=str(uuid.uuid4()),
            variant_type=variant_type,
            title=product_info.product_name,
            description=product_info.product_description,
            layout_type=category_pattern.get("layout_type", random.choice(self.layout_types)),
            color_scheme=category_pattern.get("color_scheme", random.choice(self.color_schemes)),
            cta_text=category_pattern.get("cta_text", random.choice(self.cta_texts)),
            cta_color=random.choice(self.cta_colors),
            cta_position=random.choice(self.cta_positions),
            additional_features=category_pattern.get("features", random.choice(self.additional_features)),
            image_style=random.choice(self.image_styles),
            font_style=random.choice(self.font_styles),
            created_at=datetime.now()
        )

class AutopilotScheduler:
    """자동 생성 스케줄러"""
    
    def __init__(self, ab_test_manager: ABTestManager, config: AutopilotConfig):
        self.ab_test_manager = ab_test_manager
        self.config = config
        self.product_candidates: Dict[str, ProductCandidate] = {}
        self.promotion_mode = False  # 프로모션 기간 글로벌 스위치
        self.variant_generator = VariantGenerator()
        self.cycle_manager = CycleManager(ab_test_manager, config)
        
        # 스케줄러 시작
        self._setup_scheduler()
        self.cycle_manager.start()
    
    def _setup_scheduler(self):
        """스케줄러 설정"""
        # 매일 자동 실험 생성 체크
        schedule.every(self.config.check_interval_hours).hours.do(self._check_and_create_experiments)
        
        # 매시간 수동 결정 타임아웃 체크
        schedule.every().hour.do(self._check_manual_decision_timeouts)
        
        # 매 6시간 사이클 관리
        schedule.every(self.config.cycle_check_interval_hours).hours.do(self._manage_cycles)
    
    def run_scheduler(self):
        """스케줄러 실행"""
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
    
    def _check_and_create_experiments(self):
        """실험 생성 체크 및 실행"""
        if not self.config.enabled or self.promotion_mode:
            return
        
        candidates = self.select_candidates()
        for candidate in candidates:
            self.create_experiment_for_product(candidate)
    
    def _check_manual_decision_timeouts(self):
        """수동 결정 타임아웃 체크"""
        for test_id in list(self.ab_test_manager.tests.keys()):
            self.ab_test_manager.check_manual_decision_timeout(test_id)
    
    def _manage_cycles(self):
        """사이클 관리"""
        # 장기 모니터링 완료된 테스트 체크
        for test_id in list(self.ab_test_manager.tests.keys()):
            test = self.ab_test_manager.tests.get(test_id)
            if test and test.status == TestStatus.LONG_TERM_MONITORING:
                # 장기 모니터링 기간이 끝났는지 확인
                if test.long_term_monitoring_end_date and datetime.now() >= test.long_term_monitoring_end_date:
                    self.ab_test_manager.complete_cycle(test_id)
        
        # 자동 사이클 대기열 처리
        current_time = datetime.now()
        for test_id in list(self.ab_test_manager.auto_cycle_queue):
            scheduled_date = self.ab_test_manager.cycle_scheduler.get(test_id)
            if scheduled_date and current_time >= scheduled_date:
                # 스케줄된 시간 도달 - 다음 사이클 시작
                self.ab_test_manager.start_next_cycle(test_id)
    
    def get_autopilot_status(self) -> Dict[str, Any]:
        """자동 생성 상태 조회"""
        try:
            active_tests = [test for test in self.ab_test_manager.tests.values() if test.status == TestStatus.ACTIVE]
            completed_tests = [test for test in self.ab_test_manager.tests.values() if test.status in [TestStatus.COMPLETED, TestStatus.WINNER_SELECTED]]
            autopilot_tests = [test for test in self.ab_test_manager.tests.values() if test.test_mode == TestMode.AUTOPILOT]
            
            return {
                "enabled": self.config.enabled,
                "promotion_mode": self.promotion_mode,
                "active_tests_count": len(active_tests),
                "completed_tests_count": len(completed_tests),
                "total_tests_count": len(self.ab_test_manager.tests),
                "active_autopilot_experiments": len([t for t in autopilot_tests if t.status == TestStatus.ACTIVE]),
                "total_traffic_usage": sum(self.ab_test_manager.traffic_budget_usage.values()) if hasattr(self.ab_test_manager, 'traffic_budget_usage') else 0.0,
                "auto_cycle_queue_size": len(self.ab_test_manager.auto_cycle_queue),
                "cycle_manager_running": self.cycle_manager.is_running,
                "last_check_time": datetime.now().isoformat(),
                "config": {
                    "check_interval_hours": self.config.check_interval_hours,
                    "cycle_check_interval_hours": self.config.cycle_check_interval_hours,
                    "auto_cycle_enabled": self.config.auto_cycle_enabled
                }
            }
        except Exception as e:
            logger.error(f"자동 생성 상태 조회 중 오류: {e}")
            return {
                "enabled": False,
                "error": str(e),
                "last_check_time": datetime.now().isoformat()
            }

    def add_product_candidate(self, product_info: ProductInfo):
        """상품 후보 추가"""
        candidate = ProductCandidate(
            product_id=product_info.product_id,
            product_name=product_info.product_name,
            daily_sessions=product_info.daily_sessions,
            inventory=product_info.inventory,
            last_experiment_date=None,
            cool_down_days=product_info.cool_down_days,
            category=product_info.category,
            price=product_info.price
        )
        self.product_candidates[product_info.product_id] = candidate
    
    def calculate_priority_score(self, candidate: ProductCandidate) -> float:
        """우선순위 점수 계산"""
        score = 0.0
        
        # 세션 수 점수 (0-40점)
        session_score = min(candidate.daily_sessions / 1000, 1.0) * 40
        score += session_score
        
        # 재고 점수 (0-20점)
        inventory_score = min(candidate.inventory / 100, 1.0) * 20
        score += inventory_score
        
        # 가격 점수 (0-20점) - 높은 가격일수록 높은 점수
        price_score = min(candidate.price / 1000000, 1.0) * 20
        score += price_score
        
        # 쿨다운 점수 (0-20점) - 오래된 실험이면 높은 점수
        cool_down_score = 0.0
        if candidate.last_experiment_date:
            days_since_last = (datetime.now() - candidate.last_experiment_date).days
            cool_down_score = min(days_since_last / candidate.cool_down_days, 1.0)
        else:
            cool_down_score = 1.0  # 첫 실험
        score += cool_down_score * 20
        
        return score
    
    def select_candidates(self) -> List[ProductCandidate]:
        """실험 후보 상품 선별"""
        if self.promotion_mode:
            logger.info("프로모션 모드: 자동 실험 비활성화")
            return []
        
        # 우선순위 점수 계산
        for candidate in self.product_candidates.values():
            candidate.priority_score = self.calculate_priority_score(candidate)
        
        # 필터링 조건 적용
        filtered_candidates = []
        for candidate in self.product_candidates.values():
            if (candidate.daily_sessions >= self.config.min_daily_sessions and
                candidate.inventory >= self.config.min_inventory and
                (candidate.last_experiment_date is None or
                 (datetime.now() - candidate.last_experiment_date).days >= candidate.cool_down_days)):
                filtered_candidates.append(candidate)
        
        # 우선순위 순으로 정렬
        filtered_candidates.sort(key=lambda x: x.priority_score, reverse=True)
        
        # 동시 실험 제한 적용
        active_experiments = len([t for t in self.ab_test_manager.tests.values() 
                                if t.status == TestStatus.ACTIVE])
        
        max_new_experiments = self.config.max_concurrent_experiments - active_experiments
        
        return filtered_candidates[:max_new_experiments]
    
    def create_experiment_for_product(self, candidate: ProductCandidate) -> bool:
        """상품을 위한 실험 생성"""
        try:
            # 상품 정보 생성
            product_info = ProductInfo(
                product_id=candidate.product_id,
                product_name=candidate.product_name,
                product_image="",  # 실제로는 이미지 URL 필요
                product_description=f"{candidate.product_name} 상품입니다.",
                price=candidate.price,
                category=candidate.category,
                daily_sessions=candidate.daily_sessions,
                inventory=candidate.inventory,
                cool_down_days=candidate.cool_down_days
            )
            
            # 변형 생성
            variants = self.variant_generator.generate_variants(product_info, 3)
            
            # 실험 계약서 생성
            experiment_brief = ExperimentBrief(
                objective="구매 전환율(CVR) 최대화",
                primary_metrics=["CVR"],
                secondary_metrics=["CTR", "ATC", "체류시간"],
                guardrails={"LCP": 3.5, "error_rate": 0.005, "return_rate": 0.1},
                target_categories=[candidate.category],
                target_channels=["web", "mobile"],
                target_devices=["desktop", "mobile"],
                exclude_conditions=[],
                variant_count=3,
                distribution_mode=DistributionMode.EQUAL,
                mde=0.1,
                min_sample_size=1000,
                termination_rules={},
                promotion_rules={},
                rollback_rules={},
                decision_mode=DecisionMode.HYBRID,
                manual_decision_period_days=7,
                long_term_monitoring_days=30
            )
            
            # 테스트 생성
            test = self.ab_test_manager.create_test_with_brief(
                test_name=f"{candidate.product_name} 자동 실험",
                product_info=product_info,
                variants=variants,
                experiment_brief=experiment_brief,
                test_mode=TestMode.AUTOPILOT
            )
            
            # 테스트 시작
            self.ab_test_manager.start_test(test.test_id)
            
            # 후보 정보 업데이트
            candidate.last_experiment_date = datetime.now()
            
            logger.info(f"자동 실험 생성 완료: {test.test_id} - {candidate.product_name}")
            return True
            
        except Exception as e:
            logger.error(f"자동 실험 생성 실패: {candidate.product_name} - {e}")
            return False
    
    def set_promotion_mode(self, enabled: bool):
        """프로모션 모드 설정"""
        self.promotion_mode = enabled
        logger.info(f"프로모션 모드: {'활성화' if enabled else '비활성화'}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """스케줄러 상태 조회"""
        return {
            "enabled": self.config.enabled,
            "promotion_mode": self.promotion_mode,
            "product_candidates_count": len(self.product_candidates),
            "active_experiments": len([t for t in self.ab_test_manager.tests.values() 
                                     if t.status == TestStatus.ACTIVE]),
            "auto_cycle_queue": self.ab_test_manager.get_auto_cycle_queue(),
            "cycle_manager_running": self.cycle_manager.is_running
        }

def initialize_autopilot(ab_test_manager: ABTestManager, config: AutopilotConfig = None) -> AutopilotScheduler:
    """Autopilot 초기화"""
    if config is None:
        config = AutopilotConfig()
    
    scheduler = AutopilotScheduler(ab_test_manager, config)
    
    # 스케줄러 스레드 시작
    scheduler_thread = threading.Thread(target=scheduler.run_scheduler, daemon=True)
    scheduler_thread.start()
    
    return scheduler
