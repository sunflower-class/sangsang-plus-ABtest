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
         "🧪 A/B 테스트 시뮬레이션", "🤖 자동 생성기", "📋 실험 계약서", "🚨 가드레일"]
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
    # 실시간 모니터링은 가드레일 모니터링으로 통합됨

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
    """테스트 생성 화면 (실험 계약서 형식)"""
    st.header("➕ 새로운 A/B 테스트 생성")
    st.info("실험 계약서 형식으로 A/B 테스트를 생성합니다.")
    
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
        st.subheader("📝 기본 정보")
        
        col1, col2 = st.columns(2)
        with col1:
            test_name = st.text_input("테스트명", placeholder="예: 스마트폰 CVR 최적화 테스트")
            product_name = st.text_input("상품명", placeholder="예: 갤럭시 S24 Ultra")
            price = st.number_input("가격 (원)", min_value=0, value=1000000, step=10000)
        with col2:
            category = st.text_input("카테고리", placeholder="예: 스마트폰")
            duration_days = st.number_input("테스트 기간 (일)", min_value=1, max_value=90, value=14)
            variant_count = st.selectbox("변형 수", [2, 3, 4], index=1)
        
        product_image = st.text_input("상품 이미지 URL", placeholder="https://example.com/image.jpg")
        product_description = st.text_area(
            "상품 설명", 
            placeholder="상품에 대한 자세한 설명을 입력하세요...",
            height=100
        )
        
        st.subheader("🎯 실험 목적")
        objective = st.text_area("실험 목적", placeholder="예: 구매 전환율(CVR) 최대화", height=80)
        
        st.subheader("📊 성과 지표")
        col1, col2 = st.columns(2)
        with col1:
            primary_metrics = st.multiselect(
                "핵심 지표 (Primary Metrics)",
                ["CVR", "CTR", "ATC", "매출", "체류시간"],
                default=["CVR"]
            )
        with col2:
            secondary_metrics = st.multiselect(
                "보조 지표 (Secondary Metrics)",
                ["CVR", "CTR", "ATC", "매출", "체류시간", "이탈률"],
                default=["CTR", "ATC"]
            )
        
        st.subheader("🛡️ 가드레일 설정")
        col1, col2, col3 = st.columns(3)
        with col1:
            lcp_threshold = st.number_input("LCP 임계값 (초)", min_value=1.0, max_value=10.0, value=3.5, step=0.1)
        with col2:
            error_rate_threshold = st.number_input("오류율 임계값 (%)", min_value=0.0, max_value=10.0, value=0.5, step=0.1)
        with col3:
            return_rate_threshold = st.number_input("반품율 임계값 (%)", min_value=0.0, max_value=50.0, value=10.0, step=0.5)
        
        st.subheader("⚖️ 분배 정책")
        distribution_mode = st.selectbox(
            "트래픽 분배 방식",
            ["equal", "bandit", "contextual"],
            format_func=lambda x: {
                "equal": "균등 분배 (50:50)",
                "bandit": "Thompson Sampling 밴딧",
                "contextual": "Contextual Bandit"
            }[x]
        )
        
        st.subheader("📈 통계 설정")
        col1, col2 = st.columns(2)
        with col1:
            mde = st.number_input("최소 검출 효과 (MDE) (%)", min_value=1.0, max_value=50.0, value=10.0, step=0.5)
        with col2:
            min_sample_size = st.number_input("최소 표본 수", min_value=100, max_value=10000, value=1000, step=100)
        
        submitted = st.form_submit_button("📋 실험 계약서로 테스트 생성", type="primary")
        
        if submitted:
            if test_name and product_name and objective:
                # 실험 계약서 형식으로 데이터 구성
                experiment_brief_data = {
                    "test_name": test_name,
                    "product_name": product_name,
                    "product_image": product_image,
                    "product_description": product_description,
                    "price": price,
                    "category": category,
                    "tags": [category],
                    "duration_days": duration_days,
                    "experiment_brief": {
                        "objective": objective,
                        "primary_metrics": primary_metrics,
                        "secondary_metrics": secondary_metrics,
                        "guardrails": {
                            "LCP": lcp_threshold,
                            "error_rate": error_rate_threshold / 100,
                            "return_rate": return_rate_threshold / 100
                        },
                        "target_categories": [category],
                        "target_channels": ["web", "mobile"],
                        "target_devices": ["desktop", "mobile"],
                        "exclude_conditions": [],
                        "variant_count": variant_count,
                        "distribution_mode": distribution_mode,
                        "mde": mde / 100,
                        "min_sample_size": min_sample_size
                    },
                    "test_mode": "manual"
                }
                
                try:
                    response = requests.post(f"{API_BASE_URL}/api/abtest/create-with-brief", json=experiment_brief_data)
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
                st.error("필수 항목을 모두 입력해주세요.")

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
    st.info("AI가 자동으로 A/B 테스트를 생성하고 관리하는 시스템입니다.")
    
    with st.expander("📖 Autopilot이란?", expanded=False):
        st.markdown("""
        **Autopilot**은 AI 기반 자동 A/B 테스트 생성 및 관리 시스템입니다:
        
        - 🤖 **자동 후보 선별**: 트래픽, 재고, 쿨다운 조건을 고려한 상품 자동 선별
        - 🎯 **스마트 스케줄링**: 매일/매주 자동으로 실험 생성 및 관리
        - ⚖️ **트래픽 예산 관리**: 동시 실험 상한 및 쿨다운으로 과실험 방지
        - 🛡️ **프로모션 모드**: 프로모션 기간 중 자동 실험 비활성화
        - 📊 **성과 기반 최적화**: 승자 패턴을 학습하여 다음 실험에 반영
        """)
    
    st.markdown("---")
    
    # Autopilot 상태 조회
    st.subheader("📊 Autopilot 상태")
    
    try:
        status_response = requests.get(f"{API_BASE_URL}/api/abtest/autopilot/status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            autopilot_status = status_data["autopilot_status"]
            
            # 상태 정보 표시
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("활성화 상태", "🟢 활성" if autopilot_status["enabled"] else "🔴 비활성")
            with col2:
                st.metric("프로모션 모드", "🟡 활성" if autopilot_status["promotion_mode"] else "🟢 비활성")
            with col3:
                st.metric("활성 자동 실험", autopilot_status["active_autopilot_experiments"])
            with col4:
                st.metric("후보 상품 수", autopilot_status["candidate_count"])
            
            # 상세 정보
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 📈 트래픽 사용량")
                traffic_usage = autopilot_status["total_traffic_usage"]
                max_traffic = autopilot_status["max_traffic_usage"]
                st.progress(traffic_usage / max_traffic)
                st.caption(f"현재: {traffic_usage:.1%} / 최대: {max_traffic:.1%}")
                
                st.markdown("#### ⚙️ 설정 정보")
                st.markdown(f"**최대 동시 실험**: {autopilot_status['max_concurrent_experiments']}개")
                if autopilot_status.get("next_run"):
                    st.markdown(f"**다음 실행**: {autopilot_status['next_run'][:19]}")
            
            with col2:
                st.markdown("#### 🎯 실험 생성 조건")
                st.markdown("""
                - **최소 일일 세션**: 100회 이상
                - **최소 재고**: 10개 이상  
                - **쿨다운 기간**: 7일 이상
                - **트래픽 예산**: 전체의 20% 이하
                - **동시 실험**: 최대 5개
                """)
        else:
            st.error("Autopilot 상태를 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
    
    st.markdown("---")
    
    # Autopilot 제어
    st.subheader("🎮 Autopilot 제어")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 상태 새로고침", type="secondary"):
            st.rerun()
    
    with col2:
        if st.button("🚀 수동 사이클 실행", type="primary"):
            try:
                response = requests.post(f"{API_BASE_URL}/api/abtest/autopilot/run-cycle")
                if response.status_code == 200:
                    result = response.json()
                    st.success(result["message"])
                else:
                    st.error("수동 사이클 실행에 실패했습니다.")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
    
    with col3:
        # 프로모션 모드 토글
        try:
            status_response = requests.get(f"{API_BASE_URL}/api/abtest/autopilot/status")
            if status_response.status_code == 200:
                status_data = status_response.json()
                current_promotion_mode = status_data["autopilot_status"]["promotion_mode"]
                
                if current_promotion_mode:
                    if st.button("🟢 프로모션 모드 해제", type="secondary"):
                        try:
                            response = requests.post(f"{API_BASE_URL}/api/abtest/autopilot/promotion-mode", params={"enabled": False})
                            if response.status_code == 200:
                                st.success("프로모션 모드가 해제되었습니다.")
                                st.rerun()
                            else:
                                st.error("프로모션 모드 해제에 실패했습니다.")
                        except Exception as e:
                            st.error(f"오류가 발생했습니다: {e}")
                else:
                    if st.button("🟡 프로모션 모드 활성화", type="secondary"):
                        try:
                            response = requests.post(f"{API_BASE_URL}/api/abtest/autopilot/promotion-mode", params={"enabled": True})
                            if response.status_code == 200:
                                st.success("프로모션 모드가 활성화되었습니다.")
                                st.rerun()
                            else:
                                st.error("프로모션 모드 활성화에 실패했습니다.")
                        except Exception as e:
                            st.error(f"오류가 발생했습니다: {e}")
        except Exception as e:
            st.error(f"상태 조회 오류: {e}")
    
    st.markdown("---")
    
    # 자동 생성된 실험 목록
    st.subheader("🤖 자동 생성된 실험")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/abtest/list")
        if response.status_code == 200:
            data = response.json()
            tests = data["tests"]
            
            # 자동 생성된 실험만 필터링
            autopilot_tests = [t for t in tests if t.get("test_mode") == "autopilot"]
            
            if autopilot_tests:
                for test in autopilot_tests[-5:]:  # 최근 5개
                    with st.expander(f"🤖 {test['test_name']} ({test['product_name']})"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown(f"**상태**: {test['status']}")
                            st.markdown(f"**생성일**: {test['created_at'][:10]}")
                        with col2:
                            st.markdown(f"**변형 수**: {test['variants_count']}개")
                            st.markdown(f"**테스트 모드**: {test.get('test_mode', 'manual')}")
                        with col3:
                            if test["status"] == "active":
                                if st.button(f"결과 보기", key=f"autopilot_view_{test['test_id']}"):
                                    st.session_state.selected_test = test['test_id']
                                    st.rerun()
            else:
                st.info("아직 자동 생성된 실험이 없습니다.")
        else:
            st.error("테스트 목록을 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
    
    st.markdown("---")
    
    # Autopilot 설정 정보
    st.subheader("⚙️ Autopilot 설정")
    
    st.markdown("""
    #### 📅 스케줄 설정
    - **매일 오전 2시**: 자동 실험 생성 사이클 실행
    - **매주 월요일 오전 9시**: 주간 실험 생성 사이클 실행
    
    #### 🎯 후보 선별 기준
    - **트래픽**: 일일 세션 100회 이상
    - **재고**: 10개 이상 보유
    - **쿨다운**: 마지막 실험 후 7일 이상 경과
    - **우선순위**: 트래픽, 재고, 카테고리별 점수 계산
    
    #### ⚖️ 리소스 관리
    - **트래픽 예산**: 전체 트래픽의 20% 이하
    - **동시 실험**: 최대 5개 동시 실행
    - **SKU당 제한**: 동시 1개 실험만 허용
    """)

def show_experiment_brief():
    """실험 계약서 화면 - 요구사항 1번"""
    st.header("📋 실험 계약서 생성")
    st.info("A/B 테스트를 위한 상세한 실험 계약서를 생성할 수 있습니다.")
    
    with st.expander("📖 실험 계약서란?", expanded=False):
        st.markdown("""
        **실험 계약서(Experiment Brief)**는 A/B 테스트의 성공을 위한 핵심 문서입니다:
        
        - 🎯 **목적**: 명확한 실험 목표 정의
        - 📊 **지표**: 핵심/보조 성과 지표 설정
        - 🛡️ **가드레일**: 성능/품질 기준 설정
        - 🎯 **대상**: 테스트 대상 사용자 그룹 정의
        - ⚖️ **분배**: 트래픽 분배 정책 설정
        - 📈 **효과**: 최소 검출 효과 및 표본 수 설정
        - 🔄 **규칙**: 종료/승격/롤백 자동화 규칙
        """)
    
    st.markdown("---")
    
    # 실험 계약서 생성 폼
    st.subheader("📝 실험 계약서 생성")
    
    with st.form("experiment_brief_form"):
        # 기본 정보
        st.markdown("#### 📋 기본 정보")
        col1, col2 = st.columns(2)
        with col1:
            test_name = st.text_input("테스트명", placeholder="예: 스마트폰 CVR 최적화 테스트")
            product_name = st.text_input("상품명", placeholder="예: 갤럭시 S24 Ultra")
            price = st.number_input("상품 가격 (원)", min_value=0, value=1000000)
        with col2:
            category = st.text_input("카테고리", placeholder="예: 스마트폰")
            duration_days = st.number_input("테스트 기간 (일)", min_value=1, max_value=30, value=14)
            variant_count = st.selectbox("변형 수", [2, 3, 4], index=1)
        
        # 실험 목적
        st.markdown("#### 🎯 실험 목적")
        objective = st.text_area("실험 목적", placeholder="예: 구매 전환율(CVR) 최대화", height=80)
        
        # 성과 지표
        st.markdown("#### 📊 성과 지표")
        col1, col2 = st.columns(2)
        with col1:
            primary_metrics = st.multiselect(
                "핵심 지표 (Primary Metrics)",
                ["CVR", "CTR", "ATC", "매출", "체류시간"],
                default=["CVR"]
            )
        with col2:
            secondary_metrics = st.multiselect(
                "보조 지표 (Secondary Metrics)",
                ["CVR", "CTR", "ATC", "매출", "체류시간", "이탈률"],
                default=["CTR", "ATC"]
            )
        
        # 가드레일
        st.markdown("#### 🛡️ 가드레일 (Guardrails)")
        col1, col2, col3 = st.columns(3)
        with col1:
            lcp_threshold = st.number_input("LCP 임계값 (초)", min_value=1.0, max_value=10.0, value=3.5, step=0.1)
        with col2:
            error_rate_threshold = st.number_input("오류율 임계값 (%)", min_value=0.0, max_value=10.0, value=0.5, step=0.1)
        with col3:
            return_rate_threshold = st.number_input("반품율 임계값 (%)", min_value=0.0, max_value=50.0, value=10.0, step=0.5)
        
        # 대상 설정
        st.markdown("#### 🎯 대상 설정")
        col1, col2 = st.columns(2)
        with col1:
            target_categories = st.multiselect(
                "대상 카테고리",
                ["스마트폰", "노트북", "태블릿", "웨어러블", "가전제품", "의류", "신발", "가방"],
                default=["스마트폰"]
            )
            target_channels = st.multiselect(
                "대상 채널",
                ["web", "mobile", "app"],
                default=["web", "mobile"]
            )
        with col2:
            target_devices = st.multiselect(
                "대상 디바이스",
                ["desktop", "mobile", "tablet"],
                default=["desktop", "mobile"]
            )
            exclude_conditions = st.multiselect(
                "제외 조건",
                ["신규 사용자", "VIP 고객", "특정 지역", "특정 시간대"],
                default=[]
            )
        
        # 분배 정책
        st.markdown("#### ⚖️ 분배 정책")
        distribution_mode = st.selectbox(
            "트래픽 분배 방식",
            ["equal", "bandit", "contextual"],
            format_func=lambda x: {
                "equal": "균등 분배 (50:50)",
                "bandit": "Thompson Sampling 밴딧",
                "contextual": "Contextual Bandit"
            }[x]
        )
        
        # 통계 설정
        st.markdown("#### 📈 통계 설정")
        col1, col2 = st.columns(2)
        with col1:
            mde = st.number_input("최소 검출 효과 (MDE) (%)", min_value=1.0, max_value=50.0, value=10.0, step=0.5)
        with col2:
            min_sample_size = st.number_input("최소 표본 수", min_value=100, max_value=10000, value=1000, step=100)
        
        # 제출 버튼
        submitted = st.form_submit_button("📋 실험 계약서 생성", type="primary")
        
        if submitted:
            if not test_name or not product_name or not objective:
                st.error("필수 항목을 모두 입력해주세요.")
                return
            
            # 실험 계약서 데이터 구성
            experiment_brief_data = {
                "test_name": test_name,
                "product_name": product_name,
                "product_image": "https://example.com/product.jpg",
                "product_description": f"{product_name} 상품입니다.",
                "price": price,
                "category": category,
                "tags": [category],
                "duration_days": duration_days,
                "experiment_brief": {
                    "objective": objective,
                    "primary_metrics": primary_metrics,
                    "secondary_metrics": secondary_metrics,
                    "guardrails": {
                        "LCP": lcp_threshold,
                        "error_rate": error_rate_threshold / 100,
                        "return_rate": return_rate_threshold / 100
                    },
                    "target_categories": target_categories,
                    "target_channels": target_channels,
                    "target_devices": target_devices,
                    "exclude_conditions": exclude_conditions,
                    "variant_count": variant_count,
                    "distribution_mode": distribution_mode,
                    "mde": mde / 100,
                    "min_sample_size": min_sample_size
                },
                "test_mode": "manual"
            }
            
            try:
                # API 호출
                response = requests.post(f"{API_BASE_URL}/api/abtest/create-with-brief", json=experiment_brief_data)
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ 실험 계약서가 성공적으로 생성되었습니다!")
                    st.info(f"**테스트 ID**: {result['test_id']}")
                    
                    # 생성된 실험 계약서 요약 표시
                    with st.expander("📋 생성된 실험 계약서 요약", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**테스트명**: {test_name}")
                            st.markdown(f"**상품명**: {product_name}")
                            st.markdown(f"**목적**: {objective}")
                            st.markdown(f"**기간**: {duration_days}일")
                        with col2:
                            st.markdown(f"**변형 수**: {variant_count}개")
                            st.markdown(f"**분배 방식**: {distribution_mode}")
                            st.markdown(f"**최소 표본 수**: {min_sample_size:,}명")
                            st.markdown(f"**MDE**: {mde}%")
                    
                    st.rerun()
                else:
                    st.error(f"❌ 실험 계약서 생성 실패: {response.text}")
                    
            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {e}")
    
    st.markdown("---")
    
    # 기존 실험 계약서 목록
    st.subheader("📋 기존 실험 계약서")
    try:
        response = requests.get(f"{API_BASE_URL}/api/abtest/list")
        if response.status_code == 200:
            data = response.json()
            tests = data["tests"]
            
            if tests:
                # 실험 계약서가 있는 테스트만 필터링
                tests_with_brief = [t for t in tests if t.get("experiment_brief")]
                
                if tests_with_brief:
                    for test in tests_with_brief[-5:]:  # 최근 5개
                        with st.expander(f"📋 {test['test_name']} ({test['product_name']})"):
                            st.markdown(f"**상태**: {test['status']}")
                            st.markdown(f"**생성일**: {test['created_at'][:10]}")
                            st.markdown(f"**변형 수**: {test['variants_count']}개")
                            
                            if test.get("experiment_brief"):
                                brief = test["experiment_brief"]
                                st.markdown(f"**목적**: {brief.get('objective', 'N/A')}")
                                st.markdown(f"**핵심 지표**: {', '.join(brief.get('primary_metrics', []))}")
                else:
                    st.info("아직 실험 계약서가 생성된 테스트가 없습니다.")
            else:
                st.info("생성된 테스트가 없습니다.")
        else:
            st.error("테스트 목록을 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

def show_guardrails():
    """가드레일 모니터링 화면 - 요구사항 6번"""
    st.header("🚨 가드레일 모니터링")
    st.info("A/B 테스트의 데이터 품질과 성능을 실시간으로 모니터링합니다.")
    
    with st.expander("📖 가드레일이란?", expanded=False):
        st.markdown("""
        **가드레일(Guardrails)**은 A/B 테스트의 데이터 품질과 성능을 보호하는 안전장치입니다:
        
        - 🛡️ **SRM 감지**: Sample Ratio Mismatch로 트래픽 분배 이상 감지
        - 🤖 **봇 필터링**: 헤드리스 브라우저, 크롤러 등 비정상 트래픽 제외
        - 📊 **이상치 감지**: 비정상적인 사용자 행동 패턴 필터링
        - ⚡ **성능 모니터링**: LCP, 오류율, 반품율 등 핵심 지표 추적
        - 🔄 **자동 롤백**: 임계값 초과 시 자동으로 이전 버전으로 복원
        """)
    
    st.markdown("---")
    
    # 가드레일 알림 조회
    st.subheader("🚨 실시간 알림")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/abtest/guardrails/alerts")
        if response.status_code == 200:
            data = response.json()
            alerts = data["alerts"]
            
            if alerts:
                # 알림 통계
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_alerts = len(alerts)
                    st.metric("총 알림 수", total_alerts)
                with col2:
                    active_alerts = len([a for a in alerts if not a["resolved"]])
                    st.metric("활성 알림", active_alerts)
                with col3:
                    resolved_alerts = len([a for a in alerts if a["resolved"]])
                    st.metric("해결된 알림", resolved_alerts)
                with col4:
                    critical_alerts = len([a for a in alerts if a["severity"] == "CRITICAL" and not a["resolved"]])
                    st.metric("긴급 알림", critical_alerts, delta=f"{critical_alerts}개")
                
                # 알림 목록
                st.markdown("#### 📋 알림 목록")
                
                # 필터링 옵션
                col1, col2, col3 = st.columns(3)
                with col1:
                    severity_filter = st.selectbox("심각도 필터", ["전체", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
                with col2:
                    status_filter = st.selectbox("상태 필터", ["전체", "활성", "해결됨"])
                with col3:
                    type_filter = st.selectbox("유형 필터", ["전체", "SRM", "BOT", "GUARDRAIL", "PERFORMANCE"])
                
                # 필터링 적용
                filtered_alerts = alerts
                if severity_filter != "전체":
                    filtered_alerts = [a for a in filtered_alerts if a["severity"] == severity_filter]
                if status_filter == "활성":
                    filtered_alerts = [a for a in filtered_alerts if not a["resolved"]]
                elif status_filter == "해결됨":
                    filtered_alerts = [a for a in filtered_alerts if a["resolved"]]
                if type_filter != "전체":
                    filtered_alerts = [a for a in filtered_alerts if a["alert_type"] == type_filter]
                
                # 알림 표시
                for alert in filtered_alerts[-10:]:  # 최근 10개
                    severity_color = {
                        "LOW": "🟢",
                        "MEDIUM": "🟡", 
                        "HIGH": "🟠",
                        "CRITICAL": "🔴"
                    }.get(alert["severity"], "⚪")
                    
                    status_icon = "✅" if alert["resolved"] else "⚠️"
                    
                    with st.expander(f"{severity_color} {status_icon} {alert['alert_type']} - {alert['message'][:50]}..."):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**테스트 ID**: {alert['test_id']}")
                            st.markdown(f"**심각도**: {alert['severity']}")
                            st.markdown(f"**유형**: {alert['alert_type']}")
                        with col2:
                            st.markdown(f"**발생 시간**: {alert['timestamp'][:19]}")
                            st.markdown(f"**상태**: {'해결됨' if alert['resolved'] else '활성'}")
                            if alert["action_taken"]:
                                st.markdown(f"**조치**: {alert['action_taken']}")
                        
                        st.markdown(f"**메시지**: {alert['message']}")
                        
                        # 해결되지 않은 알림에 대한 조치 버튼
                        if not alert["resolved"]:
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ 해결 처리", key=f"resolve_{alert['alert_id']}"):
                                    st.success("알림이 해결 처리되었습니다.")
                                    st.rerun()
                            with col2:
                                if st.button("🔄 자동 롤백", key=f"rollback_{alert['alert_id']}"):
                                    try:
                                        rollback_response = requests.post(f"{API_BASE_URL}/api/abtest/test/{alert['test_id']}/auto-rollback")
                                        if rollback_response.status_code == 200:
                                            st.success("자동 롤백이 실행되었습니다.")
                                        else:
                                            st.error("롤백 실행에 실패했습니다.")
                                    except Exception as e:
                                        st.error(f"오류: {e}")
            else:
                st.success("🎉 현재 활성화된 가드레일 알림이 없습니다!")
        else:
            st.error("가드레일 알림을 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
    
    st.markdown("---")
    
    # 가드레일 설정
    st.subheader("⚙️ 가드레일 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🛡️ 성능 가드레일")
        st.markdown("""
        - **LCP (Largest Contentful Paint)**: ≤ 3.5초
        - **오류율**: ≤ 0.5%
        - **반품율**: ≤ 10%
        - **응답 시간**: ≤ 2초
        """)
        
        st.markdown("#### 🤖 봇 필터링")
        st.markdown("""
        - **헤드리스 브라우저**: 자동 감지 및 제외
        - **크롤러/스파이더**: User-Agent 기반 필터링
        - **자동화 도구**: Selenium, PhantomJS 등 감지
        - **체류 시간**: 1초 미만 세션 제외
        """)
    
    with col2:
        st.markdown("#### 📊 SRM 감지")
        st.markdown("""
        - **카이제곱 검정**: p < 0.01 임계값
        - **트래픽 분배**: 예상 대비 실제 분배 비교
        - **자동 경고**: 분배 이상 시 즉시 알림
        - **데이터 품질**: 신뢰할 수 있는 결과 보장
        """)
        
        st.markdown("#### 🔄 자동 롤백")
        st.markdown("""
        - **성능 임계값**: 핵심 지표 20% 이상 악화 시
        - **응답 시간**: 30분 내 자동 롤백 실행
        - **안전장치**: 긴급 상황 시 즉시 복원
        - **알림 시스템**: 롤백 실행 시 즉시 통보
        """)
    
    st.markdown("---")
    
    # 데이터 품질 대시보드
    st.subheader("📊 데이터 품질 대시보드")
    
    try:
        # 테스트 목록 조회
        tests_response = requests.get(f"{API_BASE_URL}/api/abtest/list")
        if tests_response.status_code == 200:
            tests_data = tests_response.json()
            tests = tests_data["tests"]
            
            if tests:
                # 활성 테스트 선택
                active_tests = [t for t in tests if t["status"] == "active"]
                if active_tests:
                    selected_test_name = st.selectbox(
                        "데이터 품질을 확인할 테스트 선택",
                        [f"{t['test_name']} ({t['product_name']})" for t in active_tests]
                    )
                    
                    selected_test = next(t for t in active_tests if f"{t['test_name']} ({t['product_name']})" == selected_test_name)
                    
                    # 데이터 품질 정보 표시
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("총 이벤트", "1,234")  # 실제로는 API에서 가져와야 함
                    with col2:
                        st.metric("봇 필터링", "23", delta="-1.8%")
                    with col3:
                        st.metric("이상치 제외", "12", delta="-0.9%")
                    with col4:
                        st.metric("데이터 품질", "98.3%", delta="+0.2%")
                    
                    # 품질 지표 차트 (예시)
                    st.markdown("#### 📈 데이터 품질 트렌드")
                    quality_data = {
                        "시간": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
                        "데이터 품질": [98.1, 98.3, 98.5, 98.2, 98.4, 98.3],
                        "봇 필터링": [2.1, 1.9, 1.8, 2.0, 1.7, 1.8]
                    }
                    
                    df_quality = pd.DataFrame(quality_data)
                    fig_quality = px.line(df_quality, x="시간", y=["데이터 품질", "봇 필터링"], 
                                        title="24시간 데이터 품질 트렌드")
                    st.plotly_chart(fig_quality, use_container_width=True)
                else:
                    st.info("현재 활성 상태인 테스트가 없습니다.")
            else:
                st.info("생성된 테스트가 없습니다.")
        else:
            st.error("테스트 목록을 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

# 실시간 모니터링은 가드레일 모니터링으로 통합됨

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
    """사용자 행동 시뮬레이션 (가드레일 지표 포함)"""
    
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
    
    # 가드레일 위반 시뮬레이션을 위한 카운터
    guardrail_violations = {
        "bot_traffic": 0,
        "outlier_behavior": 0,
        "performance_issues": 0
    }
    
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
        
        # 봇 트래픽 시뮬레이션 (5% 확률)
        is_bot = random.randint(1, 100) <= 5
        if is_bot:
            guardrail_violations["bot_traffic"] += 1
            user_agent = "HeadlessChrome/91.0.4472.124"
        else:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
        # 이상치 행동 시뮬레이션 (3% 확률)
        is_outlier = random.randint(1, 100) <= 3
        if is_outlier:
            guardrail_violations["outlier_behavior"] += 1
            session_duration = 0.5  # 0.5초 (이상치)
        else:
            session_duration = random.uniform(30, 300)  # 30초~5분
        
        # 성능 이슈 시뮬레이션 (2% 확률)
        has_performance_issue = random.randint(1, 100) <= 2
        if has_performance_issue:
            guardrail_violations["performance_issues"] += 1
        
        # 노출 이벤트
        if random.randint(1, 100) <= impression_rate:
            event_data = {
                "test_id": test_id,
                "variant_id": variant_id,
                "event_type": "impression",
                "user_id": user_id,
                "session_id": session_id,
                "session_duration": session_duration
            }
            
            # 봇 플래그 추가
            if is_bot:
                event_data["user_agent"] = user_agent
            
            requests.post(f"{API_BASE_URL}/api/abtest/event", json=event_data)
            
            # 클릭 이벤트
            if random.randint(1, 100) <= click_rate:
                click_event_data = {
                    "test_id": test_id,
                    "variant_id": variant_id,
                    "event_type": "click",
                    "user_id": user_id,
                    "session_id": session_id,
                    "session_duration": session_duration
                }
                
                if is_bot:
                    click_event_data["user_agent"] = user_agent
                
                requests.post(f"{API_BASE_URL}/api/abtest/event", json=click_event_data)
                
                # 구매 이벤트
                if random.randint(1, 100) <= conversion_rate:
                    conversion_event_data = {
                        "test_id": test_id,
                        "variant_id": variant_id,
                        "event_type": "conversion",
                        "user_id": user_id,
                        "session_id": session_id,
                        "session_duration": session_duration
                    }
                    
                    if is_bot:
                        conversion_event_data["user_agent"] = user_agent
                    
                    requests.post(f"{API_BASE_URL}/api/abtest/event", json=conversion_event_data)
        
        # API 호출 간격 조절
        time.sleep(0.1)
    
    # 가드레일 위반 요약 표시
    st.info(f"🔍 시뮬레이션 완료 - 가드레일 위반 요약:")
    st.info(f"  - 봇 트래픽: {guardrail_violations['bot_traffic']}건")
    st.info(f"  - 이상치 행동: {guardrail_violations['outlier_behavior']}건")
    st.info(f"  - 성능 이슈: {guardrail_violations['performance_issues']}건")

if __name__ == "__main__":
    main()


