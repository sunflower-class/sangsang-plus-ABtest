#!/usr/bin/env python3
"""
A/B 테스트 시스템 테스트 스크립트
전체 플로우를 테스트하여 시스템이 정상적으로 작동하는지 확인합니다.
"""

import requests
import json
import time
import random
from datetime import datetime

# 서버 설정
BASE_URL = "http://localhost:5001"

def test_health_check():
    """헬스 체크 테스트"""
    print("🔍 헬스 체크 테스트...")
    try:
        response = requests.get(f"{BASE_URL}/python")
        if response.status_code == 200 and "python API is running!" in response.text:
            print("✅ 헬스 체크 성공")
            return True
        else:
            print("❌ 헬스 체크 실패")
            return False
    except Exception as e:
        print(f"❌ 헬스 체크 오류: {e}")
        return False

def test_create_ab_test():
    """A/B 테스트 생성 테스트"""
    print("\n🔍 A/B 테스트 생성 테스트...")
    
    test_data = {
        "test_name": "스마트폰 A/B 테스트",
        "product_name": "갤럭시 S24 Ultra",
        "product_image": "https://images.samsung.com/kr/smartphones/galaxy-s24-ultra/images/galaxy-s24-ultra-highlights-color-cream-front.jpg",
        "product_description": "최신 AI 기술이 적용된 프리미엄 스마트폰. S펜과 함께 더욱 강력해진 생산성과 창의성을 경험하세요.",
        "price": 1950000,
        "category": "스마트폰",
        "tags": ["삼성", "프리미엄", "AI", "S펜"],
        "duration_days": 14,
        "target_metrics": {
            "ctr": 0.6,
            "conversion_rate": 0.4
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/ab-test/create", json=test_data)
        if response.status_code == 200:
            result = response.json()
            test_id = result["test_id"]
            print(f"✅ A/B 테스트 생성 성공 - 테스트 ID: {test_id}")
            return test_id
        else:
            print(f"❌ A/B 테스트 생성 실패: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ A/B 테스트 생성 오류: {e}")
        return None

def test_get_ab_tests():
    """A/B 테스트 목록 조회 테스트"""
    print("\n🔍 A/B 테스트 목록 조회 테스트...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/ab-test/list")
        if response.status_code == 200:
            result = response.json()
            tests = result["tests"]
            print(f"✅ 테스트 목록 조회 성공 - 총 {len(tests)}개 테스트")
            for test in tests:
                print(f"  - {test['test_name']} ({test['status']})")
            return True
        else:
            print(f"❌ 테스트 목록 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 테스트 목록 조회 오류: {e}")
        return False

def test_start_ab_test(test_id):
    """A/B 테스트 시작 테스트"""
    print(f"\n🔍 A/B 테스트 시작 테스트 (ID: {test_id})...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/ab-test/action", json={
            "test_id": test_id,
            "action": "start"
        })
        if response.status_code == 200:
            result = response.json()
            if result["status"] == "success":
                print("✅ A/B 테스트 시작 성공")
                return True
            else:
                print(f"❌ A/B 테스트 시작 실패: {result['message']}")
                return False
        else:
            print(f"❌ A/B 테스트 시작 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ A/B 테스트 시작 오류: {e}")
        return False

def test_get_user_variant(test_id):
    """사용자별 변형 조회 테스트"""
    print(f"\n🔍 사용자별 변형 조회 테스트 (ID: {test_id})...")
    
    user_ids = ["user001", "user002", "user003", "user004"]
    variants = {}
    
    try:
        for user_id in user_ids:
            response = requests.get(f"{BASE_URL}/api/ab-test/{test_id}/variant/{user_id}")
            if response.status_code == 200:
                result = response.json()
                variant = result["variant"]
                variants[user_id] = variant["variant_type"]
                print(f"  - {user_id}: 변형 {variant['variant_type']}")
            else:
                print(f"❌ 사용자 {user_id} 변형 조회 실패: {response.status_code}")
                return None
        
        print("✅ 사용자별 변형 조회 성공")
        return variants
    except Exception as e:
        print(f"❌ 사용자별 변형 조회 오류: {e}")
        return None

def test_record_events(test_id, variants):
    """이벤트 기록 테스트"""
    print(f"\n🔍 이벤트 기록 테스트 (ID: {test_id})...")
    
    event_types = ["impression", "click", "conversion"]
    users = list(variants.keys())
    
    try:
        for _ in range(20):  # 20개의 이벤트 기록
            user_id = random.choice(users)
            variant_type = variants[user_id]
            
            # 변형 ID 찾기
            response = requests.get(f"{BASE_URL}/api/ab-test/{test_id}/variant/{user_id}")
            if response.status_code != 200:
                continue
            
            variant = response.json()["variant"]
            event_type = random.choice(event_types)
            
            event_data = {
                "test_id": test_id,
                "variant_id": variant["variant_id"],
                "event_type": event_type,
                "user_id": user_id,
                "session_id": f"session_{random.randint(1000, 9999)}",
                "revenue": random.uniform(0, 100000) if event_type == "conversion" else 0.0,
                "session_duration": random.uniform(10, 300)
            }
            
            response = requests.post(f"{BASE_URL}/api/ab-test/event", json=event_data)
            if response.status_code == 200:
                print(f"  - {user_id} ({variant_type}): {event_type} 이벤트 기록")
            else:
                print(f"❌ 이벤트 기록 실패: {response.status_code}")
        
        print("✅ 이벤트 기록 성공")
        return True
    except Exception as e:
        print(f"❌ 이벤트 기록 오류: {e}")
        return False

def test_get_results(test_id):
    """테스트 결과 조회 테스트"""
    print(f"\n🔍 테스트 결과 조회 테스트 (ID: {test_id})...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/ab-test/{test_id}/results")
        if response.status_code == 200:
            result = response.json()
            results = result["results"]
            
            print(f"✅ 테스트 결과 조회 성공")
            print(f"  - 테스트명: {results['test_name']}")
            print(f"  - 상태: {results['status']}")
            print(f"  - 총 노출: {results['total_impressions']}")
            print(f"  - 총 클릭: {results['total_clicks']}")
            print(f"  - 총 전환: {results['total_conversions']}")
            print(f"  - 총 수익: ₩{results['total_revenue']:,.0f}")
            
            if results['variants']:
                print("  - 변형별 결과:")
                for variant_id, variant_result in results['variants'].items():
                    print(f"    * 변형 {variant_result['variant_type']}:")
                    print(f"      - CTR: {variant_result['ctr']}%")
                    print(f"      - 전환율: {variant_result['conversion_rate']}%")
                    print(f"      - 수익: ₩{variant_result['revenue']:,.0f}")
            
            if results['winner']:
                print(f"  - 승자: {results['winner']}")
            else:
                print("  - 승자: 아직 결정되지 않음")
            
            return True
        else:
            print(f"❌ 테스트 결과 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 테스트 결과 조회 오류: {e}")
        return False

def test_generate_page(test_id):
    """페이지 생성 테스트"""
    print(f"\n🔍 페이지 생성 테스트 (ID: {test_id})...")
    
    try:
        # 테스트 정보 조회
        response = requests.get(f"{BASE_URL}/api/ab-test/{test_id}")
        if response.status_code != 200:
            print(f"❌ 테스트 정보 조회 실패: {response.status_code}")
            return False
        
        test_info = response.json()
        variants = test_info["test"]["variants_count"]
        
        # 테스트 정보에서 실제 variant_id 가져오기
        test_response = requests.get(f"{BASE_URL}/api/ab-test/{test_id}")
        if test_response.status_code != 200:
            print(f"❌ 테스트 정보 조회 실패: {test_response.status_code}")
            return False
        
        test_data = test_response.json()
        test_variants = test_data["test"]["variants_count"]
        
        # 실제 variant_id를 사용하여 페이지 생성 테스트
        results_response = requests.get(f"{BASE_URL}/api/ab-test/{test_id}/results")
        if results_response.status_code == 200:
            results_data = results_response.json()
            variant_ids = list(results_data["results"]["variants"].keys())
            
            for i, variant_id in enumerate(variant_ids[:2]):  # 최대 2개 변형만 테스트
                response = requests.get(f"{BASE_URL}/api/ab-test/{test_id}/page/{variant_id}")
                if response.status_code == 200:
                    html_content = response.text
                    if "<!DOCTYPE html>" in html_content and ("product" in html_content or "갤럭시" in html_content or "스마트폰" in html_content):
                        print(f"  ✅ 변형 {i} (ID: {variant_id[:8]}...) 페이지 생성 성공")
                    else:
                        print(f"  ❌ 변형 {i} 페이지 생성 실패 - HTML 형식 오류")
                else:
                    print(f"  ❌ 변형 {i} 페이지 생성 실패: {response.status_code}")
        else:
            print(f"❌ 테스트 결과 조회 실패: {results_response.status_code}")
            return False
        
        print("✅ 페이지 생성 테스트 완료")
        return True
    except Exception as e:
        print(f"❌ 페이지 생성 테스트 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 A/B 테스트 시스템 테스트 시작")
    print("=" * 50)
    
    # 1. 헬스 체크
    if not test_health_check():
        print("❌ 서버가 실행되지 않았습니다. 서버를 먼저 시작해주세요.")
        return
    
    # 2. A/B 테스트 생성
    test_id = test_create_ab_test()
    if not test_id:
        print("❌ A/B 테스트 생성에 실패했습니다.")
        return
    
    # 3. 테스트 목록 조회
    test_get_ab_tests()
    
    # 4. 테스트 시작
    if not test_start_ab_test(test_id):
        print("❌ A/B 테스트 시작에 실패했습니다.")
        return
    
    # 5. 사용자별 변형 조회
    variants = test_get_user_variant(test_id)
    if not variants:
        print("❌ 사용자별 변형 조회에 실패했습니다.")
        return
    
    # 6. 이벤트 기록
    if not test_record_events(test_id, variants):
        print("❌ 이벤트 기록에 실패했습니다.")
        return
    
    # 잠시 대기 (이벤트 처리 시간)
    print("\n⏳ 이벤트 처리 대기 중...")
    time.sleep(2)
    
    # 7. 결과 조회
    test_get_results(test_id)
    
    # 8. 페이지 생성 테스트
    test_generate_page(test_id)
    
    print("\n" + "=" * 50)
    print("🎉 A/B 테스트 시스템 테스트 완료!")
    print(f"📊 테스트 ID: {test_id}")
    print("💡 브라우저에서 다음 URL로 페이지를 확인할 수 있습니다:")
    print(f"   http://localhost:5001/docs (API 문서)")
    print(f"   또는 실제 variant_id를 사용하여 페이지 접근")

if __name__ == "__main__":
    main()
