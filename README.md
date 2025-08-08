# 상품 상세페이지 A/B 테스트 시스템

상품 이미지와 간단한 설명을 입력하면 다양한 스타일의 상세페이지를 자동으로 생성하고, A/B 테스트를 통해 최적의 페이지를 찾아주는 AI 기반 시스템입니다.

## 주요 기능

### 🎯 A/B 테스트 관리
- **다양한 페이지 변형 생성**: 히어로, 그리드, 카드, 갤러리 스타일
- **실시간 성과 추적**: CTR, 전환율, 수익 등 다양한 지표
- **통계적 유의성 분석**: 카이제곱 검정을 통한 신뢰할 수 있는 결과
- **사용자 일관성 보장**: 동일 사용자는 항상 같은 변형을 보게 됨

### 🎨 페이지 생성
- **4가지 기본 템플릿**: 모던, 클래식, 미니멀, 컬러풀
- **동적 콘텐츠 생성**: 상품 정보에 맞는 제목, 설명 자동 생성
- **반응형 디자인**: 모바일/데스크톱 최적화
- **실시간 이벤트 추적**: JavaScript를 통한 사용자 행동 분석

### 📊 분석 및 최적화
- **종합 점수 계산**: 목표 지표 기반 가중 평균
- **승자 자동 선정**: 통계적 유의성을 고려한 최적 변형 선택
- **실시간 대시보드**: 테스트 진행 상황 및 결과 시각화

## 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   상품 정보     │    │   페이지 생성기  │    │   A/B 테스트    │
│   입력          │───▶│   (4가지 변형)   │───▶│   관리자        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   HTML 페이지   │    │   이벤트 추적   │
                       │   생성          │    │   및 분석       │
                       └─────────────────┘    └─────────────────┘
```

## Initialize Setting
- Python 버전: v3.10.12
- venv 사용
- fastapi 서버 사용

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 사전 준비
- docker: v28.x ('25.7.7 기준 lts)
- docker compose: v2.x ('25.7.7 기준 lts)

## 사용법 (도커, 개발환경)

### 실행

```bash
# 개발 환경 실행
uvicorn src.app:app --host 0.0.0.0 --port 5001 --reload

# 도커 실행
bash ./scripts/docker-run.sh <DOCKER HUB ID> <SERVICE NAME> <SERVICE PORT: 옵션>
```

### 테스트

```bash
# 기본 API 테스트
curl -X GET "http://localhost:5001/python"

# A/B 테스트 생성
curl -X POST "http://localhost:5001/api/ab-test/create" \
  -H "Content-Type: application/json" \
  -d '{
    "test_name": "스마트폰 A/B 테스트",
    "product_name": "갤럭시 S24",
    "product_image": "https://example.com/s24.jpg",
    "product_description": "최신 갤럭시 스마트폰",
    "price": 1200000,
    "category": "스마트폰",
    "duration_days": 14
  }'
```

## API 엔드포인트

### A/B 테스트 관리

| 메서드 | 엔드포인트 | 설명 |
|--------|------------|------|
| POST | `/api/ab-test/create` | 새로운 A/B 테스트 생성 |
| GET | `/api/ab-test/list` | 모든 테스트 목록 조회 |
| GET | `/api/ab-test/{test_id}` | 특정 테스트 상세 조회 |
| POST | `/api/ab-test/action` | 테스트 시작/일시정지/완료 |
| GET | `/api/ab-test/{test_id}/results` | 테스트 결과 조회 |
| GET | `/api/ab-test/{test_id}/events` | 테스트 이벤트 조회 |

### 이벤트 추적

| 메서드 | 엔드포인트 | 설명 |
|--------|------------|------|
| POST | `/api/ab-test/event` | 이벤트 기록 (노출, 클릭, 전환) |
| GET | `/api/ab-test/{test_id}/variant/{user_id}` | 사용자별 변형 조회 |

### 페이지 생성

| 메서드 | 엔드포인트 | 설명 |
|--------|------------|------|
| GET | `/api/ab-test/{test_id}/page/{variant_id}` | 상세페이지 HTML 생성 |

## 사용 예제

### 1. A/B 테스트 생성

```python
import requests

# 테스트 생성
response = requests.post("http://localhost:5001/api/ab-test/create", json={
    "test_name": "노트북 A/B 테스트",
    "product_name": "MacBook Pro 16",
    "product_image": "https://example.com/macbook.jpg",
    "product_description": "프로페셔널을 위한 최고의 노트북",
    "price": 3500000,
    "category": "노트북",
    "tags": ["애플", "프리미엄", "개발자"],
    "duration_days": 21,
    "target_metrics": {
        "ctr": 0.6,
        "conversion_rate": 0.4
    }
})

test_id = response.json()["test_id"]
print(f"테스트 ID: {test_id}")
```

### 2. 테스트 시작

```python
# 테스트 시작
requests.post("http://localhost:5001/api/ab-test/action", json={
    "test_id": test_id,
    "action": "start"
})
```

### 3. 사용자별 변형 조회

```python
# 사용자에게 표시할 변형 조회
variant_response = requests.get(f"http://localhost:5001/api/ab-test/{test_id}/variant/user123")
variant = variant_response.json()["variant"]
print(f"사용자에게 표시할 변형: {variant['variant_type']}")
```

### 4. 이벤트 기록

```python
# 노출 이벤트 기록
requests.post("http://localhost:5001/api/ab-test/event", json={
    "test_id": test_id,
    "variant_id": variant["variant_id"],
    "event_type": "impression",
    "user_id": "user123",
    "session_id": "session456"
})

# 클릭 이벤트 기록
requests.post("http://localhost:5001/api/ab-test/event", json={
    "test_id": test_id,
    "variant_id": variant["variant_id"],
    "event_type": "click",
    "user_id": "user123",
    "session_id": "session456"
})
```

### 5. 결과 조회

```python
# 테스트 결과 조회
results = requests.get(f"http://localhost:5001/api/ab-test/{test_id}/results").json()
print(f"승자: {results['results']['winner']}")
print(f"총 노출: {results['results']['total_impressions']}")
print(f"총 클릭: {results['results']['total_clicks']}")
```

## 페이지 템플릿

### 템플릿 A: 히어로 모던
- **스타일**: 현대적이고 임팩트 있는 디자인
- **특징**: 큰 이미지, 플로팅 CTA 버튼
- **적합**: 프리미엄 제품, 브랜드 강조

### 템플릿 B: 그리드 클래식
- **스타일**: 전통적이고 안정적인 레이아웃
- **특징**: 2열 그리드, 하단 CTA
- **적합**: 실용적 제품, 정보 중심

### 템플릿 C: 카드 미니멀
- **스타일**: 깔끔하고 심플한 디자인
- **특징**: 카드 형태, 중앙 CTA
- **적합**: 미니멀 제품, 깔끔한 브랜드

### 템플릿 D: 갤러리 컬러풀
- **스타일**: 화려하고 생동감 있는 디자인
- **특징**: 갤러리 레이아웃, 상단 CTA
- **적합**: 패션, 라이프스타일 제품

## 통계 분석

### 지표 설명
- **CTR (Click-Through Rate)**: 노출 대비 클릭 비율
- **전환율**: 클릭 대비 구매/목표 행동 비율
- **수익**: 총 매출액
- **세션 지속시간**: 페이지 체류 시간
- **이탈률**: 페이지를 떠나는 비율

### 통계적 유의성
- **카이제곱 검정**: 변형 간 성과 차이의 통계적 유의성 검증
- **신뢰수준**: 95% (p < 0.05)
- **최소 표본 크기**: 변형당 100회 이상 노출 권장

## 배포 (쿠버네티스)

### 사전 설정

```bash
# azure 설치
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# azure 로그인
az login --use-device-code

# 쿠버네티스 클러스터 연결
az aks get-credentials --resource-group <마이크로소프트 리소스 그룹> --name <마이크로소프트 쿠버네티스 클러스터>
```

### 쿠버네티스 설정 실행

```bash
bash scripts/kube-run.sh <DOCKER HUB ID>
```

### 추가 명령어

```bash
# 제거하기
kubectl delete -f kubernetes/deploy.yml

# 확인하기 (pods, services, deployments..)
kubectl get all

# 로그확인(-f: 실시간 옵션)
kubectl logs <POD NAME>

# 바로 재반영
kubectl get deployment  # 확인
kubectl rollout restart deployment/gateway  # 재반영
```

## 기술 스택

- **백엔드**: FastAPI, Python 3.10
- **데이터 분석**: NumPy, SciPy
- **메시징**: Apache Kafka
- **컨테이너**: Docker
- **오케스트레이션**: Kubernetes
- **프론트엔드**: HTML5, CSS3, JavaScript

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
