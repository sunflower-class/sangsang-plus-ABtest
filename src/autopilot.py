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

from ab_test_manager import (
    ABTestManager, ProductInfo, PageVariant, VariantType, 
    ExperimentBrief, DistributionMode, TestMode, TestStatus
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
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

@dataclass
class AutopilotConfig:
    """자동 생성 설정"""
    enabled: bool = True
    max_concurrent_experiments: int = 5
    max_traffic_usage: float = 0.2  # 전체 트래픽의 20%
    min_daily_sessions: int = 100
    min_inventory: int = 10
    cool_down_days: int = 7
    experiment_duration_days: int = 14
    check_interval_hours: int = 24

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
            variant_id=f"{product_info.product_id}_{variant_type.value}",
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
            created_at=datetime.now(),
            prompt_meta={
                "layout_type": "grid",
                "cta_tone": "neutral",
                "color_palette": "light",
                "key_benefit": "standard"
            }
        )
    
    def _create_optimized_variant(self, product_info: ProductInfo, variant_type: VariantType, index: int) -> PageVariant:
        """최적화된 변형 생성 (성공 패턴 기반)"""
        
        # 카테고리별 성공 패턴 적용
        category_pattern = self.success_patterns.get(product_info.category.lower(), {})
        
        # 변형별 차별화
        if index == 1:  # 변형 B - 혜택 강조
            cta_text = "즉시 구매"
            cta_color = "#28a745"
            features = ["스펙", "리뷰"]
            layout = "hero"
        elif index == 2:  # 변형 C - 정보 강조
            cta_text = "자세히 보기"
            cta_color = "#17a2b8"
            features = ["관련상품", "Q&A"]
            layout = "carousel"
        else:  # 변형 D - 미니멀
            cta_text = "장바구니 담기"
            cta_color = "#ffc107"
            features = ["배송정보"]
            layout = "minimal"
        
        # 성공 패턴과 결합
        if category_pattern:
            layout = category_pattern.get("layout_type", layout)
            cta_text = category_pattern.get("cta_text", cta_text)
            features = category_pattern.get("features", features)
        
        return PageVariant(
            variant_id=f"{product_info.product_id}_{variant_type.value}",
            variant_type=variant_type,
            title=product_info.product_name,
            description=product_info.product_description,
            layout_type=layout,
            color_scheme=category_pattern.get("color_scheme", "light"),
            cta_text=cta_text,
            cta_color=cta_color,
            cta_position="bottom",
            additional_features=features,
            image_style="enhanced" if index == 1 else "original",
            font_style="bold" if index == 1 else "modern",
            created_at=datetime.now(),
            prompt_meta={
                "layout_type": layout,
                "cta_tone": "aggressive" if index == 1 else "neutral",
                "color_palette": category_pattern.get("color_scheme", "light"),
                "key_benefit": "feature_highlight" if index == 1 else "information_rich"
            }
        )

class AutopilotScheduler:
    """자동 생성 스케줄러"""
    
    def __init__(self, ab_test_manager: ABTestManager, config: AutopilotConfig):
        self.ab_test_manager = ab_test_manager
        self.config = config
        self.variant_generator = VariantGenerator()
        self.running = False
        
        # 상품 후보 데이터베이스 (실제로는 DB에서 관리)
        self.product_candidates: Dict[str, ProductCandidate] = {}
        
        # 프로모션 기간 글로벌 스위치
        self.promotion_mode = False
    
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
        """상품 우선순위 점수 계산"""
        score = 0.0
        
        # 트래픽 점수 (높을수록 좋음)
        traffic_score = min(candidate.daily_sessions / 1000, 1.0)
        score += traffic_score * 0.4
        
        # 재고 점수 (적당할수록 좋음)
        inventory_score = 1.0 - abs(candidate.inventory - 50) / 100
        score += max(inventory_score, 0) * 0.3
        
        # 쿨다운 점수 (오래된 실험이면 높음)
        if candidate.last_experiment_date:
            days_since_last = (datetime.now() - candidate.last_experiment_date).days
            cool_down_score = min(days_since_last / candidate.cool_down_days, 1.0)
        else:
            cool_down_score = 1.0
        score += cool_down_score * 0.3
        
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
        """상품에 대한 실험 생성"""
        try:
            # ProductInfo 생성
            product_info = ProductInfo(
                product_id=candidate.product_id,
                product_name=candidate.product_name,
                product_image=f"https://example.com/images/{candidate.product_id}.jpg",
                product_description=f"{candidate.product_name} 상품입니다.",
                price=candidate.price,
                category=candidate.category,
                daily_sessions=candidate.daily_sessions,
                inventory=candidate.inventory,
                cool_down_days=candidate.cool_down_days
            )
            
            # 변형 생성
            variants = self.variant_generator.generate_variants(product_info, 3)
            
            # 정책 필터 적용
            approved_variants = []
            for variant in variants:
                if self.ab_test_manager.apply_policy_filters(variant):
                    variant.policy_approved = True
                    approved_variants.append(variant)
            
            if len(approved_variants) < 2:
                logger.warning(f"상품 {candidate.product_id}: 정책 필터 통과 변형 부족")
                return False
            
            # 실험 계약서 생성
            experiment_brief = self.ab_test_manager.create_experiment_brief(
                objective="구매 전환율(CVR) 최대화",
                primary_metrics=["CVR"],
                secondary_metrics=["CTR", "ATC", "체류시간"],
                guardrails={"LCP": 3.5, "error_rate": 0.005, "return_rate": 0.1},
                target_categories=[candidate.category],
                target_channels=["web", "mobile"],
                target_devices=["desktop", "mobile"],
                exclude_conditions=[],
                variant_count=len(approved_variants),
                distribution_mode=DistributionMode.BANDIT if candidate.daily_sessions < 500 else DistributionMode.EQUAL,
                mde=0.1,  # 10%p
                min_sample_size=1000
            )
            
            # 테스트 생성
            test = self.ab_test_manager.create_test_with_brief(
                test_name=f"{candidate.product_name} 자동 A/B 테스트",
                product_info=product_info,
                variants=approved_variants,
                experiment_brief=experiment_brief,
                test_mode=TestMode.AUTOPILOT
            )
            
            # 테스트 시작
            success = self.ab_test_manager.start_test(test.test_id)
            
            if success:
                logger.info(f"자동 실험 생성 성공: {test.test_id} - {candidate.product_name}")
                # 마지막 실험 날짜 업데이트
                candidate.last_experiment_date = datetime.now()
                return True
            else:
                logger.error(f"자동 실험 시작 실패: {test.test_id}")
                return False
                
        except Exception as e:
            logger.error(f"자동 실험 생성 중 오류: {e}")
            return False
    
    def run_autopilot_cycle(self):
        """자동 생성 사이클 실행"""
        logger.info("자동 생성 사이클 시작")
        
        try:
            # 후보 선별
            candidates = self.select_candidates()
            
            if not candidates:
                logger.info("실험 후보 없음")
                return
            
            # 트래픽 예산 확인
            total_traffic_usage = sum(self.ab_test_manager.traffic_budget_usage.values())
            if total_traffic_usage >= self.config.max_traffic_usage:
                logger.info(f"트래픽 예산 초과: {total_traffic_usage:.2%}")
                return
            
            # 실험 생성
            created_count = 0
            for candidate in candidates:
                if self.create_experiment_for_product(candidate):
                    created_count += 1
                    
                    # 트래픽 예산 업데이트
                    self.ab_test_manager.traffic_budget_usage[candidate.product_id] = 0.05  # 5%
                    
                    if created_count >= 2:  # 한 번에 최대 2개까지만 생성
                        break
            
            logger.info(f"자동 생성 완료: {created_count}개 실험 생성")
            
        except Exception as e:
            logger.error(f"자동 생성 사이클 오류: {e}")
    
    def start_scheduler(self):
        """스케줄러 시작"""
        if self.running:
            return
        
        self.running = True
        
        # 매일 지정된 시간에 실행
        schedule.every().day.at("02:00").do(self.run_autopilot_cycle)
        
        # 매주 월요일 오전 9시에 실행
        schedule.every().monday.at("09:00").do(self.run_autopilot_cycle)
        
        logger.info("자동 생성 스케줄러 시작")
        
        # 백그라운드에서 스케줄 실행
        asyncio.create_task(self._run_scheduler())
    
    async def _run_scheduler(self):
        """스케줄러 백그라운드 실행"""
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(60)  # 1분마다 체크
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        self.running = False
        logger.info("자동 생성 스케줄러 중지")
    
    def set_promotion_mode(self, enabled: bool):
        """프로모션 모드 설정"""
        self.promotion_mode = enabled
        if enabled:
            logger.info("프로모션 모드 활성화: 자동 실험 비활성화")
        else:
            logger.info("프로모션 모드 비활성화: 자동 실험 재개")
    
    def get_autopilot_status(self) -> Dict[str, Any]:
        """자동 생성 상태 조회"""
        active_experiments = len([t for t in self.ab_test_manager.tests.values() 
                                if t.status == TestStatus.ACTIVE and t.test_mode == TestMode.AUTOPILOT])
        
        total_traffic_usage = sum(self.ab_test_manager.traffic_budget_usage.values())
        
        return {
            "enabled": self.config.enabled,
            "promotion_mode": self.promotion_mode,
            "active_autopilot_experiments": active_experiments,
            "max_concurrent_experiments": self.config.max_concurrent_experiments,
            "total_traffic_usage": total_traffic_usage,
            "max_traffic_usage": self.config.max_traffic_usage,
            "candidate_count": len(self.product_candidates),
            "next_run": schedule.next_run().isoformat() if schedule.jobs else None
        }

# 전역 인스턴스
autopilot_config = AutopilotConfig()
autopilot_scheduler = None

def initialize_autopilot(ab_test_manager: ABTestManager):
    """자동 생성기 초기화"""
    global autopilot_scheduler
    autopilot_scheduler = AutopilotScheduler(ab_test_manager, autopilot_config)
    
    # 샘플 상품 후보 추가 (실제로는 DB에서 로드)
    sample_products = [
        ProductInfo("prod_001", "갤럭시 S24", "image1.jpg", "스마트폰", 1200000, "스마트폰", daily_sessions=500, inventory=50),
        ProductInfo("prod_002", "아이폰 15", "image2.jpg", "스마트폰", 1500000, "스마트폰", daily_sessions=300, inventory=30),
        ProductInfo("prod_003", "맥북 프로", "image3.jpg", "노트북", 2500000, "컴퓨터", daily_sessions=200, inventory=20),
    ]
    
    for product in sample_products:
        autopilot_scheduler.add_product_candidate(product)
    
    # 스케줄러 시작
    autopilot_scheduler.start_scheduler()
    
    return autopilot_scheduler
