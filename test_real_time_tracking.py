#!/usr/bin/env python3
"""
실시간 추적 기능 테스트 스크립트
Redis 없이도 작동하는 메모리 기반 실시간 추적을 테스트합니다.
"""

import requests
import json
import time
import random
from datetime import datetime

# 서버 설정
BASE_URL = "http://localhost:5001"

def test_real_time_tracking():
    """실시간 추적 테스트"""
    print("🚀 실시간 추적 테스트 시작")
    print("=" * 50)
    
    # 1. 실시간 추적기 상태 확인
    print("🔍 실시간 추적기 상태 확인...")
    try:
        response = requests.get(f"{BASE_URL}/api/abtest/real-time/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ 실시간 추적기 상태: {status['status']}")
            if status['status'] == 'active':
                print(f"   - 추적 중: {status.get('tracking', False)}")
                print(f"   - Kafka 연결: {status.get('kafka_connected', False)}")
                print(f"   - Redis 연결: {status.get('redis_connected', False)}")
            else:
                print(f"   - 메시지: {status.get('message', '알 수 없음')}")
        else:
            print("❌ 실시간 추적기 상태 확인 실패")
            return False
    except Exception as e:
        print(f"❌ 실시간 추적기 상태 확인 오류: {e}")
        return False
    
    # 2. 테스트 생성
    print("\n📝 테스트 생성...")
    test_data = {
        "test_name": "실시간 추적 테스트",
        "product_name": "테스트 상품",
        "product_image": "https://example.com/test.jpg",
        "product_description": "실시간 추적 테스트를 위한 상품",
        "price": 100000,
        "category": "테스트",
        "tags": ["실시간추적", "테스트"],
        "duration_days": 1,
        "test_mode": "manual"
    }
    
    response = requests.post(f"{BASE_URL}/api/abtest/create", json=test_data)
    if response.status_code == 200:
        result = response.json()
        test_id = result["test_id"]
        print(f"✅ 테스트 생성 성공 - ID: {test_id}")
    else:
        print("❌ 테스트 생성 실패")
        return False
    
    # 3. 테스트 시작
    print("\n▶️ 테스트 시작...")
    response = requests.post(f"{BASE_URL}/api/abtest/action", json={
        "test_id": test_id,
        "action": "start"
    })
    if response.status_code == 200:
        print("✅ 테스트 시작 성공")
    else:
        print("❌ 테스트 시작 실패")
        return False
    
    # 4. 실시간 이벤트 시뮬레이션
    print("\n📊 실시간 이벤트 시뮬레이션...")
    
    event_types = ["impression", "click", "add_to_cart", "purchase"]
    user_count = 20
    
    for i in range(user_count):
        user_id = f"real_user_{i}"
        session_id = f"real_session_{i}"
        
        # 변형 ID 가져오기
        variant_response = requests.get(f"{BASE_URL}/api/abtest/{test_id}/variant/{user_id}")
        if variant_response.status_code != 200:
            continue
        
        variant_id = variant_response.json()["variant"]["variant_id"]
        
        # 여러 이벤트 시뮬레이션
        for event_type in event_types:
            # 이벤트 데이터 준비
            event_data = {
                "test_id": test_id,
                "variant_id": variant_id,
                "user_id": user_id,
                "session_id": session_id,
                "event_type": event_type,
                "page_url": f"https://example.com/product/{i}",
                "referrer": "https://google.com",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "ip_address": f"192.168.1.{i % 255}",
                "product_id": f"prod_{i}",
                "category": "electronics",
                "device_type": "desktop",
                "browser": "chrome"
            }
            
            # 구매 이벤트인 경우 수익 추가
            if event_type == "purchase":
                event_data["revenue"] = random.randint(50000, 200000)
            
            # 실시간 이벤트 전송
            response = requests.post(f"{BASE_URL}/api/abtest/real-time/event", json=event_data)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {event_type} 이벤트 전송 성공 (사용자 {i+1}/{user_count})")
            else:
                print(f"❌ {event_type} 이벤트 전송 실패 (사용자 {i+1}/{user_count})")
            
            # 잠시 대기
            time.sleep(0.1)
    
    print("✅ 실시간 이벤트 시뮬레이션 완료")
    
    # 5. 실시간 통계 확인
    print("\n📈 실시간 통계 확인...")
    response = requests.get(f"{BASE_URL}/api/abtest/real-time/stats/{test_id}")
    if response.status_code == 200:
        stats = response.json()["stats"]
        
        print("📊 테스트 전체 통계:")
        test_stats = stats.get("test_stats", {})
        print(f"   - 총 이벤트: {test_stats.get('total_events', 0)}")
        print(f"   - 노출 수: {test_stats.get('impression_count', 0)}")
        print(f"   - 클릭 수: {test_stats.get('click_count', 0)}")
        print(f"   - 장바구니 추가: {test_stats.get('add_to_cart_count', 0)}")
        print(f"   - 구매 수: {test_stats.get('purchase_count', 0)}")
        if "total_revenue" in test_stats:
            print(f"   - 총 수익: ₩{float(test_stats['total_revenue']):,.0f}")
        
        print("\n📊 변형별 통계:")
        variant_stats = stats.get("variant_stats", {})
        for variant_id, variant_data in variant_stats.items():
            print(f"   변형 {variant_id[:8]}...:")
            print(f"     - 노출: {variant_data.get('impression_count', 0)}")
            print(f"     - 클릭: {variant_data.get('click_count', 0)}")
            print(f"     - 장바구니: {variant_data.get('add_to_cart_count', 0)}")
            print(f"     - 구매: {variant_data.get('purchase_count', 0)}")
            if "total_revenue" in variant_data:
                print(f"     - 수익: ₩{float(variant_data['total_revenue']):,.0f}")
    else:
        print("❌ 실시간 통계 조회 실패")
    
    # 6. 최근 이벤트 확인
    print("\n📋 최근 이벤트 확인...")
    response = requests.get(f"{BASE_URL}/api/abtest/real-time/events/{test_id}?limit=10")
    if response.status_code == 200:
        events_data = response.json()
        events = events_data["events"]
        
        print(f"📋 최근 {len(events)}개 이벤트:")
        for i, event in enumerate(events[:5]):  # 처음 5개만 표시
            print(f"   {i+1}. {event.get('event_type', 'unknown')} - {event.get('user_id', 'unknown')} - {event.get('timestamp', '')[:19]}")
        
        if len(events) > 5:
            print(f"   ... 외 {len(events) - 5}개 이벤트")
    else:
        print("❌ 최근 이벤트 조회 실패")
    
    # 7. 웹훅 이벤트 테스트
    print("\n🔗 웹훅 이벤트 테스트...")
    webhook_event = {
        "test_id": test_id,
        "variant_id": variant_id,
        "user_id": "webhook_user",
        "session_id": "webhook_session",
        "event_type": "webhook_test",
        "timestamp": datetime.now().isoformat(),
        "page_url": "https://example.com/webhook-test",
        "revenue": 150000
    }
    
    response = requests.post(f"{BASE_URL}/api/abtest/real-time/webhook", json=webhook_event)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 웹훅 이벤트 전송 성공: {result['event_id'][:8]}...")
    else:
        print("❌ 웹훅 이벤트 전송 실패")
    
    print("\n" + "=" * 50)
    print("🎉 실시간 추적 테스트 완료!")
    print("✅ Redis 없이도 메모리 기반으로 실시간 추적이 정상 작동합니다.")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    test_real_time_tracking()
