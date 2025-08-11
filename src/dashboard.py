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

from ab_test_manager import ABTestManager, TestStatus, TestMode

@dataclass
class DashboardMetrics:
    """대시보드 메트릭"""
    total_tests: int
    active_tests: int
    completed_tests: int
    draft_tests: int
    total_impressions: int
    total_conversions: int
    overall_cvr: float
    total_revenue: float
    autopilot_experiments: int
    traffic_usage: float

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
            total_impressions=total_impressions,
            total_conversions=total_conversions,
            overall_cvr=overall_cvr,
            total_revenue=total_revenue,
            autopilot_experiments=autopilot_experiments,
            traffic_usage=traffic_usage
        )
    
    def get_test_summaries(self, limit: int = 10) -> List[TestSummary]:
        """테스트 요약 목록"""
        summaries = []
        
        for test in list(self.ab_test_manager.tests.values())[-limit:]:
            # 이벤트 통계 계산
            events = self.ab_test_manager.events.get(test.test_id, [])
            impressions = len([e for e in events if e.event_type == "impression"])
            clicks = len([e for e in events if e.event_type == "click"])
            conversions = len([e for e in events if e.event_type == "conversion"])
            # 매출 = 구매수 × 상품가격
            revenue = conversions * test.product_info.price
            
            cvr = (conversions / impressions * 100) if impressions > 0 else 0
            
            # 경고 수 계산
            alerts = self.ab_test_manager.get_guardrail_alerts(test.test_id)
            alerts_count = len([a for a in alerts if not a["resolved"]])
            
            # 승자 확인
            winner = None
            if test.status == TestStatus.COMPLETED:
                results = self.ab_test_manager.get_test_results(test.test_id)
                winner = results.get("winner")
            
            summary = TestSummary(
                test_id=test.test_id,
                test_name=test.test_name,
                status=test.status.value,
                product_name=test.product_info.product_name,
                variants_count=len(test.variants),
                impressions=impressions,
                clicks=clicks,
                conversions=conversions,
                cvr=cvr,
                revenue=revenue,
                created_at=test.created_at.strftime("%Y-%m-%d"),
                duration_days=(datetime.now() - test.created_at).days,
                winner=winner,
                alerts_count=alerts_count
            )
            summaries.append(summary)
        
        return summaries
    
    def get_real_time_metrics(self, test_id: str) -> Dict[str, Any]:
        """실시간 메트릭 - 요구사항 9번"""
        if test_id not in self.ab_test_manager.tests:
            return {}
        
        test = self.ab_test_manager.tests[test_id]
        events = self.ab_test_manager.events.get(test_id, [])
        
        # 변형별 실시간 통계
        variant_metrics = {}
        for variant in test.variants:
            variant_events = [e for e in events if e.variant_id == variant.variant_id]
            
            impressions = len([e for e in variant_events if e.event_type == "impression"])
            clicks = len([e for e in variant_events if e.event_type == "click"])
            conversions = len([e for e in variant_events if e.event_type == "conversion"])
            # 매출 = 구매수 × 상품가격
            revenue = conversions * test.product_info.price
            
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            cvr = (conversions / impressions * 100) if impressions > 0 else 0
            
            variant_metrics[variant.variant_id] = {
                "variant_type": variant.variant_type.value,
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "revenue": revenue,
                "ctr": ctr,
                "cvr": cvr
            }
        
        # 최근 1시간 트렌드
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_events = [e for e in events if e.timestamp > one_hour_ago]
        
        hourly_trend = {
            "impressions": len([e for e in recent_events if e.event_type == "impression"]),
            "clicks": len([e for e in recent_events if e.event_type == "click"]),
            "conversions": len([e for e in recent_events if e.event_type == "conversion"]),
            "revenue": len([e for e in recent_events if e.event_type == "conversion"]) * test.product_info.price
        }
        
        # 경고 상태
        alerts = self.ab_test_manager.get_guardrail_alerts(test_id)
        active_alerts = [a for a in alerts if not a["resolved"]]
        
        # 밴딧 의사결정 로그 (최근 1시간)
        bandit_decisions = self.ab_test_manager.get_bandit_decisions(test_id, limit=50)
        recent_decisions = [d for d in bandit_decisions if 
                          datetime.fromisoformat(d["timestamp"]) > one_hour_ago]
        
        return {
            "test_name": test.test_name,
            "status": test.status.value,
            "variant_metrics": variant_metrics,
            "hourly_trend": hourly_trend,
            "active_alerts": len(active_alerts),
            "recent_decisions": len(recent_decisions),
            "traffic_split": test.traffic_split
        }
    
    def create_performance_charts(self, test_id: str) -> Dict[str, Any]:
        """성과 차트 생성"""
        if test_id not in self.ab_test_manager.tests:
            return {}
        
        test = self.ab_test_manager.tests[test_id]
        events = self.ab_test_manager.events.get(test_id, [])
        
        # 시간별 데이터 준비
        df_data = []
        for event in events:
            df_data.append({
                "timestamp": event.timestamp,
                "variant_id": event.variant_id,
                "event_type": event.event_type,
                "revenue": event.revenue
            })
        
        if not df_data:
            return {}
        
        df = pd.DataFrame(df_data)
        df["hour"] = pd.to_datetime(df["timestamp"]).dt.floor("H")
        
        # 시간별 집계
        hourly_stats = df.groupby(["hour", "variant_id", "event_type"]).size().unstack(fill_value=0)
        
        # 차트 데이터 생성
        charts = {}
        
        # 1. 시간별 노출/클릭/전환 트렌드
        if "impression" in hourly_stats.columns:
            fig_trend = go.Figure()
            
            for variant_id in hourly_stats.index.get_level_values("variant_id").unique():
                variant_data = hourly_stats.xs(variant_id, level="variant_id")
                
                if "impression" in variant_data.columns:
                    fig_trend.add_trace(go.Scatter(
                        x=variant_data.index,
                        y=variant_data["impression"],
                        name=f"변형 {variant_id} - 노출",
                        mode="lines+markers"
                    ))
                
                if "click" in variant_data.columns:
                    fig_trend.add_trace(go.Scatter(
                        x=variant_data.index,
                        y=variant_data["click"],
                        name=f"변형 {variant_id} - 클릭",
                        mode="lines+markers"
                    ))
            
            fig_trend.update_layout(
                title="시간별 트렌드",
                xaxis_title="시간",
                yaxis_title="이벤트 수",
                height=400
            )
            charts["trend"] = fig_trend.to_json()
        
        # 2. 변형별 성과 비교
        variant_stats = {}
        for variant in test.variants:
            variant_events = [e for e in events if e.variant_id == variant.variant_id]
            
            impressions = len([e for e in variant_events if e.event_type == "impression"])
            clicks = len([e for e in variant_events if e.event_type == "click"])
            conversions = len([e for e in variant_events if e.event_type == "conversion"])
            # 매출 = 구매수 × 상품가격
            revenue = conversions * test.product_info.price
            
            variant_stats[variant.variant_type.value] = {
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "revenue": revenue,
                "ctr": (clicks / impressions * 100) if impressions > 0 else 0,
                "cvr": (conversions / impressions * 100) if impressions > 0 else 0
            }
        
        # CTR 비교 차트
        fig_ctr = go.Figure(data=[
            go.Bar(
                x=list(variant_stats.keys()),
                y=[stats["ctr"] for stats in variant_stats.values()],
                text=[f"{stats['ctr']:.2f}%" for stats in variant_stats.values()],
                textposition="auto"
            )
        ])
        fig_ctr.update_layout(
            title="변형별 CTR 비교",
            xaxis_title="변형",
            yaxis_title="CTR (%)",
            height=400
        )
        charts["ctr_comparison"] = fig_ctr.to_json()
        
        # CVR 비교 차트
        fig_cvr = go.Figure(data=[
            go.Bar(
                x=list(variant_stats.keys()),
                y=[stats["cvr"] for stats in variant_stats.values()],
                text=[f"{stats['cvr']:.2f}%" for stats in variant_stats.values()],
                textposition="auto"
            )
        ])
        fig_cvr.update_layout(
            title="변형별 CVR 비교",
            xaxis_title="변형",
            yaxis_title="CVR (%)",
            height=400
        )
        charts["cvr_comparison"] = fig_cvr.to_json()
        
        return charts
    
    def generate_experiment_report(self, test_id: str) -> Dict[str, Any]:
        """실험 종료 리포트 생성 - 요구사항 10번"""
        if test_id not in self.ab_test_manager.tests:
            return {}
        
        test = self.ab_test_manager.tests[test_id]
        results = self.ab_test_manager.get_test_results(test_id)
        
        # 실험 개요
        experiment_overview = {
            "test_id": test.test_id,
            "test_name": test.test_name,
            "product_name": test.product_info.product_name,
            "category": test.product_info.category,
            "start_date": test.start_date.strftime("%Y-%m-%d %H:%M"),
            "end_date": test.end_date.strftime("%Y-%m-%d %H:%M") if test.end_date else "진행 중",
            "duration_days": (test.end_date - test.start_date).days if test.end_date else (datetime.now() - test.start_date).days,
            "status": test.status.value,
            "test_mode": test.test_mode.value,
            "variants_count": len(test.variants)
        }
        
        # 실험 계약서 정보
        if test.experiment_brief:
            experiment_overview.update({
                "objective": test.experiment_brief.objective,
                "primary_metrics": test.experiment_brief.primary_metrics,
                "secondary_metrics": test.experiment_brief.secondary_metrics,
                "mde": test.experiment_brief.mde,
                "min_sample_size": test.experiment_brief.min_sample_size
            })
        
        # 최종 성과
        final_performance = {
            "total_impressions": results.get("total_impressions", 0),
            "total_clicks": results.get("total_clicks", 0),
            "total_conversions": results.get("total_conversions", 0),
            "total_revenue": results.get("total_revenue", 0),
            "overall_ctr": (results.get("total_clicks", 0) / results.get("total_impressions", 1) * 100),
            "overall_cvr": (results.get("total_conversions", 0) / results.get("total_impressions", 1) * 100),
            "winner": results.get("winner"),
            "statistical_significance": results.get("statistical_significance", 0)
        }
        
        # 변형별 상세 결과
        variant_results = {}
        if "variants" in results:
            for variant_id, variant_result in results["variants"].items():
                variant_results[variant_id] = {
                    "variant_type": variant_result.get("variant_type", ""),
                    "impressions": variant_result.get("impressions", 0),
                    "clicks": variant_result.get("clicks", 0),
                    "conversions": variant_result.get("conversions", 0),
                    "revenue": variant_result.get("revenue", 0),
                    "ctr": variant_result.get("ctr", 0),
                    "cvr": variant_result.get("cvr", 0),
                    "statistical_significance": variant_result.get("statistical_significance", 0)
                }
        
        # 세그먼트별 분석
        segment_analysis = self._analyze_segments(test_id)
        
        # SRM 및 가드레일 히스토리
        alerts = self.ab_test_manager.get_guardrail_alerts(test_id)
        alert_history = {
            "total_alerts": len(alerts),
            "resolved_alerts": len([a for a in alerts if a["resolved"]]),
            "active_alerts": len([a for a in alerts if not a["resolved"]]),
            "alert_types": {}
        }
        
        for alert in alerts:
            alert_type = alert["alert_type"]
            if alert_type not in alert_history["alert_types"]:
                alert_history["alert_types"][alert_type] = 0
            alert_history["alert_types"][alert_type] += 1
        
        # 데이터 품질
        events = self.ab_test_manager.events.get(test_id, [])
        data_quality = {
            "total_events": len(events),
            "bot_filtered": len([e for e in events if e.bot_flag]),
            "outlier_filtered": len([e for e in events if e.guardrail_breach]),
            "exclusion_rate": (len([e for e in events if e.bot_flag or e.guardrail_breach]) / len(events) * 100) if events else 0
        }
        
        # Actionable Insights
        insights = self._generate_insights(test_id, variant_results, segment_analysis)
        
        return {
            "experiment_overview": experiment_overview,
            "final_performance": final_performance,
            "variant_results": variant_results,
            "segment_analysis": segment_analysis,
            "alert_history": alert_history,
            "data_quality": data_quality,
            "insights": insights,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _analyze_segments(self, test_id: str) -> Dict[str, Any]:
        """세그먼트별 분석"""
        events = self.ab_test_manager.events.get(test_id, [])
        
        if not events:
            return {}
        
        # 디바이스별 분석
        device_analysis = {}
        for event in events:
            device = event.device or "unknown"
            if device not in device_analysis:
                device_analysis[device] = {"impressions": 0, "clicks": 0, "conversions": 0}
            
            if event.event_type == "impression":
                device_analysis[device]["impressions"] += 1
            elif event.event_type == "click":
                device_analysis[device]["clicks"] += 1
            elif event.event_type == "conversion":
                device_analysis[device]["conversions"] += 1
        
        # CTR, CVR 계산
        for device, stats in device_analysis.items():
            stats["ctr"] = (stats["clicks"] / stats["impressions"] * 100) if stats["impressions"] > 0 else 0
            stats["cvr"] = (stats["conversions"] / stats["impressions"] * 100) if stats["impressions"] > 0 else 0
        
        # 채널별 분석
        channel_analysis = {}
        for event in events:
            channel = event.channel or "unknown"
            if channel not in channel_analysis:
                channel_analysis[channel] = {"impressions": 0, "clicks": 0, "conversions": 0}
            
            if event.event_type == "impression":
                channel_analysis[channel]["impressions"] += 1
            elif event.event_type == "click":
                channel_analysis[channel]["clicks"] += 1
            elif event.event_type == "conversion":
                channel_analysis[channel]["conversions"] += 1
        
        # CTR, CVR 계산
        for channel, stats in channel_analysis.items():
            stats["ctr"] = (stats["clicks"] / stats["impressions"] * 100) if stats["impressions"] > 0 else 0
            stats["cvr"] = (stats["conversions"] / stats["impressions"] * 100) if stats["impressions"] > 0 else 0
        
        return {
            "device_analysis": device_analysis,
            "channel_analysis": channel_analysis
        }
    
    def _generate_insights(self, test_id: str, variant_results: Dict, segment_analysis: Dict) -> List[str]:
        """Actionable Insights 생성"""
        insights = []
        
        # 승자 분석
        test = self.ab_test_manager.tests[test_id]
        if test.status == TestStatus.COMPLETED and variant_results:
            # 가장 성과가 좋은 변형 찾기
            best_variant = max(variant_results.items(), key=lambda x: x[1]["cvr"])
            best_variant_id, best_stats = best_variant
            
            insights.append(f"🏆 승자 변형 {best_variant_id}: CVR {best_stats['cvr']:.2f}%")
            
            # 세그먼트별 인사이트
            if "device_analysis" in segment_analysis:
                device_stats = segment_analysis["device_analysis"]
                best_device = max(device_stats.items(), key=lambda x: x[1]["cvr"])
                insights.append(f"📱 {best_device[0]} 디바이스에서 가장 높은 CVR: {best_device[1]['cvr']:.2f}%")
            
            if "channel_analysis" in segment_analysis:
                channel_stats = segment_analysis["channel_analysis"]
                best_channel = max(channel_stats.items(), key=lambda x: x[1]["cvr"])
                insights.append(f"🔗 {best_channel[0]} 채널에서 가장 높은 CVR: {best_channel[1]['cvr']:.2f}%")
        
        # 개선 제안
        if test.experiment_brief and test.experiment_brief.objective:
            insights.append(f"🎯 목표 달성도: {test.experiment_brief.objective}")
        
        # 다음 실험 제안
        insights.append("🔄 다음 실험 제안: 승자 패턴을 기반으로 한 추가 최적화")
        
        return insights
    
    def export_report_pdf(self, test_id: str) -> str:
        """PDF 리포트 생성 (실제로는 reportlab 등 사용)"""
        report_data = self.generate_experiment_report(test_id)
        
        # 실제 구현에서는 PDF 생성 라이브러리 사용
        # 여기서는 JSON 형태로 반환
        return json.dumps(report_data, ensure_ascii=False, indent=2)
    
    def get_learning_patterns(self) -> Dict[str, Any]:
        """학습 패턴 데이터베이스 - 요구사항 10번"""
        # 실제 구현에서는 DB에서 관리
        # 여기서는 예시 데이터
        return {
            "successful_patterns": {
                "electronics": {
                    "layout_type": "grid",
                    "cta_text": "즉시 구매",
                    "color_scheme": "dark",
                    "win_rate": 0.75
                },
                "fashion": {
                    "layout_type": "carousel",
                    "cta_text": "장바구니 담기",
                    "color_scheme": "colorful",
                    "win_rate": 0.68
                }
            },
            "category_performance": {
                "electronics": {"avg_cvr": 3.2, "experiments": 15},
                "fashion": {"avg_cvr": 2.8, "experiments": 12},
                "home": {"avg_cvr": 2.5, "experiments": 8}
            },
            "cta_performance": {
                "즉시 구매": {"win_rate": 0.72, "avg_cvr": 3.1},
                "장바구니 담기": {"win_rate": 0.65, "avg_cvr": 2.8},
                "자세히 보기": {"win_rate": 0.58, "avg_cvr": 2.4}
            }
        }

# 전역 인스턴스
dashboard_manager = None

def initialize_dashboard(ab_test_manager: ABTestManager):
    """대시보드 초기화"""
    global dashboard_manager
    dashboard_manager = DashboardManager(ab_test_manager)
    return dashboard_manager
