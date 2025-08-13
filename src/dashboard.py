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
    
    def get_learning_patterns(self) -> Dict[str, Any]:
        """학습 패턴 조회 - 요구사항 10번"""
        try:
            patterns = {
                "high_performing_variants": [],
                "low_performing_variants": [],
                "category_performance": {},
                "time_based_patterns": {},
                "user_segment_insights": {}
            }
            
            # 고성능 변형 패턴 분석
            for test in self.ab_test_manager.tests.values():
                if test.status == TestStatus.COMPLETED and test.winner:
                    winner_variant = next((v for v in test.variants if v.variant_id == test.winner), None)
                    if winner_variant:
                        patterns["high_performing_variants"].append({
                            "test_id": test.test_id,
                            "variant_id": test.winner,
                            "variant_type": winner_variant.variant_type.value,
                            "layout_type": winner_variant.layout_type,
                            "color_scheme": winner_variant.color_scheme,
                            "cta_position": winner_variant.cta_position,
                            "product_category": test.product_info.category
                        })
            
            # 카테고리별 성과 분석
            category_stats = {}
            for test in self.ab_test_manager.tests.values():
                category = test.product_info.category
                if category not in category_stats:
                    category_stats[category] = {"tests": 0, "winners": 0}
                
                category_stats[category]["tests"] += 1
                if test.winner:
                    category_stats[category]["winners"] += 1
            
            patterns["category_performance"] = category_stats
            
            return patterns
            
        except Exception as e:
            raise Exception(f"학습 패턴 분석 중 오류: {str(e)}")
    
    def generate_experiment_report(self, test_id: str) -> Dict[str, Any]:
        """실험 리포트 생성 - 요구사항 10번"""
        try:
            test = self.ab_test_manager.tests.get(test_id)
            if not test:
                raise Exception("테스트를 찾을 수 없습니다.")
            
            # 기본 정보
            report = {
                "test_id": test_id,
                "test_name": test.test_name,
                "product_name": test.product_info.product_name,
                "status": test.status.value,
                "created_at": test.created_at.isoformat(),
                "start_date": test.start_date.isoformat() if test.start_date else None,
                "end_date": test.end_date.isoformat() if test.end_date else None,
                "duration_days": test.duration_days,
                "test_mode": test.test_mode.value,
                "winner": test.winner,
                "variants": [],
                "metrics": {},
                "insights": [],
                "recommendations": []
            }
            
            # 변형 정보
            for variant in test.variants:
                variant_stats = self.ab_test_manager.get_variant_stats(test_id, variant.variant_id)
                report["variants"].append({
                    "variant_id": variant.variant_id,
                    "variant_type": variant.variant_type.value,
                    "title": variant.title,
                    "layout_type": variant.layout_type,
                    "color_scheme": variant.color_scheme,
                    "cta_text": variant.cta_text,
                    "cta_position": variant.cta_position,
                    "stats": variant_stats
                })
            
            # 전체 메트릭
            if test_id in self.ab_test_manager.events:
                events = self.ab_test_manager.events[test_id]
                total_impressions = len([e for e in events if e.event_type == "impression"])
                total_clicks = len([e for e in events if e.event_type == "click"])
                total_conversions = len([e for e in events if e.event_type == "conversion"])
                
                report["metrics"] = {
                    "total_impressions": total_impressions,
                    "total_clicks": total_clicks,
                    "total_conversions": total_conversions,
                    "overall_ctr": (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
                    "overall_cvr": (total_conversions / total_impressions * 100) if total_impressions > 0 else 0,
                    "total_revenue": total_conversions * test.product_info.price
                }
            
            # 인사이트 생성
            if test.winner:
                winner_variant = next((v for v in test.variants if v.variant_id == test.winner), None)
                if winner_variant:
                    report["insights"].append(f"승자 변형: {winner_variant.variant_type.value} 레이아웃이 가장 높은 성과를 보였습니다.")
                    report["insights"].append(f"CTA 위치: {winner_variant.cta_position}이 효과적이었습니다.")
                    report["insights"].append(f"색상 스키마: {winner_variant.color_scheme}이 사용자에게 더 매력적이었습니다.")
            
            # 권장사항
            if test.winner:
                report["recommendations"].append("승자 변형을 프로덕션에 적용하세요.")
                report["recommendations"].append("유사한 상품에 동일한 패턴을 적용해보세요.")
                report["recommendations"].append("장기 모니터링을 통해 지속적인 성과를 확인하세요.")
            
            return report
            
        except Exception as e:
            raise Exception(f"리포트 생성 중 오류: {str(e)}")
    
    def export_report_pdf(self, test_id: str) -> str:
        """PDF 리포트 다운로드"""
        try:
            report = self.generate_experiment_report(test_id)
            
            # 간단한 HTML 형태로 변환 (실제로는 PDF 라이브러리 사용)
            html_content = f"""
            <html>
            <head>
                <title>실험 리포트 - {report['test_name']}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
                    .section {{ margin-bottom: 20px; }}
                    .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e8f4fd; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>실험 리포트</h1>
                    <p><strong>테스트명:</strong> {report['test_name']}</p>
                    <p><strong>상품명:</strong> {report['product_name']}</p>
                    <p><strong>상태:</strong> {report['status']}</p>
                </div>
                
                <div class="section">
                    <h2>메트릭 요약</h2>
                    <div class="metric">총 노출: {report['metrics'].get('total_impressions', 0)}</div>
                    <div class="metric">총 클릭: {report['metrics'].get('total_clicks', 0)}</div>
                    <div class="metric">총 전환: {report['metrics'].get('total_conversions', 0)}</div>
                    <div class="metric">전체 CTR: {report['metrics'].get('overall_ctr', 0):.2f}%</div>
                    <div class="metric">전체 CVR: {report['metrics'].get('overall_cvr', 0):.2f}%</div>
                </div>
                
                <div class="section">
                    <h2>변형 성과</h2>
                    <table>
                        <tr>
                            <th>변형 ID</th>
                            <th>타입</th>
                            <th>레이아웃</th>
                            <th>노출</th>
                            <th>클릭</th>
                            <th>전환</th>
                            <th>CTR</th>
                            <th>CVR</th>
                        </tr>
            """
            
            for variant in report['variants']:
                stats = variant.get('stats', {})
                html_content += f"""
                        <tr>
                            <td>{variant['variant_id'][:8]}...</td>
                            <td>{variant['variant_type']}</td>
                            <td>{variant['layout_type']}</td>
                            <td>{stats.get('impressions', 0)}</td>
                            <td>{stats.get('clicks', 0)}</td>
                            <td>{stats.get('conversions', 0)}</td>
                            <td>{stats.get('ctr', 0):.2f}%</td>
                            <td>{stats.get('cvr', 0):.2f}%</td>
                        </tr>
                """
            
            html_content += """
                    </table>
                </div>
                
                <div class="section">
                    <h2>인사이트</h2>
                    <ul>
            """
            
            for insight in report['insights']:
                html_content += f"<li>{insight}</li>"
            
            html_content += """
                    </ul>
                </div>
                
                <div class="section">
                    <h2>권장사항</h2>
                    <ul>
            """
            
            for recommendation in report['recommendations']:
                html_content += f"<li>{recommendation}</li>"
            
            html_content += """
                    </ul>
                </div>
            </body>
            </html>
            """
            
            return html_content
            
        except Exception as e:
            raise Exception(f"PDF 생성 중 오류: {str(e)}")

def initialize_dashboard(ab_test_manager: ABTestManager) -> DashboardManager:
    """대시보드 초기화"""
    return DashboardManager(ab_test_manager)

# 전역 인스턴스
dashboard_manager = None
