import logging
from datetime import datetime, timedelta
from typing import List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import ABTest, TestStatus
from .abtest_service import ABTestService

logger = logging.getLogger(__name__)

class ABTestScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
        # 매일 자정에 실행되는 작업 등록
        self.scheduler.add_job(
            self._check_completed_tests,
            CronTrigger(hour=0, minute=0),
            id='check_completed_tests',
            name='Check completed A/B tests'
        )
        
        # 매시간 실행되는 AI 승자 결정 작업 등록
        self.scheduler.add_job(
            self._check_ai_winner_determination,
            CronTrigger(minute=0),
            id='check_ai_winner_determination',
            name='Check AI winner determination'
        )
        
        logger.info("A/B 테스트 스케줄러가 시작되었습니다")

    def _check_completed_tests(self):
        """완료된 테스트를 확인하고 승자 결정 및 다음 라운드 시작"""
        logger.info("완료된 A/B 테스트 확인 시작")
        
        db = SessionLocal()
        try:
            service = ABTestService(db)
            
            # 완료 기간이 지난 활성 테스트들 조회
            completed_tests = self._get_completed_tests(db)
            
            for test in completed_tests:
                logger.info(f"완료된 테스트 처리: {test.id} - {test.name}")
                
                try:
                    # AI 승자 결정
                    winner_id = service.determine_ai_winner(test.id)
                    
                    if winner_id:
                        logger.info(f"테스트 {test.id}의 AI 승자 결정 완료: {winner_id}")
                    else:
                        logger.warning(f"테스트 {test.id}에서 AI 승자를 결정할 수 없습니다")
                        test.status = TestStatus.FAILED
                        test.ended_at = datetime.utcnow()
                    
                    db.commit()
                    
                except Exception as e:
                    logger.error(f"테스트 {test.id} 처리 중 오류 발생: {e}")
                    db.rollback()
                    continue
                    
        except Exception as e:
            logger.error(f"완료된 테스트 확인 중 오류 발생: {e}")
        finally:
            db.close()

    def _check_ai_winner_determination(self):
        """AI 승자 결정이 필요한 테스트 확인"""
        logger.info("AI 승자 결정 확인 시작")
        
        db = SessionLocal()
        try:
            service = ABTestService(db)
            
            # 충분한 데이터가 있는 활성 테스트들 조회
            active_tests = db.query(ABTest).filter(
                ABTest.status == TestStatus.ACTIVE,
                ABTest.started_at.isnot(None)
            ).all()
            
            for test in active_tests:
                try:
                    # 최소 샘플 크기 확인 (clicks 기반)
                    total_clicks = sum(v.clicks for v in test.variants)
                    
                    if total_clicks >= test.min_sample_size:
                        logger.info(f"테스트 {test.id}의 최소 샘플 크기 달성: {total_clicks}")
                        
                        # AI 승자 결정 시도
                        winner_id = service.determine_ai_winner(test.id)
                        
                        if winner_id:
                            logger.info(f"테스트 {test.id}의 AI 승자 결정 완료: {winner_id}")
                        else:
                            logger.info(f"테스트 {test.id}의 AI 승자 결정 보류 (더 많은 데이터 필요)")
                    
                except Exception as e:
                    logger.error(f"테스트 {test.id} AI 승자 결정 중 오류 발생: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"AI 승자 결정 확인 중 오류 발생: {e}")
        finally:
            db.close()

    def _get_completed_tests(self, db: Session) -> List[ABTest]:
        """완료 기간이 지난 활성 테스트들을 조회"""
        now = datetime.utcnow()
        
        completed_tests = db.query(ABTest).filter(
            ABTest.status == TestStatus.ACTIVE,
            ABTest.started_at.isnot(None),
            ABTest.test_duration_days.isnot(None)
        ).all()
        
        # 테스트 기간이 지난 테스트들만 필터링
        expired_tests = []
        for test in completed_tests:
            if test.started_at and test.test_duration_days:
                end_date = test.started_at + timedelta(days=test.test_duration_days)
                if now >= end_date:
                    expired_tests.append(test)
        
        return expired_tests

    def stop(self):
        """스케줄러 중지"""
        self.scheduler.shutdown()
        logger.info("A/B 테스트 스케줄러가 중지되었습니다")

# 전역 스케줄러 인스턴스
scheduler = ABTestScheduler()
