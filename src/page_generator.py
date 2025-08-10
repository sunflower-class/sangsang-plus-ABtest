import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class PageTemplate:
    """페이지 템플릿 정보"""
    template_id: str
    name: str
    layout_type: str
    color_scheme: str
    font_style: str
    cta_position: str
    features: List[str]
    css_styles: Dict[str, str]
    html_structure: str

class PageGenerator:
    """상세페이지 생성기"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, PageTemplate]:
        """기본 템플릿 초기화"""
        templates = {}
        
        # 템플릿 A: 히어로 스타일 (현대적)
        templates["hero_modern"] = PageTemplate(
            template_id="hero_modern",
            name="히어로 모던",
            layout_type="hero",
            color_scheme="light",
            font_style="modern",
            cta_position="floating",
            features=["리뷰", "배송정보", "스펙"],
            css_styles={
                "primary_color": "#2563eb",
                "secondary_color": "#f8fafc",
                "text_color": "#1e293b",
                "cta_color": "#dc2626",
                "font_family": "'Inter', sans-serif"
            },
            html_structure="hero_modern"
        )
        
        # 템플릿 B: 그리드 스타일 (클래식)
        templates["grid_classic"] = PageTemplate(
            template_id="grid_classic",
            name="그리드 클래식",
            layout_type="grid",
            color_scheme="neutral",
            font_style="classic",
            cta_position="bottom",
            features=["리뷰", "Q&A", "관련상품"],
            css_styles={
                "primary_color": "#374151",
                "secondary_color": "#f9fafb",
                "text_color": "#111827",
                "cta_color": "#059669",
                "font_family": "'Georgia', serif"
            },
            html_structure="grid_classic"
        )
        
        # 템플릿 C: 카드 스타일 (미니멀)
        templates["card_minimal"] = PageTemplate(
            template_id="card_minimal",
            name="카드 미니멀",
            layout_type="card",
            color_scheme="minimal",
            font_style="elegant",
            cta_position="middle",
            features=["스펙", "배송정보"],
            css_styles={
                "primary_color": "#000000",
                "secondary_color": "#ffffff",
                "text_color": "#374151",
                "cta_color": "#000000",
                "font_family": "'Helvetica Neue', sans-serif"
            },
            html_structure="card_minimal"
        )
        
        # 템플릿 D: 갤러리 스타일 (컬러풀)
        templates["gallery_colorful"] = PageTemplate(
            template_id="gallery_colorful",
            name="갤러리 컬러풀",
            layout_type="gallery",
            color_scheme="colorful",
            font_style="bold",
            cta_position="top",
            features=["리뷰", "Q&A", "관련상품", "스펙"],
            css_styles={
                "primary_color": "#7c3aed",
                "secondary_color": "#fef3c7",
                "text_color": "#1f2937",
                "cta_color": "#f59e0b",
                "font_family": "'Poppins', sans-serif"
            },
            html_structure="gallery_colorful"
        )
        
        return templates
    
    def generate_page_variants(self, product_info: Dict[str, Any], variant_count: int = 4) -> List[Dict[str, Any]]:
        """상품 정보를 바탕으로 다양한 페이지 변형 생성"""
        variants = []
        template_keys = list(self.templates.keys())
        
        # CTA 텍스트 옵션
        cta_options = [
            "지금 구매하기",
            "장바구니 담기",
            "즉시 구매",
            "자세히 보기",
            "할인 받기",
            "특가 구매"
        ]
        
        # 이미지 스타일 옵션
        image_styles = ["original", "enhanced", "minimal", "gallery"]
        
        for i in range(min(variant_count, len(template_keys))):
            template = self.templates[template_keys[i]]
            
            # 변형별 특성 설정
            variant = {
                "variant_id": str(uuid.uuid4()),
                "variant_type": chr(65 + i),  # A, B, C, D
                "title": self._generate_title(product_info, template),
                "description": self._generate_description(product_info, template),
                "layout_type": template.layout_type,
                "color_scheme": template.color_scheme,
                "cta_text": cta_options[i % len(cta_options)],
                "cta_color": template.css_styles["cta_color"],
                "cta_position": template.cta_position,
                "additional_features": template.features,
                "image_style": image_styles[i % len(image_styles)],
                "font_style": template.font_style,
                "created_at": datetime.now().isoformat(),
                "is_active": True,
                "template": asdict(template)
            }
            
            variants.append(variant)
        
        return variants
    
    def _generate_title(self, product_info: Dict[str, Any], template: PageTemplate) -> str:
        """템플릿에 맞는 제목 생성"""
        product_name = product_info.get("product_name", "")
        category = product_info.get("category", "")
        price = product_info.get("price", 0)
        
        if template.font_style == "modern":
            return f"✨ {product_name} - 최신 트렌드"
        elif template.font_style == "classic":
            return f"{product_name} | {category}"
        elif template.font_style == "elegant":
            return f"{product_name}"
        elif template.font_style == "bold":
            return f"🔥 {product_name} 특가!"
        
        return product_name
    
    def _generate_description(self, product_info: Dict[str, Any], template: PageTemplate) -> str:
        """템플릿에 맞는 설명 생성"""
        description = product_info.get("product_description", "")
        price = product_info.get("price", 0)
        category = product_info.get("category", "")
        
        if template.layout_type == "hero":
            return f"{description}\n\n💎 프리미엄 {category} 제품을 특별한 가격으로 만나보세요!"
        elif template.layout_type == "grid":
            return f"{description}\n\n📦 안전한 배송과 함께 만족도 높은 {category}를 경험하세요."
        elif template.layout_type == "card":
            return f"{description}"
        elif template.layout_type == "gallery":
            return f"{description}\n\n🎯 고객들이 선택한 인기 {category} 제품입니다!"
        
        return description
    
    def generate_html_page(self, variant: Dict[str, Any], product_info: Dict[str, Any]) -> str:
        """HTML 페이지 생성"""
        template = variant["template"]
        
        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{variant['title']}</title>
    <style>
        {self._generate_css(template, variant)}
    </style>
</head>
<body>
    {self._generate_html_structure(template['html_structure'], variant, product_info)}
    
    <script>
        {self._generate_javascript(variant)}
    </script>
</body>
</html>
        """
        
        return html
    
    def _generate_css(self, template: Dict[str, Any], variant: Dict[str, Any]) -> str:
        """CSS 스타일 생성"""
        styles = template["css_styles"]
        
        css = f"""
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: {styles['font_family']};
            background-color: {styles['secondary_color']};
            color: {styles['text_color']};
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .product-header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .product-title {{
            font-size: 2.5rem;
            font-weight: bold;
            color: {styles['primary_color']};
            margin-bottom: 10px;
        }}
        
        .product-description {{
            font-size: 1.2rem;
            color: {styles['text_color']};
            margin-bottom: 20px;
        }}
        
        .product-image {{
            width: 100%;
            max-width: 600px;
            height: auto;
            border-radius: 10px;
            margin: 20px 0;
        }}
        
        .product-price {{
            font-size: 2rem;
            font-weight: bold;
            color: {styles['primary_color']};
            margin: 20px 0;
        }}
        
        .cta-button {{
            background-color: {styles['cta_color']};
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 5px;
            font-size: 1.2rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .cta-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        
        .features-section {{
            margin: 40px 0;
            padding: 20px;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .feature-item {{
            margin: 10px 0;
            padding: 10px;
            background-color: {styles['secondary_color']};
            border-radius: 5px;
        }}
        
        .floating-cta {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
        }}
        """
        
        return css
    
    def _generate_html_structure(self, structure_type: str, variant: Dict[str, Any], product_info: Dict[str, Any]) -> str:
        """HTML 구조 생성"""
        if structure_type == "hero_modern":
            return self._generate_hero_structure(variant, product_info)
        elif structure_type == "grid_classic":
            return self._generate_grid_structure(variant, product_info)
        elif structure_type == "card_minimal":
            return self._generate_card_structure(variant, product_info)
        elif structure_type == "gallery_colorful":
            return self._generate_gallery_structure(variant, product_info)
        
        return self._generate_hero_structure(variant, product_info)
    
    def _generate_hero_structure(self, variant: Dict[str, Any], product_info: Dict[str, Any]) -> str:
        """히어로 스타일 구조"""
        return f"""
        <div class="container">
            <div class="product-header">
                <h1 class="product-title">{variant['title']}</h1>
                <p class="product-description">{variant['description']}</p>
            </div>
            
            <div style="text-align: center;">
                <img src="{product_info['product_image']}" alt="{product_info['product_name']}" class="product-image">
                <div class="product-price">₩{product_info['price']:,}</div>
                <button class="cta-button" onclick="handlePurchase()">{variant['cta_text']}</button>
            </div>
            
            <div class="features-section">
                <h3>제품 특징</h3>
                {self._generate_features_html(variant['additional_features'])}
            </div>
        </div>
        
        {self._generate_floating_cta(variant) if variant['cta_position'] == 'floating' else ''}
        """
    
    def _generate_grid_structure(self, variant: Dict[str, Any], product_info: Dict[str, Any]) -> str:
        """그리드 스타일 구조"""
        return f"""
        <div class="container">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 40px; align-items: center;">
                <div>
                    <h1 class="product-title">{variant['title']}</h1>
                    <p class="product-description">{variant['description']}</p>
                    <div class="product-price">₩{product_info['price']:,}</div>
                    <button class="cta-button" onclick="handlePurchase()">{variant['cta_text']}</button>
                </div>
                <div>
                    <img src="{product_info['product_image']}" alt="{product_info['product_name']}" class="product-image">
                </div>
            </div>
            
            <div class="features-section">
                <h3>제품 정보</h3>
                {self._generate_features_html(variant['additional_features'])}
            </div>
        </div>
        """
    
    def _generate_card_structure(self, variant: Dict[str, Any], product_info: Dict[str, Any]) -> str:
        """카드 스타일 구조"""
        return f"""
        <div class="container">
            <div style="max-width: 800px; margin: 0 auto;">
                <div style="background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h1 class="product-title">{variant['title']}</h1>
                    <img src="{product_info['product_image']}" alt="{product_info['product_name']}" class="product-image">
                    <p class="product-description">{variant['description']}</p>
                    <div class="product-price">₩{product_info['price']:,}</div>
                    <button class="cta-button" onclick="handlePurchase()">{variant['cta_text']}</button>
                    
                    <div class="features-section">
                        <h3>상세 정보</h3>
                        {self._generate_features_html(variant['additional_features'])}
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _generate_gallery_structure(self, variant: Dict[str, Any], product_info: Dict[str, Any]) -> str:
        """갤러리 스타일 구조"""
        return f"""
        <div class="container">
            <div class="product-header">
                <h1 class="product-title">{variant['title']}</h1>
                <p class="product-description">{variant['description']}</p>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                <div>
                    <img src="{product_info['product_image']}" alt="{product_info['product_name']}" class="product-image">
                </div>
                <div>
                    <div class="product-price">₩{product_info['price']:,}</div>
                    <button class="cta-button" onclick="handlePurchase()">{variant['cta_text']}</button>
                </div>
            </div>
            
            <div class="features-section">
                <h3>제품 특징</h3>
                {self._generate_features_html(variant['additional_features'])}
            </div>
        </div>
        """
    
    def _generate_features_html(self, features: List[str]) -> str:
        """특징 목록 HTML 생성"""
        feature_icons = {
            "리뷰": "⭐",
            "배송정보": "🚚",
            "스펙": "📋",
            "Q&A": "❓",
            "관련상품": "🛍️"
        }
        
        html = ""
        for feature in features:
            icon = feature_icons.get(feature, "📌")
            html += f'<div class="feature-item">{icon} {feature}</div>'
        
        return html
    
    def _generate_floating_cta(self, variant: Dict[str, Any]) -> str:
        """플로팅 CTA 버튼"""
        return f"""
        <div class="floating-cta">
            <button class="cta-button" onclick="handlePurchase()">{variant['cta_text']}</button>
        </div>
        """
    
    def _generate_javascript(self, variant: Dict[str, Any]) -> str:
        """JavaScript 코드 생성"""
        return f"""
        function handlePurchase() {{
            // A/B 테스트 이벤트 추적
            trackEvent('click', '{variant['variant_id']}');
            
            // 구매 처리 로직
            alert('구매가 완료되었습니다!');
        }}
        
        function trackEvent(eventType, variantId) {{
            // 이벤트 추적 API 호출
            fetch('/api/abtest/event', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify({{
                    test_id: getTestId(),
                    variant_id: variantId,
                    event_type: eventType,
                    user_id: getUserId(),
                    session_id: getSessionId()
                }})
            }});
        }}
        
        function getTestId() {{
            // URL 파라미터에서 테스트 ID 추출
            const urlParams = new URLSearchParams(window.location.search);
            return urlParams.get('test_id') || '';
        }}
        
        function getUserId() {{
            // 사용자 ID 반환 (실제 구현에서는 세션/쿠키에서 추출)
            return localStorage.getItem('user_id') || 'anonymous';
        }}
        
        function getSessionId() {{
            // 세션 ID 반환
            return sessionStorage.getItem('session_id') || Date.now().toString();
        }}
        
        // 페이지 로드 시 노출 이벤트 추적
        window.addEventListener('load', function() {{
            trackEvent('impression', '{variant['variant_id']}');
        }});
        """

# 전역 인스턴스
page_generator = PageGenerator()


