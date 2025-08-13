#!/usr/bin/env python3
"""
대시보드 및 리포트 시스템
요구사항 9번: 대시보드/운영 UX
요구사항 10번: 리포트 & 인사이트
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np

from ab_test_manager import ABTestManager, TestStatus, TestMode, DecisionMode

@dataclass
class DashboardMetrics:
    """대시보드 메트릭"""
    total_tests: int
    active_tests: int
    completed_tests: int
    draft_tests: int
    manual_decision_tests: int  # 수동 결정 대기 중인 테스트
    total_impressions: int
    total_conversions: int
    overall_cvr: float
    total_revenue: float
    autopilot_experiments: int
    traffic_usage: float
    cycle_completed_tests: int  # 사이클 완료된 테스트

@dataclass
class TestSummary:
    """테스트 요약 정보"""
    test_id: str
    test_name: str
    status: str
    product_name: str
    variants_count: int
    impressions: int
    clicks: int
    conversions: int
    cvr: float
    revenue: float
    created_at: str
    duration_days: int
    winner: Optional[str] = None
    alerts_count: int = 0
    cycle_number: int = 1
    decision_mode: str = "auto"
    manual_decision_time_remaining: Optional[float] = None

class DashboardManager:
    """대시보드 관리자"""
    
    def __init__(self, ab_test_manager: ABTestManager):
        self.ab_test_manager = ab_test_manager
    
    def get_dashboard_metrics(self) -> DashboardMetrics:
        """대시보드 메트릭 계산"""
        tests = self.ab_test_manager.tests.values()
        
        total_tests = len(tests)
        active_tests = len([t for t in tests if t.status == TestStatus.ACTIVE])
        completed_tests = len([t for t in tests if t.status == TestStatus.COMPLETED])
        draft_tests = len([t for t in tests if t.status == TestStatus.DRAFT])
        manual_decision_tests = len([t for t in tests if t.status == TestStatus.MANUAL_DECISION])
        cycle_completed_tests = len([t for t in tests if t.status == TestStatus.CYCLE_COMPLETED])
        
        # 전체 통계 계산
        total_impressions = 0
        total_conversions = 0
        total_revenue = 0
        
        for test in tests:
            if test.test_id in self.ab_test_manager.events:
                events = self.ab_test_manager.events[test.test_id]
                total_impressions += len([e for e in events if e.event_type == "impression"])
                total_conversions += len([e for e in events if e.event_type == "conversion"])
                # 매출 = 구매수 × 상품가격
                total_revenue += len([e for e in events if e.event_type == "conversion"]) * test.product_info.price
        
        overall_cvr = (total_conversions / total_impressions * 100) if total_impressions > 0 else 0
        
        # 자동 생성 실험 수
        autopilot_experiments = len([t for t in tests if t.test_mode == TestMode.AUTOPILOT])
        
        # 트래픽 사용량
        traffic_usage = sum(self.ab_test_manager.traffic_budget_usage.values())
        
        return DashboardMetrics(
            total_tests=total_tests,
            active_tests=active_tests,
            completed_tests=completed_tests,
            draft_tests=draft_tests,
            manual_decision_tests=manual_decision_tests,
            total_impressions=total_impressions,
            total_conversions=total_conversions,
            overall_cvr=overall_cvr,
            total_revenue=total_revenue,
            autopilot_experiments=autopilot_experiments,
            traffic_usage=traffic_usage,
            cycle_completed_tests=cycle_completed_tests
        )
    
    def get_test_summaries(self) -> List[TestSummary]:
        """테스트 요약 목록"""
        summaries = []
        
        for test in self.ab_test_manager.tests.values():
            results = self.ab_test_manager.get_test_results(test.test_id)
            
            total_impressions = 0
            total_clicks = 0
            total_conversions = 0
            total_revenue = 0
            
            if results and "variants" in results:
                for variant_result in results["variants"].values():
                    total_impressions += variant_result.get("impressions", 0)
                    total_clicks += variant_result.get("clicks", 0)
                    total_conversions += variant_result.get("conversions", 0)
                    total_revenue += variant_result.get("revenue", 0)
            
            cvr = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
            duration_days = (datetime.now() - test.created_at).days
            
            # 수동 결정 남은 시간 계산
            manual_decision_time_remaining = None
            if test.status == TestStatus.MANUAL_DECISION and test.manual_decision_end_date:
                remaining = test.manual_decision_end_date - datetime.now()
                manual_decision_time_remaining = max(0, remaining.total_seconds() / 3600)  # 시간 단위
            
            summary = TestSummary(
                test_id=test.test_id,
                test_name=test.test_name,
                status=test.status.value,
                product_name=test.product_info.product_name,
                variants_count=len(test.variants),
                impressions=total_impressions,
                clicks=total_clicks,
                conversions=total_conversions,
                cvr=round(cvr, 2),
                revenue=total_revenue,
                created_at=test.created_at.isoformat(),
                duration_days=duration_days,
                winner=test.winner_variant_id,
                cycle_number=test.cycle_number,
                decision_mode=test.decision_mode.value if test.decision_mode else "auto",
                manual_decision_time_remaining=manual_decision_time_remaining
            )
            summaries.append(summary)
        
        return summaries
    
    def get_manual_decision_tests(self) -> List[Dict[str, Any]]:
        """수동 결정 대기 중인 테스트 목록"""
        manual_tests = []
        
        for test in self.ab_test_manager.tests.values():
            if test.status == TestStatus.MANUAL_DECISION:
                decision_info = self.ab_test_manager.get_manual_decision_info(test.test_id)
                results = self.ab_test_manager.get_test_results(test.test_id)
                
                test_info = {
                    "test_id": test.test_id,
                    "test_name": test.test_name,
                    "product_name": test.product_info.product_name,
                    "cycle_number": test.cycle_number,
                    "manual_decision_start_date": test.manual_decision_start_date.isoformat() if test.manual_decision_start_date else None,
                    "manual_decision_end_date": test.manual_decision_end_date.isoformat() if test.manual_decision_end_date else None,
                    "time_remaining_hours": decision_info.get("time_remaining"),
                    "variants": results.get("variants", {}) if results else {},
                    "decision_info": decision_info
                }
                manual_tests.append(test_info)
        
        return manual_tests
    
    def get_cycle_management_info(self) -> Dict[str, Any]:
        """사이클 관리 정보"""
        cycle_info = {
            "auto_cycle_queue": self.ab_test_manager.get_auto_cycle_queue(),
            "cycle_history": {},
            "cycle_status": {}
        }
        
        # 각 테스트의 사이클 상태 조회
        for test_id in self.ab_test_manager.tests.keys():
            cycle_info["cycle_status"][test_id] = self.ab_test_manager.get_cycle_status(test_id)
            cycle_info["cycle_history"][test_id] = self.ab_test_manager.cycle_history.get(test_id, [])
        
        return cycle_info
    
    def get_long_term_monitoring_data(self, test_id: str) -> Dict[str, Any]:
        """장기 모니터링 데이터"""
        if test_id not in self.ab_test_manager.long_term_metrics:
            return {}
        
        metrics = self.ab_test_manager.long_term_metrics[test_id]
        performance = self.ab_test_manager.get_long_term_performance(test_id)
        
        return {
            "metrics": metrics,
            "performance": performance,
            "test_info": self.ab_test_manager.tests.get(test_id)
        }
    
    def create_manual_decision_chart(self, test_id: str) -> go.Figure:
        """수동 결정 대기 중인 테스트 차트"""
        results = self.ab_test_manager.get_test_results(test_id)
        if not results or "variants" not in results:
            return go.Figure()
        
        variants_data = results["variants"]
        
        # 변형별 성과 데이터
        variant_names = []
        cvr_values = []
        ctr_values = []
        revenue_values = []
        
        for variant_id, data in variants_data.items():
            variant_names.append(f"변형 {data.get('variant_type', 'Unknown')}")
            cvr_values.append(data.get('conversion_rate', 0))
            ctr_values.append(data.get('ctr', 0))
            revenue_values.append(data.get('revenue', 0))
        
        # CVR 비교 차트
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=variant_names,
            y=cvr_values,
            name='전환율 (%)',
            marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        ))
        
        fig.update_layout(
            title=f"변형별 전환율 비교 - {results.get('test_name', 'Unknown')}",
            xaxis_title="변형",
            yaxis_title="전환율 (%)",
            showlegend=True,
            height=400
        )
        
        return fig
    
    def create_cycle_progress_chart(self) -> go.Figure:
        """사이클 진행 상황 차트"""
        tests = self.ab_test_manager.tests.values()
        
        cycle_data = {}
        for test in tests:
            cycle_num = test.cycle_number
            if cycle_num not in cycle_data:
                cycle_data[cycle_num] = {"active": 0, "completed": 0, "manual_decision": 0}
            
            if test.status == TestStatus.ACTIVE:
                cycle_data[cycle_num]["active"] += 1
            elif test.status == TestStatus.CYCLE_COMPLETED:
                cycle_data[cycle_num]["completed"] += 1
            elif test.status == TestStatus.MANUAL_DECISION:
                cycle_data[cycle_num]["manual_decision"] += 1
        
        # 차트 데이터 준비
        cycle_numbers = sorted(cycle_data.keys())
        active_counts = [cycle_data[cycle]["active"] for cycle in cycle_numbers]
        completed_counts = [cycle_data[cycle]["completed"] for cycle in cycle_numbers]
        manual_counts = [cycle_data[cycle]["manual_decision"] for cycle in cycle_numbers]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=[f"사이클 {cycle}" for cycle in cycle_numbers],
            y=active_counts,
            name='진행 중',
            marker_color='#1f77b4'
        ))
        
        fig.add_trace(go.Bar(
            x=[f"사이클 {cycle}" for cycle in cycle_numbers],
            y=completed_counts,
            name='완료',
            marker_color='#2ca02c'
        ))
        
        fig.add_trace(go.Bar(
            x=[f"사이클 {cycle}" for cycle in cycle_numbers],
            y=manual_counts,
            name='수동 결정 대기',
            marker_color='#ff7f0e'
        ))
        
        fig.update_layout(
            title="사이클별 진행 상황",
            xaxis_title="사이클",
            yaxis_title="테스트 수",
            barmode='stack',
            height=400
        )
        
        return fig
    
    def create_long_term_trend_chart(self, test_id: str) -> go.Figure:
        """장기 모니터링 트렌드 차트"""
        monitoring_data = self.get_long_term_monitoring_data(test_id)
        if not monitoring_data or "metrics" not in monitoring_data:
            return go.Figure()
        
        metrics = monitoring_data["metrics"]
        
        # 시간축 (일별)
        days = list(range(1, len(metrics.get("cvr", [])) + 1))
        
        fig = go.Figure()
        
        # CVR 트렌드
        if metrics.get("cvr"):
            fig.add_trace(go.Scatter(
                x=days,
                y=metrics["cvr"],
                mode='lines+markers',
                name='CVR (%)',
                line=dict(color='#1f77b4', width=2)
            ))
        
        # CTR 트렌드
        if metrics.get("ctr"):
            fig.add_trace(go.Scatter(
                x=days,
                y=metrics["ctr"],
                mode='lines+markers',
                name='CTR (%)',
                line=dict(color='#ff7f0e', width=2)
            ))
        
        fig.update_layout(
            title=f"장기 모니터링 트렌드 - {test_id}",
            xaxis_title="일차",
            yaxis_title="비율 (%)",
            showlegend=True,
            height=400
        )
        
        return fig
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """전체 대시보드 데이터"""
        return {
            "metrics": self.get_dashboard_metrics(),
            "test_summaries": self.get_test_summaries(),
            "manual_decision_tests": self.get_manual_decision_tests(),
            "cycle_management": self.get_cycle_management_info(),
            "charts": {
                "cycle_progress": self.create_cycle_progress_chart(),
                "manual_decision": self.create_manual_decision_chart("sample") if self.get_manual_decision_tests() else None
            }
        }

def initialize_dashboard(ab_test_manager: ABTestManager) -> DashboardManager:
    """대시보드 초기화"""
    return DashboardManager(ab_test_manager)

# 전역 인스턴스
dashboard_manager = None
