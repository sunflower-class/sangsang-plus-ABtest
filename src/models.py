from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class TestStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"
    WAITING_FOR_WINNER_SELECTION = "waiting_for_winner_selection"

class VariantType(str, Enum):
    BASELINE = "baseline"
    CHALLENGER = "challenger"

class InteractionType(str, Enum):
    IMPRESSION = "impression"
    CLICK = "click"
    PURCHASE = "purchase"
    ADD_TO_CART = "add_to_cart"
    VIEW_DETAIL = "view_detail"
    BOUNCE = "bounce"

class ABTest(Base):
    """A/B 테스트 메타데이터 테이블"""
    __tablename__ = "ab_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    product_id = Column(String(100), nullable=False, index=True)
    status = Column(String(50), default=TestStatus.ACTIVE, index=True)
    
    # 이미지 URL 필드 추가
    baseline_image_url = Column(String(500), nullable=True)  # A안 이미지 URL
    challenger_image_url = Column(String(500), nullable=True)  # B안 이미지 URL
    
    # 승자 선택 관련 필드
    ai_winner_variant_id = Column(Integer, nullable=True)  # AI가 결정한 승자
    user_selected_winner_id = Column(Integer, nullable=True)  # 사용자가 선택한 승자
    winner_selection_deadline = Column(DateTime, nullable=True)  # 승자 선택 마감 시간
    
    # 테스트 사이클 관리
    test_cycle_number = Column(Integer, default=1)  # 몇 번째 테스트 사이클인지
    parent_test_id = Column(Integer, nullable=True)  # 이전 테스트 ID
    
    # 테스트 설정
    test_duration_days = Column(Integer, default=30)
    traffic_split_ratio = Column(Float, default=0.5)  # 50:50 분배
    min_sample_size = Column(Integer, default=1000)
    
    # 가중치 설정 (JSON 형태로 저장)
    weights = Column(JSON, default={
        "ctr": 0.3,
        "cvr": 0.4,
        "revenue": 0.3
    })
    
    # 가드레일 설정
    guardrail_metrics = Column(JSON, default={
        "bounce_rate_threshold": 0.8,
        "session_duration_min": 30
    })
    
    # 시간 정보
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    variants = relationship("Variant", back_populates="ab_test", cascade="all, delete-orphan")
    performance_logs = relationship("PerformanceLog", back_populates="ab_test", cascade="all, delete-orphan")

class Variant(Base):
    """A/B 테스트의 각 버전 정보"""
    __tablename__ = "variants"
    
    id = Column(Integer, primary_key=True, index=True)
    ab_test_id = Column(Integer, ForeignKey("ab_tests.id"), nullable=False)
    variant_type = Column(String(50), default=VariantType.CHALLENGER)
    name = Column(String(100), nullable=False)  # "A안", "B안" 등
    
    # AI 생성된 콘텐츠
    content = Column(JSON, nullable=False)  # AI가 생성한 상세 페이지 콘텐츠
    content_hash = Column(String(64), nullable=False, index=True)  # 콘텐츠 변경 감지용
    
    # 성과 지표 (실시간 업데이트)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    purchases = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    bounce_rate = Column(Float, default=0.0)
    avg_session_duration = Column(Float, default=0.0)
    
    # AI 점수 계산
    ai_score = Column(Float, default=0.0)  # AI가 계산한 종합 점수
    ai_confidence = Column(Float, default=0.0)  # AI 신뢰도
    
    # 상태
    is_active = Column(Boolean, default=True, index=True)
    is_winner = Column(Boolean, default=False)
    
    # 시간 정보
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    ab_test = relationship("ABTest", back_populates="variants")
    performance_logs = relationship("PerformanceLog", back_populates="variant", cascade="all, delete-orphan")

class PerformanceLog(Base):
    """사용자 상호작용 로그"""
    __tablename__ = "performance_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    ab_test_id = Column(Integer, ForeignKey("ab_tests.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
    
    # 사용자 식별
    user_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    
    # 상호작용 정보
    interaction_type = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 추가 데이터
    interaction_metadata = Column(JSON, nullable=True)  # 추가 컨텍스트 정보
    
    # 관계
    ab_test = relationship("ABTest", back_populates="performance_logs")
    variant = relationship("Variant", back_populates="performance_logs")

class TestResult(Base):
    """A/B 테스트 결과 요약"""
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, index=True)
    ab_test_id = Column(Integer, ForeignKey("ab_tests.id"), nullable=False)
    
    # 승자 정보
    winner_variant_id = Column(Integer, ForeignKey("variants.id"), nullable=True)
    winner_score = Column(Float, nullable=True)
    
    # 통계적 유의성
    p_value = Column(Float, nullable=True)
    confidence_level = Column(Float, nullable=True)
    
    # 테스트 요약
    total_impressions = Column(Integer, default=0)
    total_clicks = Column(Integer, default=0)
    total_purchases = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    
    # 생성 시간
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    ab_test = relationship("ABTest")
    winner_variant = relationship("Variant")
