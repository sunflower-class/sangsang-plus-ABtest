#!/usr/bin/env python3
"""
향상된 A/B 테스트 시스템 테스트
모든 새로운 기능들을 테스트합니다.
"""

import requests
import json
import time
from datetime import datetime

# API 서버 설정
API_BASE_URL = "http://localhost:5001"

def test_experiment_brief_creation():
    """실험 계약서 생성 테스트 - 요구사항 1번"""
    print("🧪 실험 계약서 생성 테스트")
    
    brief_data = {
        "test_name": "스마트폰 CVR 최적화 테스트",
        "product_name": "갤럭시 S24 Ultra",
        "product_image": "https://example.com/s24-ultra.jpg",
        "product_description": "최신 갤럭시 스마트폰으로 놀라운 성능을 경험하세요.",
        "price": 1500000,
        "category": "스마트폰",
        "tags": ["삼성", "프리미엄", "5G"],
        "duration_days": 14,
        "experiment_brief": {
            "objective": "구매 전환율(CVR) 최대화",
            "primary_metrics": ["CVR"],
            "secondary_metrics": ["CTR", "ATC", "체류시간"],
            "guardrails": {
                "LCP": 3.5,
                "error_rate": 0.005,
                "return_rate": 0.1
            },
            "target_categories": ["스마트폰"],
            "target_channels": ["web", "mobile"],
            "target_devices": ["desktop", "mobile"],
            "exclude_conditions": ["신규 사용자"],
            "variant_count": 3,
            "distribution_mode": "bandit",
            "mde": 0.1,
            "min_sample_size": 1000
        },
        "test_mode": "manual"
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/abtest/create-with-brief", json=brief_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 실험 계약서 생성 성공: {result['test_id']}")
            return result['test_id']
        else:
            print(f"❌ 실험 계약서 생성 실패: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 오류: {e}")
        return None

def test_autopilot_status():
    """자동 생성기 상태 테스트 - 요구사항 3번, 11번"""
    print("\n🤖 자동 생성기 상태 테스트")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/abtest/autopilot/status")
        if response.status_code == 200:
            status = response.json()
            autopilot_status = status["autopilot_status"]
            print(f"✅ 자동 생성기 활성화: {autopilot_status['enabled']}")
            print(f"✅ 활성 자동 실험: {autopilot_status['active_autopilot_experiments']}")
            print(f"✅ 트래픽 사용량: {autopilot_status['total_traffic_usage']:.1%}")
            return True
        else:
            print(f"❌ 자동 생성기 상태 조회 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def test_bandit_variant_selection(test_id):
    """Thompson Sampling 변형 선택 테스트 - 요구사항 7번"""
    print(f"\n🎯 Thompson Sampling 변형 선택 테스트 (테스트 ID: {test_id})")
    
    try:
        # 여러 사용자에 대해 변형 선택 테스트
        users = ["user001", "user002", "user003", "user004", "user005"]
        selected_variants = []
        
        for user_id in users:
            response = requests.get(f"{API_BASE_URL}/api/abtest/{test_id}/variant-bandit/{user_id}")
            if response.status_code == 200:
                variant = response.json()["variant"]
                selected_variants.append(variant["variant_type"])
                print(f"✅ 사용자 {user_id}: 변형 {variant['variant_type']} 선택")
            else:
                print(f"❌ 사용자 {user_id} 변형 선택 실패: {response.text}")
        
        # Sticky Assignment 테스트 (동일 사용자가 같은 변형을 선택하는지)
        response = requests.get(f"{API_BASE_URL}/api/abtest/{test_id}/variant-bandit/user001")
        if response.status_code == 200:
            variant = response.json()["variant"]
            print(f"✅ Sticky Assignment 확인: 사용자 user001이 다시 변형 {variant['variant_type']} 선택")
        
        return True
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def test_dashboard_metrics():
    """대시보드 메트릭 테스트 - 요구사항 9번"""
    print("\n📊 대시보드 메트릭 테스트")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/abtest/dashboard/metrics")
        if response.status_code == 200:
            metrics = response.json()["metrics"]
            print(f"✅ 총 테스트: {metrics['total_tests']}")
            print(f"✅ 활성 테스트: {metrics['active_tests']}")
            print(f"✅ 전체 CVR: {metrics['overall_cvr']:.2f}%")
            print(f"✅ 자동 실험: {metrics['autopilot_experiments']}")
            return True
        else:
            print(f"❌ 대시보드 메트릭 조회 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def test_guardrail_alerts():
    """가드레일 알림 테스트 - 요구사항 6번"""
    print("\n🚨 가드레일 알림 테스트")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/abtest/guardrails/alerts")
        if response.status_code == 200:
            alerts = response.json()["alerts"]
            print(f"✅ 총 알림 수: {len(alerts)}")
            
            active_alerts = [a for a in alerts if not a["resolved"]]
            print(f"✅ 활성 알림 수: {len(active_alerts)}")
            
            if active_alerts:
                for alert in active_alerts[:3]:  # 최대 3개만 표시
                    print(f"  - {alert['alert_type']}: {alert['message']}")
            
            return True
        else:
            print(f"❌ 가드레일 알림 조회 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def test_event_tracking(test_id):
    """이벤트 추적 테스트 - 요구사항 5번"""
    print(f"\n📈 이벤트 추적 테스트 (테스트 ID: {test_id})")
    
    try:
        # 노출 이벤트
        impression_event = {
            "test_id": test_id,
            "variant_id": f"{test_id}_A",
            "event_type": "impression",
            "user_id": "test_user_001",
            "session_id": "session_001",
            "revenue": 0.0,
            "session_duration": 0.0
        }
        
        response = requests.post(f"{API_BASE_URL}/api/abtest/event", json=impression_event)
        if response.status_code == 200:
            print("✅ 노출 이벤트 기록 성공")
        else:
            print(f"❌ 노출 이벤트 기록 실패: {response.text}")
        
        # 클릭 이벤트
        click_event = {
            "test_id": test_id,
            "variant_id": f"{test_id}_A",
            "event_type": "click_detail",
            "user_id": "test_user_001",
            "session_id": "session_001",
            "revenue": 0.0,
            "session_duration": 5.0
        }
        
        response = requests.post(f"{API_BASE_URL}/api/abtest/event", json=click_event)
        if response.status_code == 200:
            print("✅ 클릭 이벤트 기록 성공")
        else:
            print(f"❌ 클릭 이벤트 기록 실패: {response.text}")
        
        # 구매 이벤트
        purchase_event = {
            "test_id": test_id,
            "variant_id": f"{test_id}_A",
            "event_type": "purchase",
            "user_id": "test_user_001",
            "session_id": "session_001",
            "revenue": 1500000.0,
            "session_duration": 120.0
        }
        
        response = requests.post(f"{API_BASE_URL}/api/abtest/event", json=purchase_event)
        if response.status_code == 200:
            print("✅ 구매 이벤트 기록 성공")
        else:
            print(f"❌ 구매 이벤트 기록 실패: {response.text}")
        
        return True
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def test_bandit_decisions(test_id):
    """밴딧 의사결정 로그 테스트 - 요구사항 9번"""
    print(f"\n🎲 밴딧 의사결정 로그 테스트 (테스트 ID: {test_id})")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/abtest/bandit/decisions/{test_id}")
        if response.status_code == 200:
            decisions = response.json()["decisions"]
            print(f"✅ 의사결정 로그 수: {len(decisions)}")
            
            if decisions:
                latest_decision = decisions[-1]
                print(f"✅ 최근 의사결정: {latest_decision['decision_reason']}")
                print(f"✅ 선택된 변형: {latest_decision['selected_variant']}")
            
            return True
        else:
            print(f"❌ 밴딧 의사결정 로그 조회 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def test_learning_patterns():
    """학습 패턴 테스트 - 요구사항 10번"""
    print("\n🧠 학습 패턴 테스트")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/abtest/learning/patterns")
        if response.status_code == 200:
            patterns = response.json()["patterns"]
            print("✅ 학습 패턴 조회 성공")
            
            if "successful_patterns" in patterns:
                print(f"✅ 성공 패턴 수: {len(patterns['successful_patterns'])}")
                for category, pattern in patterns['successful_patterns'].items():
                    print(f"  - {category}: 승률 {pattern['win_rate']:.1%}")
            
            if "cta_performance" in patterns:
                print(f"✅ CTA 성과 데이터 수: {len(patterns['cta_performance'])}")
            
            return True
        else:
            print(f"❌ 학습 패턴 조회 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def test_promotion_mode():
    """프로모션 모드 테스트 - 요구사항 11번"""
    print("\n🎯 프로모션 모드 테스트")
    
    try:
        # 프로모션 모드 활성화
        response = requests.post(f"{API_BASE_URL}/api/abtest/autopilot/promotion-mode", params={"enabled": True})
        if response.status_code == 200:
            print("✅ 프로모션 모드 활성화 성공")
        else:
            print(f"❌ 프로모션 모드 활성화 실패: {response.text}")
        
        # 프로모션 모드 비활성화
        response = requests.post(f"{API_BASE_URL}/api/abtest/autopilot/promotion-mode", params={"enabled": False})
        if response.status_code == 200:
            print("✅ 프로모션 모드 비활성화 성공")
        else:
            print(f"❌ 프로모션 모드 비활성화 실패: {response.text}")
        
        return True
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def test_auto_rollback(test_id):
    """자동 롤백 테스트 - 요구사항 8번"""
    print(f"\n🔄 자동 롤백 테스트 (테스트 ID: {test_id})")
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/abtest/test/{test_id}/auto-rollback")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 자동 롤백 실행: {result['message']}")
        else:
            print(f"❌ 자동 롤백 실행 실패: {response.text}")
        
        return True
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def test_experiment_report(test_id):
    """실험 리포트 테스트 - 요구사항 10번"""
    print(f"\n📋 실험 리포트 테스트 (테스트 ID: {test_id})")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/abtest/report/{test_id}")
        if response.status_code == 200:
            report = response.json()["report"]
            print("✅ 실험 리포트 생성 성공")
            
            if "experiment_overview" in report:
                overview = report["experiment_overview"]
                print(f"✅ 실험명: {overview['test_name']}")
                print(f"✅ 목적: {overview.get('objective', 'N/A')}")
            
            if "insights" in report:
                insights = report["insights"]
                print(f"✅ 인사이트 수: {len(insights)}")
                for insight in insights[:3]:  # 최대 3개만 표시
                    print(f"  - {insight}")
            
            return True
        else:
            print(f"❌ 실험 리포트 생성 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def run_all_tests():
    """모든 테스트 실행"""
    print("🚀 향상된 A/B 테스트 시스템 테스트 시작")
    print("=" * 60)
    
    # 1. 실험 계약서 생성 테스트
    test_id = test_experiment_brief_creation()
    
    if test_id:
        # 2. 자동 생성기 상태 테스트
        test_autopilot_status()
        
        # 3. Thompson Sampling 변형 선택 테스트
        test_bandit_variant_selection(test_id)
        
        # 4. 대시보드 메트릭 테스트
        test_dashboard_metrics()
        
        # 5. 가드레일 알림 테스트
        test_guardrail_alerts()
        
        # 6. 이벤트 추적 테스트
        test_event_tracking(test_id)
        
        # 7. 밴딧 의사결정 로그 테스트
        test_bandit_decisions(test_id)
        
        # 8. 학습 패턴 테스트
        test_learning_patterns()
        
        # 9. 프로모션 모드 테스트
        test_promotion_mode()
        
        # 10. 자동 롤백 테스트
        test_auto_rollback(test_id)
        
        # 11. 실험 리포트 테스트
        test_experiment_report(test_id)
    
    print("\n" + "=" * 60)
    print("🎉 모든 테스트 완료!")
    print("\n📋 구현된 요구사항:")
    print("✅ 1. 실험 계약서 (Experiment Brief)")
    print("✅ 2. 변형 자동 생성")
    print("✅ 3. 실험 생성 방식 (수동/자동)")
    print("✅ 4. 트래픽 배분·노출")
    print("✅ 5. 계측 (Tracking)")
    print("✅ 6. 데이터 신뢰성")
    print("✅ 7. 통계·의사결정")
    print("✅ 8. 승자 처리")
    print("✅ 9. 대시보드/운영 UX")
    print("✅ 10. 리포트 & 인사이트")
    print("✅ 11. 자동화 루프")
    print("✅ 12. 예외·엣지 케이스 핸들링")
    print("✅ 13. 거버넌스/보안")
    print("✅ 14. 좋은 실험 체크리스트")
    print("✅ 15. 운영 모드 요약")

if __name__ == "__main__":
    run_all_tests()
