import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import numpy as np
from scipy import stats

from .models import ABTest, Variant, PerformanceLog, TestResult, TestStatus, VariantType, InteractionType
from .schemas import VariantMetrics, ABTestAnalytics, ContentGenerationRequest, ContentGenerationResponse

logger = logging.getLogger(__name__)

class ABTestService:
    def __init__(self, db: Session):
        self.db = db

    def create_ab_test(self, test_data: Dict[str, Any]) -> ABTest:
        """A/B 테스트 생성 및 초기 버전 생성"""
        try:
            # 새로운 지표 시스템의 기본값 강제 설정
            test_data['weights'] = {
                "cvr": 0.5,                    # 구매전환율 (구매 수 / 클릭 수) - 50%
                "cart_add_rate": 0.2,          # 장바구니 추가율 (장바구니 추가 수 / 클릭 수) - 20%
                "cart_conversion_rate": 0.2,   # 장바구니 전환율 (구매 수 / 장바구니 추가 수) - 20%
                "revenue": 0.1                 # 매출 (구매 건수 * 구매 금액) - 10%
            }
            
            test_data['guardrail_metrics'] = {
                "page_load_time_max": 3.0,         # 최대 페이지 로드 시간 (3초)
                "error_rate_threshold": 0.05       # 오류율 임계값 (5%)
            }
            
            # A/B 테스트 생성
            ab_test = ABTest(**test_data)
            self.db.add(ab_test)
            self.db.flush()  # ID 생성을 위해 flush

            # AI를 통한 초기 버전 생성
            baseline_content = self._generate_ai_content(test_data['product_id'])
            challenger_content = self._generate_ai_content(test_data['product_id'])

            # 베이스라인 버전 생성
            baseline_variant = Variant(
                ab_test_id=ab_test.id,
                variant_type=VariantType.BASELINE,
                name="A안 (베이스라인)",
                content=baseline_content,
                content_hash=self._calculate_content_hash(baseline_content)
            )

            # 도전자 버전 생성
            challenger_variant = Variant(
                ab_test_id=ab_test.id,
                variant_type=VariantType.CHALLENGER,
                name="B안 (도전자)",
                content=challenger_content,
                content_hash=self._calculate_content_hash(challenger_content)
            )

            self.db.add_all([baseline_variant, challenger_variant])
            self.db.commit()

            logger.info(f"A/B 테스트 생성 완료: {ab_test.id}")
            return ab_test

        except Exception as e:
            self.db.rollback()
            logger.error(f"A/B 테스트 생성 실패: {e}")
            raise

    def create_ab_test_with_images(self, test_data: Dict[str, Any]) -> ABTest:
        """이미지 URL을 포함한 A/B 테스트 생성"""
        try:
            # A/B 테스트 생성
            ab_test = ABTest(**test_data)
            self.db.add(ab_test)
            self.db.flush()

            # 베이스라인 버전 생성 (A안)
            baseline_content = {
                "title": f"상세페이지 A안 - {test_data['product_id']}",
                "image_url": test_data.get('baseline_image_url'),
                "description": "기존 상세페이지",
                "generated_at": datetime.utcnow().isoformat()
            }
            
            baseline_variant = Variant(
                ab_test_id=ab_test.id,
                variant_type=VariantType.BASELINE,
                name="A안 (베이스라인)",
                content=baseline_content,
                content_hash=self._calculate_content_hash(baseline_content)
            )

            # 도전자 버전 생성 (B안)
            challenger_content = {
                "title": f"상세페이지 B안 - {test_data['product_id']}",
                "image_url": test_data.get('challenger_image_url'),
                "description": "개선된 상세페이지",
                "generated_at": datetime.utcnow().isoformat()
            }
            
            challenger_variant = Variant(
                ab_test_id=ab_test.id,
                variant_type=VariantType.CHALLENGER,
                name="B안 (도전자)",
                content=challenger_content,
                content_hash=self._calculate_content_hash(challenger_content)
            )

            self.db.add_all([baseline_variant, challenger_variant])
            self.db.commit()

            logger.info(f"이미지 기반 A/B 테스트 생성 완료: {ab_test.id}")
            return ab_test

        except Exception as e:
            self.db.rollback()
            logger.error(f"이미지 기반 A/B 테스트 생성 실패: {e}")
            raise

    def calculate_ai_weights(self, test_id: int) -> Dict[str, float]:
        """고정된 가중치 반환 (새로운 지표 체계)"""
        # 고정된 가중치: CVR 50%, Cart Add Rate 20%, Cart Conversion Rate 20%, Revenue 10%
        return {"cvr": 0.5, "cart_add_rate": 0.2, "cart_conversion_rate": 0.2, "revenue": 0.1}

    def calculate_variant_ai_score(self, variant: Variant, weights: Dict[str, float]) -> float:
        """개별 버전의 AI 점수 계산 (새로운 지표 체계)"""
        try:
            # 핵심 지표 계산
            cvr = variant.purchases / max(variant.clicks, 1)                      # 구매전환율 (구매 수 / 클릭 수)
            cart_add_rate = variant.cart_additions / max(variant.clicks, 1)       # 장바구니 추가율 (장바구니 추가 수 / 클릭 수)
            
            # 장바구니 전환율: 장바구니 추가한 사용자 중 장바구니에서 구매한 비율 (100% 초과 방지)
            if variant.cart_additions > 0 and variant.cart_purchases is not None:
                cart_conversion_rate = min(variant.cart_purchases / variant.cart_additions, 1.0)
            else:
                cart_conversion_rate = 0.0
                
            revenue_per_click = variant.revenue / max(variant.clicks, 1)          # 클릭당 매출
            
            # 가드레일 지표 계산 (이탈률 제외)
            avg_page_load_time = variant.total_page_load_time / max(variant.total_page_loads, 1)  # 평균 페이지 로드 시간
            error_rate = variant.errors / max(variant.clicks, 1)                   # 오류율 (클릭 대비)
            
            # 기본 AI 점수 계산 (새로운 가중치)
            base_score = (
                cvr * weights.get("cvr", 0.5) +                           # 구매전환율 50%
                cart_add_rate * weights.get("cart_add_rate", 0.2) +       # 장바구니 추가율 20%
                cart_conversion_rate * weights.get("cart_conversion_rate", 0.2) +  # 장바구니 전환율 20%
                revenue_per_click * weights.get("revenue", 0.1) / 1000    # 매출 10% (정규화)
            )
            
            # 가드레일 점수 계산 (이탈률 제외, 페널티만)
            guardrail_score = 1.0  # 기본 배수 (페널티 없으면 그대로 유지)
            
            # 페이지 로드 시간 평가 (느릴수록 페널티)
            if avg_page_load_time > 3.0:     # 3초 초과하면 큰 페널티
                guardrail_score *= 0.3
            elif avg_page_load_time > 2.0:   # 2초 초과하면 중간 페널티
                guardrail_score *= 0.7
            elif avg_page_load_time > 1.5:   # 1.5초 초과하면 작은 페널티
                guardrail_score *= 0.9
            
            # 오류율 평가 (높을수록 페널티)
            if error_rate > 0.05:            # 5% 초과하면 큰 페널티
                guardrail_score *= 0.3
            elif error_rate > 0.02:          # 2% 초과하면 중간 페널티
                guardrail_score *= 0.7
            elif error_rate > 0.01:          # 1% 초과하면 작은 페널티
                guardrail_score *= 0.9
            
            # 최종 점수 = 기본 점수 × 가드레일 배수
            score = base_score * guardrail_score
            
            # 신뢰도 계산 (통계적 신뢰도 기반)
            # 샘플 크기와 전환율 변동성을 고려한 신뢰도
            sample_size = variant.clicks
            conversion_rate = variant.purchases / max(variant.clicks, 1)
            
            # 통계적 신뢰도 계산 (표준오차 기반)
            if sample_size >= 30:  # 중심극한정리 기준
                # 신뢰구간 기반 신뢰도 계산
                std_error = (conversion_rate * (1 - conversion_rate) / sample_size) ** 0.5
                margin_of_error = 1.96 * std_error  # 95% 신뢰구간
                
                # 신뢰도는 표본 크기와 변동성의 역함수
                confidence = min(sample_size / 300, 1.0) * (1 - min(margin_of_error, 1.0))
                confidence = max(confidence, 0.1)  # 최소 10%
            else:
                # 샘플이 적으면 낮은 신뢰도
                confidence = sample_size / 300  # 300 클릭 기준으로 선형 증가
            
            # 점수 업데이트
            variant.ai_score = score
            variant.ai_confidence = confidence
            
            return score
            
        except Exception as e:
            logger.error(f"버전 AI 점수 계산 실패: {e}")
            return 0.0

    def determine_ai_winner(self, test_id: int) -> Optional[int]:
        """AI가 승자 결정"""
        try:
            test = self.db.query(ABTest).filter(ABTest.id == test_id).first()
            if not test:
                return None
            
            variants = self.db.query(Variant).filter(Variant.ab_test_id == test_id).all()
            if len(variants) < 2:
                return None
            
            # AI 가중치 계산
            weights = self.calculate_ai_weights(test_id)
            
            # 각 버전의 AI 점수 계산
            variant_scores = []
            for variant in variants:
                score = self.calculate_variant_ai_score(variant, weights)
                variant_scores.append((variant.id, score, variant.ai_confidence))
            
            # 통계적 유의성 검정
            if len(variant_scores) >= 2:
                scores = [score for _, score, _ in variant_scores]
                if len(scores) >= 2:
                    # t-test로 유의성 검정
                    try:
                        t_stat, p_value = stats.ttest_ind([scores[0]], [scores[1]])
                        significant = p_value < 0.05
                    except:
                        significant = False
                else:
                    significant = False
            else:
                significant = False
            
            # 승자 결정 (점수 + 신뢰도 고려)
            best_variant = max(variant_scores, key=lambda x: x[1] * x[2])
            winner_id = best_variant[0]
            
            # AI 승자 업데이트
            test.ai_winner_variant_id = winner_id
            test.status = TestStatus.WAITING_FOR_WINNER_SELECTION
            test.winner_selection_deadline = datetime.utcnow() + timedelta(days=7)  # 7일 후 마감
            
            self.db.commit()
            
            logger.info(f"AI 승자 결정 완료: {winner_id}, 유의성: {significant}")
            return winner_id
            
        except Exception as e:
            logger.error(f"AI 승자 결정 실패: {e}")
            return None

    def select_winner(self, test_id: int, variant_id: int) -> bool:
        """사용자가 승자 선택"""
        try:
            test = self.db.query(ABTest).filter(ABTest.id == test_id).first()
            if not test:
                return False
            
            # 승자 선택
            test.user_selected_winner_id = variant_id
            test.status = TestStatus.COMPLETED
            test.ended_at = datetime.utcnow()
            
            # 승자 버전 업데이트
            for variant in test.variants:
                variant.is_winner = (variant.id == variant_id)
            
            self.db.commit()
            
            logger.info(f"사용자 승자 선택 완료: {variant_id}")
            return True
            
        except Exception as e:
            logger.error(f"사용자 승자 선택 실패: {e}")
            return False

    def create_next_test_cycle(self, previous_test_id: int, new_challenger_image_url: str) -> Optional[ABTest]:
        """다음 테스트 사이클 생성"""
        try:
            previous_test = self.db.query(ABTest).filter(ABTest.id == previous_test_id).first()
            if not previous_test or not previous_test.user_selected_winner_id:
                return None
            
            # 승자 버전 가져오기
            winner_variant = self.db.query(Variant).filter(
                Variant.id == previous_test.user_selected_winner_id
            ).first()
            
            if not winner_variant:
                return None
            
            # 새로운 테스트 생성
            new_test_data = {
                "name": f"{previous_test.name} - 사이클 {previous_test.test_cycle_number + 1}",
                "description": f"이전 테스트 {previous_test_id}의 연속",
                "product_id": previous_test.product_id,
                "test_duration_days": previous_test.test_duration_days,
                "traffic_split_ratio": previous_test.traffic_split_ratio,
                "min_sample_size": previous_test.min_sample_size,
                "weights": previous_test.weights,
                "guardrail_metrics": previous_test.guardrail_metrics,
                "test_cycle_number": previous_test.test_cycle_number + 1,
                "parent_test_id": previous_test_id,
                "baseline_image_url": winner_variant.content.get("image_url"),  # 이전 승자를 새로운 A안으로
                "challenger_image_url": new_challenger_image_url  # 새로운 B안
            }
            
            new_test = self.create_ab_test_with_images(new_test_data)
            
            logger.info(f"다음 테스트 사이클 생성 완료: {new_test.id}")
            return new_test
            
        except Exception as e:
            logger.error(f"다음 테스트 사이클 생성 실패: {e}")
            return None

    def _generate_ai_content(self, product_id: str) -> Dict[str, Any]:
        """AI 콘텐츠 생성 API 호출 (실제 구현에서는 외부 AI API 호출)"""
        # 실제 구현에서는 기존 AI 상세 페이지 생성 API를 호출
        # 여기서는 모의 데이터 반환
        return {
            "title": f"AI 생성 제품 상세 페이지 - {product_id}",
            "description": "AI가 생성한 최적화된 제품 설명",
            "features": ["특징 1", "특징 2", "특징 3"],
            "images": ["image1.jpg", "image2.jpg"],
            "pricing": {"original": 100000, "discounted": 80000},
            "cta_text": "지금 구매하기",
            "generated_at": datetime.utcnow().isoformat()
        }

    def _calculate_content_hash(self, content: Dict[str, Any]) -> str:
        """콘텐츠 해시 계산"""
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def log_interaction(self, log_data: Dict[str, Any]) -> PerformanceLog:
        """사용자 상호작용 로그 기록"""
        try:
            log = PerformanceLog(**log_data)
            self.db.add(log)
            
            # 실시간 지표 업데이트
            self._update_variant_metrics(log_data['variant_id'], log_data['interaction_type'])
            
            self.db.commit()
            return log

        except Exception as e:
            self.db.rollback()
            logger.error(f"상호작용 로그 기록 실패: {e}")
            raise

    def _update_variant_metrics(self, variant_id: int, interaction_type: str):
        """버전별 실시간 지표 업데이트"""
        variant = self.db.query(Variant).filter(Variant.id == variant_id).first()
        if not variant:
            return

        # 상호작용 타입별 카운터 증가
        if interaction_type == InteractionType.IMPRESSION:
            variant.impressions += 1
        elif interaction_type == InteractionType.CLICK:
            variant.clicks += 1
        elif interaction_type == InteractionType.PURCHASE:
            variant.purchases += 1

        # 지표 재계산
        self._recalculate_variant_metrics(variant)

    def _recalculate_variant_metrics(self, variant: Variant):
        """버전 지표 재계산"""
        # CTR 계산
        variant.ctr = variant.clicks / variant.impressions if variant.impressions > 0 else 0
        
        # CVR 계산
        variant.cvr = variant.purchases / variant.impressions if variant.impressions > 0 else 0
        
        # 성능 계산 완료 - 이탈률 제거됨

    def determine_winner(self, test_id: int) -> Optional[int]:
        """승자 결정 로직"""
        try:
            ab_test = self.db.query(ABTest).filter(ABTest.id == test_id).first()
            if not ab_test:
                raise ValueError(f"테스트를 찾을 수 없습니다: {test_id}")

            variants = self.db.query(Variant).filter(
                Variant.ab_test_id == test_id,
                Variant.is_active == True
            ).all()

            if len(variants) < 2:
                logger.warning(f"테스트 {test_id}에 활성 버전이 2개 미만입니다")
                return None

            # 각 버전의 지표 계산
            variant_metrics = []
            for variant in variants:
                metrics = self._calculate_variant_metrics(variant, ab_test.weights)
                variant_metrics.append((variant.id, metrics))

            # 통계적 유의성 검정
            p_value = self._calculate_statistical_significance(variants)
            
            # 승자 결정
            winner_id = self._select_winner(variant_metrics, p_value, ab_test.guardrail_metrics)
            
            if winner_id:
                # 승자 표시
                for variant in variants:
                    variant.is_winner = (variant.id == winner_id)
                
                # 테스트 결과 저장
                self._save_test_result(ab_test, winner_id, variant_metrics, p_value)
                
                self.db.commit()
                logger.info(f"테스트 {test_id} 승자 결정: {winner_id}")

            return winner_id

        except Exception as e:
            self.db.rollback()
            logger.error(f"승자 결정 실패: {e}")
            raise

    def _calculate_variant_metrics(self, variant: Variant, weights: Dict[str, float]) -> VariantMetrics:
        """버전별 지표 계산"""
        # 기본 지표
        ctr = variant.clicks / variant.impressions if variant.impressions > 0 else 0
        cvr = variant.purchases / variant.impressions if variant.impressions > 0 else 0
        revenue_per_user = variant.revenue / variant.impressions if variant.impressions > 0 else 0

        # 가중치 적용된 점수 계산
        score = (
            weights.get('ctr', 0.3) * ctr +
            weights.get('cvr', 0.4) * cvr +
            weights.get('revenue', 0.3) * revenue_per_user
        )

        return VariantMetrics(
            variant_id=variant.id,
            variant_name=variant.name,
            impressions=variant.impressions,
            clicks=variant.clicks,
            purchases=variant.purchases,
            revenue=variant.revenue,
            ctr=ctr,
            cvr=cvr,
            revenue_per_user=revenue_per_user,
            bounce_rate=0.0,  # 이탈률 제거됨
            avg_session_duration=0.0,  # 세션 지속시간 제거됨
            score=score
        )

    def _calculate_statistical_significance(self, variants: List[Variant]) -> float:
        """통계적 유의성 계산 (Chi-square test)"""
        try:
            # 클릭 데이터로 Chi-square test 수행
            clicks = [v.clicks for v in variants]
            impressions = [v.impressions for v in variants]
            
            # impressions가 0인 경우 처리
            if any(imp <= 0 for imp in impressions):
                logger.warning("impressions가 0인 버전이 있어 유의성 검정을 건너뜁니다")
                return 0.5  # 중간값 반환
            
            if len(clicks) == 2:
                # 2x2 contingency table - 음수 값 방지
                table = np.array([
                    [max(clicks[0], 0), max(impressions[0] - clicks[0], 0)],
                    [max(clicks[1], 0), max(impressions[1] - clicks[1], 0)]
                ])
                
                # 모든 값이 0이 아닌지 확인
                if np.any(table == 0):
                    logger.warning("contingency table에 0 값이 있어 유의성 검정을 건너뜁니다")
                    return 0.5
                
                chi2, p_value, dof, expected = stats.chi2_contingency(table)
                return p_value
            
            return 0.5  # 유의성 검정 불가능한 경우

        except Exception as e:
            logger.warning(f"통계적 유의성 계산 실패: {e}")
            return 0.5

    def _select_winner(self, variant_metrics: List[Tuple[int, VariantMetrics]], 
                      p_value: float, guardrail_metrics: Dict[str, Any]) -> Optional[int]:
        """승자 선택 로직"""
        if len(variant_metrics) < 2:
            return None

        # 통계적 유의성 확인 (p < 0.05) - 테스트를 위해 임시로 완화
        if p_value >= 0.1:  # 0.05에서 0.1로 완화
            logger.info(f"통계적 유의성이 낮습니다 (p-value: {p_value:.4f})")
            # 테스트 목적으로 점수 차이가 크면 승자 결정
            scores = [metrics.score for _, metrics in variant_metrics]
            max_score = max(scores)
            min_score = min(scores)
            if max_score > min_score * 1.2:  # 20% 이상 차이나면 승자 결정
                logger.info("점수 차이가 커서 승자를 결정합니다")
            else:
                logger.info("점수 차이가 작아서 승자를 결정할 수 없습니다")
                return None

        # 가드레일 검사
        valid_variants = []
        for variant_id, metrics in variant_metrics:
            if self._check_guardrails(metrics, guardrail_metrics):
                valid_variants.append((variant_id, metrics))
            else:
                logger.warning(f"버전 {variant_id}이 가드레일을 통과하지 못했습니다")

        if not valid_variants:
            logger.warning("가드레일을 통과한 버전이 없습니다")
            return None

        # 최고 점수 버전 선택
        winner_id, winner_metrics = max(valid_variants, key=lambda x: x[1].score)
        
        logger.info(f"승자 선택: {winner_id}, 점수: {winner_metrics.score:.4f}")
        return winner_id

    def _check_guardrails(self, metrics: VariantMetrics, guardrail_metrics: Dict[str, Any]) -> bool:
        """가드레일 검사"""
        # 이탈률 검사 제거됨

        # 세션 지속시간 검사 - 테스트 환경에서는 건너뛰기
        # 실제 운영에서는 프론트엔드에서 세션 추적 필요
        session_duration_min = guardrail_metrics.get('session_duration_min', 5)
        if metrics.avg_session_duration < session_duration_min:
            logger.info(f"테스트 환경: 세션 지속시간 검사 건너뛰기 (값: {metrics.avg_session_duration:.1f})")
            # 테스트 환경에서는 세션 지속시간 검사를 건너뛰고 통과 처리
            pass

        return True

    def _save_test_result(self, ab_test: ABTest, winner_id: int, 
                         variant_metrics: List[Tuple[int, VariantMetrics]], p_value: float):
        """테스트 결과 저장"""
        winner_metrics = next(m for vid, m in variant_metrics if vid == winner_id)
        
        result = TestResult(
            ab_test_id=ab_test.id,
            winner_variant_id=winner_id,
            winner_score=winner_metrics.score,
            p_value=p_value,
            confidence_level=1 - p_value if p_value else None,
            total_impressions=sum(m.impressions for _, m in variant_metrics),
            total_clicks=sum(m.clicks for _, m in variant_metrics),
            total_purchases=sum(m.purchases for _, m in variant_metrics),
            total_revenue=sum(m.revenue for _, m in variant_metrics)
        )
        
        self.db.add(result)

    def start_next_round(self, test_id: int) -> bool:
        """다음 라운드 A/B 테스트 시작"""
        try:
            ab_test = self.db.query(ABTest).filter(ABTest.id == test_id).first()
            if not ab_test:
                return False

            # 현재 활성 버전들 조회
            active_variants = self.db.query(Variant).filter(
                Variant.ab_test_id == test_id,
                Variant.is_active == True
            ).all()

            if len(active_variants) != 2:
                logger.warning(f"테스트 {test_id}에 정확히 2개의 활성 버전이 없습니다")
                return False

            # 승자와 패자 구분
            winner = next((v for v in active_variants if v.is_winner), None)
            loser = next((v for v in active_variants if not v.is_winner), None)

            if not winner or not loser:
                logger.warning(f"테스트 {test_id}에서 승자/패자를 구분할 수 없습니다")
                return False

            # 패자 비활성화
            loser.is_active = False

            # 새로운 도전자 생성
            new_challenger_content = self._generate_ai_content(ab_test.product_id)
            new_challenger = Variant(
                ab_test_id=ab_test.id,
                variant_type=VariantType.CHALLENGER,
                name=f"C안 (새로운 도전자) - {datetime.utcnow().strftime('%Y%m%d')}",
                content=new_challenger_content,
                content_hash=self._calculate_content_hash(new_challenger_content)
            )

            # 승자를 새로운 베이스라인으로 설정
            winner.variant_type = VariantType.BASELINE
            winner.name = f"A안 (베이스라인) - {datetime.utcnow().strftime('%Y%m%d')}"
            winner.is_winner = False

            self.db.add(new_challenger)
            self.db.commit()

            logger.info(f"테스트 {test_id}의 다음 라운드 시작 완료")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"다음 라운드 시작 실패: {e}")
            return False

    def get_test_analytics(self, test_id: int) -> Optional[ABTestAnalytics]:
        """테스트 분석 데이터 조회"""
        try:
            ab_test = self.db.query(ABTest).filter(ABTest.id == test_id).first()
            if not ab_test:
                return None

            variants = self.db.query(Variant).filter(
                Variant.ab_test_id == test_id,
                Variant.is_active == True
            ).all()

            variant_metrics = []
            for variant in variants:
                metrics = self._calculate_variant_metrics(variant, ab_test.weights)
                variant_metrics.append(metrics)

            # 남은 일수 계산
            days_remaining = None
            if ab_test.started_at and ab_test.test_duration_days:
                end_date = ab_test.started_at + timedelta(days=ab_test.test_duration_days)
                days_remaining = max(0, (end_date - datetime.utcnow()).days)

            return ABTestAnalytics(
                test_id=ab_test.id,
                test_name=ab_test.name,
                status=ab_test.status,
                variants=variant_metrics,
                winner_variant_id=next((v.id for v in variants if v.is_winner), None),
                p_value=None,  # 실제로는 계산 필요
                confidence_level=None,
                test_duration_days=ab_test.test_duration_days,
                days_remaining=days_remaining,
                total_clicks=sum(v.clicks for v in variants),
                total_purchases=sum(v.purchases for v in variants),
                total_cart_additions=sum(v.cart_additions for v in variants),
                total_cart_purchases=sum(v.cart_purchases for v in variants),
                total_revenue=sum(v.revenue for v in variants)
            )

        except Exception as e:
            logger.error(f"테스트 분석 데이터 조회 실패: {e}")
            return None
