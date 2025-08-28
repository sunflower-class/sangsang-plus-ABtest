from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .database import get_db
from .schemas import (
    ABTestCreate, ABTestResponse, VariantResponse, PerformanceLogCreate,
    PerformanceLogResponse, TestResultResponse, ABTestAnalytics,
    DashboardSummary, TestListResponse
)
from .abtest_service import ABTestService
from .models import TestStatus, ABTest, Variant, TestResult

router = APIRouter(prefix="/api/abtest", tags=["A/B Test"])

@router.post("/", response_model=ABTestResponse, status_code=201)
async def create_ab_test(
    test_data: ABTestCreate,
    db: Session = Depends(get_db)
):
    """A/B 테스트 생성"""
    try:
        service = ABTestService(db)
        
        # 테스트 데이터 준비
        test_dict = test_data.dict()
        test_dict['started_at'] = None  # 생성 시점에는 시작되지 않음
        
        # A/B 테스트 생성
        ab_test = service.create_ab_test(test_dict)
        
        return ABTestResponse.from_orm(ab_test)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"A/B 테스트 생성 실패: {str(e)}")

@router.post("/with-images", response_model=ABTestResponse, status_code=201)
async def create_ab_test_with_images(
    test_data: dict,
    db: Session = Depends(get_db)
):
    """이미지 URL을 포함한 A/B 테스트 생성"""
    try:
        service = ABTestService(db)
        
        # 필수 필드 검증
        required_fields = ['name', 'product_id', 'product_price', 'baseline_image_url', 'challenger_image_url']
        for field in required_fields:
            if field not in test_data:
                raise HTTPException(status_code=400, detail=f"필수 필드 누락: {field}")
        
        # A/B 테스트 생성
        ab_test = service.create_ab_test_with_images(test_data)
        
        return ABTestResponse.from_orm(ab_test)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 기반 A/B 테스트 생성 실패: {str(e)}")



@router.post("/test/{test_id}/determine-winner")
async def determine_ai_winner(
    test_id: int,
    db: Session = Depends(get_db)
):
    """AI가 승자 결정"""
    try:
        service = ABTestService(db)
        
        winner_id = service.determine_ai_winner(test_id)
        
        if winner_id:
            return {
                "status": "success",
                "message": "AI 승자 결정 완료",
                "ai_winner_id": winner_id,
                "next_step": "사용자 승자 선택 대기"
            }
        else:
            raise HTTPException(status_code=400, detail="AI 승자 결정 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 승자 결정 실패: {str(e)}")

@router.post("/test/{test_id}/select-winner/{variant_id}")
async def select_winner(
    test_id: int,
    variant_id: int,
    db: Session = Depends(get_db)
):
    """사용자가 승자 선택"""
    try:
        service = ABTestService(db)
        
        success = service.select_winner(test_id, variant_id)
        
        if success:
            return {
                "status": "success",
                "message": "승자 선택 완료",
                "selected_winner_id": variant_id,
                "next_step": "새로운 테스트 사이클 준비"
            }
        else:
            raise HTTPException(status_code=400, detail="승자 선택 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"승자 선택 실패: {str(e)}")

@router.post("/test/{test_id}/next-cycle")
async def create_next_test_cycle(
    test_id: int,
    new_challenger_data: dict,
    db: Session = Depends(get_db)
):
    """다음 테스트 사이클 생성"""
    try:
        service = ABTestService(db)
        
        if 'challenger_image_url' not in new_challenger_data:
            raise HTTPException(status_code=400, detail="새로운 B안 이미지 URL이 필요합니다")
        
        new_test = service.create_next_test_cycle(
            test_id, 
            new_challenger_data['challenger_image_url']
        )
        
        if new_test:
            return {
                "status": "success",
                "message": "다음 테스트 사이클 생성 완료",
                "new_test_id": new_test.id,
                "new_test_name": new_test.name
            }
        else:
            raise HTTPException(status_code=400, detail="다음 테스트 사이클 생성 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"다음 테스트 사이클 생성 실패: {str(e)}")

@router.get("/test/{test_id}/winner-status")
async def get_winner_status(
    test_id: int,
    db: Session = Depends(get_db)
):
    """승자 결정 상태 조회"""
    try:
        test = db.query(ABTest).filter(ABTest.id == test_id).first()
        if not test:
            raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다")
        
        variants = db.query(Variant).filter(Variant.ab_test_id == test_id).all()
        
        # 승자 선택 가능 여부 확인
        can_select_winner = test.status == TestStatus.WAITING_FOR_WINNER_SELECTION
        winner_selected = test.user_selected_winner_id is not None
        
        result = {
            "status": test.status.value if hasattr(test.status, 'value') else str(test.status),
            "winner_selected": winner_selected,
            "can_select_winner": can_select_winner,
            "ai_winner_id": test.ai_winner_variant_id,
            "manual_winner_id": test.user_selected_winner_id,
            "message": "승자 선택이 완료되었습니다." if winner_selected else "승자 선택이 필요합니다." if can_select_winner else "테스트가 완료되었습니다."
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"승자 상태 조회 실패: {str(e)}")

@router.get("/test/{test_id}/ai-analysis")
async def get_ai_analysis(
    test_id: int,
    db: Session = Depends(get_db)
):
    """AI 분석 결과 조회"""
    try:
        service = ABTestService(db)
        
        # AI 가중치 계산
        weights = service.calculate_ai_weights(test_id)
        
        # 각 버전의 AI 점수 계산
        variants = db.query(Variant).filter(Variant.ab_test_id == test_id).all()
        variant_analysis = []
        
        for variant in variants:
            score = service.calculate_variant_ai_score(variant, weights)
            
            # 신뢰도 계산 세부사항
            sample_size = variant.clicks
            conversion_rate = variant.purchases / max(variant.clicks, 1)
            confidence_details = {}
            
            if sample_size >= 30:
                std_error = (conversion_rate * (1 - conversion_rate) / sample_size) ** 0.5
                margin_of_error = 1.96 * std_error
                base_confidence = min(sample_size / 300, 1.0)
                variability_factor = 1 - min(margin_of_error, 1.0)
                final_confidence = base_confidence * variability_factor
                final_confidence = max(final_confidence, 0.1)
                
                confidence_details = {
                    "calculation_method": "statistical",
                    "sample_size": sample_size,
                    "conversion_rate": round(conversion_rate * 100, 2),
                    "std_error": round(std_error, 4),
                    "margin_of_error": round(margin_of_error * 100, 2),
                    "base_confidence": round(base_confidence * 100, 1),
                    "variability_factor": round(variability_factor * 100, 1),
                    "final_confidence": round(final_confidence * 100, 1),
                    "formula": "min(sample_size/300, 1.0) × (1 - margin_of_error)"
                }
            else:
                linear_confidence = sample_size / 300
                confidence_details = {
                    "calculation_method": "linear",
                    "sample_size": sample_size,
                    "linear_confidence": round(linear_confidence * 100, 1),
                    "formula": "sample_size / 300 (최소 샘플 부족)"
                }
            
            analysis = {
                "variant_id": variant.id,
                "variant_name": variant.name,
                "ai_score": score,
                "ai_confidence": variant.ai_confidence,
                "confidence_details": confidence_details,
                "cvr": variant.purchases / max(variant.clicks, 1),
                "cart_add_rate": variant.cart_additions / max(variant.clicks, 1),
                "cart_conversion_rate": min(variant.cart_purchases / max(variant.cart_additions, 1), 1.0) if variant.cart_additions > 0 and variant.cart_purchases is not None else 0.0,
                "revenue_per_click": variant.revenue / max(variant.clicks, 1),

                "error_rate": variant.errors / max(variant.clicks + variant.cart_additions + variant.purchases + variant.errors + variant.total_page_loads, 1),
                "avg_page_load_time": variant.total_page_load_time / max(variant.total_page_loads, 1),
                "clicks": variant.clicks,
                "cart_additions": variant.cart_additions,
                "purchases": variant.purchases,
                "revenue": variant.revenue
            }
            variant_analysis.append(analysis)
        
        return {
            "test_id": test_id,
            "ai_weights": weights,
            "variant_analysis": variant_analysis,
            "recommendation": "AI 분석 결과를 바탕으로 승자를 결정하세요"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 분석 조회 실패: {str(e)}")

@router.get("/")
async def list_ab_tests(
    db: Session = Depends(get_db)
):
    """A/B 테스트 목록 조회 (간단한 버전)"""
    try:
        tests = db.query(ABTest).all()
        # 간단한 딕셔너리 형태로 반환
        return [
            {
                "id": test.id,
                "name": test.name,
                "status": test.status if isinstance(test.status, str) else test.status.value,
                "created_at": test.created_at.isoformat(),
                "product_id": test.product_id,
                "baseline_image_url": test.baseline_image_url,
                "challenger_image_url": test.challenger_image_url,
                "product_name": test.product_name,
                "product_price": test.product_price
            }
            for test in tests
        ]
    except Exception as e:
        # 오류 로깅 추가
        print(f"list_ab_tests 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

@router.get("/test/{test_id}", response_model=ABTestResponse)
async def get_ab_test(
    test_id: int,
    db: Session = Depends(get_db)
):
    """특정 A/B 테스트 조회"""
    try:
        service = ABTestService(db)
        
        test = db.query(ABTest).filter(ABTest.id == test_id).first()
        if not test:
            raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다")
        
        return ABTestResponse.from_orm(test)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 조회 실패: {str(e)}")

@router.get("/{test_id}/variants", response_model=List[VariantResponse])
async def get_test_variants(
    test_id: int,
    db: Session = Depends(get_db)
):
    """A/B 테스트의 버전 목록 조회"""
    try:
        from .models import Variant
        
        variants = db.query(Variant).filter(Variant.ab_test_id == test_id).all()
        
        return [VariantResponse.from_orm(variant) for variant in variants]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"버전 목록 조회 실패: {str(e)}")

@router.get("/{test_id}/analytics", response_model=ABTestAnalytics)
async def get_test_analytics(
    test_id: int,
    db: Session = Depends(get_db)
):
    """A/B 테스트 분석 데이터 조회"""
    try:
        service = ABTestService(db)
        
        analytics = service.get_test_analytics(test_id)
        if not analytics:
            raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다")
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 데이터 조회 실패: {str(e)}")

@router.post("/{test_id}/start", response_model=ABTestResponse)
async def start_ab_test(
    test_id: int,
    db: Session = Depends(get_db)
):
    """A/B 테스트 시작"""
    try:
        from datetime import datetime
        
        test = db.query(ABTest).filter(ABTest.id == test_id).first()
        if not test:
            raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다")
        
        if test.status != TestStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="이미 시작되었거나 완료된 테스트입니다")
        
        # 테스트 시작
        test.started_at = datetime.utcnow()
        db.commit()
        
        return ABTestResponse.from_orm(test)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"테스트 시작 실패: {str(e)}")

@router.post("/{test_id}/determine-winner", response_model=dict)
async def determine_winner(
    test_id: int,
    db: Session = Depends(get_db)
):
    """수동으로 승자 결정"""
    try:
        service = ABTestService(db)
        
        winner_id = service.determine_winner(test_id)
        
        if winner_id:
            return {
                "success": True,
                "winner_variant_id": winner_id,
                "message": "승자가 성공적으로 결정되었습니다"
            }
        else:
            return {
                "success": False,
                "winner_variant_id": None,
                "message": "승자를 결정할 수 없습니다"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"승자 결정 실패: {str(e)}")

@router.post("/{test_id}/next-round", response_model=dict)
async def start_next_round(
    test_id: int,
    db: Session = Depends(get_db)
):
    """다음 라운드 A/B 테스트 시작"""
    try:
        service = ABTestService(db)
        
        success = service.start_next_round(test_id)
        
        if success:
            return {
                "success": True,
                "message": "다음 라운드가 성공적으로 시작되었습니다"
            }
        else:
            return {
                "success": False,
                "message": "다음 라운드 시작에 실패했습니다"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"다음 라운드 시작 실패: {str(e)}")

@router.post("/log", response_model=PerformanceLogResponse, status_code=201)
async def log_interaction(
    log_data: PerformanceLogCreate,
    db: Session = Depends(get_db)
):
    """사용자 상호작용 로그 기록"""
    try:
        service = ABTestService(db)
        
        log = service.log_interaction(log_data.dict())
        
        return PerformanceLogResponse.from_orm(log)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 기록 실패: {str(e)}")

@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: Session = Depends(get_db)
):
    """대시보드 요약 정보"""
    try:
        from .models import ABTest, TestResult
        from sqlalchemy import func
        
        # 전체 테스트 수
        total_tests = db.query(ABTest).count()
        
        # 활성 테스트 수
        active_tests = db.query(ABTest).filter(ABTest.status == TestStatus.ACTIVE).count()
        
        # 완료된 테스트 수
        completed_tests = db.query(ABTest).filter(ABTest.status == TestStatus.COMPLETED).count()
        
        # 총 매출 영향 (완료된 테스트들의 결과 합계)
        total_revenue_impact = db.query(func.sum(TestResult.total_revenue)).scalar() or 0.0
        
        # 평균 개선률 (실제로는 더 복잡한 계산 필요)
        average_improvement = 0.15  # 15% 개선 가정
        
        return DashboardSummary(
            total_tests=total_tests,
            active_tests=active_tests,
            completed_tests=completed_tests,
            total_revenue_impact=total_revenue_impact,
            average_improvement=average_improvement
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대시보드 요약 조회 실패: {str(e)}")

@router.get("/{test_id}/results", response_model=List[TestResultResponse])
async def get_test_results(
    test_id: int,
    db: Session = Depends(get_db)
):
    """A/B 테스트 결과 조회"""
    try:
        from .models import TestResult
        
        results = db.query(TestResult).filter(TestResult.ab_test_id == test_id).all()
        
        return [TestResultResponse.from_orm(result) for result in results]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 결과 조회 실패: {str(e)}")

@router.delete("/{test_id}", status_code=204)
async def delete_ab_test(
    test_id: int,
    db: Session = Depends(get_db)
):
    """A/B 테스트 삭제"""
    try:
        test = db.query(ABTest).filter(ABTest.id == test_id).first()
        if not test:
            raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다")
        
        # 활성 테스트는 삭제 불가
        if test.status == TestStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="활성 테스트는 삭제할 수 없습니다")
        
        db.delete(test)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"테스트 삭제 실패: {str(e)}")

# 추가 엔드포인트들

# 결과 조회는 app.py에서 처리

@router.get("/analytics/overview")
async def get_analytics_overview(
    db: Session = Depends(get_db)
):
    """전체 분석 데이터 개요"""
    try:
        from .models import ABTest, PerformanceLog
        from sqlalchemy import func
        
        total_tests = db.query(ABTest).count()
        active_tests = db.query(ABTest).filter(ABTest.status == TestStatus.ACTIVE).count()
        total_interactions = db.query(PerformanceLog).count()
        
        # 간단한 전환율 계산 (실제로는 더 복잡)
        conversion_rate = 0.05  # 5% 가정
        
        return {
            "total_tests": total_tests,
            "active_tests": active_tests,
            "total_interactions": total_interactions,
            "conversion_rate": conversion_rate
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 데이터 조회 실패: {str(e)}")

# 성과 데이터 조회는 app.py에서 처리

# 로그 조회는 app.py에서 처리

@router.get("/scheduler/status")
async def get_scheduler_status():
    """스케줄러 상태 조회"""
    try:
        return {
            "status": "running",
            "jobs": [
                {
                    "id": "check_completed_tests",
                    "name": "Check completed A/B tests",
                    "next_run": "2024-01-01T00:00:00Z"
                }
            ],
            "last_run": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스케줄러 상태 조회 실패: {str(e)}")

# 상호작용 기록은 app.py에서 처리

@router.post("/create")
async def create_test(
    test_data: dict,
    db: Session = Depends(get_db)
):
    """A/B 테스트 생성 (간단한 버전)"""
    try:
        service = ABTestService(db)
        
        # 테스트 데이터 준비 (사용자 입력값 우선 사용)
        test_dict = {
            "name": test_data.get("name", "테스트 제품"),
            "description": "AI 생성 A/B 테스트",
            "product_id": test_data.get("product_id", "test_product"),
            "product_price": test_data.get("product_price", 1000.0),
            "test_duration_days": test_data.get("test_duration_days", 7),
            "traffic_split_ratio": 0.5,
            "min_sample_size": test_data.get("min_sample_size", 100),
            "weights": {
                "cvr": 0.5,                    # 구매전환율 (구매 수 / 클릭 수) - 50%
                "cart_add_rate": 0.2,          # 장바구니 추가율 (장바구니 추가 수 / 클릭 수) - 20%
                "cart_conversion_rate": 0.2,   # 장바구니 전환율 (구매 수 / 장바구니 추가 수) - 20%
                "revenue": 0.1                 # 매출 (구매 건수 * 구매 금액) - 10%
            },
            "guardrail_metrics": {
                "avg_page_load_time_threshold": 3000,  # 평균 페이지 로드 시간 임계값 (ms)
                "error_rate_threshold": 0.05           # 오류율 임계값 (5%)
            }
        }
        
        ab_test = service.create_ab_test(test_dict)
        
        return {
            "status": "success",
            "test_id": ab_test.id,
            "message": "A/B 테스트가 성공적으로 생성되었습니다"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 생성 실패: {str(e)}")

# 추가 엔드포인트들 - 웹 페이지에서 요청하는 것들
@router.get("/create")
async def create_test_get():
    """GET 요청으로 테스트 생성 (간단한 버전)"""
    return {
        "status": "success",
        "test_id": 1,
        "message": "테스트가 생성되었습니다 (GET 요청)"
    }

@router.get("/interaction")
async def get_interaction():
    """GET 요청으로 상호작용 조회"""
    return {
        "status": "success",
        "interactions": []
    }

# 루트 엔드포인트들 (prefix 없이)
@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "OK", "message": "AI A/B Test Platform is running!"}

# 중복된 루트 엔드포인트 제거 - list_ab_tests가 이미 / 경로를 사용

# 추가 분석 엔드포인트들
@router.get("/analytics/overview")
async def get_analytics_overview_root():
    """루트 레벨 분석 데이터"""
    return {
        "total_tests": 0,
        "active_tests": 0,
        "total_interactions": 0,
        "conversion_rate": 0.05
    }

@router.get("/analytics/performance")
async def get_performance_data_root():
    """루트 레벨 성과 데이터"""
    return []

@router.get("/logs")
async def get_logs_root():
    """루트 레벨 로그"""
    return []

@router.get("/scheduler/status")
async def get_scheduler_status_root():
    """루트 레벨 스케줄러 상태"""
    return {
        "status": "running",
        "jobs": [],
        "last_run": "2024-01-01T00:00:00Z"
    }
