#!/usr/bin/env python3
"""
A/B 테스트 시스템 프론트엔드
Streamlit을 사용한 웹 인터페이스
"""

import streamlit as st
import requests
import json
import time
import random
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# 브라우저 경고 줄이기 위한 설정
st.set_page_config(
    page_title="A/B 테스트 시스템",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사용자 정의 CSS와 JavaScript로 브라우저 경고 숨기기
st.markdown("""
<style>
    /* 브라우저 경고 메시지 숨기기 */
    .stDeployButton {display: none;}
    
    /* 스크롤바 스타일링 */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
    }
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    
    /* 전역 스타일 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* 메트릭 카드 스타일 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
</style>

<script>
// 브라우저 콘솔 경고 줄이기
(function() {
    'use strict';
    
    // Feature Policy 경고 숨기기
    const originalWarn = console.warn;
    console.warn = function(...args) {
        const message = args.join(' ');
        
        // 특정 경고 메시지 필터링
        const ignoredWarnings = [
            'Unrecognized feature:',
            'ambient-light-sensor',
            'battery',
            'document-domain',
            'layout-animations',
            'legacy-image-formats',
            'oversized-images',
            'vr',
            'wake-lock'
        ];
        
        const shouldIgnore = ignoredWarnings.some(warning => 
            message.includes(warning)
        );
        
        if (!shouldIgnore) {
            originalWarn.apply(console, args);
        }
    };
    
    // Feature Policy 설정
    if ('featurePolicy' in document) {
        try {
            document.featurePolicy.allowsFeature('ambient-light-sensor');
            document.featurePolicy.allowsFeature('battery');
            document.featurePolicy.allowsFeature('document-domain');
            document.featurePolicy.allowsFeature('layout-animations');
            document.featurePolicy.allowsFeature('legacy-image-formats');
            document.featurePolicy.allowsFeature('oversized-images');
            document.featurePolicy.allowsFeature('vr');
            document.featurePolicy.allowsFeature('wake-lock');
        } catch (e) {
            // 무시
        }
    }
    
    // 성능 최적화
    if ('requestIdleCallback' in window) {
        requestIdleCallback(() => {
            // 페이지 로드 후 정리 작업
        });
    }
    
    // 에러 핸들링 개선
    window.addEventListener('error', function(e) {
        // 중요하지 않은 에러는 무시
        if (e.message.includes('Feature Policy') || 
            e.message.includes('Unrecognized feature')) {
            e.preventDefault();
            return false;
        }
    });
    
})();
</script>
""", unsafe_allow_html=True)

# API 기본 URL
API_BASE_URL = "http://localhost:5001"

def main():
    st.title("🧪 상품 상세페이지 A/B 테스트 시스템 (AI 기능 테스트용)")
    st.markdown("---")
    
    # 사이드바 메뉴 (테스트용)
    st.sidebar.markdown("### 🧪 AI 기능 테스트")
    menu = st.sidebar.selectbox(
        "메뉴 선택",
        ["🏠 대시보드", "➕ 테스트 생성", "📊 테스트 관리", "📈 결과 분석", "👀 페이지 미리보기", 
         "🧪 A/B 테스트 시뮬레이션", "🤖 자동 생성기", "📋 실험 계약서", "🚨 가드레일", "📊 실시간 모니터링"]
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
    elif menu == "🧪 A/B 테스트 시뮬레이션":
        show_ab_test_simulation()
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
        response = requests.get(f"{API_BASE_URL}/api/abtest/list")
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
    
    # 테스트 생성 성공 메시지 표시
    if st.session_state.get('test_created', False):
        result = st.session_state.get('test_result', {})
        st.success(f"✅ 테스트가 성공적으로 생성되었습니다!")
        st.info(f"테스트 ID: {result.get('test_id', 'N/A')}")
        
        # 테스트 시작 버튼
        if st.button("🚀 테스트 시작하기", key="start_test_btn"):
            start_test(result.get('test_id'))
            # 세션 상태 초기화
            st.session_state.test_created = False
            st.session_state.test_result = {}
            st.rerun()
        
        st.markdown("---")
    
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
                    response = requests.post(f"{API_BASE_URL}/api/abtest/create", json=test_data)
                    if response.status_code == 200:
                        result = response.json()
                        # 생성된 테스트를 세션에 저장
                        st.session_state.created_test_id = result['test_id']
                        st.session_state.test_created = True
                        st.session_state.test_result = result
                        st.rerun()
                    else:
                        st.error(f"테스트 생성에 실패했습니다: {response.text}")
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
            else:
                st.error("모든 필수 필드를 입력해주세요.")

def start_test(test_id):
    """테스트 시작"""
    try:
        response = requests.post(f"{API_BASE_URL}/api/abtest/action", json={
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
        response = requests.get(f"{API_BASE_URL}/api/abtest/list")
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
        response = requests.post(f"{API_BASE_URL}/api/abtest/action", json={
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
        response = requests.post(f"{API_BASE_URL}/api/abtest/action", json={
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
        response = requests.get(f"{API_BASE_URL}/api/abtest/list")
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
            results_response = requests.get(f"{API_BASE_URL}/api/abtest/{selected_test_id}/results")
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
                
                # 승자 정보 표시
                if results.get('winner'):
                    st.success(f"🏆 **승자: 변형 {results['winner']}**")
                else:
                    st.info("🤔 아직 승자가 결정되지 않았습니다.")
                
                # 변형별 결과 차트
                if results['variants']:
                    st.subheader("📈 변형별 성과 비교")
                    
                    # 데이터 준비
                    variant_data = []
                    for variant_id, variant_result in results['variants'].items():
                        is_winner = results.get('winner') == variant_id
                        variant_data.append({
                            '변형': f"{variant_result['variant_type']}{' 🏆' if is_winner else ''}",
                            'CTR (%)': variant_result['ctr'],
                            '전환율 (%)': variant_result['conversion_rate'],
                            '수익 (원)': variant_result['revenue'],
                            '노출': variant_result['impressions'],
                            '클릭': variant_result['clicks'],
                            '전환': variant_result['conversions'],
                            '통계적 유의성': variant_result.get('statistical_significance', 0)
                        })
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
        response = requests.get(f"{API_BASE_URL}/api/abtest/list")
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
            results_response = requests.get(f"{API_BASE_URL}/api/abtest/{selected_test_id}/results")
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
                    page_url = f"{API_BASE_URL}/api/abtest/{selected_test_id}/page/{selected_variant_id}"
                    
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

def show_ab_test_simulation():
    """A/B 테스트 시뮬레이션 화면"""
    st.header("🧪 A/B 테스트 시뮬레이션")
    st.info("실제 사용자 행동을 시뮬레이션하여 A/B 테스트가 제대로 작동하는지 확인할 수 있습니다.")
    
    try:
        # 활성 테스트 목록 조회
        response = requests.get(f"{API_BASE_URL}/api/abtest/list")
        if response.status_code == 200:
            data = response.json()
            tests = data["tests"]
            
            # 활성 테스트만 필터링
            active_tests = [t for t in tests if t["status"] == "active"]
            
            if not active_tests:
                st.warning("활성 상태인 테스트가 없습니다. 먼저 테스트를 생성하고 시작해주세요.")
                return
            
            # 테스트 선택
            test_options = {f"{t['test_name']} ({t['product_name']})": t['test_id'] for t in active_tests}
            selected_test_name = st.selectbox("시뮬레이션할 테스트 선택", list(test_options.keys()))
            selected_test_id = test_options[selected_test_name]
            
            st.markdown("---")
            
            # 시뮬레이션 설정
            st.subheader("⚙️ 시뮬레이션 설정")
            
            col1, col2 = st.columns(2)
            with col1:
                user_count = st.number_input("시뮬레이션할 사용자 수", min_value=1, max_value=100, value=10)
                impression_rate = st.slider("노출 확률 (%)", 0, 100, 80)
            with col2:
                click_rate = st.slider("클릭 확률 (%)", 0, 100, 15)
                conversion_rate = st.slider("구매 확률 (%)", 0, 100, 3)
            
            st.markdown("---")
            
            # 시뮬레이션 실행
            if st.button("🚀 시뮬레이션 시작", type="primary"):
                with st.spinner("시뮬레이션을 실행 중입니다..."):
                    simulate_user_behavior(selected_test_id, user_count, impression_rate, click_rate, conversion_rate)
                
                st.success("✅ 시뮬레이션이 완료되었습니다!")
                st.rerun()
            
            st.markdown("---")
            
            # 실시간 결과 표시
            st.subheader("📊 실시간 결과")
            if st.button("🔄 결과 새로고침"):
                st.rerun()
            
            # 테스트 결과 조회
            results_response = requests.get(f"{API_BASE_URL}/api/abtest/{selected_test_id}/results")
            if results_response.status_code == 200:
                results_data = results_response.json()
                results = results_data["results"]
                
                # 전체 통계
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("총 노출수", results.get("total_impressions", 0))
                with col2:
                    st.metric("총 클릭수", results.get("total_clicks", 0))
                with col3:
                    st.metric("총 구매수", results.get("total_conversions", 0))
                with col4:
                    total_revenue = results.get("total_revenue", 0)
                    st.metric("총 매출", f"₩{total_revenue:,}")
                
                # 변형별 성과
                st.subheader("🎯 변형별 성과")
                variants = results.get("variants", {})
                
                if variants:
                    # 데이터프레임 생성
                    variant_data = []
                    for variant_id, variant in variants.items():
                        variant_data.append({
                            "변형": variant["variant_type"],
                            "노출수": variant["impressions"],
                            "클릭수": variant["clicks"],
                            "구매수": variant["conversions"],
                            "CTR (%)": round(variant["ctr"], 2),
                            "전환율 (%)": round(variant["conversion_rate"], 2),
                            "매출": f"₩{variant['revenue']:,}",
                            "승률 (%)": round(variant["win_probability"] * 100, 1)
                        })
                    
                    df = pd.DataFrame(variant_data)
                    st.dataframe(df, use_container_width=True)
                    
                    # 차트 표시
                    if len(variant_data) > 1:
                        st.subheader("📈 성과 차트")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            # CTR 차트
                            fig_ctr = px.bar(df, x="변형", y="CTR (%)", title="변형별 CTR 비교")
                            st.plotly_chart(fig_ctr, use_container_width=True)
                        
                        with col2:
                            # 전환율 차트
                            fig_conv = px.bar(df, x="변형", y="전환율 (%)", title="변형별 전환율 비교")
                            st.plotly_chart(fig_conv, use_container_width=True)
                else:
                    st.info("아직 변형 데이터가 없습니다.")
            else:
                st.error("테스트 결과를 불러올 수 없습니다.")
        else:
            st.error("테스트 목록을 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

def simulate_user_behavior(test_id, user_count, impression_rate, click_rate, conversion_rate):
    """사용자 행동 시뮬레이션"""
    
    # 테스트 정보 조회
    response = requests.get(f"{API_BASE_URL}/api/abtest/{test_id}/results")
    if response.status_code != 200:
        st.error("테스트 정보를 불러올 수 없습니다.")
        return
    
    results_data = response.json()
    results = results_data["results"]
    variants = results.get("variants", {})
    
    if not variants:
        st.error("변형 정보를 찾을 수 없습니다.")
        return
    
    variant_ids = list(variants.keys())
    
    # 사용자별 시뮬레이션
    for i in range(user_count):
        user_id = f"sim_user_{i+1}"
        session_id = f"sim_session_{i+1}"
        
        # 랜덤 변형 선택 (실제 A/B 테스트 로직 사용)
        variant_response = requests.get(f"{API_BASE_URL}/api/abtest/{test_id}/variant/{user_id}")
        if variant_response.status_code == 200:
            variant_data = variant_response.json()
            variant_id = variant_data["variant"]["variant_id"]
        else:
            # API 호출 실패 시 랜덤 선택
            variant_id = random.choice(variant_ids)
        
        # 노출 이벤트
        if random.randint(1, 100) <= impression_rate:
            requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                "test_id": test_id,
                "variant_id": variant_id,
                "event_type": "impression",
                "user_id": user_id,
                "session_id": session_id
            })
            
            # 클릭 이벤트
            if random.randint(1, 100) <= click_rate:
                requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                    "test_id": test_id,
                    "variant_id": variant_id,
                    "event_type": "click",
                    "user_id": user_id,
                    "session_id": session_id
                })
                
                # 구매 이벤트
                if random.randint(1, 100) <= conversion_rate:
                    # 매출은 상품가격으로 고정 (같은 제품이므로)
                    requests.post(f"{API_BASE_URL}/api/abtest/event", json={
                        "test_id": test_id,
                        "variant_id": variant_id,
                        "event_type": "conversion",
                        "user_id": user_id,
                        "session_id": session_id
                    })
        
        # API 호출 간격 조절
        time.sleep(0.1)

if __name__ == "__main__":
    main()


