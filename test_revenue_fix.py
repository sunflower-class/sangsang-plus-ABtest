#!/usr/bin/env python3
"""
매출 계산 수정 테스트
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:5001"

def test_revenue_calculation():
    """매출 계산이 제대로 작동하는지 테스트"""
    print("🧪 매출 계산 수정 테스트 시작")
    print("=" * 50)
    
    # 1. A/B 테스트 생성
    print("1. A/B 테스트 생성 중...")
    test_data = {
        "test_name": "매출 계산 테스트",
        "product_name": "테스트 상품",
        "product_image": "https://example.com/image.jpg",
        "product_description": "매출 계산을 테스트하기 위한 상품",
        "price": 50000,  # 5만원으로 고정
        "category": "테스트",
        "tags": ["테스트"],
        "duration_days": 7
    }
    
    response = requests.post(f"{API_BASE_URL}/api/abtest/create", json=test_data)
    if response.status_code != 200:
        print(f"❌ 테스트 생성 실패: {response.status_code}")
        return
    
    test_result = response.json()
    test_id = test_result["test_id"]
    print(f"✅ 테스트 생성 완료: {test_id}")
    
    # 2. 테스트 시작
    print("2. 테스트 시작 중...")
    start_response = requests.post(f"{API_BASE_URL}/api/abtest/action", json={
        "test_id": test_id,
        "action": "start"
    })
    if start_response.status_code != 200:
        print(f"❌ 테스트 시작 실패: {start_response.status_code}")
        return
    
    print("✅ 테스트 시작 완료")
    
    # 3. 변형 정보 가져오기
    print("3. 변형 정보 조회 중...")
    test_detail_response = requests.get(f"{API_BASE_URL}/api/abtest/{test_id}")
    if test_detail_response.status_code != 200:
        print(f"❌ 테스트 상세 조회 실패: {test_detail_response.status_code}")
        return
    
    test_detail = test_detail_response.json()
    results = test_detail.get("results", {})
    variants = results.get("variants", {})
    
    # 변형 ID 매핑
    variant_ids = {}
    for variant_id, variant_data in variants.items():
        variant_type = variant_data.get("variant_type", "")
        variant_ids[variant_type] = variant_id
        print(f"  - 변형 {variant_type}: {variant_id}")
    
    # 4. 이벤트 기록 (올바른 변형 ID 사용)
    print("4. 이벤트 기록 중...")
    
    # 변형 A에 대한 이벤트
    variant_a_id = variant_ids.get("A")
    if variant_a_id:
        for i in range(5):  # 5번 구매
            # 노출
            requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_a_id,
                "event_type": "impression",
                "user_id": f"user_{i}",
                "session_id": f"session_{i}"
            })
            
            # 클릭
            requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_a_id,
                "event_type": "click",
                "user_id": f"user_{i}",
                "session_id": f"session_{i}"
            })
            
            # 구매 (매출은 자동으로 상품가격으로 설정됨)
            requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_a_id,
                "event_type": "conversion",
                "user_id": f"user_{i}",
                "session_id": f"session_{i}"
            })
    
    # 변형 B에 대한 이벤트 (3번 구매)
    variant_b_id = variant_ids.get("B")
    if variant_b_id:
        for i in range(3):
            # 노출
            requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_b_id,
                "event_type": "impression",
                "user_id": f"user_b_{i}",
                "session_id": f"session_b_{i}"
            })
            
            # 클릭
            requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_b_id,
                "event_type": "click",
                "user_id": f"user_b_{i}",
                "session_id": f"session_b_{i}"
            })
            
            # 구매
            requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_b_id,
                "event_type": "conversion",
                "user_id": f"user_b_{i}",
                "session_id": f"session_b_{i}"
            })
    
    print("✅ 이벤트 기록 완료")
    
    # 5. 결과 확인
    print("5. 결과 확인 중...")
    time.sleep(2)  # 잠시 대기
    
    results_response = requests.get(f"{API_BASE_URL}/api/abtest/{test_id}/results")
    if results_response.status_code != 200:
        print(f"❌ 결과 조회 실패: {results_response.status_code}")
        return
    
    results = results_response.json()
    print(f"\n🔍 결과 응답 구조:")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    results_data = results.get("results", {})
    variants = results_data.get("variants", {})
    
    print("\n📊 매출 계산 결과:")
    print("-" * 30)
    
    expected_revenue_a = 5 * 50000  # 5번 구매 × 5만원 = 25만원
    expected_revenue_b = 3 * 50000  # 3번 구매 × 5만원 = 15만원
    
    for variant_id, variant_data in variants.items():
        actual_revenue = variant_data.get("revenue", 0)
        conversions = variant_data.get("conversions", 0)
        variant_type = variant_data.get("variant_type", "")
        
        print(f"변형 {variant_type} ({variant_id[:8]}...):")
        print(f"  - 구매수: {conversions}")
        print(f"  - 실제 매출: ₩{actual_revenue:,}")
        
        if variant_type == "A":
            expected = expected_revenue_a
        elif variant_type == "B":
            expected = expected_revenue_b
        else:
            expected = 0
            
        print(f"  - 예상 매출: ₩{expected:,}")
        
        if abs(actual_revenue - expected) < 1:  # 부동소수점 오차 허용
            print(f"  ✅ 매출 계산 정확!")
        else:
            print(f"  ❌ 매출 계산 오류! 차이: ₩{abs(actual_revenue - expected):,}")
    
    total_revenue = results_data.get("total_revenue", 0)
    expected_total = expected_revenue_a + expected_revenue_b
    print(f"\n총 매출: ₩{total_revenue:,} (예상: ₩{expected_total:,})")
    
    if abs(total_revenue - expected_total) < 1:
        print("✅ 총 매출 계산 정확!")
    else:
        print(f"❌ 총 매출 계산 오류! 차이: ₩{abs(total_revenue - expected_total):,}")
    
    print("\n🎉 매출 계산 테스트 완료!")

if __name__ == "__main__":
    test_revenue_calculation()
