#!/usr/bin/env python3
"""
A/B 테스트 API 전체 기능 테스트 스크립트
"""

import requests
import json
import time
from datetime import datetime
import random

# API 기본 URL
BASE_URL = "http://localhost:8000/api/abtest"

def print_response(response, title):
    """응답 출력 헬퍼 함수"""
    print(f"\n=== {title} ===")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200 or response.status_code == 201:
        print("Response:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Error: {response.text}")
    print("=" * 50)

def test_create_ab_test():
    """A/B 테스트 생성 테스트"""
    print("\n🔧 A/B 테스트 생성 테스트")
    
    test_data = {
        "name": "테스트 제품 상세페이지 최적화",
        "description": "AI 생성 상세페이지의 성과 개선을 위한 A/B 테스트",
        "product_id": "PROD_001",
        "test_duration_days": 30,
        "traffic_split_ratio": 0.5,
        "min_sample_size": 1000,
        "weights": {
            "ctr": 0.3,
            "cvr": 0.4,
            "revenue": 0.3
        },
        "guardrail_metrics": {
            "bounce_rate_threshold": 0.8,
            "session_duration_min": 30
        }
    }
    
    response = requests.post(f"{BASE_URL}/", json=test_data)
    print_response(response, "A/B 테스트 생성")
    
    if response.status_code == 201:
        return response.json()["id"]
    return None

def test_list_ab_tests():
    """A/B 테스트 목록 조회 테스트"""
    print("\n📋 A/B 테스트 목록 조회 테스트")
    
    response = requests.get(f"{BASE_URL}/list")
    print_response(response, "A/B 테스트 목록 조회")
    
    if response.status_code == 200:
        data = response.json()
        return data.get("tests", []) if isinstance(data, dict) else data
    return []

def test_get_ab_test(test_id):
    """특정 A/B 테스트 조회 테스트"""
    print(f"\n🔍 A/B 테스트 {test_id} 조회 테스트")
    
    response = requests.get(f"{BASE_URL}/test/{test_id}")
    print_response(response, f"A/B 테스트 {test_id} 조회")
    
    return response.status_code == 200

def test_get_variants(test_id):
    """버전 목록 조회 테스트"""
    print(f"\n📊 A/B 테스트 {test_id} 버전 목록 조회 테스트")
    
    response = requests.get(f"{BASE_URL}/test/{test_id}/variants")
    print_response(response, f"A/B 테스트 {test_id} 버전 목록")
    
    if response.status_code == 200:
        data = response.json()
        return data.get("variants", []) if isinstance(data, dict) else data
    return []

def test_start_ab_test(test_id):
    """A/B 테스트 시작 테스트"""
    print(f"\n🚀 A/B 테스트 {test_id} 시작 테스트")
    
    response = requests.post(f"{BASE_URL}/test/{test_id}/start")
    print_response(response, f"A/B 테스트 {test_id} 시작")
    
    return response.status_code == 200

def test_log_interactions(test_id, variants):
    """상호작용 로그 기록 테스트"""
    print(f"\n📝 상호작용 로그 기록 테스트")
    
    interaction_types = ["impression", "click", "purchase", "add_to_cart", "view_detail", "bounce"]
    
    # 더 많은 로그 생성 (승자 결정을 위해)
    for i in range(50):  # 50개의 샘플 로그 생성
        variant = random.choice(variants)
        interaction_type = random.choice(interaction_types)
        
        # variant 3 (베이스라인)에 더 많은 성과를 주어 승자로 만들기
        if variant["id"] == 3:
            # 베이스라인에 더 많은 클릭과 구매
            if interaction_type in ["click", "purchase"]:
                interaction_type = random.choice(["click", "purchase", "add_to_cart"])
        else:
            # 도전자에 더 많은 이탈
            if interaction_type in ["bounce"]:
                interaction_type = "bounce"
        
        log_data = {
            "ab_test_id": test_id,
            "variant_id": variant["id"],
            "user_id": f"user_{random.randint(1000, 9999)}",
            "session_id": f"session_{random.randint(10000, 99999)}",
            "interaction_type": interaction_type,
            "interaction_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "referrer": "https://example.com"
            }
        }
        
        response = requests.post(f"{BASE_URL}/log", json=log_data)
        if response.status_code == 201:
            print(f"✅ 로그 기록 성공: {interaction_type} for variant {variant['id']}")
        else:
            print(f"❌ 로그 기록 실패: {response.text}")
        
        time.sleep(0.05)  # API 호출 간격 단축

def test_get_analytics(test_id):
    """분석 데이터 조회 테스트"""
    print(f"\n📈 A/B 테스트 {test_id} 분석 데이터 조회 테스트")
    
    response = requests.get(f"{BASE_URL}/test/{test_id}/analytics")
    print_response(response, f"A/B 테스트 {test_id} 분석 데이터")
    
    return response.status_code == 200

def test_determine_winner(test_id):
    """승자 결정 테스트"""
    print(f"\n🏆 A/B 테스트 {test_id} 승자 결정 테스트")
    
    response = requests.post(f"{BASE_URL}/test/{test_id}/determine-winner")
    print_response(response, f"A/B 테스트 {test_id} 승자 결정")
    
    return response.status_code == 200

def test_start_next_round(test_id):
    """다음 라운드 시작 테스트"""
    print(f"\n🔄 A/B 테스트 {test_id} 다음 라운드 시작 테스트")
    
    response = requests.post(f"{BASE_URL}/test/{test_id}/next-round")
    print_response(response, f"A/B 테스트 {test_id} 다음 라운드 시작")
    
    return response.status_code == 200

def test_dashboard_summary():
    """대시보드 요약 조회 테스트"""
    print("\n📊 대시보드 요약 조회 테스트")
    
    response = requests.get(f"{BASE_URL}/dashboard/summary")
    print_response(response, "대시보드 요약")
    
    return response.status_code == 200

def test_get_results(test_id):
    """테스트 결과 조회 테스트"""
    print(f"\n📋 A/B 테스트 {test_id} 결과 조회 테스트")
    
    response = requests.get(f"{BASE_URL}/test/{test_id}/results")
    print_response(response, f"A/B 테스트 {test_id} 결과")
    
    return response.status_code == 200

def main():
    """메인 테스트 실행"""
    print("🧪 A/B 테스트 API 전체 기능 테스트 시작")
    print("=" * 60)
    
    # 1. A/B 테스트 생성
    test_id = test_create_ab_test()
    if not test_id:
        print("❌ A/B 테스트 생성 실패. 테스트를 중단합니다.")
        return
    
    # 2. 테스트 목록 조회
    tests = test_list_ab_tests()
    
    # 3. 특정 테스트 조회
    test_get_ab_test(test_id)
    
    # 4. 버전 목록 조회
    variants = test_get_variants(test_id)
    
    # 5. 테스트 시작
    test_start_ab_test(test_id)
    
    # 6. 상호작용 로그 기록 (실제 사용자 행동 시뮬레이션)
    test_log_interactions(test_id, variants)
    
    # 7. 분석 데이터 조회
    test_get_analytics(test_id)
    
    # 8. 대시보드 요약 조회
    test_dashboard_summary()
    
    # 9. 승자 결정 (충분한 데이터가 있다고 가정)
    test_determine_winner(test_id)
    
    # 10. 다음 라운드 시작
    test_start_next_round(test_id)
    
    # 11. 결과 조회
    test_get_results(test_id)
    
    print("\n🎉 모든 테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
