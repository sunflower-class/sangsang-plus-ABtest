#!/usr/bin/env python3
"""
A/B 테스트 시스템 프론트엔드
Streamlit을 사용한 웹 인터페이스
"""

import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# API 서버 설정 (테스트용)
API_BASE_URL = "http://localhost:5001"

def main():
    st.set_page_config(
        page_title="A/B 테스트 시스템",
        page_icon="🧪",
        layout="wide"
    )
    
    st.title("🧪 상품 상세페이지 A/B 테스트 시스템 (AI 기능 테스트용)")
    st.markdown("---")
    
    # 사이드바 메뉴 (테스트용)
    st.sidebar.markdown("### 🧪 AI 기능 테스트")
    menu = st.sidebar.selectbox(
        "메뉴 선택",
        ["🏠 대시보드", "➕ 테스트 생성", "📊 테스트 관리", "📈 결과 분석", "👀 페이지 미리보기", 
         "🤖 자동 생성기", "📋 실험 계약서", "🚨 가드레일", "📊 실시간 모니터링"]
    )
    
    if menu == "🏠 대시보드":
        show_dashboard()
    elif menu == "➕ 테스트 생성":
        create_test()
    elif menu == "📊 테스트 관리":
        manage_tests()
    elif menu == "📈 결과 분석":
        analyze_results()
    elif menu == "👀 페이지 미리보기":
        preview_pages()
    elif menu == "🤖 자동 생성기":
        show_autopilot()
    elif menu == "📋 실험 계약서":
        show_experiment_brief()
    elif menu == "🚨 가드레일":
        show_guardrails()
    elif menu == "📊 실시간 모니터링":
        show_real_time_monitoring()

def show_dashboard():
    """대시보드 화면"""
    st.header("📊 대시보드")
    
    try:
        # 테스트 목록 조회
        response = requests.get(f"{API_BASE_URL}/api/ab-test/list")
        if response.status_code == 200:
            data = response.json()
            tests = data["tests"]
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("총 테스트 수", len(tests))
            
            with col2:
                active_tests = len([t for t in tests if t["status"] == "active"])
                st.metric("활성 테스트", active_tests)
            
            with col3:
                completed_tests = len([t for t in tests if t["status"] == "completed"])
                st.metric("완료된 테스트", completed_tests)
            
            with col4:
                draft_tests = len([t for t in tests if t["status"] == "draft"])
                st.metric("초안 테스트", draft_tests)
            
            # 최근 테스트 목록
            st.subheader("📋 최근 테스트 목록")
            if tests:
                df = pd.DataFrame(tests)
                df["created_at"] = pd.to_datetime(df["created_at"])
                df = df.sort_values("created_at", ascending=False)
                
                # 상태별 색상 매핑
                status_colors = {
                    "draft": "🟡",
                    "active": "🟢", 
                    "paused": "🟠",
                    "completed": "🔵"
                }
                df["status_icon"] = df["status"].map(status_colors)
                
                for _, test in df.head(5).iterrows():
                    with st.expander(f"{test['status_icon']} {test['test_name']} ({test['product_name']})"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**상태:** {test['status']}")
                        with col2:
                            st.write(f"**변형 수:** {test['variants_count']}")
                        with col3:
                            st.write(f"**생성일:** {test['created_at'].strftime('%Y-%m-%d')}")
                        
                        if test["status"] == "active":
                            if st.button(f"결과 보기", key=f"view_{test['test_id']}"):
                                st.session_state.selected_test = test['test_id']
                                st.rerun()
            else:
                st.info("아직 생성된 테스트가 없습니다.")
        else:
            st.error("테스트 목록을 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

def create_test():
    """테스트 생성 화면"""
    st.header("➕ 새로운 A/B 테스트 생성")
    
    with st.form("create_test_form"):
        st.subheader("📝 테스트 정보")
        
        col1, col2 = st.columns(2)
        with col1:
            test_name = st.text_input("테스트명", placeholder="예: 스마트폰 A/B 테스트")
            product_name = st.text_input("상품명", placeholder="예: 갤럭시 S24 Ultra")
            product_image = st.text_input("상품 이미지 URL", placeholder="https://example.com/image.jpg")
        
        with col2:
            price = st.number_input("가격 (원)", min_value=0, value=1000000, step=10000)
            category = st.text_input("카테고리", placeholder="예: 스마트폰")
            duration_days = st.number_input("테스트 기간 (일)", min_value=1, max_value=90, value=14)
        
        product_description = st.text_area(
            "상품 설명", 
            placeholder="상품에 대한 자세한 설명을 입력하세요...",
            height=100
        )
        
        st.subheader("🎯 목표 지표 설정")
        col1, col2 = st.columns(2)
        with col1:
            ctr_weight = st.slider("CTR 가중치", 0.0, 1.0, 0.6, 0.1)
        with col2:
            conversion_weight = st.slider("전환율 가중치", 0.0, 1.0, 0.4, 0.1)
        
        st.info(f"총 가중치: {ctr_weight + conversion_weight:.1f}")
        
        submitted = st.form_submit_button("테스트 생성")
        
        if submitted:
            if test_name and product_name and product_image and product_description:
                test_data = {
                    "test_name": test_name,
                    "product_name": product_name,
                    "product_image": product_image,
                    "product_description": product_description,
                    "price": price,
                    "category": category,
                    "duration_days": duration_days,
                    "target_metrics": {
                        "ctr": ctr_weight,
                        "conversion_rate": conversion_weight
                    }
                }
                
                try:
                    response = requests.post(f"{API_BASE_URL}/api/ab-test/create", json=test_data)
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ 테스트가 성공적으로 생성되었습니다!")
                        st.info(f"테스트 ID: {result['test_id']}")
                        
                        # 생성된 테스트를 세션에 저장
                        st.session_state.created_test_id = result['test_id']
                        
                        if st.button("테스트 시작하기"):
                            start_test(result['test_id'])
                    else:
                        st.error(f"테스트 생성에 실패했습니다: {response.text}")
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
            else:
                st.error("모든 필수 필드를 입력해주세요.")

def start_test(test_id):
    """테스트 시작"""
    try:
        response = requests.post(f"{API_BASE_URL}/api/ab-test/action", json={
            "test_id": test_id,
            "action": "start"
        })
        if response.status_code == 200:
            st.success("🚀 테스트가 시작되었습니다!")
            st.rerun()
        else:
            st.error("테스트 시작에 실패했습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

def manage_tests():
    """테스트 관리 화면"""
    st.header("📊 테스트 관리")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/ab-test/list")
        if response.status_code == 200:
            data = response.json()
            tests = data["tests"]
            
            if not tests:
                st.info("관리할 테스트가 없습니다.")
                return
            
            # 테스트 선택
            test_options = {f"{t['test_name']} ({t['product_name']})": t['test_id'] for t in tests}
            selected_test_name = st.selectbox("테스트 선택", list(test_options.keys()))
            selected_test_id = test_options[selected_test_name]
            
            # 선택된 테스트 정보 표시
            selected_test = next(t for t in tests if t['test_id'] == selected_test_id)
            
            st.subheader(f"📋 {selected_test['test_name']}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("상태", selected_test['status'])
            with col2:
                st.metric("변형 수", selected_test['variants_count'])
            with col3:
                st.metric("생성일", selected_test['created_at'][:10])
            
            # 액션 버튼
            st.subheader("⚙️ 테스트 액션")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if selected_test['status'] == 'draft':
                    if st.button("🚀 테스트 시작", key="start"):
                        start_test(selected_test_id)
            
            with col2:
                if selected_test['status'] == 'active':
                    if st.button("⏸️ 일시정지", key="pause"):
                        pause_test(selected_test_id)
            
            with col3:
                if selected_test['status'] in ['active', 'paused']:
                    if st.button("✅ 테스트 완료", key="complete"):
                        complete_test(selected_test_id)
            
            # 결과 보기 버튼
            if st.button("📈 결과 보기", key="view_results"):
                st.session_state.selected_test = selected_test_id
                st.rerun()
                
        else:
            st.error("테스트 목록을 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

def pause_test(test_id):
    """테스트 일시정지"""
    try:
        response = requests.post(f"{API_BASE_URL}/api/ab-test/action", json={
            "test_id": test_id,
            "action": "pause"
        })
        if response.status_code == 200:
            st.success("⏸️ 테스트가 일시정지되었습니다!")
            st.rerun()
        else:
            st.error("테스트 일시정지에 실패했습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

def complete_test(test_id):
    """테스트 완료"""
    try:
        response = requests.post(f"{API_BASE_URL}/api/ab-test/action", json={
            "test_id": test_id,
            "action": "complete"
        })
        if response.status_code == 200:
            st.success("✅ 테스트가 완료되었습니다!")
            st.rerun()
        else:
            st.error("테스트 완료에 실패했습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

def analyze_results():
    """결과 분석 화면"""
    st.header("📈 결과 분석")
    
    # 테스트 선택
    try:
        response = requests.get(f"{API_BASE_URL}/api/ab-test/list")
        if response.status_code == 200:
            data = response.json()
            tests = data["tests"]
            
            if not tests:
                st.info("분석할 테스트가 없습니다.")
                return
            
            test_options = {f"{t['test_name']} ({t['product_name']})": t['test_id'] for t in tests}
            selected_test_name = st.selectbox("테스트 선택", list(test_options.keys()))
            selected_test_id = test_options[selected_test_name]
            
            # 결과 조회
            results_response = requests.get(f"{API_BASE_URL}/api/ab-test/{selected_test_id}/results")
            if results_response.status_code == 200:
                results_data = results_response.json()
                results = results_data["results"]
                
                st.subheader(f"📊 {results['test_name']} 결과")
                
                # 전체 통계
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("총 노출", results['total_impressions'])
                with col2:
                    st.metric("총 클릭", results['total_clicks'])
                with col3:
                    st.metric("총 전환", results['total_conversions'])
                with col4:
                    st.metric("총 수익", f"₩{results['total_revenue']:,.0f}")
                
                # 변형별 결과 차트
                if results['variants']:
                    st.subheader("📈 변형별 성과 비교")
                    
                    # 데이터 준비
                    variant_data = []
                    for variant_id, variant_result in results['variants'].items():
                        variant_data.append({
                            '변형': variant_result['variant_type'],
                            'CTR (%)': variant_result['ctr'],
                            '전환율 (%)': variant_result['conversion_rate'],
                            '수익 (원)': variant_result['revenue'],
                            '노출': variant_result['impressions'],
                            '클릭': variant_result['clicks'],
                            '전환': variant_result['conversions']
                        })
                    
                    df = pd.DataFrame(variant_data)
                    
                    # CTR 비교 차트
                    fig_ctr = px.bar(df, x='변형', y='CTR (%)', 
                                   title='변형별 CTR 비교',
                                   color='변형')
                    st.plotly_chart(fig_ctr, use_container_width=True)
                    
                    # 전환율 비교 차트
                    fig_conversion = px.bar(df, x='변형', y='전환율 (%)', 
                                          title='변형별 전환율 비교',
                                          color='변형')
                    st.plotly_chart(fig_conversion, use_container_width=True)
                    
                    # 수익 비교 차트
                    fig_revenue = px.bar(df, x='변형', y='수익 (원)', 
                                       title='변형별 수익 비교',
                                       color='변형')
                    st.plotly_chart(fig_revenue, use_container_width=True)
                    
                    # 상세 결과 테이블
                    st.subheader("📋 상세 결과")
                    st.dataframe(df, use_container_width=True)
                    
                    # 승자 표시
                    if results['winner']:
                        st.success(f"🏆 승자: 변형 {results['winner']}")
                    else:
                        st.info("🤔 아직 승자가 결정되지 않았습니다.")
                        
            else:
                st.error("결과를 불러올 수 없습니다.")
        else:
            st.error("테스트 목록을 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

def preview_pages():
    """페이지 미리보기 화면"""
    st.header("👀 페이지 미리보기")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/ab-test/list")
        if response.status_code == 200:
            data = response.json()
            tests = data["tests"]
            
            if not tests:
                st.info("미리보기할 테스트가 없습니다.")
                return
            
            test_options = {f"{t['test_name']} ({t['product_name']})": t['test_id'] for t in tests}
            selected_test_name = st.selectbox("테스트 선택", list(test_options.keys()))
            selected_test_id = test_options[selected_test_name]
            
            # 테스트 결과에서 variant_id 가져오기
            results_response = requests.get(f"{API_BASE_URL}/api/ab-test/{selected_test_id}/results")
            if results_response.status_code == 200:
                results_data = results_response.json()
                results = results_data["results"]
                
                if results['variants']:
                    st.subheader("🎨 페이지 미리보기")
                    
                    # 변형 선택
                    variant_options = {f"변형 {v['variant_type']}": k for k, v in results['variants'].items()}
                    selected_variant_name = st.selectbox("변형 선택", list(variant_options.keys()))
                    selected_variant_id = variant_options[selected_variant_name]
                    
                    # 페이지 URL 생성
                    page_url = f"{API_BASE_URL}/api/ab-test/{selected_test_id}/page/{selected_variant_id}"
                    
                    st.info(f"페이지 URL: {page_url}")
                    
                    # iframe으로 페이지 미리보기
                    st.subheader(f"📱 {selected_variant_name} 미리보기")
                    
                    # iframe 높이 설정
                    iframe_height = 800
                    
                    st.components.v1.iframe(
                        page_url,
                        height=iframe_height,
                        scrolling=True
                    )
                    
                    # 새 탭에서 열기 버튼
                    if st.button("🔄 새 탭에서 열기"):
                        st.markdown(f'<a href="{page_url}" target="_blank">페이지 열기</a>', unsafe_allow_html=True)
                        
                else:
                    st.info("아직 변형이 생성되지 않았습니다.")
            else:
                st.error("테스트 결과를 불러올 수 없습니다.")
        else:
            st.error("테스트 목록을 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

def show_autopilot():
    """자동 생성기 화면 - 요구사항 3번, 11번"""
    st.header("🤖 자동 생성기 (Autopilot)")
    st.info("자동 생성기 기능이 구현되었습니다. API를 통해 관리할 수 있습니다.")
    
    # API 엔드포인트 정보 표시
    st.subheader("📋 API 엔드포인트")
    st.code("""
GET /api/abtest/autopilot/status
POST /api/abtest/autopilot/promotion-mode
POST /api/abtest/autopilot/run-cycle
    """)

def show_experiment_brief():
    """실험 계약서 화면 - 요구사항 1번"""
    st.header("📋 실험 계약서 생성")
    st.info("실험 계약서 기능이 구현되었습니다. API를 통해 생성할 수 있습니다.")
    
    # API 엔드포인트 정보 표시
    st.subheader("📋 API 엔드포인트")
    st.code("""
POST /api/abtest/create-with-brief
    """)

def show_guardrails():
    """가드레일 모니터링 화면 - 요구사항 6번"""
    st.header("🚨 가드레일 모니터링")
    st.info("가드레일 모니터링 기능이 구현되었습니다. API를 통해 확인할 수 있습니다.")
    
    # API 엔드포인트 정보 표시
    st.subheader("📋 API 엔드포인트")
    st.code("""
GET /api/abtest/guardrails/alerts
    """)

def show_real_time_monitoring():
    """실시간 모니터링 화면 - 요구사항 9번"""
    st.header("📊 실시간 모니터링")
    st.info("실시간 모니터링 기능이 구현되었습니다. API를 통해 확인할 수 있습니다.")
    
    # API 엔드포인트 정보 표시
    st.subheader("📋 API 엔드포인트")
    st.code("""
GET /api/abtest/dashboard/real-time/{test_id}
GET /api/abtest/bandit/decisions/{test_id}
    """)

if __name__ == "__main__":
    main()


