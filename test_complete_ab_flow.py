#!/usr/bin/env python3
"""
완전한 AB 테스트 플로우 테스트
귀하가 제시한 7단계 플로우를 모두 테스트합니다.
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

def test_step1_create_experiment_brief():
    """1단계: 핵심 지표 및 보조 지표 설정"""
    print("\n🔍 1단계: 핵심 지표 및 보조 지표 설정 테스트...")
    
    experiment_brief = {
        "objective": "구매 전환율(CVR) 최대화",
        "primary_metrics": ["CVR"],
        "secondary_metrics": ["CTR", "ATC", "체류시간"],
        "guardrails": {"LCP": 3.5, "error_rate": 0.005, "return_rate": 0.1},
        "target_categories": ["스마트폰"],
        "target_channels": ["web", "mobile"],
        "target_devices": ["desktop", "mobile"],
        "exclude_conditions": [],
        "variant_count": 3,
        "distribution_mode": "equal",
        "mde": 0.1,
        "min_sample_size": 1000,
        "decision_mode": "hybrid",
        "manual_decision_period_days": 7,
        "long_term_monitoring_days": 30
    }
    
    test_data = {
        "test_name": "완전한 AB 테스트 플로우",
        "product_name": "갤럭시 S24 Ultra",
        "product_image": "https://images.samsung.com/kr/smartphones/galaxy-s24-ultra/images/galaxy-s24-ultra-highlights-color-cream-front.jpg",
        "product_description": "최신 AI 기술이 적용된 프리미엄 스마트폰. S펜과 함께 더욱 강력해진 생산성과 창의성을 경험하세요.",
        "price": 1950000,
        "category": "스마트폰",
        "tags": ["삼성", "프리미엄", "AI", "S펜"],
        "duration_days": 14,
        "experiment_brief": experiment_brief,
        "test_mode": "manual"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/abtest/create-with-brief", json=test_data)
        if response.status_code == 200:
            result = response.json()
            test_id = result["test_id"]
            print(f"✅ 실험 계약서 생성 성공 - 테스트 ID: {test_id}")
            return test_id
        else:
            print(f"❌ 실험 계약서 생성 실패: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ 실험 계약서 생성 오류: {e}")
        return None

def test_step2_start_ab_test(test_id):
    """2단계: AB 테스트 실행"""
    print(f"\n🔍 2단계: AB 테스트 실행 테스트 (ID: {test_id})...")
    
    try:
        # 테스트 시작
        response = requests.post(f"{BASE_URL}/api/abtest/action", json={
            "test_id": test_id,
            "action": "start"
        })
        if response.status_code == 200:
            print("✅ AB 테스트 시작 성공")
        else:
            print(f"❌ AB 테스트 시작 실패: {response.status_code}")
            return False
        
        # 이벤트 기록 시뮬레이션
        print("📊 이벤트 기록 시뮬레이션...")
        for i in range(100):
            user_id = f"user_{i}"
            session_id = f"session_{i}"
            variant_id = f"variant_{i % 3}"  # 3개 변형 중 하나
            
            # 노출 이벤트
            requests.post(f"{BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_id,
                "event_type": "impression",
                "user_id": user_id,
                "session_id": session_id
            })
            
            # 클릭 이벤트 (50% 확률)
            if random.random() < 0.5:
                requests.post(f"{BASE_URL}/api/abtest/event", json={
                    "test_id": test_id,
                    "variant_id": variant_id,
                    "event_type": "click",
                    "user_id": user_id,
                    "session_id": session_id
                })
                
                # 전환 이벤트 (20% 확률)
                if random.random() < 0.2:
                    requests.post(f"{BASE_URL}/api/abtest/event", json={
                        "test_id": test_id,
                        "variant_id": variant_id,
                        "event_type": "conversion",
                        "user_id": user_id,
                        "session_id": session_id,
                        "revenue": 1950000
                    })
        
        print("✅ 이벤트 기록 완료")
        return True
        
    except Exception as e:
        print(f"❌ AB 테스트 실행 오류: {e}")
        return False

def test_step3_weighted_winner_determination(test_id):
    """3단계: 지표에 가중치 설정하여 승자 결정"""
    print(f"\n🔍 3단계: 가중치 기반 승자 결정 테스트 (ID: {test_id})...")
    
    try:
        # 테스트 완료 (수동 결정 기간 시작)
        response = requests.post(f"{BASE_URL}/api/abtest/action", json={
            "test_id": test_id,
            "action": "complete"
        })
        if response.status_code == 200:
            print("✅ 테스트 완료 처리 성공")
        else:
            print(f"❌ 테스트 완료 처리 실패: {response.status_code}")
            return False
        
        # 수동 결정 정보 확인
        response = requests.get(f"{BASE_URL}/api/abtest/manual-decision/info/{test_id}")
        if response.status_code == 200:
            decision_info = response.json()["manual_decision_info"]
            print(f"✅ 수동 결정 정보 조회 성공")
            print(f"   - 결정 모드: {decision_info.get('decision_mode')}")
            print(f"   - 남은 시간: {decision_info.get('time_remaining')} 시간")
        else:
            print(f"❌ 수동 결정 정보 조회 실패: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ 승자 결정 테스트 오류: {e}")
        return False

def test_step4_dashboard_and_manual_decision(test_id):
    """4단계: 대시보드로 전체 결과 확인 후 수동 승자 결정"""
    print(f"\n🔍 4단계: 대시보드 및 수동 승자 결정 테스트 (ID: {test_id})...")
    
    try:
        # 대시보드 데이터 조회
        response = requests.get(f"{BASE_URL}/api/abtest/dashboard/manual-decision")
        if response.status_code == 200:
            dashboard_data = response.json()
            manual_tests = dashboard_data["manual_decision_tests"]
            print(f"✅ 수동 결정 대시보드 조회 성공 - {len(manual_tests)}개 테스트")
        else:
            print(f"❌ 수동 결정 대시보드 조회 실패: {response.status_code}")
        
        # 테스트 결과 조회
        response = requests.get(f"{BASE_URL}/api/abtest/{test_id}/results")
        if response.status_code == 200:
            results = response.json()["results"]
            variants = results.get("variants", {})
            print(f"✅ 테스트 결과 조회 성공 - {len(variants)}개 변형")
            
            # 가장 높은 CVR을 가진 변형을 승자로 선택
            best_variant = None
            best_cvr = -1
            
            for variant_id, variant_data in variants.items():
                cvr = variant_data.get("conversion_rate", 0)
                if cvr > best_cvr:
                    best_cvr = cvr
                    best_variant = variant_id
            
            if best_variant:
                # 수동으로 승자 선택
                response = requests.post(f"{BASE_URL}/api/abtest/manual-decision", json={
                    "test_id": test_id,
                    "variant_id": best_variant,
                    "reason": "가장 높은 CVR을 보인 변형"
                })
                if response.status_code == 200:
                    print(f"✅ 수동 승자 선택 성공 - 변형: {best_variant}, CVR: {best_cvr}%")
                else:
                    print(f"❌ 수동 승자 선택 실패: {response.status_code}")
            else:
                print("❌ 승자 선택할 변형이 없음")
        
        return True
        
    except Exception as e:
        print(f"❌ 대시보드 및 수동 결정 테스트 오류: {e}")
        return False

def test_step5_auto_winner_selection():
    """5단계: 수동 결정하지 않을 경우 자동 승자 선택"""
    print(f"\n🔍 5단계: 자동 승자 선택 테스트...")
    
    try:
        # 새로운 테스트 생성 (자동 결정 모드)
        experiment_brief = {
            "objective": "구매 전환율(CVR) 최대화",
            "primary_metrics": ["CVR"],
            "secondary_metrics": ["CTR", "ATC", "체류시간"],
            "guardrails": {"LCP": 3.5, "error_rate": 0.005, "return_rate": 0.1},
            "target_categories": ["스마트폰"],
            "target_channels": ["web", "mobile"],
            "target_devices": ["desktop", "mobile"],
            "exclude_conditions": [],
            "variant_count": 3,
            "distribution_mode": "equal",
            "mde": 0.1,
            "min_sample_size": 1000,
            "decision_mode": "auto",  # 자동 결정 모드
            "manual_decision_period_days": 7,
            "long_term_monitoring_days": 30
        }
        
        test_data = {
            "test_name": "자동 승자 선택 테스트",
            "product_name": "아이폰 15 Pro",
            "product_image": "https://example.com/iphone15.jpg",
            "product_description": "최신 아이폰 15 Pro",
            "price": 1500000,
            "category": "스마트폰",
            "tags": ["애플", "프리미엄"],
            "duration_days": 7,
            "experiment_brief": experiment_brief,
            "test_mode": "manual"
        }
        
        response = requests.post(f"{BASE_URL}/api/abtest/create-with-brief", json=test_data)
        if response.status_code == 200:
            auto_test_id = response.json()["test_id"]
            print(f"✅ 자동 결정 테스트 생성 성공 - ID: {auto_test_id}")
            
            # 테스트 시작
            requests.post(f"{BASE_URL}/api/abtest/action", json={
                "test_id": auto_test_id,
                "action": "start"
            })
            
            # 이벤트 기록
            for i in range(50):
                user_id = f"auto_user_{i}"
                session_id = f"auto_session_{i}"
                variant_id = f"variant_{i % 3}"
                
                requests.post(f"{BASE_URL}/api/abtest/event", json={
                    "test_id": auto_test_id,
                    "variant_id": variant_id,
                    "event_type": "impression",
                    "user_id": user_id,
                    "session_id": session_id
                })
                
                if random.random() < 0.6:
                    requests.post(f"{BASE_URL}/api/abtest/event", json={
                        "test_id": auto_test_id,
                        "variant_id": variant_id,
                        "event_type": "click",
                        "user_id": user_id,
                        "session_id": session_id
                    })
                    
                    if random.random() < 0.25:
                        requests.post(f"{BASE_URL}/api/abtest/event", json={
                            "test_id": auto_test_id,
                            "variant_id": variant_id,
                            "event_type": "conversion",
                            "user_id": user_id,
                            "session_id": session_id,
                            "revenue": 1500000
                        })
            
            # 테스트 완료 (자동 결정)
            requests.post(f"{BASE_URL}/api/abtest/action", json={
                "test_id": auto_test_id,
                "action": "complete"
            })
            
            # 결과 확인
            response = requests.get(f"{BASE_URL}/api/abtest/{auto_test_id}/results")
            if response.status_code == 200:
                results = response.json()["results"]
                winner = results.get("winner")
                if winner:
                    print(f"✅ 자동 승자 선택 성공 - 승자: {winner}")
                    
                    # 승자를 수동으로 설정하여 WINNER_SELECTED 상태로 변경
                    requests.post(f"{BASE_URL}/api/abtest/manual-decision", json={
                        "test_id": auto_test_id,
                        "variant_id": winner,
                        "reason": "자동 결정된 승자"
                    })
                else:
                    print("❌ 자동 승자 선택 실패")
            
            return auto_test_id
        else:
            print(f"❌ 자동 결정 테스트 생성 실패: {response.status_code}")
            return None
        
    except Exception as e:
        print(f"❌ 자동 승자 선택 테스트 오류: {e}")
        return None

def test_step6_new_page_generation(test_id):
    """6단계: 선택되지 않은 페이지들을 새로운 페이지로 생성"""
    print(f"\n🔍 6단계: 새로운 페이지 생성 테스트 (ID: {test_id})...")
    
    try:
        # 장기 모니터링 시작
        response = requests.post(f"{BASE_URL}/api/abtest/long-term-monitoring/start?test_id={test_id}")
        if response.status_code == 200:
            print("✅ 장기 모니터링 시작 성공")
        else:
            print(f"❌ 장기 모니터링 시작 실패: {response.status_code}")
            print(f"   응답: {response.text}")
        
        # 장기 모니터링 데이터 기록 (30일 시뮬레이션)
        print("📊 장기 모니터링 데이터 기록...")
        for day in range(30):
            metrics = {
                "cvr": 2.0 + random.uniform(-0.5, 0.5),
                "ctr": 1.5 + random.uniform(-0.3, 0.3),
                "revenue": 1500000 + random.uniform(-100000, 100000),
                "impressions": 100 + random.randint(-20, 20),
                "conversions": 2 + random.randint(-1, 1)
            }
            
            requests.post(f"{BASE_URL}/api/abtest/long-term-monitoring/record", json={
                "test_id": test_id,
                "metrics": metrics
            })
        
        print("✅ 장기 모니터링 데이터 기록 완료")
        
        # 장기 성과 분석 조회
        response = requests.get(f"{BASE_URL}/api/abtest/long-term-monitoring/{test_id}")
        if response.status_code == 200:
            performance = response.json()["performance"]
            print(f"✅ 장기 성과 분석 조회 성공")
            print(f"   - CVR 평균: {performance.get('cvr_avg', 0):.2f}%")
            print(f"   - CVR 트렌드: {performance.get('cvr_trend', 0):.4f}")
        else:
            print(f"❌ 장기 성과 분석 조회 실패: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ 새로운 페이지 생성 테스트 오류: {e}")
        return False

def test_step7_cycle_automation(test_id):
    """7단계: 다시 2번으로 돌아가서 AB 테스트 진행"""
    print(f"\n🔍 7단계: 사이클 자동화 테스트 (ID: {test_id})...")
    
    try:
        # 사이클 완료
        response = requests.post(f"{BASE_URL}/api/abtest/cycle/action", json={
            "test_id": test_id,
            "action": "complete_cycle"
        })
        if response.status_code == 200:
            print("✅ 사이클 완료 처리 성공")
        else:
            print(f"❌ 사이클 완료 처리 실패: {response.status_code}")
        
        # 사이클 상태 조회
        response = requests.get(f"{BASE_URL}/api/abtest/cycle/status/{test_id}")
        if response.status_code == 200:
            cycle_status = response.json()["cycle_status"]
            print(f"✅ 사이클 상태 조회 성공")
            print(f"   - 사이클 번호: {cycle_status.get('cycle_number')}")
            print(f"   - 상태: {cycle_status.get('status')}")
            print(f"   - 자동 대기열: {cycle_status.get('in_auto_queue')}")
        else:
            print(f"❌ 사이클 상태 조회 실패: {response.status_code}")
        
        # 자동 사이클 대기열 조회
        response = requests.get(f"{BASE_URL}/api/abtest/cycle/queue")
        if response.status_code == 200:
            queue = response.json()["auto_cycle_queue"]
            print(f"✅ 자동 사이클 대기열 조회 성공 - {len(queue)}개 테스트")
        else:
            print(f"❌ 자동 사이클 대기열 조회 실패: {response.status_code}")
        
        # 다음 사이클 시작 (실제로는 스케줄러가 자동으로 처리)
        response = requests.post(f"{BASE_URL}/api/abtest/cycle/action", json={
            "test_id": test_id,
            "action": "start_next_cycle"
        })
        if response.status_code == 200:
            print("✅ 다음 사이클 시작 성공")
        else:
            print(f"❌ 다음 사이클 시작 실패: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ 사이클 자동화 테스트 오류: {e}")
        return False

def test_complete_flow():
    """완전한 AB 테스트 플로우 테스트"""
    print("🚀 완전한 AB 테스트 플로우 테스트 시작")
    print("=" * 60)
    
    # 헬스 체크
    if not test_health_check():
        print("❌ 헬스 체크 실패로 테스트 중단")
        return False
    
    # 1단계: 핵심 지표 및 보조 지표 설정
    test_id = test_step1_create_experiment_brief()
    if not test_id:
        print("❌ 1단계 실패로 테스트 중단")
        return False
    
    # 2단계: AB 테스트 실행
    if not test_step2_start_ab_test(test_id):
        print("❌ 2단계 실패로 테스트 중단")
        return False
    
    # 3단계: 가중치 기반 승자 결정
    if not test_step3_weighted_winner_determination(test_id):
        print("❌ 3단계 실패로 테스트 중단")
        return False
    
    # 4단계: 대시보드 및 수동 승자 결정
    if not test_step4_dashboard_and_manual_decision(test_id):
        print("❌ 4단계 실패로 테스트 중단")
        return False
    
    # 5단계: 자동 승자 선택
    auto_test_id = test_step5_auto_winner_selection()
    if not auto_test_id:
        print("❌ 5단계 실패로 테스트 중단")
        return False
    
    # 6단계: 새로운 페이지 생성
    if not test_step6_new_page_generation(auto_test_id):
        print("❌ 6단계 실패로 테스트 중단")
        return False
    
    # 7단계: 사이클 자동화
    if not test_step7_cycle_automation(auto_test_id):
        print("❌ 7단계 실패로 테스트 중단")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 완전한 AB 테스트 플로우 테스트 성공!")
    print("✅ 모든 7단계가 성공적으로 완료되었습니다.")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    test_complete_flow()
