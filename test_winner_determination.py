#!/usr/bin/env python3
"""
승자 결정 기능 테스트
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:5001"

def test_winner_determination():
    """승자 결정 기능 테스트"""
    print("🧪 승자 결정 기능 테스트 시작")
    print("=" * 50)
    
    # 1. A/B 테스트 생성
    print("1. A/B 테스트 생성 중...")
    test_data = {
        "test_name": "승자 결정 테스트",
        "product_name": "테스트 상품",
        "product_image": "https://example.com/image.jpg",
        "product_description": "승자 결정을 테스트하기 위한 상품",
        "price": 30000,  # 3만원으로 고정
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
    
    # 4. 이벤트 기록 (변형별로 다른 성과)
    print("4. 이벤트 기록 중...")
    
    # 변형 A: 높은 성과 (10번 구매)
    variant_a_id = variant_ids.get("A")
    if variant_a_id:
        for i in range(10):
            # 노출
            requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_a_id,
                "event_type": "impression",
                "user_id": f"user_a_{i}",
                "session_id": f"session_a_{i}"
            })
            
            # 클릭
            requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_a_id,
                "event_type": "click",
                "user_id": f"user_a_{i}",
                "session_id": f"session_a_{i}"
            })
            
            # 구매
            requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_a_id,
                "event_type": "conversion",
                "user_id": f"user_a_{i}",
                "session_id": f"session_a_{i}"
            })
    
    # 변형 B: 낮은 성과 (3번 구매)
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
    
    # 5. 테스트 완료 전 결과 확인
    print("5. 테스트 완료 전 결과 확인...")
    time.sleep(2)
    
    results_response = requests.get(f"{API_BASE_URL}/api/abtest/{test_id}/results")
    if results_response.status_code == 200:
        results_data = results_response.json()
        results = results_data["results"]
        
        print(f"📊 테스트 완료 전 결과:")
        print(f"  - 총 노출: {results['total_impressions']}")
        print(f"  - 총 클릭: {results['total_clicks']}")
        print(f"  - 총 전환: {results['total_conversions']}")
        print(f"  - 총 수익: ₩{results['total_revenue']:,}")
        
        if results.get('winner'):
            print(f"  - 승자: {results['winner']}")
        else:
            print("  - 승자: 아직 결정되지 않음")
    
    # 6. 테스트 완료
    print("6. 테스트 완료 중...")
    complete_response = requests.post(f"{API_BASE_URL}/api/abtest/action", json={
        "test_id": test_id,
        "action": "complete"
    })
    if complete_response.status_code != 200:
        print(f"❌ 테스트 완료 실패: {complete_response.status_code}")
        return
    
    print("✅ 테스트 완료")
    
    # 7. 테스트 완료 후 결과 확인
    print("7. 테스트 완료 후 결과 확인...")
    time.sleep(2)
    
    final_results_response = requests.get(f"{API_BASE_URL}/api/abtest/{test_id}/results")
    if final_results_response.status_code == 200:
        final_results_data = final_results_response.json()
        final_results = final_results_data["results"]
        
        print(f"\n📊 테스트 완료 후 최종 결과:")
        print(f"  - 테스트 상태: {final_results['status']}")
        print(f"  - 총 노출: {final_results['total_impressions']}")
        print(f"  - 총 클릭: {final_results['total_clicks']}")
        print(f"  - 총 전환: {final_results['total_conversions']}")
        print(f"  - 총 수익: ₩{final_results['total_revenue']:,}")
        
        if final_results.get('winner'):
            print(f"  - 🏆 승자: {final_results['winner']}")
            
            # 승자 변형의 상세 정보
            winner_variant = final_results['variants'].get(final_results['winner'])
            if winner_variant:
                print(f"    * 승자 변형 상세:")
                print(f"      - 변형 타입: {winner_variant['variant_type']}")
                print(f"      - 전환율: {winner_variant['conversion_rate']}%")
                print(f"      - CTR: {winner_variant['ctr']}%")
                print(f"      - 수익: ₩{winner_variant['revenue']:,}")
                print(f"      - 통계적 유의성: {winner_variant.get('statistical_significance', 0)}")
        else:
            print("  - ❌ 승자가 결정되지 않았습니다.")
        
        # 모든 변형의 성과 비교
        print(f"\n📈 변형별 성과 비교:")
        for variant_id, variant_result in final_results['variants'].items():
            is_winner = final_results.get('winner') == variant_id
            winner_mark = "🏆" if is_winner else ""
            print(f"  - 변형 {variant_result['variant_type']} {winner_mark}:")
            print(f"    * 전환율: {variant_result['conversion_rate']}%")
            print(f"    * CTR: {variant_result['ctr']}%")
            print(f"    * 수익: ₩{variant_result['revenue']:,}")
            print(f"    * 통계적 유의성: {variant_result.get('statistical_significance', 0)}")
    
    print("\n🎉 승자 결정 테스트 완료!")

if __name__ == "__main__":
    test_winner_determination()
