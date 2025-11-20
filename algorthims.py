import math
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import json

# ===== ENUMS & DATA CLASSES =====

class DiscountType(Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    BUY_X_GET_Y = "buy_x_get_y"
    TIERED = "tiered"
    BUNDLE = "bundle"

class CustomerTier(Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    VIP = "vip"

@dataclass
class Product:
    id: int
    name: str
    price: float
    category: str
    stock: int = 0
    cost_price: float = 0.0
    weight: float = 0.0  # kg
    
    def __str__(self):
        return f"Product(id={self.id}, name='{self.name}', price={self.price:,.0f})"

@dataclass
class CartItem:
    product: Product
    quantity: int
    
    @property
    def subtotal(self) -> float:
        return self.product.price * self.quantity
    
    def __str__(self):
        return f"CartItem({self.product.name} x{self.quantity} = {self.subtotal:,.0f})"

@dataclass
class DiscountRule:
    name: str
    discount_type: DiscountType
    value: float  # Percentage or fixed amount
    min_quantity: int = 0
    min_amount: float = 0.0
    max_discount: float = float('inf')
    applicable_categories: List[str] = field(default_factory=list)
    applicable_products: List[int] = field(default_factory=list)
    customer_tiers: List[CustomerTier] = field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    buy_quantity: int = 0  # For buy X get Y
    get_quantity: int = 0  # For buy X get Y
    tier_thresholds: Dict[float, float] = field(default_factory=dict)  # amount: discount%
    
    def is_active(self) -> bool:
        """Kiểm tra khuyến mãi có còn hiệu lực không"""
        now = datetime.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

@dataclass
class Customer:
    id: str
    name: str
    tier: CustomerTier = CustomerTier.BRONZE
    total_spent: float = 0.0
    total_orders: int = 0
    join_date: datetime = field(default_factory=datetime.now)
    
    def get_tier_discount(self) -> float:
        """Lấy % giảm giá theo tier khách hàng"""
        tier_discounts = {
            CustomerTier.BRONZE: 0.0,
            CustomerTier.SILVER: 5.0,
            CustomerTier.GOLD: 10.0,
            CustomerTier.PLATINUM: 15.0,
            CustomerTier.VIP: 20.0
        }
        return tier_discounts.get(self.tier, 0.0)

# ===== MAIN PRICING ENGINE =====

class PricingEngine:
    def __init__(self):
        self.discount_rules: List[DiscountRule] = []
        self.tax_rate = 0.1  # 10% VAT
        self.shipping_rates = {
            (0, 200000): 50000,      # < 200k: 50k ship
            (200000, 500000): 30000, # 200k-500k: 30k ship
            (500000, float('inf')): 0 # >= 500k: free ship
        }
    
    def add_discount_rule(self, rule: DiscountRule):
        """Thêm rule giảm giá"""
        self.discount_rules.append(rule)
        print(f"✅ Đã thêm rule giảm giá: {rule.name}")
    
    def calculate_item_discount(self, cart_item: CartItem, rule: DiscountRule, customer: Customer) -> float:
        """Tính giảm giá cho 1 item theo 1 rule cụ thể"""
        if not rule.is_active():
            return 0.0
        
        # Kiểm tra điều kiện áp dụng
        if not self._is_rule_applicable(cart_item, rule, customer):
            return 0.0
        
        discount = 0.0
        
        if rule.discount_type == DiscountType.PERCENTAGE:
            discount = cart_item.subtotal * (rule.value / 100)
        
        elif rule.discount_type == DiscountType.FIXED_AMOUNT:
            discount = min(rule.value, cart_item.subtotal)
        
        elif rule.discount_type == DiscountType.BUY_X_GET_Y:
            # Mua X tặng Y (giảm giá cho Y sản phẩm rẻ nhất)
            if cart_item.quantity >= rule.buy_quantity:
                free_items = (cart_item.quantity // rule.buy_quantity) * rule.get_quantity
                free_items = min(free_items, cart_item.quantity)
                discount = free_items * cart_item.product.price
        
        elif rule.discount_type == DiscountType.TIERED:
            # Giảm giá theo bậc thang
            for threshold, discount_percent in sorted(rule.tier_thresholds.items()):
                if cart_item.subtotal >= threshold:
                    discount = cart_item.subtotal * (discount_percent / 100)
        
        # Áp dụng giới hạn giảm giá tối đa
        return min(discount, rule.max_discount)
    
    def _is_rule_applicable(self, cart_item: CartItem, rule: DiscountRule, customer: Customer) -> bool:
        """Kiểm tra rule có áp dụng được cho item không"""
        # Kiểm tra số lượng tối thiểu
        if cart_item.quantity < rule.min_quantity:
            return False
        
        # Kiểm tra số tiền tối thiểu
        if cart_item.subtotal < rule.min_amount:
            return False
        
        # Kiểm tra danh mục
        if rule.applicable_categories and cart_item.product.category not in rule.applicable_categories:
            return False
        
        # Kiểm tra sản phẩm cụ thể
        if rule.applicable_products and cart_item.product.id not in rule.applicable_products:
            return False
        
        # Kiểm tra tier khách hàng
        if rule.customer_tiers and customer.tier not in rule.customer_tiers:
            return False
        
        return True
    
    def calculate_best_discount_combination(self, cart_items: List[CartItem], customer: Customer) -> Dict:
        """Thuật toán tìm tổ hợp giảm giá tối ưu"""
        results = {
            'item_discounts': {},
            'total_discount': 0.0,
            'applied_rules': [],
            'subtotal': 0.0
        }
        
        subtotal = sum(item.subtotal for item in cart_items)
        results['subtotal'] = subtotal
        
        # Tính giảm giá cho từng item với từng rule
        for item in cart_items:
            item_key = f"{item.product.id}_{item.quantity}"
            best_discount = 0.0
            best_rule = None
            
            for rule in self.discount_rules:
                discount = self.calculate_item_discount(item, rule, customer)
                if discount > best_discount:
                    best_discount = discount
                    best_rule = rule
            
            if best_discount > 0:
                results['item_discounts'][item_key] = {
                    'product_name': item.product.name,
                    'discount_amount': best_discount,
                    'rule_name': best_rule.name,
                    'original_price': item.subtotal
                }
                results['total_discount'] += best_discount
                if best_rule.name not in results['applied_rules']:
                    results['applied_rules'].append(best_rule.name)
        
        return results
    
    def calculate_shipping_fee(self, subtotal: float, weight: float = 0.0) -> float:
        """Tính phí vận chuyển"""
        base_fee = 0
        for (min_amount, max_amount), fee in self.shipping_rates.items():
            if min_amount <= subtotal < max_amount:
                base_fee = fee
                break
        
        # Thêm phí theo trọng lượng (nếu > 5kg)
        if weight > 5.0:
            weight_fee = (weight - 5.0) * 10000  # 10k/kg
            base_fee += weight_fee
        
        return base_fee
    
    def calculate_final_price(self, cart_items: List[CartItem], customer: Customer, 
                            apply_customer_discount: bool = True) -> Dict:
        """Tính giá cuối cùng với đầy đủ các loại phí và giảm giá"""
        
        # 1. Tính subtotal
        subtotal = sum(item.subtotal for item in cart_items)
        total_weight = sum(item.product.weight * item.quantity for item in cart_items)
        
        # 2. Áp dụng giảm giá sản phẩm
        discount_info = self.calculate_best_discount_combination(cart_items, customer)
        product_discount = discount_info['total_discount']
        
        # 3. Áp dụng giảm giá tier khách hàng (trên subtotal sau giảm giá sản phẩm)
        customer_discount = 0.0
        if apply_customer_discount:
            discounted_subtotal = subtotal - product_discount
            customer_discount = discounted_subtotal * (customer.get_tier_discount() / 100)
        
        # 4. Tính thuế (trên subtotal sau tất cả giảm giá)
        taxable_amount = subtotal - product_discount - customer_discount
        tax_amount = taxable_amount * self.tax_rate
        
        # 5. Tính phí ship (dựa trên subtotal gốc)
        shipping_fee = self.calculate_shipping_fee(subtotal, total_weight)
        
        # 6. Tổng cuối cùng
        total = subtotal - product_discount - customer_discount + tax_amount + shipping_fee
        
        return {
            'subtotal': subtotal,
            'product_discount': product_discount,
            'customer_tier_discount': customer_discount,
            'total_discount': product_discount + customer_discount,
            'tax_amount': tax_amount,
            'shipping_fee': shipping_fee,
            'total': total,
            'total_weight': total_weight,
            'discount_details': discount_info,
            'savings_percentage': ((product_discount + customer_discount) / subtotal * 100) if subtotal > 0 else 0
        }

# ===== ADVANCED ALGORITHMS =====

class AdvancedPricingAlgorithms:
    
    @staticmethod
    def dynamic_pricing(base_price: float, demand_factor: float, competitor_price: float, 
                       inventory_level: int, target_margin: float = 0.3) -> float:
        """Thuật toán định giá động"""
        
        # Điều chỉnh theo cầu
        demand_adjustment = 1 + (demand_factor - 1) * 0.2
        
        # Điều chỉnh theo đối thủ
        competitor_adjustment = 0.95 if competitor_price < base_price else 1.0
        
        # Điều chỉnh theo tồn kho
        if inventory_level < 10:
            inventory_adjustment = 1.1  # Tăng giá khi ít hàng
        elif inventory_level > 100:
            inventory_adjustment = 0.9  # Giảm giá khi nhiều hàng
        else:
            inventory_adjustment = 1.0
        
        dynamic_price = base_price * demand_adjustment * competitor_adjustment * inventory_adjustment
        
        # Đảm bảo margin tối thiểu
        min_price = base_price * (1 + target_margin)
        
        return max(dynamic_price, min_price)
    
    @staticmethod
    def optimal_bundle_pricing(products: List[Product], bundle_discount: float = 0.15) -> Dict:
        """Thuật toán tính giá gói sản phẩm tối ưu"""
        total_price = sum(product.price for product in products)
        bundle_price = total_price * (1 - bundle_discount)
        savings = total_price - bundle_price
        
        return {
            'products': [p.name for p in products],
            'individual_total': total_price,
            'bundle_price': bundle_price,
            'savings': savings,
            'discount_percentage': bundle_discount * 100
        }
    
    @staticmethod
    def loyalty_point_calculation(amount_spent: float, tier: CustomerTier, 
                                bonus_multiplier: float = 1.0) -> int:
        """Tính điểm thưởng loyalty"""
        base_points = int(amount_spent / 1000)  # 1 điểm/1000 VND
        
        tier_multipliers = {
            CustomerTier.BRONZE: 1.0,
            CustomerTier.SILVER: 1.2,
            CustomerTier.GOLD: 1.5,
            CustomerTier.PLATINUM: 2.0,
            CustomerTier.VIP: 3.0
        }
        
        multiplier = tier_multipliers.get(tier, 1.0) * bonus_multiplier
        return int(base_points * multiplier)

# ===== DEMO & TESTING =====

def create_sample_data():
    """Tạo dữ liệu mẫu để test"""
    
    # Sản phẩm mẫu
    products = [
        Product(1, "iPhone 15 Pro Max", 32990000, "Electronics", 50, 25000000, 0.24),
        Product(2, "MacBook Air M2", 28990000, "Electronics", 30, 22000000, 1.29),
        Product(3, "AirPods Pro 2", 6990000, "Electronics", 100, 4500000, 0.056),
        Product(4, "iPad Air", 16990000, "Electronics", 40, 12000000, 0.46),
        Product(5, "Apple Watch Ultra", 19990000, "Electronics", 25, 15000000, 0.061),
        Product(6, "Áo thun", 299000, "Fashion", 200, 150000, 0.2),
        Product(7, "Giày sneaker", 1990000, "Fashion", 80, 1200000, 0.8),
    ]
    
    # Khách hàng mẫu
    customers = [
        Customer("CUST001", "Nguyễn Văn A", CustomerTier.BRONZE, 0, 0),
        Customer("VIP001", "Trần Thị B", CustomerTier.VIP, 50000000, 25),
        Customer("GOLD001", "Lê Văn C", CustomerTier.GOLD, 15000000, 12),
    ]
    
    return products, customers

def create_discount_rules():
    """Tạo các rule giảm giá mẫu"""
    rules = [
        # Giảm giá phần trăm cho Electronics
        DiscountRule(
            name="Flash Sale Electronics 20%",
            discount_type=DiscountType.PERCENTAGE,
            value=20.0,
            applicable_categories=["Electronics"],
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            max_discount=5000000
        ),
        
        # Mua 2 tặng 1 cho Fashion
        DiscountRule(
            name="Buy 2 Get 1 Free Fashion",
            discount_type=DiscountType.BUY_X_GET_Y,
            buy_quantity=2,
            get_quantity=1,
            applicable_categories=["Fashion"],
            value=0  # Không dùng cho loại này
        ),
        
        # Giảm giá theo bậc thang
        DiscountRule(
            name="Tiered Discount",
            discount_type=DiscountType.TIERED,
            tier_thresholds={
                10000000: 5.0,   # >= 10M: 5%
                20000000: 10.0,  # >= 20M: 10%
                50000000: 15.0   # >= 50M: 15%
            },
            value=0
        ),
        
        # Giảm giá cố định cho VIP
        DiscountRule(
            name="VIP Fixed Discount",
            discount_type=DiscountType.FIXED_AMOUNT,
            value=1000000,  # Giảm 1M
            customer_tiers=[CustomerTier.VIP, CustomerTier.PLATINUM],
            min_amount=5000000
        )
    ]
    
    return rules

def main():
    print("🧮 === THUẬT TOÁN TÍNH TIỀN & GIẢM GIÁ PYTHON ===\n")
    
    # Khởi tạo
    pricing_engine = PricingEngine()
    products, customers = create_sample_data()
    rules = create_discount_rules()
    
    # Thêm rules
    for rule in rules:
        pricing_engine.add_discount_rule(rule)
    
    print("\n📱 DANH SÁCH SẢN PHẨM:")
    for product in products[:5]:  # Hiển thị 5 sản phẩm đầu
        print(f"  {product}")
    
    # Tạo giỏ hàng test
    cart_items = [
        CartItem(products[0], 2),  # iPhone x2
        CartItem(products[1], 1),  # MacBook x1
        CartItem(products[2], 3),  # AirPods x3
        CartItem(products[5], 4),  # Áo thun x4 (để test buy 2 get 1)
    ]
    
    customer = customers[1]  # VIP customer
    
    print(f"\n👤 KHÁCH HÀNG: {customer.name} ({customer.tier.value.upper()})")
    print("🛒 GIỎ HÀNG:")
    for item in cart_items:
        print(f"  {item}")
    
    # Tính toán giá cuối cùng
    result = pricing_engine.calculate_final_price(cart_items, customer)
    
    print(f"\n💰 TÍNH TOÁN GIÁ CUỐI CÙNG:")
    print(f"📊 Tạm tính: {result['subtotal']:,.0f} VNĐ")
    print(f"🎯 Giảm giá sản phẩm: -{result['product_discount']:,.0f} VNĐ")
    print(f"👑 Giảm giá tier ({customer.get_tier_discount()}%): -{result['customer_tier_discount']:,.0f} VNĐ")
    print(f"💸 Tổng giảm giá: -{result['total_discount']:,.0f} VNĐ ({result['savings_percentage']:.1f}%)")
    print(f"🧾 Thuế VAT (10%): +{result['tax_amount']:,.0f} VNĐ")
    print(f"🚚 Phí vận chuyển: +{result['shipping_fee']:,.0f} VNĐ")
    print(f"⚖️  Tổng trọng lượng: {result['total_weight']:.2f} kg")
    print(f"💳 THÀNH TIỀN: {result['total']:,.0f} VNĐ")
    
    # Chi tiết giảm giá
    print(f"\n🎁 CHI TIẾT GIẢM GIÁ:")
    for item_key, discount_detail in result['discount_details']['item_discounts'].items():
        print(f"  📱 {discount_detail['product_name']}: -{discount_detail['discount_amount']:,.0f} VNĐ ({discount_detail['rule_name']})")
    
    print(f"\n📋 CÁC RULE ÁP DỤNG: {', '.join(result['discount_details']['applied_rules'])}")
    
    # Demo thuật toán nâng cao
    print(f"\n🚀 === THUẬT TOÁN NÂNG CAO ===")
    
    # Dynamic pricing
    dynamic_price = AdvancedPricingAlgorithms.dynamic_pricing(
        base_price=products[0].price,
        demand_factor=1.5,  # Cầu cao
        competitor_price=30000000,  # Đối thủ rẻ hơn
        inventory_level=5   # Ít hàng
    )
    print(f"📈 Dynamic Pricing iPhone: {dynamic_price:,.0f} VNĐ (gốc: {products[0].price:,.0f} VNĐ)")
    
    # Bundle pricing
    bundle_info = AdvancedPricingAlgorithms.optimal_bundle_pricing(
        products=[products[0], products[2], products[4]], 
        bundle_discount=0.12
    )
    print(f"📦 Bundle Apple Ecosystem:")
    print(f"  - Sản phẩm: {', '.join(bundle_info['products'])}")
    print(f"  - Giá lẻ: {bundle_info['individual_total']:,.0f} VNĐ")
    print(f"  - Giá bundle: {bundle_info['bundle_price']:,.0f} VNĐ")
    print(f"  - Tiết kiệm: {bundle_info['savings']:,.0f} VNĐ ({bundle_info['discount_percentage']}%)")
    
    # Loyalty points
    points = AdvancedPricingAlgorithms.loyalty_point_calculation(
        amount_spent=result['total'],
        tier=customer.tier,
        bonus_multiplier=1.5  # Khuyến mãi x1.5 điểm
    )
    print(f"🎁 Điểm thưởng: +{points:,} điểm (tier {customer.tier.value}, bonus x1.5)")
    
    # Tính toán ROI cho shop
    total_cost = sum(item.product.cost_price * item.quantity for item in cart_items)
    profit = result['total'] - result['tax_amount'] - total_cost
    roi = (profit / total_cost * 100) if total_cost > 0 else 0
    
    print(f"\n💼 === PHÂN TÍCH KINH DOANH ===")
    print(f"💰 Doanh thu (sau thuế): {result['total'] - result['tax_amount']:,.0f} VNĐ")
    print(f"💸 Tổng chi phí: {total_cost:,.0f} VNĐ")
    print(f"📈 Lợi nhuận: {profit:,.0f} VNĐ")
    print(f"📊 ROI: {roi:.1f}%")
    
    print(f"\n✅ Demo hoàn thành!")

if __name__ == "__main__":
    main()      