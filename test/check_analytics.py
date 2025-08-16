#!/usr/bin/env python3
"""
현재 A/B 테스트 데이터 분석 확인 스크립트
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/abtest"

def check_analytics():
    """현재 테스트의 분석 데이터 확인"""
    print("📊 현재 A/B 테스트 분석 데이터 확인")
    
    # 테스트 목록 조회
    response = requests.get(f"{BASE_URL}/list")
    if response.status_code != 200:
        print("❌ 테스트 목록 조회 실패")
        return
    
    data = response.json()
    tests = data.get("tests", []) if isinstance(data, dict) else data
    if not tests:
        print("❌ 생성된 테스트가 없습니다")
        return
    
    # 가장 최근 테스트 선택
    latest_test = tests[-1]
    test_id = latest_test["id"]
    
    print(f"\n🔍 테스트 ID: {test_id}")
    print(f"📝 테스트명: {latest_test['name']}")
    print(f"📅 생성일: {latest_test['created_at']}")
    
    # 분석 데이터 조회
    response = requests.get(f"{BASE_URL}/{test_id}/analytics")
    if response.status_code != 200:
        print("❌ 분석 데이터 조회 실패")
        return
    
    analytics = response.json()
    print(f"\n📈 분석 결과:")
    print(f"상태: {analytics['status']}")
    print(f"총 노출: {analytics['total_impressions']}")
    print(f"총 클릭: {analytics['total_clicks']}")
    print(f"총 구매: {analytics['total_purchases']}")
    print(f"총 매출: {analytics['total_revenue']}")
    
    print(f"\n📊 버전별 성과:")
    for variant in analytics['variants']:
        print(f"\n{variant['variant_name']} (ID: {variant['variant_id']}):")
        print(f"  - 노출: {variant['impressions']}")
        print(f"  - 클릭: {variant['clicks']}")
        print(f"  - 구매: {variant['purchases']}")
        print(f"  - CTR: {variant['ctr']:.4f}")
        print(f"  - CVR: {variant['cvr']:.4f}")
        print(f"  - 이탈률: {variant['bounce_rate']:.4f}")
        print(f"  - 점수: {variant['score']:.4f}")
    
    # 승자 결정 시도
    print(f"\n🏆 승자 결정 시도:")
    response = requests.post(f"{BASE_URL}/{test_id}/determine-winner")
    if response.status_code == 200:
        result = response.json()
        print(f"결과: {result['message']}")
        if result['success']:
            print(f"승자 ID: {result['winner_variant_id']}")
    else:
        print("❌ 승자 결정 실패")

if __name__ == "__main__":
    check_analytics()
