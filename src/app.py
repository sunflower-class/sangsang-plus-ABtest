import os
import json
import threading
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import uuid

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from confluent_kafka import Producer, Consumer, KafkaException

# A/B 테스트 모듈 import
from ab_test_manager import (
    ABTestManager, ProductInfo, PageVariant, TestStatus, VariantType,
    DistributionMode, TestMode, ExperimentBrief
)
from page_generator import page_generator
from autopilot import AutopilotScheduler

# 전역 변수들
ab_test_manager = None
autopilot_scheduler = None
dashboard_manager = None
real_time_tracker = None

from dashboard import DashboardManager

# 실시간 추적기 import 추가
from real_time_tracker import RealTimeTracker, RealTimeEvent

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
    decision_mode: str = "hybrid"
    manual_decision_period_days: int = 7
    long_term_monitoring_days: int = 30

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

class ManualDecisionRequest(BaseModel):
    test_id: str
    variant_id: str
    reason: str = ""

class LongTermMetricsRequest(BaseModel):
    test_id: str
    metrics: Dict[str, float]  # {"cvr": 2.5, "ctr": 1.8, "revenue": 15000}

class CycleActionRequest(BaseModel):
    test_id: str
    action: str  # "start_next_cycle", "complete_cycle", "archive"

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
    
    # A/B 테스트 매니저 초기화
    global ab_test_manager, autopilot_scheduler, dashboard_manager, real_time_tracker
    
    ab_test_manager = ABTestManager()
    
    # 오토파일럿 스케줄러 초기화
    from autopilot import AutopilotConfig
    autopilot_config = AutopilotConfig()
    autopilot_scheduler = AutopilotScheduler(ab_test_manager, autopilot_config)
    print("Autopilot initialized")
    
    # 대시보드 매니저 초기화
    dashboard_manager = DashboardManager(ab_test_manager)
    print("Dashboard initialized")
    
    # 실시간 추적기 초기화 (선택적)
    try:
        real_time_tracker = RealTimeTracker(
            kafka_bootstrap_servers=['localhost:9092'],
            webhook_url=None  # 웹훅은 선택적
        )
        await real_time_tracker.initialize()
        await real_time_tracker.start_tracking()
        print("Real-time tracker initialized (memory-based)")
    except Exception as e:
        print(f"Real-time tracker initialization failed: {e}")
        real_time_tracker = None
    
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
async def get_test_detail(test_id: str):
    """테스트 상세 정보 조회"""
    try:
        test = ab_test_manager.tests.get(test_id)
        if not test:
            raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다.")
        
        return {
            "status": "success",
            "test": {
                "test_id": test.test_id,
                "test_name": test.test_name,
                "status": test.status.value,
                "start_date": test.start_date.isoformat(),
                "end_date": test.end_date.isoformat() if test.end_date else None,
                "product_name": test.product_info.product_name,
                "variants_count": len(test.variants),
                "created_at": test.created_at.isoformat(),
                "test_mode": test.test_mode.value
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 조회 중 오류가 발생했습니다: {str(e)}")

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

@app.post("/api/abtest/action")
async def test_action(request: TestActionRequest):
    """테스트 액션 (시작, 일시정지, 완료)"""
    try:
        if request.action == "start":
            success = ab_test_manager.start_test(request.test_id)
        elif request.action == "pause":
            success = ab_test_manager.pause_test(request.test_id)
        elif request.action == "complete":
            success = ab_test_manager.complete_test(request.test_id)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unknown action: {request.action}"}
            )
        
        if success:
            return {"status": "success", "message": f"Test {request.action} successful"}
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Failed to {request.action} test"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error during test action: {str(e)}"}
        )

@app.post("/api/abtest/manual-decision")
async def manual_select_winner(request: ManualDecisionRequest):
    """수동으로 승자 선택"""
    try:
        success = ab_test_manager.manual_select_winner(
            request.test_id, 
            request.variant_id, 
            request.reason
        )
        
        if success:
            return {"status": "success", "message": "Winner manually selected"}
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "Failed to select winner manually"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error during manual decision: {str(e)}"}
        )

@app.post("/api/abtest/long-term-monitoring/start")
async def start_long_term_monitoring(test_id: str):
    """장기 모니터링 시작"""
    try:
        success = ab_test_manager.start_long_term_monitoring(test_id)
        
        if success:
            return {"status": "success", "message": "Long-term monitoring started"}
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "Failed to start long-term monitoring"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error starting long-term monitoring: {str(e)}"}
        )

@app.post("/api/abtest/long-term-monitoring/record")
async def record_long_term_metrics(request: LongTermMetricsRequest):
    """장기 모니터링 메트릭 기록"""
    try:
        success = ab_test_manager.record_long_term_metrics(
            request.test_id, 
            request.metrics
        )
        
        if success:
            return {"status": "success", "message": "Long-term metrics recorded"}
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "Failed to record long-term metrics"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error recording long-term metrics: {str(e)}"}
        )

@app.get("/api/abtest/long-term-monitoring/{test_id}")
async def get_long_term_performance(test_id: str):
    """장기 성과 분석 조회"""
    try:
        performance = ab_test_manager.get_long_term_performance(test_id)
        return {"status": "success", "performance": performance}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting long-term performance: {str(e)}"}
        )

@app.post("/api/abtest/cycle/action")
async def cycle_action(request: CycleActionRequest):
    """사이클 액션"""
    try:
        if request.action == "start_next_cycle":
            success = ab_test_manager.start_next_cycle(request.test_id)
        elif request.action == "complete_cycle":
            success = ab_test_manager.complete_cycle(request.test_id)
        elif request.action == "archive":
            # 아카이브 처리
            test = ab_test_manager.tests.get(request.test_id)
            if test:
                test.status = TestStatus.ARCHIVED
                success = True
            else:
                success = False
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unknown cycle action: {request.action}"}
            )
        
        if success:
            return {"status": "success", "message": f"Cycle action {request.action} successful"}
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Failed to perform cycle action: {request.action}"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error during cycle action: {str(e)}"}
        )

@app.get("/api/abtest/cycle/status/{test_id}")
async def get_cycle_status(test_id: str):
    """사이클 상태 조회"""
    try:
        status = ab_test_manager.get_cycle_status(test_id)
        return {"status": "success", "cycle_status": status}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting cycle status: {str(e)}"}
        )

@app.get("/api/abtest/cycle/queue")
async def get_auto_cycle_queue():
    """자동 사이클 대기열 조회"""
    try:
        queue = ab_test_manager.get_auto_cycle_queue()
        return {"status": "success", "auto_cycle_queue": queue}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting auto cycle queue: {str(e)}"}
        )

@app.get("/api/abtest/manual-decision/info/{test_id}")
async def get_manual_decision_info(test_id: str):
    """수동 결정 정보 조회"""
    try:
        info = ab_test_manager.get_manual_decision_info(test_id)
        return {"status": "success", "manual_decision_info": info}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting manual decision info: {str(e)}"}
        )

@app.get("/api/abtest/manual-decision/list")
async def get_manual_decision_tests():
    """수동 결정 대기 중인 테스트 목록"""
    try:
        tests = []
        for test in ab_test_manager.tests.values():
            if test.status == TestStatus.MANUAL_DECISION:
                decision_info = ab_test_manager.get_manual_decision_info(test.test_id)
                tests.append({
                    "test_id": test.test_id,
                    "test_name": test.test_name,
                    "product_name": test.product_info.product_name,
                    "decision_info": decision_info
                })
        return {"status": "success", "manual_decision_tests": tests}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting manual decision tests: {str(e)}"}
        )

@app.post("/api/abtest/check-timeouts")
async def check_manual_decision_timeouts():
    """수동 결정 타임아웃 체크"""
    try:
        timeout_count = 0
        for test_id in list(ab_test_manager.tests.keys()):
            if ab_test_manager.check_manual_decision_timeout(test_id):
                timeout_count += 1
        
        return {"status": "success", "timeout_count": timeout_count}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error checking timeouts: {str(e)}"}
        )

@app.get("/api/abtest/dashboard/cycle-management")
async def get_cycle_management_dashboard():
    """사이클 관리 대시보드"""
    try:
        if not dashboard_manager:
            return JSONResponse(
                status_code=500,
                content={"error": "Dashboard manager not initialized"}
            )
        
        cycle_info = dashboard_manager.get_cycle_management_info()
        return {"status": "success", "cycle_management": cycle_info}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting cycle management dashboard: {str(e)}"}
        )

@app.get("/api/abtest/dashboard/long-term-monitoring/{test_id}")
async def get_long_term_monitoring_dashboard(test_id: str):
    """장기 모니터링 대시보드"""
    try:
        if not dashboard_manager:
            return JSONResponse(
                status_code=500,
                content={"error": "Dashboard manager not initialized"}
            )
        
        monitoring_data = dashboard_manager.get_long_term_monitoring_data(test_id)
        return {"status": "success", "long_term_monitoring": monitoring_data}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting long-term monitoring dashboard: {str(e)}"}
        )

@app.get("/api/abtest/dashboard/manual-decision")
async def get_manual_decision_dashboard():
    """수동 결정 대시보드"""
    try:
        # dashboard_manager가 초기화되지 않은 경우 초기화
        global dashboard_manager
        if not dashboard_manager:
            from ab_test_manager import ab_test_manager
            dashboard_manager = initialize_dashboard(ab_test_manager)
        
        manual_tests = dashboard_manager.get_manual_decision_tests()
        return {"status": "success", "manual_decision_tests": manual_tests}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting manual decision dashboard: {str(e)}"}
        )

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
    """자동 생성 사이클을 수동으로 실행"""
    try:
        # 상품 후보 선택 및 실험 생성
        candidates = autopilot_scheduler.select_candidates()
        experiments_created = 0
        
        for candidate in candidates[:2]:  # 최대 2개만 생성
            if autopilot_scheduler.create_experiment_for_product(candidate):
                experiments_created += 1
        
        return {
            "status": "success",
            "experiments_created": experiments_created,
            "message": f"{experiments_created}개의 실험이 생성되었습니다."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자동 생성 사이클 실행 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/abtest/autopilot/test-mode", summary="테스트 모드 설정")
async def set_test_mode(enabled: bool = True):
    """테스트 모드를 활성화/비활성화"""
    try:
        if enabled:
            # 테스트 모드로 설정 변경
            autopilot_scheduler.config.test_mode = True
            autopilot_scheduler.config.check_interval_hours = 1
            autopilot_scheduler.config.cycle_check_interval_hours = 1
            autopilot_scheduler.config.manual_decision_timeout_hours = 1
            message = "테스트 모드가 활성화되었습니다. (1시간 간격)"
        else:
            # 일반 모드로 복원
            autopilot_scheduler.config.test_mode = False
            autopilot_scheduler.config.check_interval_hours = 24
            autopilot_scheduler.config.cycle_check_interval_hours = 6
            autopilot_scheduler.config.manual_decision_timeout_hours = 168
            message = "일반 모드로 복원되었습니다."
        
        return {
            "status": "success",
            "test_mode": enabled,
            "message": message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 모드 설정 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/abtest/autopilot/fast-cycle", summary="빠른 사이클 실행")
async def run_fast_cycle():
    """테스트용 빠른 사이클 실행 (1분 간격)"""
    try:
        # 모든 대기 중인 테스트를 즉시 처리
        processed_tests = 0
        
        # 수동 결정 타임아웃 체크
        for test_id in list(ab_test_manager.tests.keys()):
            try:
                if ab_test_manager.check_manual_decision_timeout(test_id):
                    processed_tests += 1
            except Exception as e:
                print(f"수동 결정 타임아웃 체크 오류 (test_id: {test_id}): {e}")
                continue
        
        # 장기 모니터링 완료 체크
        for test_id in list(ab_test_manager.tests.keys()):
            try:
                test = ab_test_manager.tests.get(test_id)
                if test and test.status == TestStatus.LONG_TERM_MONITORING:
                    if test.long_term_monitoring_end_date and datetime.now() >= test.long_term_monitoring_end_date:
                        ab_test_manager.complete_cycle(test_id)
                        processed_tests += 1
            except Exception as e:
                print(f"장기 모니터링 체크 오류 (test_id: {test_id}): {e}")
                continue
        
        # 자동 사이클 대기열 처리
        current_time = datetime.now()
        for test_id in list(ab_test_manager.auto_cycle_queue):
            try:
                scheduled_date = ab_test_manager.cycle_scheduler.get(test_id)
                if scheduled_date and current_time >= scheduled_date:
                    ab_test_manager.start_next_cycle(test_id)
                    processed_tests += 1
            except Exception as e:
                print(f"자동 사이클 대기열 처리 오류 (test_id: {test_id}): {e}")
                continue
        
        return {
            "status": "success",
            "processed_tests": processed_tests,
            "message": f"{processed_tests}개의 테스트가 처리되었습니다."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"빠른 사이클 실행 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/abtest/autopilot/accelerate-time", summary="시간 가속")
async def accelerate_time(hours: int = 1):
    """테스트용 시간 가속 (수동 결정 기간 단축)"""
    try:
        accelerated_tests = 0
        
        for test_id in list(ab_test_manager.tests.keys()):
            test = ab_test_manager.tests.get(test_id)
            if test and test.manual_decision_end_date:
                # 수동 결정 기간을 단축
                test.manual_decision_end_date = datetime.now() - timedelta(hours=1)
                accelerated_tests += 1
            
            if test and test.long_term_monitoring_end_date:
                # 장기 모니터링 기간을 단축
                test.long_term_monitoring_end_date = datetime.now() - timedelta(hours=1)
                accelerated_tests += 1
        
        return {
            "status": "success",
            "accelerated_tests": accelerated_tests,
            "message": f"{accelerated_tests}개의 테스트 시간이 {hours}시간 가속되었습니다."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시간 가속 중 오류가 발생했습니다: {str(e)}")

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

# 실제 서비스 연동 API 엔드포인트들

@app.post("/api/abtest/real-time/event", summary="실시간 이벤트 기록")
async def record_real_time_event(event_data: dict):
    """실제 서비스에서 발생한 이벤트를 실시간으로 기록"""
    try:
        if not real_time_tracker:
            raise HTTPException(status_code=503, detail="실시간 추적기가 초기화되지 않았습니다.")
        
        # 이벤트 ID 생성
        event_id = str(uuid.uuid4())
        
        # 이벤트 객체 생성
        event = RealTimeEvent(
            event_id=event_id,
            test_id=event_data.get('test_id'),
            variant_id=event_data.get('variant_id'),
            user_id=event_data.get('user_id'),
            session_id=event_data.get('session_id'),
            event_type=event_data.get('event_type'),
            timestamp=datetime.now(),
            page_url=event_data.get('page_url'),
            referrer=event_data.get('referrer'),
            user_agent=event_data.get('user_agent'),
            ip_address=event_data.get('ip_address'),
            revenue=event_data.get('revenue'),
            product_id=event_data.get('product_id'),
            category=event_data.get('category'),
            device_type=event_data.get('device_type'),
            browser=event_data.get('browser'),
            country=event_data.get('country'),
            city=event_data.get('city')
        )
        
        # 이벤트 기록
        await real_time_tracker.record_event(event)
        
        # 기존 A/B 테스트 시스템에도 이벤트 기록
        ab_test_manager.record_event(
            test_id=event.test_id,
            variant_id=event.variant_id,
            event_type=event.event_type,
            user_id=event.user_id,
            session_id=event.session_id,
            revenue=event.revenue
        )
        
        return {
            "status": "success",
            "event_id": event_id,
            "message": "이벤트가 성공적으로 기록되었습니다."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이벤트 기록 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/real-time/stats/{test_id}", summary="실시간 통계 조회")
async def get_real_time_stats(test_id: str):
    """실시간 통계 조회"""
    try:
        if not real_time_tracker:
            raise HTTPException(status_code=503, detail="실시간 추적기가 초기화되지 않았습니다.")
        
        stats = await real_time_tracker.get_real_time_stats(test_id)
        
        return {
            "status": "success",
            "test_id": test_id,
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"실시간 통계 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/real-time/events/{test_id}", summary="최근 이벤트 조회")
async def get_recent_events(test_id: str, limit: int = 100):
    """최근 이벤트 조회"""
    try:
        if not real_time_tracker:
            raise HTTPException(status_code=503, detail="실시간 추적기가 초기화되지 않았습니다.")
        
        events = await real_time_tracker.get_recent_events(test_id, limit)
        
        return {
            "status": "success",
            "test_id": test_id,
            "events": events,
            "count": len(events)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"최근 이벤트 조회 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/abtest/real-time/webhook", summary="웹훅 이벤트 수신")
async def receive_webhook_event(event_data: dict):
    """웹훅을 통해 실제 서비스에서 이벤트를 받음"""
    try:
        if not real_time_tracker:
            raise HTTPException(status_code=503, detail="실시간 추적기가 초기화되지 않았습니다.")
        
        # 이벤트 ID 생성
        event_id = str(uuid.uuid4())
        
        # 이벤트 객체 생성
        event = RealTimeEvent(
            event_id=event_id,
            test_id=event_data.get('test_id'),
            variant_id=event_data.get('variant_id'),
            user_id=event_data.get('user_id'),
            session_id=event_data.get('session_id'),
            event_type=event_data.get('event_type'),
            timestamp=datetime.fromisoformat(event_data.get('timestamp', datetime.now().isoformat())),
            page_url=event_data.get('page_url'),
            referrer=event_data.get('referrer'),
            user_agent=event_data.get('user_agent'),
            ip_address=event_data.get('ip_address'),
            revenue=event_data.get('revenue'),
            product_id=event_data.get('product_id'),
            category=event_data.get('category'),
            device_type=event_data.get('device_type'),
            browser=event_data.get('browser'),
            country=event_data.get('country'),
            city=event_data.get('city')
        )
        
        # 이벤트 기록
        await real_time_tracker.record_event(event)
        
        # 기존 A/B 테스트 시스템에도 이벤트 기록
        ab_test_manager.record_event(
            test_id=event.test_id,
            variant_id=event.variant_id,
            event_type=event.event_type,
            user_id=event.user_id,
            session_id=event.session_id,
            revenue=event.revenue
        )
        
        return {
            "status": "success",
            "event_id": event_id,
            "message": "웹훅 이벤트가 성공적으로 처리되었습니다."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"웹훅 이벤트 처리 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/abtest/real-time/status", summary="실시간 추적기 상태 조회")
async def get_real_time_tracker_status():
    """실시간 추적기 상태 조회"""
    try:
        if not real_time_tracker:
            return {
                "status": "inactive",
                "message": "실시간 추적기가 초기화되지 않았습니다."
            }
        
        return {
            "status": "active" if real_time_tracker.is_tracking else "inactive",
            "tracking": real_time_tracker.is_tracking,
            "kafka_connected": real_time_tracker.kafka_producer is not None,
            "storage_type": "memory",  # Redis 대신 메모리 기반
            "webhook_url": real_time_tracker.webhook_url,
            "last_update": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 조회 중 오류가 발생했습니다: {str(e)}")
