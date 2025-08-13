#!/usr/bin/env python3
"""
실제 서비스 연동을 위한 실시간 이벤트 추적기
클릭 수, 전환 수, 구매 수 등을 실시간으로 수집합니다.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import aiohttp
import threading
import time
import uuid

logger = logging.getLogger(__name__)

@dataclass
class RealTimeEvent:
    """실시간 이벤트 데이터"""
    event_id: str
    test_id: str
    variant_id: str
    user_id: str
    session_id: str
    event_type: str  # impression, click, add_to_cart, purchase
    timestamp: datetime
    page_url: str
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    revenue: Optional[float] = None
    product_id: Optional[str] = None
    category: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None

class MemoryStorage:
    """메모리 기반 저장소 (Redis 대체)"""
    
    def __init__(self):
        self.data = {}
        self.locks = {}
    
    async def setex(self, key: str, expire_seconds: int, value: str):
        """키-값 설정 (만료 시간 포함)"""
        self.data[key] = {
            'value': value,
            'expire_at': datetime.now() + timedelta(seconds=expire_seconds)
        }
    
    async def get(self, key: str) -> Optional[str]:
        """값 조회"""
        if key not in self.data:
            return None
        
        item = self.data[key]
        if datetime.now() > item['expire_at']:
            del self.data[key]
            return None
        
        return item['value']
    
    async def hincrby(self, key: str, field: str, increment: int = 1) -> int:
        """해시 필드 증가"""
        if key not in self.data:
            self.data[key] = {}
        
        if field not in self.data[key]:
            self.data[key][field] = 0
        
        self.data[key][field] += increment
        return self.data[key][field]
    
    async def hincrbyfloat(self, key: str, field: str, increment: float = 1.0) -> float:
        """해시 필드 증가 (부동소수점)"""
        if key not in self.data:
            self.data[key] = {}
        
        if field not in self.data[key]:
            self.data[key][field] = 0.0
        
        self.data[key][field] += increment
        return self.data[key][field]
    
    async def hset(self, key: str, field: str, value: str):
        """해시 필드 설정"""
        if key not in self.data:
            self.data[key] = {}
        
        self.data[key][field] = value
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """해시 전체 조회"""
        if key not in self.data:
            return {}
        
        return self.data[key].copy()
    
    async def lpush(self, key: str, value: str):
        """리스트 앞에 추가"""
        if key not in self.data:
            self.data[key] = []
        
        self.data[key].insert(0, value)
    
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """리스트 범위 조회"""
        if key not in self.data:
            return []
        
        return self.data[key][start:end+1]
    
    async def expire(self, key: str, seconds: int):
        """만료 시간 설정"""
        # 메모리 기반이므로 만료 시간은 별도로 관리하지 않음
        pass
    
    async def scan_iter(self, match: str = None) -> List[str]:
        """키 스캔"""
        keys = list(self.data.keys())
        if match:
            # 간단한 패턴 매칭
            import re
            pattern = match.replace('*', '.*')
            keys = [k for k in keys if re.match(pattern, k)]
        return keys

class RealTimeTracker:
    """실시간 이벤트 추적기"""
    
    def __init__(self, 
                 kafka_bootstrap_servers: List[str] = None,
                 redis_host: str = 'localhost',
                 redis_port: int = 6379,
                 webhook_url: str = None):
        """
        실시간 추적기 초기화
        
        Args:
            kafka_bootstrap_servers: Kafka 서버 목록
            redis_host: Redis 호스트 (사용하지 않음)
            redis_port: Redis 포트 (사용하지 않음)
            webhook_url: 웹훅 URL (실제 서비스에서 이벤트를 받을 URL)
        """
        self.kafka_bootstrap_servers = kafka_bootstrap_servers or ['localhost:9092']
        self.webhook_url = webhook_url
        
        # Kafka 프로듀서/컨슈머 (선택적)
        self.kafka_producer = None
        self.kafka_consumer = None
        
        # 메모리 저장소 (Redis 대체)
        self.storage = MemoryStorage()
        
        # 이벤트 큐
        self.event_queue = asyncio.Queue()
        
        # 실시간 통계
        self.real_time_stats = {}
        
        # 추적 상태
        self.is_tracking = False
        self.tracking_thread = None
        
    async def initialize(self):
        """초기화"""
        try:
            # 메모리 저장소는 이미 초기화됨
            logger.info("메모리 저장소 초기화 성공")
            
            # Kafka는 선택적으로 초기화
            try:
                from kafka import KafkaProducer, KafkaConsumer
                
                # Kafka 프로듀서 초기화
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
                logger.info("Kafka 프로듀서 초기화 성공")
                
                # Kafka 컨슈머 초기화
                self.kafka_consumer = KafkaConsumer(
                    'ab_test_events',
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    group_id='real_time_tracker'
                )
                logger.info("Kafka 컨슈머 초기화 성공")
                
            except ImportError:
                logger.warning("Kafka 모듈이 설치되지 않았습니다. Kafka 기능을 사용할 수 없습니다.")
            except Exception as e:
                logger.warning(f"Kafka 초기화 실패: {e}")
            
        except Exception as e:
            logger.error(f"초기화 실패: {e}")
            raise
    
    async def start_tracking(self):
        """실시간 추적 시작"""
        if self.is_tracking:
            logger.warning("이미 추적 중입니다.")
            return
        
        self.is_tracking = True
        
        # 이벤트 처리 태스크 시작
        asyncio.create_task(self._process_events())
        
        # Kafka 메시지 수신 태스크 시작 (선택적)
        if self.kafka_consumer:
            asyncio.create_task(self._consume_kafka_messages())
        
        logger.info("실시간 추적 시작됨")
    
    async def stop_tracking(self):
        """실시간 추적 중지"""
        self.is_tracking = False
        
        if self.kafka_producer:
            self.kafka_producer.close()
        
        if self.kafka_consumer:
            self.kafka_consumer.close()
        
        logger.info("실시간 추적 중지됨")
    
    async def record_event(self, event: RealTimeEvent):
        """이벤트 기록"""
        try:
            # 이벤트 큐에 추가
            await self.event_queue.put(event)
            
            # 실시간 통계 업데이트
            await self._update_real_time_stats(event)
            
            # Kafka로 이벤트 전송 (선택적)
            if self.kafka_producer:
                self.kafka_producer.send(
                    'ab_test_events',
                    key=event.test_id,
                    value=asdict(event)
                )
            
            logger.debug(f"이벤트 기록됨: {event.event_type} - {event.test_id}")
            
        except Exception as e:
            logger.error(f"이벤트 기록 실패: {e}")
    
    async def _process_events(self):
        """이벤트 처리"""
        while self.is_tracking:
            try:
                # 이벤트 큐에서 이벤트 가져오기
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # 저장소에 이벤트 저장
                await self._save_event_to_storage(event)
                
                # 실시간 통계 업데이트
                await self._update_real_time_stats(event)
                
                # 웹훅으로 이벤트 전송 (실제 서비스 연동)
                if self.webhook_url:
                    await self._send_webhook(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"이벤트 처리 실패: {e}")
    
    async def _consume_kafka_messages(self):
        """Kafka 메시지 수신"""
        if not self.kafka_consumer:
            return
        
        try:
            for message in self.kafka_consumer:
                if not self.is_tracking:
                    break
                
                event_data = message.value
                event = RealTimeEvent(**event_data)
                
                # 실시간 통계 업데이트
                await self._update_real_time_stats(event)
                
        except Exception as e:
            logger.error(f"Kafka 메시지 수신 실패: {e}")
    
    async def _save_event_to_storage(self, event: RealTimeEvent):
        """저장소에 이벤트 저장"""
        try:
            # 이벤트 데이터를 JSON으로 저장
            event_key = f"event:{event.event_id}"
            event_data = asdict(event)
            
            await self.storage.setex(
                event_key,
                86400,  # 24시간 만료
                json.dumps(event_data, default=str)
            )
            
            # 테스트별 이벤트 목록에 추가
            test_events_key = f"test_events:{event.test_id}"
            await self.storage.lpush(test_events_key, event.event_id)
            await self.storage.expire(test_events_key, 86400)
            
        except Exception as e:
            logger.error(f"저장소 저장 실패: {e}")
    
    async def _update_real_time_stats(self, event: RealTimeEvent):
        """실시간 통계 업데이트"""
        try:
            test_key = f"stats:{event.test_id}"
            variant_key = f"stats:{event.test_id}:{event.variant_id}"
            
            # 테스트 전체 통계
            await self.storage.hincrby(test_key, f"{event.event_type}_count", 1)
            await self.storage.hincrby(test_key, "total_events", 1)
            
            # 변형별 통계
            await self.storage.hincrby(variant_key, f"{event.event_type}_count", 1)
            await self.storage.hincrby(variant_key, "total_events", 1)
            
            # 수익 통계 (구매 이벤트인 경우)
            if event.event_type == 'purchase' and event.revenue:
                await self.storage.hincrbyfloat(test_key, "total_revenue", event.revenue)
                await self.storage.hincrbyfloat(variant_key, "total_revenue", event.revenue)
            
            # 최근 이벤트 시간 업데이트
            current_time = datetime.now().isoformat()
            await self.storage.hset(test_key, "last_event_time", current_time)
            await self.storage.hset(variant_key, "last_event_time", current_time)
            
        except Exception as e:
            logger.error(f"실시간 통계 업데이트 실패: {e}")
    
    async def _send_webhook(self, event: RealTimeEvent):
        """웹훅으로 이벤트 전송"""
        if not self.webhook_url:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=asdict(event),
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status != 200:
                        logger.warning(f"웹훅 전송 실패: {response.status}")
                        
        except Exception as e:
            logger.error(f"웹훅 전송 실패: {e}")
    
    async def get_real_time_stats(self, test_id: str) -> Dict[str, Any]:
        """실시간 통계 조회"""
        try:
            test_key = f"stats:{test_id}"
            stats = await self.storage.hgetall(test_key)
            
            # 변형별 통계 조회
            variant_stats = {}
            pattern = f"stats:{test_id}:*"
            for key in await self.storage.scan_iter(match=pattern):
                variant_id = key.split(':')[-1]
                variant_data = await self.storage.hgetall(key)
                variant_stats[variant_id] = variant_data
            
            return {
                "test_stats": stats,
                "variant_stats": variant_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"실시간 통계 조회 실패: {e}")
            return {}
    
    async def get_recent_events(self, test_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """최근 이벤트 조회"""
        try:
            test_events_key = f"test_events:{test_id}"
            event_ids = await self.storage.lrange(test_events_key, 0, limit - 1)
            
            events = []
            for event_id in event_ids:
                event_key = f"event:{event_id}"
                event_data = await self.storage.get(event_key)
                if event_data:
                    events.append(json.loads(event_data))
            
            return events
            
        except Exception as e:
            logger.error(f"최근 이벤트 조회 실패: {e}")
            return []

class WebhookReceiver:
    """웹훅 수신기 (실제 서비스에서 이벤트를 받을 경우)"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.tracker = None
    
    def set_tracker(self, tracker: RealTimeTracker):
        """트래커 설정"""
        self.tracker = tracker
    
    async def start_server(self):
        """웹훅 서버 시작"""
        from aiohttp import web
        
        async def webhook_handler(request):
            try:
                data = await request.json()
                
                # 이벤트 데이터 변환
                event = RealTimeEvent(
                    event_id=data.get('event_id'),
                    test_id=data.get('test_id'),
                    variant_id=data.get('variant_id'),
                    user_id=data.get('user_id'),
                    session_id=data.get('session_id'),
                    event_type=data.get('event_type'),
                    timestamp=datetime.fromisoformat(data.get('timestamp')),
                    page_url=data.get('page_url'),
                    referrer=data.get('referrer'),
                    user_agent=data.get('user_agent'),
                    ip_address=data.get('ip_address'),
                    revenue=data.get('revenue'),
                    product_id=data.get('product_id'),
                    category=data.get('category'),
                    device_type=data.get('device_type'),
                    browser=data.get('browser'),
                    country=data.get('country'),
                    city=data.get('city')
                )
                
                # 트래커에 이벤트 전달
                if self.tracker:
                    await self.tracker.record_event(event)
                
                return web.json_response({"status": "success"})
                
            except Exception as e:
                logger.error(f"웹훅 처리 실패: {e}")
                return web.json_response({"status": "error", "message": str(e)}, status=400)
        
        app = web.Application()
        app.router.add_post('/webhook', webhook_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        
        logger.info(f"웹훅 서버 시작됨: http://localhost:{self.port}/webhook")

# 사용 예시
async def main():
    """메인 함수"""
    # 실시간 추적기 초기화
    tracker = RealTimeTracker(
        kafka_bootstrap_servers=['localhost:9092'],
        webhook_url='http://localhost:8080/webhook'
    )
    
    await tracker.initialize()
    await tracker.start_tracking()
    
    # 웹훅 수신기 시작
    webhook_receiver = WebhookReceiver(port=8080)
    webhook_receiver.set_tracker(tracker)
    await webhook_receiver.start_server()
    
    try:
        # 무한 루프로 실행
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await tracker.stop_tracking()

if __name__ == "__main__":
    asyncio.run(main())
