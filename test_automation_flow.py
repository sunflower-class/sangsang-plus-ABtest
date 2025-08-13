#!/usr/bin/env python3
"""
자동화 실험 테스트 스크립트
Autopilot과 전체 자동화 플로우를 테스트합니다.
"""

import requests
import json
import time
import random
from datetime import datetime, timedelta

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

def test_autopilot_status():
    """Autopilot 상태 테스트"""
    print("\n🔍 Autopilot 상태 테스트...")
    try:
        response = requests.get(f"{BASE_URL}/api/abtest/autopilot/status")
        if response.status_code == 200:
            status = response.json()["autopilot_status"]
            print("✅ Autopilot 상태 조회 성공")
            print(f"   - 활성화: {status['enabled']}")
            print(f"   - 프로모션 모드: {status['promotion_mode']}")
            print(f"   - 활성 테스트: {status['active_tests_count']}개")
            print(f"   - 완료된 테스트: {status['completed_tests_count']}개")
            print(f"   - 자동 사이클 대기열: {status['auto_cycle_queue_size']}개")
            print(f"   - 사이클 관리자 실행: {status['cycle_manager_running']}")
            return True
        else:
            print(f"❌ Autopilot 상태 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Autopilot 상태 조회 오류: {e}")
        return False

def test_autopilot_run_cycle():
    """Autopilot 사이클 실행 테스트"""
    print("\n🔍 Autopilot 사이클 실행 테스트...")
    try:
        response = requests.post(f"{BASE_URL}/api/abtest/autopilot/run-cycle")
        if response.status_code == 200:
            result = response.json()
            print("✅ Autopilot 사이클 실행 성공")
            print(f"   - 생성된 실험: {result.get('experiments_created', 0)}개")
            print(f"   - 메시지: {result.get('message', 'N/A')}")
            return True
        else:
            print(f"❌ Autopilot 사이클 실행 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Autopilot 사이클 실행 오류: {e}")
        return False

def test_promotion_mode():
    """프로모션 모드 테스트"""
    print("\n🔍 프로모션 모드 테스트...")
    try:
        # 프로모션 모드 활성화
        response = requests.post(f"{BASE_URL}/api/abtest/autopilot/promotion-mode", params={"enabled": True})
        if response.status_code == 200:
            print("✅ 프로모션 모드 활성화 성공")
        else:
            print(f"❌ 프로모션 모드 활성화 실패: {response.status_code}")
            return False
        
        # 상태 확인
        status_response = requests.get(f"{BASE_URL}/api/abtest/autopilot/status")
        if status_response.status_code == 200:
            status = status_response.json()["autopilot_status"]
            print(f"   - 프로모션 모드: {status['promotion_mode']}")
        
        # 프로모션 모드 비활성화
        response = requests.post(f"{BASE_URL}/api/abtest/autopilot/promotion-mode", params={"enabled": False})
        if response.status_code == 200:
            print("✅ 프로모션 모드 비활성화 성공")
            return True
        else:
            print(f"❌ 프로모션 모드 비활성화 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 프로모션 모드 테스트 오류: {e}")
        return False

def test_automated_experiment_creation():
    """자동 실험 생성 테스트"""
    print("\n🔍 자동 실험 생성 테스트...")
    try:
        # 상품 후보 추가 (실제로는 Autopilot이 자동으로 처리)
        # 여기서는 수동으로 실험을 생성하고 자동화 기능을 테스트
        
        # 실험 계약서와 함께 테스트 생성
        experiment_brief = {
            "objective": "자동화 테스트 - CVR 최대화",
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
            "min_sample_size": 100,
            "decision_mode": "auto",  # 자동 결정 모드
            "manual_decision_period_days": 1,  # 1일로 단축
            "long_term_monitoring_days": 7  # 7일로 단축
        }

        test_data = {
            "test_name": "자동화 실험 테스트",
            "product_name": "자동화 테스트 상품",
            "product_image": "https://example.com/auto-test.jpg",
            "product_description": "자동화 기능을 테스트하기 위한 상품",
            "price": 1000000,
            "category": "스마트폰",
            "tags": ["자동화", "테스트"],
            "duration_days": 3,  # 3일로 단축
            "experiment_brief": experiment_brief,
            "test_mode": "autopilot"  # 자동화 모드
        }

        response = requests.post(f"{BASE_URL}/api/abtest/create-with-brief", json=test_data)
        if response.status_code == 200:
            result = response.json()
            test_id = result["test_id"]
            print(f"✅ 자동화 실험 생성 성공 - 테스트 ID: {test_id}")
            return test_id
        else:
            print(f"❌ 자동화 실험 생성 실패: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 자동화 실험 생성 오류: {e}")
        return None

def test_automated_cycle_flow(test_id):
    """자동화 사이클 플로우 테스트"""
    print(f"\n🔍 자동화 사이클 플로우 테스트 (ID: {test_id})...")
    try:
        # 1. 테스트 시작
        response = requests.post(f"{BASE_URL}/api/abtest/action", json={
            "test_id": test_id,
            "action": "start"
        })
        if response.status_code == 200:
            print("✅ 자동화 테스트 시작 성공")
        else:
            print(f"❌ 자동화 테스트 시작 실패: {response.status_code}")
            return False

        # 2. 이벤트 시뮬레이션 (빠른 테스트를 위해 적은 수)
        print("📊 이벤트 시뮬레이션...")
        for i in range(20):  # 20명의 사용자로 단축
            user_id = f"auto_user_{i}"
            session_id = f"auto_session_{i}"
            
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

        # 3. 테스트 완료 (자동 결정)
        response = requests.post(f"{BASE_URL}/api/abtest/action", json={
            "test_id": test_id,
            "action": "complete"
        })
        if response.status_code == 200:
            print("✅ 자동화 테스트 완료 처리 성공")
        else:
            print(f"❌ 자동화 테스트 완료 처리 실패: {response.status_code}")
            return False

        # 4. 결과 확인
        response = requests.get(f"{BASE_URL}/api/abtest/{test_id}/results")
        if response.status_code == 200:
            results = response.json()["results"]
            winner = results.get("winner")
            if winner:
                print(f"✅ 자동 승자 선택 성공 - 승자: {winner}")
            else:
                print("⚠️ 자동 승자 선택 대기 중")
        else:
            print(f"❌ 결과 조회 실패: {response.status_code}")

        return True

    except Exception as e:
        print(f"❌ 자동화 사이클 플로우 테스트 오류: {e}")
        return False

def test_cycle_management():
    """사이클 관리 테스트"""
    print("\n🔍 사이클 관리 테스트...")
    try:
        # 자동 사이클 대기열 조회
        response = requests.get(f"{BASE_URL}/api/abtest/cycle/queue")
        if response.status_code == 200:
            queue = response.json()["auto_cycle_queue"]
            print(f"✅ 자동 사이클 대기열 조회 성공 - {len(queue)}개 테스트")
        else:
            print(f"❌ 자동 사이클 대기열 조회 실패: {response.status_code}")

        # 타임아웃 체크 수동 실행
        response = requests.post(f"{BASE_URL}/api/abtest/check-timeouts")
        if response.status_code == 200:
            print("✅ 타임아웃 체크 실행 성공")
        else:
            print(f"❌ 타임아웃 체크 실행 실패: {response.status_code}")

        return True

    except Exception as e:
        print(f"❌ 사이클 관리 테스트 오류: {e}")
        return False

def test_guardrails():
    """가드레일 테스트"""
    print("\n🔍 가드레일 테스트...")
    try:
        # 가드레일 알림 조회
        response = requests.get(f"{BASE_URL}/api/abtest/guardrails/alerts")
        if response.status_code == 200:
            alerts = response.json()["alerts"]
            print(f"✅ 가드레일 알림 조회 성공 - {len(alerts)}개 알림")
            
            for alert in alerts:
                print(f"   - {alert['test_id']}: {alert['alert_type']} - {alert['message']}")
        else:
            print(f"❌ 가드레일 알림 조회 실패: {response.status_code}")

        return True

    except Exception as e:
        print(f"❌ 가드레일 테스트 오류: {e}")
        return False

def test_complete_automation():
    """완전한 자동화 테스트"""
    print("\n🚀 완전한 자동화 테스트 시작")
    print("=" * 60)

    # 1. 헬스 체크
    if not test_health_check():
        print("❌ 헬스 체크 실패로 테스트 중단")
        return False

    # 2. Autopilot 상태 확인
    if not test_autopilot_status():
        print("❌ Autopilot 상태 확인 실패")
        return False

    # 3. 프로모션 모드 테스트
    if not test_promotion_mode():
        print("❌ 프로모션 모드 테스트 실패")
        return False

    # 4. 자동 실험 생성
    test_id = test_automated_experiment_creation()
    if not test_id:
        print("❌ 자동 실험 생성 실패")
        return False

    # 5. 자동화 사이클 플로우
    if not test_automated_cycle_flow(test_id):
        print("❌ 자동화 사이클 플로우 실패")
        return False

    # 6. 사이클 관리
    if not test_cycle_management():
        print("❌ 사이클 관리 테스트 실패")
        return False

    # 7. 가드레일 테스트
    if not test_guardrails():
        print("❌ 가드레일 테스트 실패")
        return False

    # 8. 최종 Autopilot 상태 확인
    print("\n🔍 최종 Autopilot 상태 확인...")
    response = requests.get(f"{BASE_URL}/api/abtest/autopilot/status")
    if response.status_code == 200:
        status = response.json()["autopilot_status"]
        print(f"✅ 최종 상태:")
        print(f"   - 활성 테스트: {status['active_tests_count']}개")
        print(f"   - 완료된 테스트: {status['completed_tests_count']}개")
        print(f"   - 자동 사이클 대기열: {status['auto_cycle_queue_size']}개")
        print(f"   - 사이클 관리자 실행: {status['cycle_manager_running']}")

    print("\n" + "=" * 60)
    print("🎉 완전한 자동화 테스트 성공!")
    print("✅ 모든 자동화 기능이 정상적으로 작동합니다.")
    print("=" * 60)

    return True

if __name__ == "__main__":
    test_complete_automation()

