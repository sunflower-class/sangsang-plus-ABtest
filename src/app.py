import os
import json
import threading
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from datetime import datetime
import uuid

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from confluent_kafka import Producer, Consumer, KafkaException

# A/B 테스트 모듈 import
from ab_test_manager import (
    ab_test_manager, ProductInfo, PageVariant, TestStatus, VariantType,
    DistributionMode, TestMode, ExperimentBrief
)
from page_generator import page_generator
from autopilot import initialize_autopilot, autopilot_scheduler
from dashboard import initialize_dashboard, dashboard_manager

# --- 설정 (변경 없음) ---
KAFKA_BROKER = 'localhost:9092'
TOPIC_NAME = 'fastapi-confluent-topic'
MODE = os.environ.get("MODE", "development")

print(f"Running in {MODE} mode...")

if MODE == "docker":
    KAFKA_BROKER = 'kafka:9092'
elif MODE == "kubernetes":
    KAFKA_BROKER = 'kafka-svc:9092'

if MODE != "development":
    print(f"Kafka Broker is set to {KAFKA_BROKER}")

# --- Pydantic 모델 ---
class CreateTestRequest(BaseModel):
    test_name: str
    product_name: str
    product_image: str
    product_description: str
    price: float
    category: str
    tags: Optional[List[str]] = []
    duration_days: int = 14
    target_metrics: Optional[Dict[str, float]] = None

class TestEventRequest(BaseModel):
    test_id: str
    variant_id: str
    event_type: str  # "impression", "click", "conversion", "bounce"
    user_id: str
    session_id: str
    revenue: Optional[float] = 0.0
    session_duration: Optional[float] = 0.0

class TestActionRequest(BaseModel):
    test_id: str
    action: str  # "start", "pause", "complete"

class ExperimentBriefRequest(BaseModel):
    objective: str
    primary_metrics: List[str]
    secondary_metrics: List[str]
    guardrails: Dict[str, float]
    target_categories: List[str]
    target_channels: List[str]
    target_devices: List[str]
    exclude_conditions: List[str]
    variant_count: int
    distribution_mode: str
    mde: float
    min_sample_size: int

class CreateTestWithBriefRequest(BaseModel):
    test_name: str
    product_name: str
    product_image: str
    product_description: str
    price: float
    category: str
    tags: Optional[List[str]] = []
    duration_days: int = 14
    experiment_brief: ExperimentBriefRequest
    test_mode: str = "manual"

# --- Kafka Consumer ---
def consume_messages():
    conf = {
        'bootstrap.servers': KAFKA_BROKER,
        'group.id': 'fastapi-consumer-group',
        'auto.offset.reset': 'latest'
    }
    consumer = Consumer(conf)
    try:
        consumer.subscribe([TOPIC_NAME])
        print(f"Consumer started on topic '{TOPIC_NAME}'...")
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaException._PARTITION_EOF:
                    continue
                else:
                    print(f"Consumer error: {msg.error()}")
                    break
            try:
                received_data = json.loads(msg.value().decode('utf-8'))
                print(f"Received message: {received_data}")
            except json.JSONDecodeError:
                print(f"Could not decode message: {msg.value()}")
    except Exception as e:
        print(f"Error in consumer thread: {e}")
    finally:
        print("Consumer closing...")
        consumer.close()

# --- Lifespan 이벤트 핸들러 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # A/B 테스트 시스템 초기화
    print("Initializing A/B Test System...")
    
    # 자동 생성기 초기화
    initialize_autopilot(ab_test_manager)
    print("Autopilot initialized")
    
    # 대시보드 초기화
    initialize_dashboard(ab_test_manager)
    print("Dashboard initialized")
    
    # Kafka 연결 (개발 모드가 아닌 경우)
    if MODE != "development":
        print("Connecting to Kafka...")
        try:
            producer_conf = {'bootstrap.servers': KAFKA_BROKER}
            app.state.producer = Producer(producer_conf)
            print("Kafka Producer connected successfully.")
        except Exception as e:
            print(f"Error creating producer: {e}")
            app.state.producer = None
        
        consumer_thread = threading.Thread(target=consume_messages, daemon=True)
        consumer_thread.start()
        print("Kafka Consumer thread started.")
    else:
        print("Running in development mode without Kafka connection.")
        app.state.producer = None

    yield

    if MODE != "development" and app.state.producer:
        print("Application shutdown: Flushing final messages...")
        app.state.producer.flush()
        print("Producer flushed.")
    else:
        print("Application shutdown.")

# --- FastAPI 앱 생성 ---
app = FastAPI(
    lifespan=lifespan,
    title="상품 상세페이지 A/B 테스트 시스템",
    description="상품 이미지와 설명을 바탕으로 다양한 상세페이지를 생성하고 A/B 테스트를 수행하는 시스템"
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Kafka 전송 로직을 처리하는 헬퍼 함수 ---
def handle_kafka_production(producer: Optional[Producer], data: Dict[str, Any]):
    """
    모드에 따라 Kafka 메시지 전송 또는 로깅을 처리하는 중앙 함수.
    운영 모드에서 Producer가 없으면 예외를 발생시킵니다.
    """
    if MODE == "development":
        # 개발 모드에서는 로깅만 하고 종료
        print(f"DEV MODE: Received message, not sending to Kafka: {data}")
        return {"status": "Message accepted for processing", "data": data}

    # 운영 모드(docker, kubernetes 등) 로직
    if not producer:
        # Producer가 준비되지 않았으면 명시적인 에러 발생
        raise HTTPException(status_code=503, detail="Kafka Producer is not available.")
    
    try:
        producer.produce(
            TOPIC_NAME,
            value=json.dumps(data).encode('utf-8'),
            callback=delivery_report
        )
        producer.poll(0)
        print(f"Message sent to Kafka topic '{TOPIC_NAME}': {data}")
        return {"status": "Message accepted for processing", "data": data}
    except Exception as e:
        # Kafka 전송 중 다른 에러가 발생하면 그대로 전달
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

def delivery_report(err, msg):
    """ 메시지 전송 결과를 비동기적으로 처리하는 콜백 함수 """
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

# --- A/B 테스트 API 엔드포인트 ---

@app.get('/python')
def running_test():
    return "python API is running!"

@app.post("/python/message", status_code=202)
async def send_message(message_data: Dict[str, Any], request: Request):
    # 모드에 따른 분기 처리를 헬퍼 함수에 위임
    return handle_kafka_production(request.app.state.producer, message_data)

@app.get("/actuator/health", include_in_schema=False)
async def health_check(request: Request):
    if MODE == "development":
        return {"status": "OK", "detail": "Running in development mode"}
    
    if not request.app.state.producer:
         raise HTTPException(status_code=503, detail="Producer is not available")
    return {"status": "OK"}

# --- A/B 테스트 관리 API ---

@app.post("/api/abtest/create", summary="A/B 테스트 생성")
async def create_ab_test(request: CreateTestRequest):
    """새로운 A/B 테스트 생성"""
    try:
        # 상품 정보 생성
        product_info = ProductInfo(
            product_id=str(uuid.uuid4()),
            product_name=request.product_name,
            product_image=request.product_image,
            product_description=request.product_description,
            price=request.price,
            category=request.category,
            tags=request.tags or []
        )
        
        # 페이지 변형 생성
        page_variants = []
        variants_data = page_generator.generate_page_variants({
            "product_name": request.product_name,
            "product_image": request.product_image,
            "product_description": request.product_description,
            "price": request.price,
            "category": request.category
        })
        
        for variant_data in variants_data:
            page_variant = PageVariant(
                variant_id=variant_data["variant_id"],
                variant_type=VariantType(variant_data["variant_type"]),
                title=variant_data["title"],
                description=variant_data["description"],
                layout_type=variant_data["layout_type"],
                color_scheme=variant_data["color_scheme"],
                cta_text=variant_data["cta_text"],
                cta_color=variant_data["cta_color"],
                cta_position=variant_data["cta_position"],
                additional_features=variant_data["additional_features"],
                image_style=variant_data["image_style"],
                font_style=variant_data["font_style"],
                created_at=datetime.now(),
                is_active=True
            )
            page_variants.append(page_variant)
        
        # A/B 테스트 생성
        test = ab_test_manager.create_test(
            test_name=request.test_name,
            product_info=product_info,
            variants=page_variants,
            duration_days=request.duration_days,
            target_metrics=request.target_metrics
        )
        
        return {
            "status": "success",
            "test_id": test.test_id,
            "message": "A/B 테스트가 성공적으로 생성되었습니다."
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 생성 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/list", summary="A/B 테스트 목록 조회")
async def get_ab_tests():
    """모든 A/B 테스트 목록 조회"""
    try:
        tests = ab_test_manager.get_all_tests()
        return {
            "status": "success",
            "tests": tests,
            "total_count": len(tests)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 목록 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/{test_id}", summary="A/B 테스트 상세 조회")
async def get_ab_test_detail(test_id: str):
    """특정 A/B 테스트 상세 정보 조회"""
    try:
        test = ab_test_manager.tests.get(test_id)
        if not test:
            raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다.")
        
        results = ab_test_manager.get_test_results(test_id)
        return {
            "status": "success",
            "test": {
                "test_id": test.test_id,
                "test_name": test.test_name,
                "status": test.status.value,
                "start_date": test.start_date.isoformat(),
                "end_date": test.end_date.isoformat() if test.end_date else None,
                "product_info": {
                    "product_name": test.product_info.product_name,
                    "product_image": test.product_info.product_image,
                    "product_description": test.product_info.product_description,
                    "price": test.product_info.price,
                    "category": test.product_info.category
                },
                "variants_count": len(test.variants),
                "target_metrics": test.target_metrics
            },
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 조회 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/abtest/action", summary="A/B 테스트 액션 수행")
async def perform_test_action(request: TestActionRequest):
    """테스트 시작/일시정지/완료"""
    try:
        if request.action == "start":
            success = ab_test_manager.start_test(request.test_id)
            message = "테스트가 시작되었습니다." if success else "테스트를 시작할 수 없습니다."
        elif request.action == "pause":
            success = ab_test_manager.pause_test(request.test_id)
            message = "테스트가 일시정지되었습니다." if success else "테스트를 일시정지할 수 없습니다."
        elif request.action == "complete":
            success = ab_test_manager.complete_test(request.test_id)
            message = "테스트가 완료되었습니다." if success else "테스트를 완료할 수 없습니다."
        else:
            raise HTTPException(status_code=400, detail="잘못된 액션입니다.")
        
        return {
            "status": "success" if success else "error",
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 액션 수행 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/{test_id}/results", summary="A/B 테스트 결과 조회")
async def get_test_results(test_id: str):
    """테스트 결과 및 통계 조회"""
    try:
        results = ab_test_manager.get_test_results(test_id)
        if not results:
            raise HTTPException(status_code=404, detail="테스트 결과를 찾을 수 없습니다.")
        
        return {
            "status": "success",
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 결과 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/{test_id}/events", summary="A/B 테스트 이벤트 조회")
async def get_test_events(test_id: str, limit: int = 100):
    """테스트 이벤트 목록 조회"""
    try:
        events = ab_test_manager.get_test_events(test_id, limit)
        return {
            "status": "success",
            "events": events,
            "total_count": len(events)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이벤트 조회 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/abtest/event", summary="A/B 테스트 이벤트 기록")
async def record_test_event(request: TestEventRequest):
    """테스트 이벤트 기록 (노출, 클릭, 전환 등)"""
    try:
        # 테스트 존재 여부 확인
        test = ab_test_manager.tests.get(request.test_id)
        if not test:
            return {
                "status": "warning",
                "message": "테스트를 찾을 수 없습니다. 이벤트가 기록되지 않았습니다."
            }
        
        # 매출 계산: conversion 이벤트인 경우 상품가격으로 설정
        calculated_revenue = 0.0
        if request.event_type == "conversion":
            calculated_revenue = test.product_info.price
        
        success = ab_test_manager.record_event(
            test_id=request.test_id,
            variant_id=request.variant_id,
            user_id=request.user_id,
            event_type=request.event_type,
            session_id=request.session_id,
            revenue=calculated_revenue,
            session_duration=request.session_duration
        )
        
        if success:
            return {
                "status": "success",
                "message": "이벤트가 성공적으로 기록되었습니다."
            }
        else:
            return {
                "status": "warning",
                "message": "이벤트 기록에 실패했습니다. 테스트 상태를 확인해주세요."
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"이벤트 기록 중 오류가 발생했습니다: {str(e)}"
        }

@app.get("/api/abtest/{test_id}/variant/{user_id}", summary="사용자별 변형 조회")
async def get_user_variant(test_id: str, user_id: str, session_id: str = "default"):
    """사용자에게 표시할 변형 조회"""
    try:
        variant = ab_test_manager.get_variant_for_user(test_id, user_id, session_id)
        if not variant:
            raise HTTPException(status_code=404, detail="활성 테스트를 찾을 수 없습니다.")
        
        return {
            "status": "success",
            "variant": {
                "variant_id": variant.variant_id,
                "variant_type": variant.variant_type.value,
                "title": variant.title,
                "description": variant.description,
                "layout_type": variant.layout_type,
                "color_scheme": variant.color_scheme,
                "cta_text": variant.cta_text,
                "cta_color": variant.cta_color,
                "cta_position": variant.cta_position,
                "additional_features": variant.additional_features,
                "image_style": variant.image_style,
                "font_style": variant.font_style
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"변형 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/{test_id}/page/{variant_id}", response_class=HTMLResponse, summary="상세페이지 HTML 생성")
async def generate_product_page(test_id: str, variant_id: str):
    """특정 변형의 상세페이지 HTML 생성"""
    try:
        test = ab_test_manager.tests.get(test_id)
        if not test:
            raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다.")
        
        variant = next((v for v in test.variants if v.variant_id == variant_id), None)
        if not variant:
            raise HTTPException(status_code=404, detail="변형을 찾을 수 없습니다.")
        
        # 변형 데이터를 딕셔너리로 변환
        variant_data = {
            "variant_id": variant.variant_id,
            "variant_type": variant.variant_type.value,
            "title": variant.title,
            "description": variant.description,
            "layout_type": variant.layout_type,
            "color_scheme": variant.color_scheme,
            "cta_text": variant.cta_text,
            "cta_color": variant.cta_color,
            "cta_position": variant.cta_position,
            "additional_features": variant.additional_features,
            "image_style": variant.image_style,
            "font_style": variant.font_style,
            "template": {
                "css_styles": {
                    "primary_color": "#2563eb",
                    "secondary_color": "#f8fafc",
                    "text_color": "#1e293b",
                    "cta_color": variant.cta_color,
                    "font_family": "'Inter', sans-serif"
                },
                "html_structure": f"{variant.layout_type}_{variant.color_scheme}"
            }
        }
        
        # 상품 정보
        product_info = {
            "product_name": test.product_info.product_name,
            "product_image": test.product_info.product_image,
            "product_description": test.product_info.product_description,
            "price": test.product_info.price,
            "category": test.product_info.category
        }
        
        # HTML 페이지 생성
        html_content = page_generator.generate_html_page(variant_data, product_info)
        
        return HTMLResponse(content=html_content)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"페이지 생성 중 오류가 발생했습니다: {str(e)}")

# --- 새로운 API 엔드포인트들 ---

@app.post("/api/abtest/create-with-brief", summary="실험 계약서와 함께 A/B 테스트 생성")
async def create_test_with_brief(request: CreateTestWithBriefRequest):
    """실험 계약서와 함께 A/B 테스트 생성 - 요구사항 1번"""
    try:
        # ProductInfo 생성
        product_info = ProductInfo(
            product_id=str(uuid.uuid4()),
            product_name=request.product_name,
            product_image=request.product_image,
            product_description=request.product_description,
            price=request.price,
            category=request.category,
            tags=request.tags
        )
        
        # ExperimentBrief 생성
        experiment_brief = ab_test_manager.create_experiment_brief(
            objective=request.experiment_brief.objective,
            primary_metrics=request.experiment_brief.primary_metrics,
            secondary_metrics=request.experiment_brief.secondary_metrics,
            guardrails=request.experiment_brief.guardrails,
            target_categories=request.experiment_brief.target_categories,
            target_channels=request.experiment_brief.target_channels,
            target_devices=request.experiment_brief.target_devices,
            exclude_conditions=request.experiment_brief.exclude_conditions,
            variant_count=request.experiment_brief.variant_count,
            distribution_mode=DistributionMode(request.experiment_brief.distribution_mode),
            mde=request.experiment_brief.mde,
            min_sample_size=request.experiment_brief.min_sample_size
        )
        
        # 변형 생성 (자동 생성기 사용)
        from autopilot import VariantGenerator
        variant_generator = VariantGenerator()
        variants = variant_generator.generate_variants(product_info, request.experiment_brief.variant_count)
        
        # 정책 필터 적용
        approved_variants = []
        for variant in variants:
            if ab_test_manager.apply_policy_filters(variant):
                variant.policy_approved = True
                approved_variants.append(variant)
        
        if len(approved_variants) < 2:
            raise HTTPException(status_code=400, detail="정책 필터를 통과한 변형이 부족합니다.")
        
        # 테스트 생성
        test = ab_test_manager.create_test_with_brief(
            test_name=request.test_name,
            product_info=product_info,
            variants=approved_variants,
            experiment_brief=experiment_brief,
            test_mode=TestMode(request.test_mode)
        )
        
        return {
            "status": "success",
            "test_id": test.test_id,
            "message": "실험 계약서와 함께 테스트가 생성되었습니다.",
            "experiment_brief": {
                "objective": experiment_brief.objective,
                "primary_metrics": experiment_brief.primary_metrics,
                "guardrails": experiment_brief.guardrails,
                "mde": experiment_brief.mde,
                "min_sample_size": experiment_brief.min_sample_size
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 생성 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/{test_id}/variant-bandit/{user_id}", summary="Thompson Sampling을 사용한 변형 선택")
async def get_variant_with_bandit(test_id: str, user_id: str, session_id: str = "default"):
    """Thompson Sampling을 사용한 변형 선택 - 요구사항 7번"""
    try:
        variant = ab_test_manager.get_variant_with_bandit(test_id, user_id, session_id)
        if not variant:
            raise HTTPException(status_code=404, detail="활성 테스트를 찾을 수 없습니다.")
        
        return {
            "status": "success",
            "variant": {
                "variant_id": variant.variant_id,
                "variant_type": variant.variant_type.value,
                "title": variant.title,
                "description": variant.description,
                "layout_type": variant.layout_type,
                "color_scheme": variant.color_scheme,
                "cta_text": variant.cta_text,
                "cta_color": variant.cta_color,
                "cta_position": variant.cta_position,
                "additional_features": variant.additional_features,
                "image_style": variant.image_style,
                "font_style": variant.font_style
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"변형 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/dashboard/metrics", summary="대시보드 메트릭 조회")
async def get_dashboard_metrics():
    """대시보드 메트릭 조회 - 요구사항 9번"""
    try:
        if not dashboard_manager:
            raise HTTPException(status_code=500, detail="대시보드가 초기화되지 않았습니다.")
        
        metrics = dashboard_manager.get_dashboard_metrics()
        
        return {
            "status": "success",
            "metrics": {
                "total_tests": metrics.total_tests,
                "active_tests": metrics.active_tests,
                "completed_tests": metrics.completed_tests,
                "draft_tests": metrics.draft_tests,
                "total_impressions": metrics.total_impressions,
                "total_conversions": metrics.total_conversions,
                "overall_cvr": metrics.overall_cvr,
                "total_revenue": metrics.total_revenue,
                "autopilot_experiments": metrics.autopilot_experiments,
                "traffic_usage": metrics.traffic_usage
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메트릭 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/dashboard/test-summaries", summary="테스트 요약 목록 조회")
async def get_test_summaries(limit: int = 10):
    """테스트 요약 목록 조회"""
    try:
        if not dashboard_manager:
            raise HTTPException(status_code=500, detail="대시보드가 초기화되지 않았습니다.")
        
        summaries = dashboard_manager.get_test_summaries(limit)
        
        return {
            "status": "success",
            "summaries": [
                {
                    "test_id": summary.test_id,
                    "test_name": summary.test_name,
                    "status": summary.status,
                    "product_name": summary.product_name,
                    "variants_count": summary.variants_count,
                    "impressions": summary.impressions,
                    "clicks": summary.clicks,
                    "conversions": summary.conversions,
                    "cvr": summary.cvr,
                    "revenue": summary.revenue,
                    "created_at": summary.created_at,
                    "duration_days": summary.duration_days,
                    "winner": summary.winner,
                    "alerts_count": summary.alerts_count
                }
                for summary in summaries
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 요약 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/dashboard/real-time/{test_id}", summary="실시간 메트릭 조회")
async def get_real_time_metrics(test_id: str):
    """실시간 메트릭 조회 - 요구사항 9번"""
    try:
        if not dashboard_manager:
            raise HTTPException(status_code=500, detail="대시보드가 초기화되지 않았습니다.")
        
        metrics = dashboard_manager.get_real_time_metrics(test_id)
        
        return {
            "status": "success",
            "metrics": metrics
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"실시간 메트릭 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/dashboard/charts/{test_id}", summary="성과 차트 생성")
async def get_performance_charts(test_id: str):
    """성과 차트 생성"""
    try:
        if not dashboard_manager:
            raise HTTPException(status_code=500, detail="대시보드가 초기화되지 않았습니다.")
        
        charts = dashboard_manager.create_performance_charts(test_id)
        
        return {
            "status": "success",
            "charts": charts
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"차트 생성 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/report/{test_id}", summary="실험 리포트 생성")
async def generate_experiment_report(test_id: str):
    """실험 리포트 생성 - 요구사항 10번"""
    try:
        if not dashboard_manager:
            raise HTTPException(status_code=500, detail="대시보드가 초기화되지 않았습니다.")
        
        report = dashboard_manager.generate_experiment_report(test_id)
        
        return {
            "status": "success",
            "report": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리포트 생성 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/report/{test_id}/pdf", summary="PDF 리포트 다운로드")
async def download_report_pdf(test_id: str):
    """PDF 리포트 다운로드"""
    try:
        if not dashboard_manager:
            raise HTTPException(status_code=500, detail="대시보드가 초기화되지 않았습니다.")
        
        pdf_content = dashboard_manager.export_report_pdf(test_id)
        
        return {
            "status": "success",
            "pdf_content": pdf_content
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 생성 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/guardrails/alerts", summary="가드레일 알림 조회")
async def get_guardrail_alerts(test_id: str = None):
    """가드레일 알림 조회 - 요구사항 6번"""
    try:
        alerts = ab_test_manager.get_guardrail_alerts(test_id)
        
        return {
            "status": "success",
            "alerts": alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/bandit/decisions/{test_id}", summary="밴딧 의사결정 로그 조회")
async def get_bandit_decisions(test_id: str, limit: int = 100):
    """밴딧 의사결정 로그 조회 - 요구사항 9번"""
    try:
        decisions = ab_test_manager.get_bandit_decisions(test_id, limit)
        
        return {
            "status": "success",
            "decisions": decisions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"의사결정 로그 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/autopilot/status", summary="자동 생성 상태 조회")
async def get_autopilot_status():
    """자동 생성 상태 조회 - 요구사항 11번"""
    try:
        if not autopilot_scheduler:
            raise HTTPException(status_code=500, detail="자동 생성기가 초기화되지 않았습니다.")
        
        status = autopilot_scheduler.get_autopilot_status()
        
        return {
            "status": "success",
            "autopilot_status": status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자동 생성 상태 조회 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/abtest/autopilot/promotion-mode", summary="프로모션 모드 설정")
async def set_promotion_mode(enabled: bool):
    """프로모션 모드 설정 - 요구사항 11번"""
    try:
        if not autopilot_scheduler:
            raise HTTPException(status_code=500, detail="자동 생성기가 초기화되지 않았습니다.")
        
        autopilot_scheduler.set_promotion_mode(enabled)
        
        return {
            "status": "success",
            "message": f"프로모션 모드가 {'활성화' if enabled else '비활성화'}되었습니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프로모션 모드 설정 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/abtest/autopilot/run-cycle", summary="자동 생성 사이클 수동 실행")
async def run_autopilot_cycle():
    """자동 생성 사이클 수동 실행"""
    try:
        if not autopilot_scheduler:
            return {
                "status": "warning",
                "message": "자동 생성기가 초기화되지 않았습니다. 시스템을 재시작해주세요."
            }
        
        autopilot_scheduler.run_autopilot_cycle()
        
        return {
            "status": "success",
            "message": "자동 생성 사이클이 실행되었습니다."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"자동 생성 사이클 실행 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/api/abtest/test/{test_id}/promote-winner", summary="승자 승격")
async def promote_winner(test_id: str, variant_id: str):
    """승자 승격 - 요구사항 8번"""
    try:
        success = ab_test_manager.promote_winner(test_id, variant_id)
        
        if success:
            return {
                "status": "success",
                "message": f"변형 {variant_id}가 승격되었습니다."
            }
        else:
            raise HTTPException(status_code=400, detail="승격에 실패했습니다.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"승격 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/abtest/test/{test_id}/auto-rollback", summary="자동 롤백 실행")
async def execute_auto_rollback(test_id: str):
    """자동 롤백 실행 - 요구사항 8번"""
    try:
        success = ab_test_manager.auto_rollback(test_id)
        
        if success:
            return {
                "status": "success",
                "message": "자동 롤백이 실행되었습니다."
            }
        else:
            return {
                "status": "success",
                "message": "롤백 조건이 충족되지 않았습니다."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"롤백 실행 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/learning/patterns", summary="학습 패턴 조회")
async def get_learning_patterns():
    """학습 패턴 조회 - 요구사항 10번"""
    try:
        if not dashboard_manager:
            raise HTTPException(status_code=500, detail="대시보드가 초기화되지 않았습니다.")
        
        patterns = dashboard_manager.get_learning_patterns()
        
        return {
            "status": "success",
            "patterns": patterns
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"학습 패턴 조회 중 오류가 발생했습니다: {str(e)}")

# --- 메인 실행 ---
if __name__ == '__main__':
    uvicorn.run(
        "app:app", 
        host='0.0.0.0', 
        port=5001, 
        reload=(MODE != "kubernetes")
    )
