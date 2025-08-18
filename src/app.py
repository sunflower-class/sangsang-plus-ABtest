import os
import json
import threading
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from confluent_kafka import Producer, Consumer, KafkaException

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
    # A/B 테스트 스케줄러 시작
    from .scheduler import scheduler
    print("A/B 테스트 스케줄러 시작...")
    
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

    # A/B 테스트 스케줄러 중지
    print("A/B 테스트 스케줄러 중지...")
    scheduler.stop()
    
    if MODE != "development" and app.state.producer:
        print("Application shutdown: Flushing final messages...")
        app.state.producer.flush()
        print("Producer flushed.")
    else:
        print("Application shutdown.")

# --- FastAPI 앱 생성 ---
app = FastAPI(
    lifespan=lifespan,
    title="AI 기반 이커머스 A/B 테스트 플랫폼",
    description="AI 기반 상세 페이지 자동 생성 및 A/B 테스트 자동화 플랫폼",
    version="1.0.0"
)

# 정적 파일 서빙 설정
try:
    app.mount("/test", StaticFiles(directory="test"), name="test")
except Exception as e:
    print(f"Warning: Could not mount static files: {e}")

# A/B 테스트 API 라우터 등록은 엔드포인트 정의 후에 수행

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

# --- API 엔드포인트 ---

@app.get('/health')
def health_check():
    return {"status": "OK", "message": "AI A/B Test Platform is running!"}

@app.get('/analytics/overview')
def analytics_overview():
    return {
        "total_tests": 0,
        "active_tests": 0,
        "total_interactions": 0,
        "conversion_rate": 0.05
    }

@app.get('/scheduler/status')
def scheduler_status():
    return {
        "status": "running",
        "jobs": [],
        "last_run": "2024-01-01T00:00:00Z"
    }

@app.get('/api/abtest/list')
def abtest_list():
    """A/B 테스트 목록 조회"""
    try:
        from sqlalchemy.orm import Session
        from .database import SessionLocal
        from .models import ABTest, PerformanceLog
        
        db = SessionLocal()
        try:
            tests = db.query(ABTest).all()
            
            result = []
            for test in tests:
                # status가 이미 문자열인지 확인
                status_value = test.status.value if hasattr(test.status, 'value') else str(test.status)
                
                # 해당 테스트의 변형들에서 새로운 지표 집계
                from .models import Variant
                variants = db.query(Variant).filter(Variant.ab_test_id == test.id).all()
                
                total_detail_views = sum(v.detail_page_views for v in variants)
                total_clicks = sum(v.clicks for v in variants)
                total_purchases = sum(v.purchases for v in variants)
                total_unique_viewers = sum(v.unique_detail_viewers for v in variants)
                total_unique_purchasers = sum(v.unique_purchasers for v in variants)
                
                # A/B 버전별 통계 계산 (간단화)
                baseline_variant = next((v for v in variants if v.variant_type == 'baseline'), None)
                challenger_variant = next((v for v in variants if v.variant_type == 'challenger'), None)
                
                baseline_detail_views = baseline_variant.detail_page_views if baseline_variant else 0
                baseline_unique_purchasers = baseline_variant.unique_purchasers if baseline_variant else 0
                challenger_detail_views = challenger_variant.detail_page_views if challenger_variant else 0
                challenger_unique_purchasers = challenger_variant.unique_purchasers if challenger_variant else 0
                
                result.append({
                    "id": test.id,
                    "name": test.name,
                    "status": status_value,
                    "created_at": test.created_at.isoformat(),
                    "product_id": test.product_id,
                    # 새로운 지표들
                    "total_detail_views": total_detail_views,
                    "total_clicks": total_clicks,
                    "total_purchases": total_purchases,
                    "total_unique_viewers": total_unique_viewers,
                    "total_unique_purchasers": total_unique_purchasers,
                    # A/B 버전별 데이터
                    "baseline_detail_views": baseline_detail_views,
                    "baseline_unique_purchasers": baseline_unique_purchasers,
                    "challenger_detail_views": challenger_detail_views,
                    "challenger_unique_purchasers": challenger_unique_purchasers,
                    "baseline_description": "기존 버전",
                    "challenger_description": "AI 생성 버전"
                })
            
            print(f"Found {len(result)} tests in database")
            return {"tests": result}
        finally:
            db.close()
    except Exception as e:
        print(f"Error in abtest_list: {e}")
        import traceback
        traceback.print_exc()
        return []

@app.get('/api/abtest/results')
def abtest_results():
    """A/B 테스트 결과 조회"""
    try:
        from sqlalchemy.orm import Session
        from .database import SessionLocal
        from .models import TestResult
        
        db = SessionLocal()
        try:
            results = db.query(TestResult).all()
            
            result = []
            for res in results:
                result.append({
                    "id": res.id,
                    "test_id": res.ab_test_id,
                    "winner_variant_id": res.winner_variant_id,
                    "winner_score": float(res.winner_score) if res.winner_score else 0.0,
                    "total_impressions": res.total_impressions,
                    "total_clicks": res.total_clicks,
                    "total_purchases": res.total_purchases,
                    "total_revenue": float(res.total_revenue) if res.total_revenue else 0.0,
                    "p_value": float(res.p_value) if res.p_value else 0.0,
                    "confidence_level": float(res.confidence_level) if res.confidence_level else 0.0,
                    "created_at": res.created_at.isoformat() if res.created_at else None
                })
            
            print(f"Found {len(result)} results in database")
            return {"results": result}
        finally:
            db.close()
    except Exception as e:
        print(f"Error in abtest_results: {e}")
        import traceback
        traceback.print_exc()
        return []

@app.get('/api/abtest/logs')
def abtest_logs():
    """A/B 테스트 로그 조회"""
    try:
        from sqlalchemy.orm import Session
        from .database import SessionLocal
        from .models import PerformanceLog
        
        db = SessionLocal()
        logs = db.query(PerformanceLog).order_by(PerformanceLog.timestamp.desc()).limit(50).all()
        
        result = []
        for log in logs:
            result.append({
                "timestamp": log.timestamp.isoformat(),
                "level": "info",
                "message": f"상호작용 기록: {log.interaction_type} - 테스트 {log.ab_test_id}"
            })
        
        db.close()
        return {"logs": result}
    except Exception as e:
        print(f"Error in abtest_logs: {e}")
        return []

@app.get('/api/abtest/analytics/performance')
def abtest_performance():
    """A/B 테스트 성과 데이터 (새로운 지표 체계)"""
    try:
        from sqlalchemy.orm import Session
        from .database import SessionLocal
        from .models import ABTest, PerformanceLog, Variant
        from sqlalchemy import func
        import numpy as np
        
        db = SessionLocal()
        try:
            tests = db.query(ABTest).all()
            
            result = []
            for test in tests:
                # status가 이미 문자열인지 확인
                status_value = test.status.value if hasattr(test.status, 'value') else str(test.status)
                
                # 테스트의 변형들 가져오기
                variants = db.query(Variant).filter(Variant.ab_test_id == test.id).all()
                
                baseline_variant = None
                challenger_variant = None
                
                for variant in variants:
                    if variant.variant_type == 'baseline':
                        baseline_variant = variant
                    elif variant.variant_type == 'challenger':
                        challenger_variant = variant
                
                if not baseline_variant or not challenger_variant:
                    continue
                
                # 새로운 지표 계산
                # A안 (baseline) 지표
                baseline_cvr_detail = baseline_variant.unique_purchasers / max(baseline_variant.unique_detail_viewers, 1)
                baseline_cvr_click = baseline_variant.purchases / max(baseline_variant.clicks, 1)
                baseline_cart_rate = baseline_variant.unique_cart_adders / max(baseline_variant.unique_detail_viewers, 1)
                baseline_avg_session = baseline_variant.total_session_duration / max(baseline_variant.session_count, 1)
                baseline_bounce_rate = baseline_variant.bounced_sessions / max(baseline_variant.session_count, 1)
                baseline_load_time = np.mean(baseline_variant.page_load_times) if baseline_variant.page_load_times else 0
                
                # B안 (challenger) 지표
                challenger_cvr_detail = challenger_variant.unique_purchasers / max(challenger_variant.unique_detail_viewers, 1)
                challenger_cvr_click = challenger_variant.purchases / max(challenger_variant.clicks, 1)
                challenger_cart_rate = challenger_variant.unique_cart_adders / max(challenger_variant.unique_detail_viewers, 1)
                challenger_avg_session = challenger_variant.total_session_duration / max(challenger_variant.session_count, 1)
                challenger_bounce_rate = challenger_variant.bounced_sessions / max(challenger_variant.session_count, 1)
                challenger_load_time = np.mean(challenger_variant.page_load_times) if challenger_variant.page_load_times else 0
                
                # 승자 결정 (핵심 지표인 CVR_detail_to_purchase 기준)
                winner = "baseline" if baseline_cvr_detail > challenger_cvr_detail else "challenger" if challenger_cvr_detail > baseline_cvr_detail else "tie"
                improvement_rate = round(((challenger_cvr_detail - baseline_cvr_detail) / baseline_cvr_detail * 100) if baseline_cvr_detail > 0 else 0, 1)
                
                result.append({
                    "product_name": test.name,
                    "status": status_value,
                    "test_id": test.id,
                    # A안 새로운 지표
                    "baseline_detail_views": baseline_variant.unique_detail_viewers,
                    "baseline_clicks": baseline_variant.clicks,
                    "baseline_purchases": baseline_variant.unique_purchasers,
                    "baseline_cart_adds": baseline_variant.unique_cart_adders,
                    "baseline_cvr_detail": round(baseline_cvr_detail, 3),
                    "baseline_cvr_click": round(baseline_cvr_click, 3),
                    "baseline_cart_rate": round(baseline_cart_rate, 3),
                    "baseline_avg_session": round(baseline_avg_session, 1),
                    "baseline_bounce_rate": round(baseline_bounce_rate, 3),
                    "baseline_load_time": round(baseline_load_time, 2),
                    # B안 새로운 지표
                    "challenger_detail_views": challenger_variant.unique_detail_viewers,
                    "challenger_clicks": challenger_variant.clicks,
                    "challenger_purchases": challenger_variant.unique_purchasers,
                    "challenger_cart_adds": challenger_variant.unique_cart_adders,
                    "challenger_cvr_detail": round(challenger_cvr_detail, 3),
                    "challenger_cvr_click": round(challenger_cvr_click, 3),
                    "challenger_cart_rate": round(challenger_cart_rate, 3),
                    "challenger_avg_session": round(challenger_avg_session, 1),
                    "challenger_bounce_rate": round(challenger_bounce_rate, 3),
                    "challenger_load_time": round(challenger_load_time, 2),
                    # 전체 및 승자 정보
                    "total_detail_views": baseline_variant.unique_detail_viewers + challenger_variant.unique_detail_viewers,
                    "total_clicks": baseline_variant.clicks + challenger_variant.clicks,
                    "total_purchases": baseline_variant.unique_purchasers + challenger_variant.unique_purchasers,
                    "total_revenue": baseline_variant.revenue + challenger_variant.revenue,
                    "winner": winner,
                    "improvement_rate": improvement_rate
                })
            
            print(f"Found {len(result)} performance data in database")
            return {"performance": result}
        finally:
            db.close()
    except Exception as e:
        print(f"Error in abtest_performance: {e}")
        import traceback
        traceback.print_exc()
        return []

@app.get('/api/abtest/interaction')
def abtest_interaction():
    """A/B 테스트 상호작용 조회"""
    return {"status": "success", "interactions": []}

@app.post('/api/abtest/interaction')
def abtest_interaction_post(interaction: dict):
    """A/B 테스트 상호작용 기록"""
    try:
        from sqlalchemy.orm import Session
        from .database import SessionLocal
        from .models import PerformanceLog, Variant
        from datetime import datetime
        import json
        
        db = SessionLocal()
        try:
            test_id = interaction.get('test_id')
            variant_type = interaction.get('variant')
            interaction_type = interaction.get('interaction_type', 'view')
            
            # 실제 variant ID 조회
            variant = db.query(Variant).filter(
                Variant.ab_test_id == test_id,
                Variant.variant_type == variant_type
            ).first()
            
            if not variant:
                return {"status": "error", "message": f"Variant not found for test {test_id}, type {variant_type}"}
            
            variant_id = variant.id
            
            # 상호작용 로그 생성
            log = PerformanceLog(
                ab_test_id=test_id,
                variant_id=variant_id,
                user_id=f"simulator_{datetime.utcnow().timestamp()}",
                session_id=f"session_simulator_{test_id}",
                interaction_type=interaction_type,
                interaction_metadata=json.dumps(interaction),
                timestamp=datetime.utcnow()
            )
            
            db.add(log)
            
            # Variant 테이블의 새로운 지표 업데이트
            if interaction_type == 'view_detail':
                variant.detail_page_views += 1
                variant.unique_detail_viewers += 1  # 간단화 (실제로는 중복 제거 필요)
            elif interaction_type == 'click':
                variant.clicks += 1
            elif interaction_type == 'purchase':
                variant.purchases += 1
                variant.unique_purchasers += 1  # 간단화
                # 구매 시 수익 추가 (테스트용으로 1000원 고정)
                variant.revenue += 1000
            elif interaction_type == 'add_to_cart':
                variant.add_to_carts += 1
                variant.unique_cart_adders += 1  # 간단화
            elif interaction_type == 'session_start':
                variant.session_count += 1
            elif interaction_type == 'session_end':
                # 메타데이터에서 세션 지속시간 추출
                metadata = json.loads(interaction.get('metadata', '{}'))
                session_duration = metadata.get('session_duration', 30)  # 기본값 30초
                variant.total_session_duration += session_duration
            elif interaction_type == 'bounce':
                variant.bounced_sessions += 1
            elif interaction_type == 'page_load':
                # 페이지 로드 시간 기록
                metadata = json.loads(interaction.get('metadata', '{}'))
                load_time = metadata.get('load_time', 1.5)  # 기본값 1.5초
                if variant.page_load_times is None:
                    variant.page_load_times = []
                variant.page_load_times.append(load_time)
            elif interaction_type == 'error':
                variant.error_count += 1
            
            db.commit()
            
            print(f"Interaction logged: {interaction_type} for test {test_id} variant {variant_type} (ID: {variant_id})")
            return {"status": "success", "log_id": log.id}
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    except Exception as e:
        print(f"Error in abtest_interaction_post: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.post('/api/abtest/test/{test_id}/reset')
def reset_test_data(test_id: int):
    """특정 테스트의 상호작용 데이터 초기화"""
    try:
        from sqlalchemy.orm import Session
        from .database import SessionLocal
        from .models import PerformanceLog
        
        db = SessionLocal()
        try:
            # 해당 테스트의 모든 PerformanceLog 삭제
            deleted_count = db.query(PerformanceLog).filter(PerformanceLog.ab_test_id == test_id).delete()
            db.commit()
            
            print(f"Reset test {test_id}: deleted {deleted_count} interaction logs")
            return {"status": "success", "message": f"테스트 ID {test_id}의 {deleted_count}개 상호작용 데이터가 삭제되었습니다."}
        finally:
            db.close()
    except Exception as e:
        print(f"Error in reset_test_data: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.get('/api/abtest/test/{test_id}/variants')
def get_test_variants(test_id: int):
    """테스트의 버전 목록 조회"""
    try:
        from sqlalchemy.orm import Session
        from .database import SessionLocal
        from .models import Variant
        
        db = SessionLocal()
        try:
            variants = db.query(Variant).filter(Variant.ab_test_id == test_id).all()
            
            result = []
            for variant in variants:
                # 새로운 지표 계산
                cvr_detail_to_purchase = variant.unique_purchasers / max(variant.unique_detail_viewers, 1)
                cvr_click_to_purchase = variant.purchases / max(variant.clicks, 1)
                cart_add_rate = variant.unique_cart_adders / max(variant.unique_detail_viewers, 1)
                avg_session_duration = variant.total_session_duration / max(variant.session_count, 1)
                bounce_rate = variant.bounced_sessions / max(variant.session_count, 1)
                
                import numpy as np
                avg_page_load_time = np.mean(variant.page_load_times) if variant.page_load_times else 0
                error_rate = variant.error_count / max(variant.detail_page_views, 1)
                
                result.append({
                    "id": variant.id,
                    "name": variant.name,
                    "content": variant.content,
                    "is_active": variant.is_active,
                    "is_winner": variant.is_winner,
                    # 새로운 지표들
                    "detail_page_views": variant.detail_page_views,
                    "clicks": variant.clicks,
                    "purchases": variant.purchases,
                    "add_to_carts": variant.add_to_carts,
                    "revenue": float(variant.revenue) if variant.revenue else 0.0,
                    "unique_detail_viewers": variant.unique_detail_viewers,
                    "unique_purchasers": variant.unique_purchasers,
                    "unique_cart_adders": variant.unique_cart_adders,
                    "session_count": variant.session_count,
                    "bounced_sessions": variant.bounced_sessions,
                    "total_session_duration": float(variant.total_session_duration),
                    "error_count": variant.error_count,
                    # 계산된 지표들
                    "cvr_detail_to_purchase": cvr_detail_to_purchase,
                    "cvr_click_to_purchase": cvr_click_to_purchase,
                    "cart_add_rate": cart_add_rate,
                    "avg_session_duration": avg_session_duration,
                    "bounce_rate": bounce_rate,
                    "avg_page_load_time": avg_page_load_time,
                    "error_rate": error_rate
                })
            
            print(f"Found {len(result)} variants for test {test_id}")
            return {"variants": result}
        finally:
            db.close()
    except Exception as e:
        print(f"Error in get_test_variants: {e}")
        import traceback
        traceback.print_exc()
        return {"variants": []}

@app.delete('/api/abtest/test/{test_id}')
def delete_test(test_id: int):
    """테스트 완전 삭제 (테스트와 관련된 모든 데이터 삭제)"""
    try:
        from sqlalchemy.orm import Session
        from .database import SessionLocal
        from .models import ABTest, PerformanceLog, Variant, TestResult
        
        db = SessionLocal()
        try:
            # 테스트 존재 확인
            test = db.query(ABTest).filter(ABTest.id == test_id).first()
            if not test:
                return {"status": "error", "message": f"테스트 ID {test_id}를 찾을 수 없습니다."}
            
            test_name = test.name
            
            # 관련 데이터 삭제 (CASCADE로 자동 삭제됨)
            # 1. PerformanceLog 삭제
            deleted_logs = db.query(PerformanceLog).filter(PerformanceLog.ab_test_id == test_id).delete()
            
            # 2. TestResult 삭제
            deleted_results = db.query(TestResult).filter(TestResult.ab_test_id == test_id).delete()
            
            # 3. Variant 삭제
            deleted_variants = db.query(Variant).filter(Variant.ab_test_id == test_id).delete()
            
            # 4. ABTest 삭제
            db.delete(test)
            
            db.commit()
            
            print(f"Deleted test {test_id} ({test_name}): {deleted_logs} logs, {deleted_results} results, {deleted_variants} variants")
            return {
                "status": "success", 
                "message": f"테스트 '{test_name}' (ID: {test_id})가 완전히 삭제되었습니다.",
                "deleted_data": {
                    "logs": deleted_logs,
                    "results": deleted_results,
                    "variants": deleted_variants
                }
            }
        finally:
            db.close()
    except Exception as e:
        print(f"Error in delete_test: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.delete('/api/abtest/cleanup')
def cleanup_old_tests():
    """오래된 테스트들 정리 (7일 이상 된 완료된 테스트)"""
    try:
        from sqlalchemy.orm import Session
        from .database import SessionLocal
        from .models import ABTest
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        try:
            # 7일 전 날짜 계산
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            # 7일 이상 된 완료된 테스트들 찾기
            old_tests = db.query(ABTest).filter(
                ABTest.status == 'completed',
                ABTest.updated_at < cutoff_date
            ).all()
            
            deleted_count = 0
            for test in old_tests:
                # delete_test 함수 재사용
                result = delete_test(test.id)
                if result.get("status") == "success":
                    deleted_count += 1
            
            return {
                "status": "success",
                "message": f"{deleted_count}개의 오래된 테스트가 정리되었습니다.",
                "deleted_count": deleted_count
            }
        finally:
            db.close()
    except Exception as e:
        print(f"Error in cleanup_old_tests: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.get('/python')
def running_test():
    return "python API is running!"

@app.get('/test-db')
def test_database():
    """데이터베이스 연결 테스트"""
    try:
        from sqlalchemy.orm import Session
        from .database import SessionLocal
        from .models import ABTest
        
        db = SessionLocal()
        try:
            count = db.query(ABTest).count()
            return {"status": "success", "test_count": count, "message": f"데이터베이스에 {count}개의 테스트가 있습니다"}
        finally:
            db.close()
    except Exception as e:
        return {"status": "error", "message": str(e)}

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


# A/B 테스트 API 라우터 등록 (엔드포인트 정의 후에 수행)
from .abtest_api import router as abtest_router
app.include_router(abtest_router)

# --- 메인 실행 (미사용) ---
if __name__ == '__main__':
    uvicorn.run(
        "main:app", 
        host='0.0.0.0', 
        port=5001, 
        reload=(MODE != "kubernetes")
    )
