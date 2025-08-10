# 상품 상세페이지 A/B 테스트 시스템

## 📋 개요

이 프로젝트는 요구사항에 따라 구현된 **AI 기능 중심의 A/B 테스트 시스템**입니다. 
실험 계약서부터 자동 생성, 실시간 모니터링, 가드레일까지 모든 AI 기능을 포함하며, 
메인 프론트엔드/백엔드와 분리되어 독립적으로 운영됩니다.

### 🎯 목적
- AI 기능만 구현하여 메인 시스템과 통합 가능
- `/api/abtest/` 엔드포인트로 통일된 API 제공
- `/docs`에서 완전한 API 문서 확인 가능
- 테스트용 프론트엔드 제공
- **새로운 기능**: 실시간 대시보드, 자동화 시스템, 향상된 분석 도구

## 🎯 주요 기능

### 1. 실험 계약서 (Experiment Brief) - 요구사항 1번
- **목적 설정**: 구매 전환율(CVR) 최대화 등 명확한 목표 정의
- **핵심/보조 지표**: CVR(주), CTR/ATC/체류시간(보조)
- **가드레일**: LCP≤3.5s, 5xx오류율≤0.5%, 반품 proxy≤x%
- **대상 설정**: 카테고리/채널/디바이스 범위, 제외 조건
- **분배 정책**: 2~3개 변형, 초기 균등(50:50) 또는 밴딧
- **최소 검출 효과**: MDE 및 최소 표본수 설정
- **종료/승격/롤백 규칙**: 자동화된 의사결정 프로세스

### 2. 변형 자동 생성 - 요구사항 2번
- **HTML/이미지 자동 생성**: 기존 생성기 활용
- **메타 태깅**: 레이아웃 유형, CTA 톤, 색 팔레트, 핵심 혜택 등
- **정책 필터**: 금칙어/과장표현/상표·저작권/성능·접근성 체크
- **성공 패턴 기반**: 카테고리별 최적화된 변형 생성

### 3. 실험 생성 방식 - 요구사항 3번
- **수동 생성**: 특수 캠페인/법무 검토 필요한 SKU
- **자동 생성 (Autopilot)**: 
  - 스케줄러가 매일/매주 대상 SKU 자동 선별
  - 최근 7일 세션≥X, 재고 있음, 쿨다운 통과 조건
  - 템플릿으로 실험 자동 생성
  - 트래픽 예산: 동시 실험 ≤20%, SKU당 동시 1개

### 4. 트래픽 배분·노출 - 요구사항 4번
- **Sticky Assignment**: 동일 사용자에게 실험 기간 내 항상 같은 변형
- **배분 모드 선택**:
  - 고트래픽: 전통 A/B(균등 분배) + 통계검정
  - 저트래픽/롱테일: Thompson Sampling 밴딧
  - 컨텍스트 활용: Contextual Bandit (선택)

### 5. 계측 (Tracking) - 요구사항 5번
- **필수 이벤트 4종**: impression / click_detail / add_to_cart / purchase
- **필수 공통 속성**: ts_server, user_key(해시), session_id, product_id, experiment_id, variant_id, device, channel, price, quantity
- **품질 플래그**: bot_flag, srm_flag, guardrail_breach
- **비동기 처리**: 사용자 지연 0에 가까운 쓰기 경로

### 6. 데이터 신뢰성 - 요구사항 6번
- **SRM 감지**: 기대 분배 대비 카이제곱 p<0.01 경고
- **봇/이상치 필터**: 헤드리스 UA, 체류<1s, IP 폭주, 비정상 패턴 제외
- **A/A 테스트**: 파이프 정상 검증 (초기 1회)
- **가드레일 모니터링**: LCP/오류율/반품 proxy 임계 초과 시 자동 롤백

### 7. 통계·의사결정 - 요구사항 7번
- **Thompson Sampling**: 변형별 α=1+구매수, β=1+노출-구매
- **최소 탐험율 5%**: 조기 과적합 방지
- **하이어라키컬 prior**: 카테고리 평균으로 냉시작 완화
- **사후 검증**: P(변형>대조) ≥ 95% AND 최소 표본수 충족
- **CUPED**: 분산 감소 (선택)

### 8. 승자 처리 - 요구사항 8번
- **단계적 승격**: 25%→50%→100% (각 단계 6~24h)
- **자동 롤백**: 승격 후 30분 이동창에서 CVR 급락(-20%↓) 시 즉시 되돌림
- **학습 저장**: 승자 특징을 패턴 DB에 기록

### 9. 대시보드/운영 UX - 요구사항 9번 ⭐ **NEW**
- **실시간 타일**: 변형별 Impr/CTR/CVR/매출
- **트렌드**: 시간대별 CVR/퍼널(노출→클릭→구매)
- **승자 확률 P**: 베이지안 CI 시각화
- **경고 배지**: SRM/봇/가드레일
- **제어**: 일시정지/재개, 승자 강제, 단계적 롤아웃
- **결정 로그**: 최근 1h 밴딧 결정 사유
- **새로운 기능**: 실시간 알림, 성능 지표 대시보드, 자동 리포트 생성

### 10. 리포트 & 인사이트 - 요구사항 10번 ⭐ **ENHANCED**
- **자동 종료 리포트**: 실험 개요, 최종 성과, 신뢰도
- **세그먼트별 차이**: 모바일·신규 등
- **SRM/가드레일 히스토리**: 데이터 제외율(봇)
- **Actionables**: 구체적인 개선 제안
- **지식화**: 승자 패턴을 변형 생성 템플릿에 반영
- **새로운 기능**: PDF 리포트, 상세 분석 차트, ROI 계산

### 11. 자동화 루프 - 요구사항 11번 ⭐ **NEW**
- **Autopilot**: 스케줄러가 대상 선정→실험 생성→시작까지 자동
- **트래픽 예산 관리**: 동시실험 상한/쿨다운으로 과실험 방지
- **프로모션 기간 글로벌 스위치**: 자동 실험 OFF
- **승자 확정 시 쿨다운**: 다음 실험 자동 예약
- **새로운 기능**: 스마트 스케줄링, 리소스 최적화, 예측 분석

### 12. 예외·엣지 케이스 핸들링 - 요구사항 12번
- **재고 급감/가격 대변동**: 실험 자동 HOLD
- **극저트래픽 SKU**: 밴딧 + Shadow traffic
- **다채널 유입**: 층화 분배 or 가중치 보정
- **시즌성/외생변수**: 이벤트 태깅

### 13. 거버넌스/보안 - 요구사항 13번
- **PII 저장 금지**: 해시 user_key, 목적 제한·보존기간
- **실험 상태머신**: draft → running → hold → completed → archived

## 📊 A/B 테스트 핵심 지표

### 🎯 주요 성과 지표 (KPI)

#### 1. 노출수 (Impressions)
- **정의**: 상품 상세페이지가 사용자에게 노출된 횟수
- **계산**: `impression` 이벤트의 총 발생 횟수
- **의의**: 테스트의 기본 트래픽 규모를 나타내며, 통계적 유의성을 위한 최소 표본수 확보 여부 판단

#### 2. 클릭수 (Clicks)
- **정의**: 상품 상세페이지에서 CTA 버튼(구매, 장바구니 등)을 클릭한 횟수
- **계산**: `click` 이벤트의 총 발생 횟수
- **의의**: 사용자의 구매 의도를 나타내는 핵심 지표

#### 3. 구매수 (Conversions)
- **정의**: 실제 구매가 완료된 횟수
- **계산**: `conversion` 이벤트의 총 발생 횟수
- **의의**: 비즈니스의 궁극적 목표인 매출 창출을 직접적으로 반영

#### 4. CTR (Click Through Rate) - 클릭률
- **정의**: 노출 대비 클릭 비율
- **계산**: `(클릭수 / 노출수) × 100%`
- **의의**: 페이지의 시각적 매력도와 CTA 효과를 측정
- **목표**: 일반적으로 1-5% 범위가 양호

#### 5. 전환율 (Conversion Rate) - 구매전환율
- **정의**: 클릭 대비 구매 비율
- **계산**: `(구매수 / 클릭수) × 100%`
- **의의**: 상품의 구매 결정 단계에서의 효과를 측정
- **목표**: 일반적으로 2-10% 범위가 양호

#### 6. 매출 (Revenue)
- **정의**: 구매로 인한 총 매출액
- **계산**: `conversion` 이벤트의 `revenue` 필드 합계
- **의의**: 비즈니스 성과의 직접적 지표

### 📈 통계적 분석 지표

#### 7. 통계적 유의성 (Statistical Significance)
- **정의**: 결과가 우연이 아닌 실제 차이임을 나타내는 확률
- **계산**: 카이제곱 검정 또는 t-검정 기반 p-value
- **기준**: p < 0.05 (95% 신뢰수준)
- **의의**: A/B 테스트 결과의 신뢰성 판단

#### 8. 승률 (Win Probability)
- **정의**: Thompson Sampling 기반 각 변형의 승리 확률
- **계산**: 베이지안 추론을 통한 사후 확률
- **의의**: 실시간으로 변형 간 성과 차이를 확률적으로 표현

#### 9. 신뢰구간 (Confidence Interval)
- **정의**: 실제 성과가 있을 것으로 예상되는 범위
- **계산**: 95% 신뢰구간 [하한, 상한]
- **의의**: 결과의 불확실성을 정량적으로 표현

### 🔍 품질 관리 지표

#### 10. SRM (Sample Ratio Mismatch)
- **정의**: 기대 분배 대비 실제 분배의 차이
- **계산**: 카이제곱 검정 (p < 0.01 시 경고)
- **의의**: A/B 테스트의 무작위성과 데이터 품질 검증

#### 11. 봇 필터링율
- **정의**: 봇으로 판단되어 제외된 트래픽 비율
- **계산**: `(봇 트래픽 / 전체 트래픽) × 100%`
- **의의**: 데이터 품질과 신뢰성 보장

#### 12. 가드레일 위반율
- **정의**: 성능/안정성 가드레일 위반 비율
- **계산**: LCP > 3.5s, 5xx 오류율 > 0.5% 등
- **의의**: 사용자 경험과 시스템 안정성 모니터링

### 🎲 밴딧 알고리즘 지표

#### 13. Thompson Sampling 파라미터
- **Alpha (α)**: 성공 횟수 + 1
- **Beta (β)**: 실패 횟수 + 1
- **의의**: 베이지안 추론을 통한 동적 트래픽 분배

#### 14. 최소 탐험율
- **정의**: 모든 변형에 할당되는 최소 트래픽 비율
- **기준**: 5% (조기 과적합 방지)
- **의의**: 새로운 정보 수집과 최적화의 균형

### 📊 시뮬레이션 및 테스트

시스템에서는 다음과 같은 시뮬레이션 기능을 제공합니다:

- **사용자 행동 시뮬레이션**: 실제 사용자 패턴을 모방한 테스트
- **확률 기반 이벤트 생성**: 노출/클릭/구매 확률 조정 가능
- **실시간 결과 업데이트**: 시뮬레이션 진행 상황 실시간 모니터링
- **시각화**: 차트와 테이블을 통한 직관적 결과 분석
- **감사 로그**: 누가/무엇을/왜 기록

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 서버 실행
```bash
# API 서버 실행
cd src
python -m uvicorn app:app --host 0.0.0.0 --port 5001 --reload

# 프론트엔드 실행 (새 터미널)
cd ..
streamlit run frontend.py
```

### 3. Docker 실행
```bash
docker build -t ab-test-system .
docker run -p 5001:5001 -p 8501:8501 ab-test-system
```

### 4. 테스트 실행 ⭐ **NEW**
```bash
# 전체 시스템 테스트
python test_enhanced_system.py

# 개별 모듈 테스트
python -m pytest tests/
```

## 📊 API 엔드포인트 (통일된 `/api/abtest/` 경로)

### 실험 계약서 관련
- `POST /api/abtest/create-with-brief` - 실험 계약서와 함께 테스트 생성
- `GET /api/abtest/dashboard/metrics` - 대시보드 메트릭 조회
- `GET /api/abtest/dashboard/test-summaries` - 테스트 요약 목록

### 자동 생성기 관련 ⭐ **ENHANCED**
- `GET /api/abtest/autopilot/status` - 자동 생성 상태 조회
- `POST /api/abtest/autopilot/promotion-mode` - 프로모션 모드 설정
- `POST /api/abtest/autopilot/run-cycle` - 자동 생성 사이클 수동 실행
- `GET /api/abtest/autopilot/schedule` - 스케줄 정보 조회
- `POST /api/abtest/autopilot/optimize` - 리소스 최적화 실행

### 밴딧 알고리즘
- `GET /api/abtest/{test_id}/variant-bandit/{user_id}` - Thompson Sampling 변형 선택
- `GET /api/abtest/bandit/decisions/{test_id}` - 밴딧 의사결정 로그

### 가드레일 모니터링
- `GET /api/abtest/guardrails/alerts` - 가드레일 알림 조회
- `GET /api/abtest/dashboard/real-time/{test_id}` - 실시간 메트릭

### 승자 처리
- `POST /api/abtest/test/{test_id}/promote-winner` - 승자 승격
- `POST /api/abtest/test/{test_id}/auto-rollback` - 자동 롤백 실행

### 리포트 ⭐ **ENHANCED**
- `GET /api/abtest/report/{test_id}` - 실험 리포트 생성
- `GET /api/abtest/report/{test_id}/pdf` - PDF 리포트 다운로드
- `GET /api/abtest/learning/patterns` - 학습 패턴 조회
- `GET /api/abtest/report/{test_id}/roi` - ROI 분석
- `GET /api/abtest/report/{test_id}/segments` - 세그먼트별 분석

### 📖 API 문서
서버 실행 후 `http://localhost:5001/docs`에서 완전한 API 문서를 확인할 수 있습니다.

## 🏗️ 시스템 아키텍처 ⭐ **UPDATED**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Server    │    │   Autopilot     │
│   (Streamlit)   │◄──►│   (FastAPI)     │◄──►│   Scheduler     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  AB Test        │
                       │  Manager        │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Dashboard      │    │  Analytics      │
                       │  Manager        │◄──►│  Engine         │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Report         │
                       │  Generator      │
                       └─────────────────┘
```

## 📈 사용 예시

### 1. 실험 계약서 생성
```python
import requests

brief_data = {
    "objective": "구매 전환율(CVR) 최대화",
    "primary_metrics": ["CVR"],
    "secondary_metrics": ["CTR", "ATC"],
    "guardrails": {"LCP": 3.5, "error_rate": 0.005},
    "target_categories": ["스마트폰"],
    "variant_count": 3,
    "distribution_mode": "bandit",
    "mde": 0.1,
    "min_sample_size": 1000
}

response = requests.post("http://localhost:5001/api/abtest/create-with-brief", 
                        json=brief_data)
```

### 2. 자동 생성기 상태 확인 ⭐ **ENHANCED**
```python
response = requests.get("http://localhost:5001/api/abtest/autopilot/status")
status = response.json()
print(f"활성 실험: {status['autopilot_status']['active_autopilot_experiments']}")
print(f"스케줄 상태: {status['schedule_status']}")
print(f"리소스 사용량: {status['resource_usage']}")
```

### 3. 실시간 모니터링
```python
response = requests.get("http://localhost:5001/api/abtest/dashboard/real-time/{test_id}")
metrics = response.json()
print(f"실시간 CVR: {metrics['metrics']['variant_metrics']}")
```

### 4. 향상된 리포트 생성 ⭐ **NEW**
```python
# ROI 분석
roi_response = requests.get(f"http://localhost:5001/api/abtest/report/{test_id}/roi")
roi_data = roi_response.json()
print(f"ROI: {roi_data['roi_percentage']}%")

# 세그먼트별 분석
segments_response = requests.get(f"http://localhost:5001/api/abtest/report/{test_id}/segments")
segments_data = segments_response.json()
print(f"모바일 CVR: {segments_data['mobile']['cvr']}")
```

## 🔧 설정

### 환경 변수
- `MODE`: development/docker/kubernetes
- `KAFKA_BROKER`: Kafka 브로커 주소
- `API_BASE_URL`: API 서버 주소

### 자동 생성기 설정 ⭐ **ENHANCED**
- `max_concurrent_experiments`: 최대 동시 실험 수 (기본값: 5)
- `max_traffic_usage`: 최대 트래픽 사용량 (기본값: 20%)
- `min_daily_sessions`: 최소 일일 세션 수 (기본값: 100)
- `cool_down_days`: 쿨다운 기간 (기본값: 7일)
- `resource_optimization`: 리소스 최적화 활성화 (기본값: true)
- `smart_scheduling`: 스마트 스케줄링 활성화 (기본값: true)

### 대시보드 설정 ⭐ **NEW**
- `real_time_refresh_interval`: 실시간 새로고침 간격 (기본값: 30초)
- `alert_threshold`: 알림 임계값 (기본값: 0.05)
- `performance_monitoring`: 성능 모니터링 활성화 (기본값: true)

## 📝 체크리스트

### "좋은 실험"의 체크리스트 (요구사항 14번)
- [ ] 목표·MDE·기간이 사전에 문서화되어 있다
- [ ] Sticky·SRM·봇 필터가 ON이다
- [ ] 대조군/변형의 페이지 속도 차이가 크지 않다
- [ ] 단 하나의 핵심지표만으로 승패를 가른다
- [ ] 승자라도 가드레일을 깨면 배포하지 않는다
- [ ] 리포트에 세그먼트별 차이와 학습 포인트가 포함된다

### 운영 모드 요약 (요구사항 15번)
- **일일 세션 수가 N 이상?** → A/B + 베이지안 종료
- **아니면** → 밴딧(Thompson)
- **프로모션/법무 이슈?** → 수동 생성
- **아니면** → Autopilot
- **승자 확률 ≥95% & 최소 표본 충족?** → 단계적 승격
- **아니면** → 지속 탐험 또는 기간 상한으로 종료

## 🆕 최신 업데이트 (v2.0)

### 새로운 기능들
- ✅ **실시간 대시보드**: 성능 지표 실시간 모니터링
- ✅ **자동화 시스템**: 스마트 스케줄링 및 리소스 최적화
- ✅ **향상된 분석**: ROI 계산, 세그먼트별 분석
- ✅ **PDF 리포트**: 자동 PDF 리포트 생성
- ✅ **성능 모니터링**: 시스템 성능 실시간 추적
- ✅ **알림 시스템**: 실시간 알림 및 경고
- ✅ **테스트 프레임워크**: 종합적인 테스트 시스템

### 개선된 기능들
- 🔄 **API 성능**: 응답 시간 최적화
- 🔄 **데이터 처리**: 대용량 데이터 처리 개선
- 🔄 **사용자 경험**: 더 직관적인 인터페이스
- 🔄 **문서화**: 상세한 API 문서 및 예시

## 🤝 기여

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원

문제가 있거나 질문이 있으시면 이슈를 생성해 주세요.

## 🔄 버전 히스토리

- **v2.0** (현재): 실시간 대시보드, 자동화 시스템, 향상된 분석 도구 추가
- **v1.0**: 기본 A/B 테스트 시스템 구현
