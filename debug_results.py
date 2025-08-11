#!/usr/bin/env python3
"""
결과 디버깅 스크립트
"""

import requests
import json

API_BASE_URL = "http://localhost:5001"

def debug_results():
    """결과를 자세히 디버깅"""
    print("🔍 결과 디버깅 시작")
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
    
    # 상세 결과 조회
    results_response = requests.get(f"{API_BASE_URL}/api/abtest/{test_id}/results")
    if results_response.status_code != 200:
        print(f"❌ 결과 조회 실패: {results_response.status_code}")
        return
    
    results = results_response.json()
    print(f"\n📊 전체 결과:")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # 이벤트 목록 조회
    events_response = requests.get(f"{API_BASE_URL}/api/abtest/{test_id}/events")
    if events_response.status_code == 200:
        events = events_response.json().get("events", [])
        print(f"\n📋 이벤트 목록 (총 {len(events)}개):")
        for event in events:
            print(f"  - {event['event_type']} | {event['variant_id']} | {event['user_id']} | 매출: {event.get('revenue', 0)}")

if __name__ == "__main__":
    debug_results()
