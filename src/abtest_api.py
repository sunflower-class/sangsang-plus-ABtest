from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    ABTestCreate, ABTestResponse, VariantResponse, PerformanceLogCreate,
    PerformanceLogResponse, TestResultResponse, ABTestAnalytics,
    DashboardSummary, TestListResponse
)
from abtest_service import ABTestService
from models import TestStatus, ABTest, Variant, TestResult

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

@router.get("/", response_model=TestListResponse)
async def list_ab_tests(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(10, ge=1, le=100, description="페이지 크기"),
    status: Optional[TestStatus] = Query(None, description="테스트 상태 필터"),
    db: Session = Depends(get_db)
):
    """A/B 테스트 목록 조회"""
    try:
        service = ABTestService(db)
        
        # 쿼리 조건 구성
        query = db.query(ABTest)
        if status:
            query = query.filter(ABTest.status == status)
        
        # 페이징
        total_count = query.count()
        tests = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return TestListResponse(
            tests=[ABTestResponse.from_orm(test) for test in tests],
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 목록 조회 실패: {str(e)}")

@router.get("/{test_id}", response_model=ABTestResponse)
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
        from models import Variant
        
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
        from models import ABTest, TestResult
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
        from models import TestResult
        
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
