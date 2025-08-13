#!/usr/bin/env python3
"""
빠른 자동화 테스트 스크립트
6시간 기다리지 않고 빠르게 자동화를 테스트합니다.
"""

import requests
import json
import time
import random
from datetime import datetime, timedelta

# 서버 설정
BASE_URL = "http://localhost:5001"

def test_quick_automation():
    """빠른 자동화 테스트"""
    print("🚀 빠른 자동화 테스트 시작")
    print("=" * 50)
    
    # 1. 테스트 모드 활성화
    print("🔧 테스트 모드 활성화...")
    response = requests.post(f"{BASE_URL}/api/abtest/autopilot/test-mode", params={"enabled": True})
    if response.status_code == 200:
        print("✅ 테스트 모드 활성화 성공 (1시간 간격)")
    else:
        print("❌ 테스트 모드 활성화 실패")
        return False
    
    # 2. 수동으로 실험 생성 (자동 생성 대신)
    print("\n🤖 수동 실험 생성...")
    experiment_brief = {
        "objective": "빠른 테스트 - CVR 최대화",
        "primary_metrics": ["CVR"],
        "secondary_metrics": ["CTR", "ATC"],
        "guardrails": {"LCP": 3.5, "error_rate": 0.005},
        "target_categories": ["스마트폰"],
        "target_channels": ["web", "mobile"],
        "target_devices": ["desktop", "mobile"],
        "exclude_conditions": [],
        "variant_count": 3,
        "distribution_mode": "equal",
        "mde": 0.1,
        "min_sample_size": 50,
        "decision_mode": "auto",
        "manual_decision_period_days": 1,
        "long_term_monitoring_days": 7
    }

    test_data = {
        "test_name": "빠른 자동화 테스트",
        "product_name": "빠른 테스트 상품",
        "product_image": "https://example.com/quick-test.jpg",
        "product_description": "빠른 자동화 테스트를 위한 상품",
        "price": 1000000,
        "category": "스마트폰",
        "tags": ["빠른테스트", "자동화"],
        "duration_days": 1,
        "experiment_brief": experiment_brief,
        "test_mode": "autopilot"
    }

    response = requests.post(f"{BASE_URL}/api/abtest/create-with-brief", json=test_data)
    if response.status_code == 200:
        result = response.json()
        test_id = result["test_id"]
        print(f"✅ 실험 생성 성공 - 테스트 ID: {test_id}")
    else:
        print("❌ 실험 생성 실패")
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
    
    # 4. 이벤트 시뮬레이션
    print("\n📊 이벤트 시뮬레이션...")
    for i in range(10):  # 10명의 사용자
        user_id = f"quick_user_{i}"
        session_id = f"quick_session_{i}"
        
        # 변형 선택
        variant_response = requests.get(f"{BASE_URL}/api/abtest/{test_id}/variant/{user_id}")
        if variant_response.status_code == 200:
            variant_id = variant_response.json()["variant"]["variant_id"]
        else:
            continue
        
        # 노출 이벤트
        requests.post(f"{BASE_URL}/api/abtest/event", json={
            "test_id": test_id,
            "variant_id": variant_id,
            "event_type": "impression",
            "user_id": user_id,
            "session_id": session_id
        })
        
        # 클릭 이벤트 (60% 확률)
        if random.random() < 0.6:
            requests.post(f"{BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_id,
                "event_type": "click",
                "user_id": user_id,
                "session_id": session_id
            })
            
            # 전환 이벤트 (25% 확률)
            if random.random() < 0.25:
                requests.post(f"{BASE_URL}/api/abtest/event", json={
                    "test_id": test_id,
                    "variant_id": variant_id,
                    "event_type": "conversion",
                    "user_id": user_id,
                    "session_id": session_id,
                    "revenue": 1000000
                })
    
    print("✅ 이벤트 시뮬레이션 완료")
    
    # 5. 테스트 완료
    print("\n🏁 테스트 완료...")
    response = requests.post(f"{BASE_URL}/api/abtest/action", json={
        "test_id": test_id,
        "action": "complete"
    })
    if response.status_code == 200:
        print("✅ 테스트 완료 처리 성공")
    else:
        print("❌ 테스트 완료 처리 실패")
        return False
    
    # 6. 시간 가속
    print("\n⏰ 시간 가속...")
    response = requests.post(f"{BASE_URL}/api/abtest/autopilot/accelerate-time", params={"hours": 1})
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['accelerated_tests']}개 테스트 시간 가속됨")
    else:
        print("❌ 시간 가속 실패")
    
    # 7. 빠른 사이클 실행
    print("\n🔄 빠른 사이클 실행...")
    response = requests.post(f"{BASE_URL}/api/abtest/autopilot/fast-cycle")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['processed_tests']}개 테스트 처리됨")
    else:
        print("❌ 빠른 사이클 실행 실패")
    
    # 8. 결과 확인
    print("\n📊 결과 확인...")
    response = requests.get(f"{BASE_URL}/api/abtest/{test_id}/results")
    if response.status_code == 200:
        results = response.json()["results"]
        winner = results.get("winner")
        if winner:
            print(f"✅ 승자 선택됨: {winner}")
        else:
            print("⚠️ 승자 선택 대기 중")
        
        # 전체 통계
        print(f"📈 전체 통계:")
        print(f"   - 총 노출: {results['total_impressions']}")
        print(f"   - 총 클릭: {results['total_clicks']}")
        print(f"   - 총 전환: {results['total_conversions']}")
        print(f"   - 총 수익: ₩{results['total_revenue']:,.0f}")
    else:
        print("❌ 결과 조회 실패")
    
    # 9. 최종 상태 확인
    print("\n🔍 최종 상태 확인...")
    response = requests.get(f"{BASE_URL}/api/abtest/autopilot/status")
    if response.status_code == 200:
        status = response.json()["autopilot_status"]
        print(f"✅ 최종 상태:")
        print(f"   - 활성 테스트: {status['active_tests_count']}개")
        print(f"   - 완료된 테스트: {status['completed_tests_count']}개")
        print(f"   - 자동 사이클 대기열: {status['auto_cycle_queue_size']}개")
        print(f"   - 테스트 모드: {'활성' if status.get('config', {}).get('test_mode') else '비활성'}")
    
    print("\n" + "=" * 50)
    print("🎉 빠른 자동화 테스트 완료!")
    print("✅ 6시간 기다리지 않고 자동화를 테스트했습니다.")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    test_quick_automation()
