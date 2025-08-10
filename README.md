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

### 9. 대시보드/운영 UX - 요구사항 9번
- **실시간 타일**: 변형별 Impr/CTR/CVR/매출
- **트렌드**: 시간대별 CVR/퍼널(노출→클릭→구매)
- **승자 확률 P**: 베이지안 CI 시각화
- **경고 배지**: SRM/봇/가드레일
- **제어**: 일시정지/재개, 승자 강제, 단계적 롤아웃
- **결정 로그**: 최근 1h 밴딧 결정 사유

### 10. 리포트 & 인사이트 - 요구사항 10번
- **자동 종료 리포트**: 실험 개요, 최종 성과, 신뢰도
- **세그먼트별 차이**: 모바일·신규 등
- **SRM/가드레일 히스토리**: 데이터 제외율(봇)
- **Actionables**: 구체적인 개선 제안
- **지식화**: 승자 패턴을 변형 생성 템플릿에 반영

### 11. 자동화 루프 - 요구사항 11번
- **Autopilot**: 스케줄러가 대상 선정→실험 생성→시작까지 자동
- **트래픽 예산 관리**: 동시실험 상한/쿨다운으로 과실험 방지
- **프로모션 기간 글로벌 스위치**: 자동 실험 OFF
- **승자 확정 시 쿨다운**: 다음 실험 자동 예약

### 12. 예외·엣지 케이스 핸들링 - 요구사항 12번
- **재고 급감/가격 대변동**: 실험 자동 HOLD
- **극저트래픽 SKU**: 밴딧 + Shadow traffic
- **다채널 유입**: 층화 분배 or 가중치 보정
- **시즌성/외생변수**: 이벤트 태깅

### 13. 거버넌스/보안 - 요구사항 13번
- **PII 저장 금지**: 해시 user_key, 목적 제한·보존기간
- **실험 상태머신**: draft → running → hold → completed → archived
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

## 📊 API 엔드포인트 (통일된 `/api/abtest/` 경로)

### 실험 계약서 관련
- `POST /api/abtest/create-with-brief` - 실험 계약서와 함께 테스트 생성
- `GET /api/abtest/dashboard/metrics` - 대시보드 메트릭 조회
- `GET /api/abtest/dashboard/test-summaries` - 테스트 요약 목록

### 자동 생성기 관련
- `GET /api/abtest/autopilot/status` - 자동 생성 상태 조회
- `POST /api/abtest/autopilot/promotion-mode` - 프로모션 모드 설정
- `POST /api/abtest/autopilot/run-cycle` - 자동 생성 사이클 수동 실행

### 밴딧 알고리즘
- `GET /api/abtest/{test_id}/variant-bandit/{user_id}` - Thompson Sampling 변형 선택
- `GET /api/abtest/bandit/decisions/{test_id}` - 밴딧 의사결정 로그

### 가드레일 모니터링
- `GET /api/abtest/guardrails/alerts` - 가드레일 알림 조회
- `GET /api/abtest/dashboard/real-time/{test_id}` - 실시간 메트릭

### 승자 처리
- `POST /api/abtest/test/{test_id}/promote-winner` - 승자 승격
- `POST /api/abtest/test/{test_id}/auto-rollback` - 자동 롤백 실행

### 리포트
- `GET /api/abtest/report/{test_id}` - 실험 리포트 생성
- `GET /api/abtest/report/{test_id}/pdf` - PDF 리포트 다운로드
- `GET /api/abtest/learning/patterns` - 학습 패턴 조회

### 📖 API 문서
서버 실행 후 `http://localhost:5001/docs`에서 완전한 API 문서를 확인할 수 있습니다.

## 🏗️ 시스템 아키텍처

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
                       ┌─────────────────┐
                       │  Dashboard      │
                       │  Manager        │
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

### 2. 자동 생성기 상태 확인
```python
response = requests.get("http://localhost:5001/api/abtest/autopilot/status")
status = response.json()
print(f"활성 실험: {status['autopilot_status']['active_autopilot_experiments']}")
```

### 3. 실시간 모니터링
```python
response = requests.get("http://localhost:5001/api/abtest/dashboard/real-time/{test_id}")
metrics = response.json()
print(f"실시간 CVR: {metrics['metrics']['variant_metrics']}")
```

## 🔧 설정

### 환경 변수
- `MODE`: development/docker/kubernetes
- `KAFKA_BROKER`: Kafka 브로커 주소
- `API_BASE_URL`: API 서버 주소

### 자동 생성기 설정
- `max_concurrent_experiments`: 최대 동시 실험 수 (기본값: 5)
- `max_traffic_usage`: 최대 트래픽 사용량 (기본값: 20%)
- `min_daily_sessions`: 최소 일일 세션 수 (기본값: 100)
- `cool_down_days`: 쿨다운 기간 (기본값: 7일)

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
