from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .models import TestStatus, VariantType, InteractionType

# --- A/B 테스트 관련 스키마 ---

class ABTestCreate(BaseModel):
    name: str = Field(..., description="테스트 이름")
    description: Optional[str] = Field(None, description="테스트 설명")
    product_id: str = Field(..., description="제품 ID")
    test_duration_days: int = Field(30, description="테스트 기간 (일)")
    traffic_split_ratio: float = Field(0.5, description="트래픽 분배 비율")
    min_sample_size: int = Field(1000, description="최소 샘플 크기")
    weights: Dict[str, float] = Field(
        default={"ctr": 0.3, "cvr": 0.4, "revenue": 0.3},
        description="지표 가중치"
    )
    guardrail_metrics: Dict[str, Any] = Field(
        default={"bounce_rate_threshold": 0.8, "session_duration_min": 30},
        description="가드레일 지표 설정"
    )

class ABTestResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    product_id: str
    status: TestStatus
    test_duration_days: int
    traffic_split_ratio: float
    min_sample_size: int
    weights: Dict[str, float]
    guardrail_metrics: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True

class VariantResponse(BaseModel):
    id: int
    ab_test_id: int
    variant_type: VariantType
    name: str
    content: Dict[str, Any]
    content_hash: str
    impressions: int
    clicks: int
    purchases: int
    revenue: float
    bounce_rate: float
    avg_session_duration: float
    is_active: bool
    is_winner: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PerformanceLogCreate(BaseModel):
    ab_test_id: int = Field(..., description="A/B 테스트 ID")
    variant_id: int = Field(..., description="버전 ID")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    session_id: str = Field(..., description="세션 ID")
    interaction_type: InteractionType = Field(..., description="상호작용 타입")
    interaction_metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")

class PerformanceLogResponse(BaseModel):
    id: int
    ab_test_id: int
    variant_id: int
    user_id: Optional[str]
    session_id: str
    interaction_type: InteractionType
    timestamp: datetime
    interaction_metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True

class TestResultResponse(BaseModel):
    id: int
    ab_test_id: int
    winner_variant_id: Optional[int]
    winner_score: Optional[float]
    p_value: Optional[float]
    confidence_level: Optional[float]
    total_impressions: int
    total_clicks: int
    total_purchases: int
    total_revenue: float
    created_at: datetime

    class Config:
        from_attributes = True

# --- 통계 및 분석 관련 스키마 ---

class VariantMetrics(BaseModel):
    variant_id: int
    variant_name: str
    impressions: int
    clicks: int
    purchases: int
    revenue: float
    ctr: float  # Click Through Rate
    cvr: float  # Conversion Rate
    revenue_per_user: float
    bounce_rate: float
    avg_session_duration: float
    score: float  # 가중치 적용된 최종 점수

class ABTestAnalytics(BaseModel):
    test_id: int
    test_name: str
    status: TestStatus
    variants: List[VariantMetrics]
    winner_variant_id: Optional[int]
    p_value: Optional[float]
    confidence_level: Optional[float]
    test_duration_days: int
    days_remaining: Optional[int]
    total_impressions: int
    total_clicks: int
    total_purchases: int
    total_revenue: float

# --- AI 콘텐츠 생성 관련 스키마 ---

class ContentGenerationRequest(BaseModel):
    product_id: str = Field(..., description="제품 ID")
    product_info: Dict[str, Any] = Field(..., description="제품 정보")
    target_audience: Optional[str] = Field(None, description="타겟 오디언스")
    style_preferences: Optional[Dict[str, Any]] = Field(None, description="스타일 선호도")

class ContentGenerationResponse(BaseModel):
    content: Dict[str, Any] = Field(..., description="생성된 콘텐츠")
    content_hash: str = Field(..., description="콘텐츠 해시")
    generation_metadata: Dict[str, Any] = Field(..., description="생성 메타데이터")

# --- 대시보드 관련 스키마 ---

class DashboardSummary(BaseModel):
    total_tests: int
    active_tests: int
    completed_tests: int
    total_revenue_impact: float
    average_improvement: float

class TestListResponse(BaseModel):
    tests: List[ABTestResponse]
    total_count: int
    page: int
    page_size: int
