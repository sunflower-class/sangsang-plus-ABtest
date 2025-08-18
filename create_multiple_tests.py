#!/usr/bin/env python3
"""
다양한 AB테스트 생성 스크립트 - 사용자가 선택할 수 있는 여러 테스트 생성
"""

import requests
import json
import time
import random
from datetime import datetime

BASE_URL = "http://localhost:8000/api/abtest"

def create_test(test_data):
    """AB테스트 생성"""
    response = requests.post(f"{BASE_URL}/", json=test_data)
    if response.status_code == 201:
        test_info = response.json()
        print(f"✅ 테스트 생성 성공: {test_info['name']} (ID: {test_info['id']})")
        return test_info['id']
    else:
        print(f"❌ 테스트 생성 실패: {response.text}")
        return None

def add_sample_interactions(test_id, num_interactions=30):
    """테스트에 샘플 상호작용 추가"""
    print(f"📝 테스트 {test_id}에 {num_interactions}개 상호작용 추가 중...")
    
    # 버전 목록 조회
    response = requests.get(f"{BASE_URL}/test/{test_id}/variants")
    if response.status_code != 200:
        print(f"❌ 버전 조회 실패: {test_id}")
        return
    
    variants_data = response.json()
    variants = variants_data.get("variants", [])
    if not variants:
        print(f"❌ 버전이 없습니다: {test_id}")
        return
    
    interaction_types = ["impression", "click", "purchase", "add_to_cart", "view_detail", "bounce"]
    
    for i in range(num_interactions):
        variant = random.choice(variants)
        interaction_type = random.choice(interaction_types)
        
        # 랜덤하게 성과 차이를 만들어줌
        if variant["name"] == "A안 (베이스라인)" and random.random() < 0.4:
            interaction_type = random.choice(["click", "purchase", "add_to_cart"])
        elif variant["name"] == "B안 (도전자)" and random.random() < 0.3:
            interaction_type = random.choice(["bounce", "impression"])
        
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
            if i % 10 == 0:
                print(f"  📊 {i+1}/{num_interactions} 완료")
        
        time.sleep(0.01)  # 빠른 생성
    
    print(f"✅ 테스트 {test_id} 상호작용 데이터 추가 완료!")

def main():
    """다양한 AB테스트들 생성"""
    print("🧪 다양한 AB테스트 생성 시작")
    print("=" * 60)
    
    # 테스트 데이터들
    test_configs = [
        {
            "name": "프리미엄 무선이어폰 상세페이지 최적화",
            "description": "고급 무선이어폰의 제품 설명과 이미지 배치 최적화",
            "product_id": "ELECTRONICS_001",
            "test_duration_days": 14,
            "traffic_split_ratio": 0.5,
            "min_sample_size": 500,
            "weights": {"ctr": 0.4, "cvr": 0.4, "revenue": 0.2},
            "guardrail_metrics": {"bounce_rate_threshold": 0.7, "session_duration_min": 45}
        },
        {
            "name": "여성 겨울 코트 컬렉션 페이지 테스트",
            "description": "계절 의류 상품의 색상 표시 방식과 사이즈 가이드 개선",
            "product_id": "FASHION_002",
            "test_duration_days": 21,
            "traffic_split_ratio": 0.5,
            "min_sample_size": 800,
            "weights": {"ctr": 0.3, "cvr": 0.5, "revenue": 0.2},
            "guardrail_metrics": {"bounce_rate_threshold": 0.6, "session_duration_min": 60}
        },
        {
            "name": "프리미엄 스킨케어 세트 판매 페이지",
            "description": "고가 화장품의 성분 설명과 사용법 동영상 배치 테스트",
            "product_id": "BEAUTY_003",
            "test_duration_days": 28,
            "traffic_split_ratio": 0.5,
            "min_sample_size": 1200,
            "weights": {"ctr": 0.2, "cvr": 0.6, "revenue": 0.2},
            "guardrail_metrics": {"bounce_rate_threshold": 0.5, "session_duration_min": 90}
        },
        {
            "name": "스마트 홈 IoT 디바이스 번들 상품",
            "description": "복합 기술 제품의 설치 가이드와 호환성 정보 표시 개선",
            "product_id": "TECH_004",
            "test_duration_days": 35,
            "traffic_split_ratio": 0.5,
            "min_sample_size": 600,
            "weights": {"ctr": 0.3, "cvr": 0.4, "revenue": 0.3},
            "guardrail_metrics": {"bounce_rate_threshold": 0.8, "session_duration_min": 120}
        },
        {
            "name": "유기농 건강식품 정기배송 서비스",
            "description": "구독형 상품의 배송 주기 선택과 혜택 설명 최적화",
            "product_id": "HEALTH_005",
            "test_duration_days": 42,
            "traffic_split_ratio": 0.5,
            "min_sample_size": 1000,
            "weights": {"ctr": 0.25, "cvr": 0.5, "revenue": 0.25},
            "guardrail_metrics": {"bounce_rate_threshold": 0.65, "session_duration_min": 75}
        }
    ]
    
    created_tests = []
    
    # 각 테스트 생성
    for i, config in enumerate(test_configs, 1):
        print(f"\n{i}. {config['name']} 생성 중...")
        test_id = create_test(config)
        
        if test_id:
            created_tests.append(test_id)
            # 각 테스트에 샘플 데이터 추가
            add_sample_interactions(test_id, random.randint(20, 50))
            time.sleep(1)  # 테스트 간 간격
    
    print(f"\n🎉 총 {len(created_tests)}개의 AB테스트가 생성되었습니다!")
    print("=" * 60)
    
    # 생성된 테스트 목록 확인
    print("\n📋 생성된 테스트 목록:")
    response = requests.get(f"{BASE_URL}/list")
    if response.status_code == 200:
        data = response.json()
        tests = data.get("tests", [])
        for test in tests:
            print(f"  • ID {test['id']}: {test['name']}")
            print(f"    상태: {test['status']}, 노출: {test['total_impressions']}, 클릭: {test['total_clicks']}, 구매: {test['total_purchases']}")
    
    print(f"\n🌐 웹 대시보드에서 확인하세요:")
    print(f"  메인 페이지: http://localhost:8000/")
    print(f"  대시보드: http://localhost:8000/test/dashboard.html")
    print(f"  시뮬레이터: http://localhost:8000/test/simple_test_simulator.html")

if __name__ == "__main__":
    main()
