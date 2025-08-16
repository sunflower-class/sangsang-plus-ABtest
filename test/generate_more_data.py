#!/usr/bin/env python3
"""
더 많은 상호작용 데이터를 생성하여 승자 결정 테스트
"""

import requests
import json
import time
import random
from datetime import datetime

BASE_URL = "http://localhost:8000/api/abtest"

def generate_more_data():
    """더 많은 상호작용 데이터 생성"""
    print("📝 더 많은 상호작용 데이터 생성")
    
    # 테스트 목록 조회
    response = requests.get(f"{BASE_URL}/")
    if response.status_code != 200:
        print("❌ 테스트 목록 조회 실패")
        return None
    
    tests = response.json()["tests"]
    if not tests:
        print("❌ 생성된 테스트가 없습니다")
        return None
    
    # 가장 최근 테스트 선택
    latest_test = tests[-1]
    test_id = latest_test["id"]
    
    # 버전 목록 조회
    response = requests.get(f"{BASE_URL}/{test_id}/variants")
    if response.status_code != 200:
        print("❌ 버전 목록 조회 실패")
        return None
    
    variants = response.json()
    print(f"테스트 ID: {test_id}")
    print(f"버전 수: {len(variants)}")
    
    # 더 많은 데이터 생성 (200개)
    interaction_types = ["impression", "click", "purchase", "add_to_cart", "view_detail", "bounce"]
    
    for i in range(200):
        variant = random.choice(variants)
        interaction_type = random.choice(interaction_types)
        
        # 베이스라인(variant 5)에 더 나은 성과를 주기
        if variant["id"] == 5:  # 베이스라인
            # 베이스라인에 더 많은 클릭과 구매, 적은 이탈
            if random.random() < 0.6:  # 60% 확률로 좋은 상호작용
                interaction_type = random.choice(["click", "purchase", "add_to_cart", "view_detail"])
        else:  # 도전자
            # 도전자에 더 많은 이탈
            if random.random() < 0.4:  # 40% 확률로 이탈
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
            if i % 50 == 0:  # 50개마다 진행상황 출력
                print(f"✅ {i+1}/200 로그 기록 완료")
        else:
            print(f"❌ 로그 기록 실패: {response.text}")
        
        time.sleep(0.02)  # 빠른 생성
    
    print("✅ 모든 데이터 생성 완료!")
    return test_id

def check_winner_determination(test_id):
    """승자 결정 확인"""
    print(f"\n🏆 승자 결정 확인 (테스트 ID: {test_id})")
    
    # 분석 데이터 확인
    response = requests.get(f"{BASE_URL}/{test_id}/analytics")
    if response.status_code == 200:
        analytics = response.json()
        print(f"\n📊 최종 분석 결과:")
        print(f"총 노출: {analytics['total_impressions']}")
        print(f"총 클릭: {analytics['total_clicks']}")
        print(f"총 구매: {analytics['total_purchases']}")
        
        for variant in analytics['variants']:
            print(f"\n{variant['variant_name']}:")
            print(f"  - 노출: {variant['impressions']}")
            print(f"  - 클릭: {variant['clicks']}")
            print(f"  - 구매: {variant['purchases']}")
            print(f"  - CTR: {variant['ctr']:.4f}")
            print(f"  - CVR: {variant['cvr']:.4f}")
            print(f"  - 점수: {variant['score']:.4f}")
    
    # 승자 결정
    response = requests.post(f"{BASE_URL}/{test_id}/determine-winner")
    if response.status_code == 200:
        result = response.json()
        print(f"\n🏆 승자 결정 결과:")
        print(f"성공: {result['success']}")
        print(f"메시지: {result['message']}")
        if result['success']:
            print(f"승자 ID: {result['winner_variant_id']}")
            
            # 다음 라운드 시작
            print(f"\n🔄 다음 라운드 시작:")
            response = requests.post(f"{BASE_URL}/{test_id}/next-round")
            if response.status_code == 200:
                result = response.json()
                print(f"결과: {result['message']}")
            else:
                print("❌ 다음 라운드 시작 실패")
    else:
        print("❌ 승자 결정 실패")

if __name__ == "__main__":
    test_id = generate_more_data()
    if test_id:
        check_winner_determination(test_id)
