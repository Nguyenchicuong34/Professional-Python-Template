// ===== PRODUCT CLASS =====
class Product {
    private int id;
    private String name;
    private double price;
    private int stock;
    private String category;
    private double discount;
    private boolean isActive;
    
    public Product(int id, String name, double price, int stock, String category) {
        this.id = id;
        this.name = name;
        this.price = price;
        this.stock = stock;
        this.category = category;
        this.discount = 0.0;
        this.isActive = true;
    }
    
    // Getters and Setters
    public int getId() { return id; }
    public String getName() { return name; }
    public double getPrice() { return price; }
    public int getStock() { return stock; }
    public String getCategory() { return category; }
    public double getDiscount() { return discount; }
    public boolean isActive() { return isActive; }
    
    public void setStock(int stock) { this.stock = stock; }
    public void setDiscount(double discount) { this.discount = discount; }
    public void setActive(boolean active) { this.isActive = active; }
    
    // Tính giá sau giảm giá
    public double getDiscountedPrice() {
        return price * (1 - discount / 100);
    }
    
    // Kiểm tra có đủ hàng không
    public boolean isAvailable(int quantity) {
        return isActive && stock >= quantity;
    }
    
    // Giảm số lượng tồn kho
    public boolean reduceStock(int quantity) {
        if (isAvailable(quantity)) {
            stock -= quantity;
            return true;
        }
        return false;
    }
    
    @Override
    public String toString() {
        return String.format("Product{id=%d, name='%s', price=%.2f, stock=%d, category='%s', discount=%.1f%%}", 
                            id, name, price, stock, category, discount);
    }
}

// ===== CART ITEM CLASS =====
class CartItem {
    private Product product;
    private int quantity;
    private double unitPrice;
    
    public CartItem(Product product, int quantity) {
        this.product = product;
        this.quantity = quantity;
        this.unitPrice = product.getDiscountedPrice();
    }
    
    // Getters
    public Product getProduct() { return product; }
    public int getQuantity() { return quantity; }
    public double getUnitPrice() { return unitPrice; }
    
    // Setters
    public void setQuantity(int quantity) { this.quantity = quantity; }
    
    // Tính tổng tiền của item này
    public double getTotalPrice() {
        return unitPrice * quantity;
    }
    
    // Cập nhật số lượng
    public boolean updateQuantity(int newQuantity) {
        if (product.isAvailable(newQuantity)) {
            this.quantity = newQuantity;
            return true;
        }
        return false;
    }
    
    @Override
    public String toString() {
        return String.format("CartItem{product='%s', quantity=%d, unitPrice=%.2f, total=%.2f}", 
                            product.getName(), quantity, unitPrice, getTotalPrice());
    }
}

// ===== SHOPPING CART CLASS =====
import java.util.*;

class ShoppingCart {
    private List<CartItem> items;
    private String customerId;
    private Date createdAt;
    
    public ShoppingCart(String customerId) {
        this.customerId = customerId;
        this.items = new ArrayList<>();
        this.createdAt = new Date();
    }
    
    // Thêm sản phẩm vào giỏ hàng
    public boolean addProduct(Product product, int quantity) {
        if (!product.isAvailable(quantity)) {
            System.out.println("❌ Không đủ hàng trong kho! Còn lại: " + product.getStock());
            return false;
        }
        
        // Kiểm tra xem sản phẩm đã có trong giỏ chưa
        for (CartItem item : items) {
            if (item.getProduct().getId() == product.getId()) {
                int newQuantity = item.getQuantity() + quantity;
                if (product.isAvailable(newQuantity)) {
                    item.setQuantity(newQuantity);
                    System.out.println("✅ Đã cập nhật số lượng: " + product.getName() + " x" + newQuantity);
                    return true;
                } else {
                    System.out.println("❌ Không thể thêm. Tổng số lượng vượt quá tồn kho!");
                    return false;
                }
            }
        }
        
        // Thêm sản phẩm mới
        items.add(new CartItem(product, quantity));
        System.out.println("✅ Đã thêm vào giỏ hàng: " + product.getName() + " x" + quantity);
        return true;
    }
    
    // Xóa sản phẩm khỏi giỏ hàng
    public boolean removeProduct(int productId) {
        items.removeIf(item -> item.getProduct().getId() == productId);
        System.out.println("🗑️ Đã xóa sản phẩm khỏi giỏ hàng!");
        return true;
    }
    
    // Cập nhật số lượng sản phẩm
    public boolean updateQuantity(int productId, int newQuantity) {
        for (CartItem item : items) {
            if (item.getProduct().getId() == productId) {
                if (newQuantity <= 0) {
                    return removeProduct(productId);
                }
                return item.updateQuantity(newQuantity);
            }
        }
        return false;
    }
    
    // Tính tổng số lượng sản phẩm
    public int getTotalItems() {
        return items.stream().mapToInt(CartItem::getQuantity).sum();
    }
    
    // Tính tổng tiền trước thuế
    public double getSubtotal() {
        return items.stream().mapToDouble(CartItem::getTotalPrice).sum();
    }
    
    // Tính thuế VAT (10%)
    public double getTax() {
        return getSubtotal() * 0.1;
    }
    
    // Tính phí ship (miễn phí nếu > 500k)
    public double getShippingFee() {
        double subtotal = getSubtotal();
        if (subtotal >= 500000) {
            return 0.0;
        } else if (subtotal >= 200000) {
            return 30000;
        } else {
            return 50000;
        }
    }
    
    // Tính tổng tiền cuối cùng
    public double getTotal() {
        return getSubtotal() + getTax() + getShippingFee();
    }
    
    // Lấy danh sách sản phẩm
    public List<CartItem> getItems() {
        return new ArrayList<>(items);
    }
    
    // Kiểm tra giỏ hàng có trống không
    public boolean isEmpty() {
        return items.isEmpty();
    }
    
    // Xóa toàn bộ giỏ hàng
    public void clear() {
        items.clear();
    }
}

// ===== ORDER CLASS =====
import java.util.UUID;
import java.text.SimpleDateFormat;

class Order {
    public enum OrderStatus {
        PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED
    }
    
    private String orderId;
    private String customerId;
    private List<CartItem> items;
    private double subtotal;
    private double tax;
    private double shippingFee;
    private double total;
    private OrderStatus status;
    private Date orderDate;
    private String shippingAddress;
    private String paymentMethod;
    
    public Order(String customerId, ShoppingCart cart, String shippingAddress, String paymentMethod) {
        this.orderId = "ORD" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        this.customerId = customerId;
        this.items = new ArrayList<>(cart.getItems());
        this.subtotal = cart.getSubtotal();
        this.tax = cart.getTax();
        this.shippingFee = cart.getShippingFee();
        this.total = cart.getTotal();
        this.status = OrderStatus.PENDING;
        this.orderDate = new Date();
        this.shippingAddress = shippingAddress;
        this.paymentMethod = paymentMethod;
    }
    
    // Getters
    public String getOrderId() { return orderId; }
    public String getCustomerId() { return customerId; }
    public List<CartItem> getItems() { return items; }
    public double getSubtotal() { return subtotal; }
    public double getTax() { return tax; }
    public double getShippingFee() { return shippingFee; }
    public double getTotal() { return total; }
    public OrderStatus getStatus() { return status; }
    public Date getOrderDate() { return orderDate; }
    public String getShippingAddress() { return shippingAddress; }
    public String getPaymentMethod() { return paymentMethod; }
    
    // Cập nhật trạng thái đơn hàng
    public void updateStatus(OrderStatus newStatus) {
        this.status = newStatus;
        System.out.println("📦 Đơn hàng " + orderId + " đã cập nhật trạng thái: " + newStatus);
    }
    
    // Tính toán thuật toán ước tính thời gian giao hàng
    public int getEstimatedDeliveryDays() {
        switch (paymentMethod.toLowerCase()) {
            case "cod": return 3 + (int)(Math.random() * 3); // 3-5 ngày
            case "banking": return 2 + (int)(Math.random() * 2); // 2-3 ngày
            case "credit": return 1 + (int)(Math.random() * 2); // 1-2 ngày
            default: return 5;
        }
    }
    
    @Override
    public String toString() {
        SimpleDateFormat sdf = new SimpleDateFormat("dd/MM/yyyy HH:mm:ss");
        return String.format(
            "=== ĐON HÀNG %s ===\n" +
            "Khách hàng: %s\n" +
            "Ngày đặt: %s\n" +
            "Trạng thái: %s\n" +
            "Địa chỉ: %s\n" +
            "Thanh toán: %s\n" +
            "Số sản phẩm: %d\n" +
            "Tạm tính: %.2f VNĐ\n" +
            "Thuế VAT: %.2f VNĐ\n" +
            "Phí ship: %.2f VNĐ\n" +
            "TỔNG CỘNG: %.2f VNĐ\n" +
            "Dự kiến giao: %d ngày",
            orderId, customerId, sdf.format(orderDate), status, 
            shippingAddress, paymentMethod, items.size(),
            subtotal, tax, shippingFee, total, getEstimatedDeliveryDays()
        );
    }
}

// ===== ORDER MANAGEMENT SYSTEM =====
class OrderManager {
    private List<Order> orders;
    private Map<String, Integer> productSales; // Thống kê bán hàng
    
    public OrderManager() {
        this.orders = new ArrayList<>();
        this.productSales = new HashMap<>();
    }
    
    // Tạo đơn hàng mới
    public Order createOrder(String customerId, ShoppingCart cart, String address, String paymentMethod) {
        if (cart.isEmpty()) {
            throw new IllegalArgumentException("❌ Giỏ hàng trống!");
        }
        
        // Kiểm tra tồn kho trước khi tạo đơn
        for (CartItem item : cart.getItems()) {
            if (!item.getProduct().isAvailable(item.getQuantity())) {
                throw new IllegalStateException("❌ Sản phẩm " + item.getProduct().getName() + " không đủ hàng!");
            }
        }
        
        Order order = new Order(customerId, cart, address, paymentMethod);
        orders.add(order);
        
        // Cập nhật tồn kho và thống kê
        updateInventoryAndStats(order);
        
        System.out.println("✅ Đã tạo đơn hàng thành công: " + order.getOrderId());
        return order;
    }
    
    // Cập nhật tồn kho và thống kê bán hàng
    private void updateInventoryAndStats(Order order) {
        for (CartItem item : order.getItems()) {
            Product product = item.getProduct();
            int quantity = item.getQuantity();
            
            // Giảm tồn kho
            product.reduceStock(quantity);
            
            // Cập nhật thống kê
            productSales.put(product.getName(), 
                productSales.getOrDefault(product.getName(), 0) + quantity);
        }
    }
    
    // Tìm đơn hàng theo ID
    public Order findOrder(String orderId) {
        return orders.stream()
                    .filter(order -> order.getOrderId().equals(orderId))
                    .findFirst()
                    .orElse(null);
    }
    
    // Lấy đơn hàng theo khách hàng
    public List<Order> getOrdersByCustomer(String customerId) {
        return orders.stream()
                    .filter(order -> order.getCustomerId().equals(customerId))
                    .collect(ArrayList::new, (list, order) -> list.add(order), List::addAll);
    }
    
    // Thuật toán tính doanh thu theo thời gian
    public double calculateRevenue(Date startDate, Date endDate) {
        return orders.stream()
                    .filter(order -> order.getOrderDate().after(startDate) && 
                                   order.getOrderDate().before(endDate))
                    .mapToDouble(Order::getTotal)
                    .sum();
    }
    
    // Sản phẩm bán chạy nhất
    public String getBestSellingProduct() {
        return productSales.entrySet().stream()
                          .max(Map.Entry.comparingByValue())
                          .map(Map.Entry::getKey)
                          .orElse("Chưa có dữ liệu");
    }
    
    // Thống kê tổng quan
    public void printStatistics() {
        System.out.println("\n=== THỐNG KÊ BÁN HÀNG ===");
        System.out.println("Tổng đơn hàng: " + orders.size());
        System.out.println("Doanh thu: " + calculateRevenue(new Date(0), new Date()) + " VNĐ");
        System.out.println("Sản phẩm bán chạy: " + getBestSellingProduct());
        System.out.println("\n📊 Chi tiết bán hàng:");
        productSales.forEach((product, quantity) -> 
            System.out.println("  - " + product + ": " + quantity + " sản phẩm"));
    }
}

// ===== DISCOUNT ALGORITHM =====
class DiscountManager {
    
    // Tính giảm giá theo số lượng (Bulk discount)
    public static double calculateBulkDiscount(int quantity) {
        if (quantity >= 10) return 15.0;      // 15% cho >= 10 sản phẩm
        else if (quantity >= 5) return 10.0;  // 10% cho >= 5 sản phẩm
        else if (quantity >= 3) return 5.0;   // 5% cho >= 3 sản phẩm
        return 0.0;
    }
    
    // Giảm giá cho khách hàng VIP
    public static double calculateVIPDiscount(String customerId, double totalAmount) {
        // Giả sử VIP được xác định bởi prefix "VIP"
        if (customerId.startsWith("VIP")) {
            if (totalAmount >= 1000000) return 20.0;      // 20% cho VIP mua >= 1M
            else if (totalAmount >= 500000) return 15.0;  // 15% cho VIP mua >= 500k
            else return 10.0;                             // 10% cho VIP
        }
        return 0.0;
    }
    
    // Giảm giá theo thời gian (Flash sale)
    public static double calculateTimeBasedDiscount() {
        Calendar cal = Calendar.getInstance();
        int hour = cal.get(Calendar.HOUR_OF_DAY);
        
        // Flash sale 12h-14h và 20h-22h
        if ((hour >= 12 && hour <= 14) || (hour >= 20 && hour <= 22)) {
            return 25.0; // 25% giảm giá flash sale
        }
        return 0.0;
    }
    
    // Tính tổng giảm giá tối ưu
    public static double calculateOptimalDiscount(String customerId, int totalQuantity, double totalAmount) {
        double bulkDiscount = calculateBulkDiscount(totalQuantity);
        double vipDiscount = calculateVIPDiscount(customerId, totalAmount);
        double timeDiscount = calculateTimeBasedDiscount();
        
        // Áp dụng giảm giá cao nhất (không cộng dồn)
        return Math.max(Math.max(bulkDiscount, vipDiscount), timeDiscount);
    }
}

// ===== MAIN DEMO CLASS =====
public class ShoppingSystem {
    public static void main(String[] args) {
        System.out.println("🛒 === HỆ THỐNG MUA BÁN JAVA ===\n");
        
        // Tạo sản phẩm
        Product[] products = {
            new Product(1, "iPhone 15 Pro Max", 32990000, 50, "Phone"),
            new Product(2, "MacBook Air M2", 28990000, 30, "Laptop"),
            new Product(3, "AirPods Pro 2", 6990000, 100, "Accessory"),
            new Product(4, "iPad Air", 16990000, 40, "Tablet"),
            new Product(5, "Samsung Galaxy S24", 22990000, 35, "Phone")
        };
        
        // Thiết lập giảm giá
        products[0].setDiscount(10.0); // iPhone giảm 10%
        products[2].setDiscount(5.0);  // AirPods giảm 5%
        
        // Tạo giỏ hàng cho khách VIP
        ShoppingCart cart = new ShoppingCart("VIP001");
        OrderManager orderManager = new OrderManager();
        
        System.out.println("📱 DANH SÁCH SẢN PHẨM:");
        for (Product p : products) {
            System.out.println("  " + p);
        }
        
        // Demo thêm sản phẩm vào giỏ
        System.out.println("\n🛍️ THÊM SẢN PHẨM VÀO GIỎ HÀNG:");
        cart.addProduct(products[0], 2); // iPhone x2
        cart.addProduct(products[1], 1); // MacBook x1
        cart.addProduct(products[2], 3); // AirPods x3
        cart.addProduct(products[0], 1); // Thêm iPhone (sẽ cập nhật số lượng)
        
        // Hiển thị giỏ hàng
        System.out.println("\n📋 THÔNG TIN GIỎ HÀNG:");
        System.out.println("Tổng sản phẩm: " + cart.getTotalItems());
        System.out.println("Tạm tính: " + String.format("%.2f", cart.getSubtotal()) + " VNĐ");
        System.out.println("Thuế VAT (10%): " + String.format("%.2f", cart.getTax()) + " VNĐ");
        System.out.println("Phí ship: " + String.format("%.2f", cart.getShippingFee()) + " VNĐ");
        System.out.println("TỔNG CỘNG: " + String.format("%.2f", cart.getTotal()) + " VNĐ");
        
        // Tính giảm giá
        double discount = DiscountManager.calculateOptimalDiscount(
            "VIP001", cart.getTotalItems(), cart.getSubtotal());
        double discountAmount = cart.getSubtotal() * (discount / 100);
        double finalTotal = cart.getTotal() - discountAmount;
        
        System.out.println("\n💰 TÍNH TOÁN GIẢM GIÁ:");
        System.out.println("Giảm giá tối ưu: " + discount + "%");
        System.out.println("Số tiền giảm: " + String.format("%.2f", discountAmount) + " VNĐ");
        System.out.println("THÀNH TIỀN: " + String.format("%.2f", finalTotal) + " VNĐ");
        
        // Tạo đơn hàng
        System.out.println("\n📦 TẠO ĐƠN HÀNG:");
        try {
            Order order = orderManager.createOrder(
                "VIP001", 
                cart, 
                "140 Âu Cơ, Quận 1, TP.HCM", 
                "banking"
            );
            
            System.out.println("\n" + order);
            
            // Cập nhật trạng thái đơn hàng
            System.out.println("\n🔄 CẬP NHẬT TRẠNG THÁI:");
            order.updateStatus(Order.OrderStatus.CONFIRMED);
            order.updateStatus(Order.OrderStatus.PROCESSING);
            order.updateStatus(Order.OrderStatus.SHIPPED);
            
            // Demo đơn hàng thứ 2
            System.out.println("\n--- ĐƠN HÀNG THỨ 2 ---");
            ShoppingCart cart2 = new ShoppingCart("CUST002");
            cart2.addProduct(products[3], 1); // iPad
            cart2.addProduct(products[4], 2); // Samsung x2
            
            Order order2 = orderManager.createOrder(
                "CUST002", cart2, "456 Lê Văn B, Quận 3, TP.HCM", "cod");
            
            // Thống kê
            orderManager.printStatistics();
            
            // Kiểm tra tồn kho sau khi bán
            System.out.println("\n📦 TỒN KHO SAU KHI BÁN:");
            for (Product p : products) {
                System.out.println("  " + p.getName() + ": còn " + p.getStock() + " sản phẩm");
            }
            
        } catch (Exception e) {
            System.err.println("Lỗi: " + e.getMessage());
        }
        
        System.out.println("\n✅ Demo hoàn thành!");
    }
}