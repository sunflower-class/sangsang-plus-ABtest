#!/usr/bin/env python3
"""
변형 정보 디버깅 스크립트
"""

import requests
import json

API_BASE_URL = "http://localhost:5001"

def debug_variants():
    """변형 정보를 디버깅"""
    print("🔍 변형 정보 디버깅 시작")
    print("=" * 50)
    
    # 모든 테스트 목록 조회
    response = requests.get(f"{API_BASE_URL}/api/abtest/list")
    if response.status_code != 200:
        print(f"❌ 테스트 목록 조회 실패: {response.status_code}")
        return
    
    tests = response.json().get("tests", [])
    if not tests:
        print("❌ 테스트가 없습니다.")
        return
    
    # 가장 최근 테스트 선택
    latest_test = tests[-1]
    test_id = latest_test["test_id"]
    print(f"📋 테스트 ID: {test_id}")
    print(f"📋 테스트 이름: {latest_test['test_name']}")
    
    # 테스트 상세 조회
    detail_response = requests.get(f"{API_BASE_URL}/api/abtest/{test_id}")
    if detail_response.status_code != 200:
        print(f"❌ 테스트 상세 조회 실패: {detail_response.status_code}")
        return
    
    detail = detail_response.json()
    print(f"\n📊 테스트 상세 정보:")
    print(json.dumps(detail, indent=2, ensure_ascii=False))
    
    # 변형 정보 확인
    variants = detail.get("variants", {})
    print(f"\n📋 변형 정보 (총 {len(variants)}개):")
    for variant_id, variant_data in variants.items():
        print(f"  - ID: {variant_id}")
        print(f"    타입: {variant_data.get('variant_type', 'N/A')}")
        print(f"    제목: {variant_data.get('title', 'N/A')}")

if __name__ == "__main__":
    debug_variants()
