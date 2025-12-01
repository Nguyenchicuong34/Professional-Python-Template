import json
import os
from datetime import datetime
from typing import List, Dict, Optional

# Thư viện giao diện
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.layout import Layout
from rich import box
from rich.text import Text

console = Console()
DATA_FILE = "finance_pro_data.json"

class Transaction:
    """
    Class đại diện cho một giao dịch (tương tự POJO/DTO trong Java/C#)
    Dùng class giúp code tường minh hơn dict thuần.
    """
    def __init__(self, t_id: int, t_type: str, category: str, amount: int, desc: str, date: str):
        self.id = t_id
        self.type = t_type       # "Thu" hoặc "Chi"
        self.category = category # Ăn uống, Di chuyển, Lương...
        self.amount = amount
        self.desc = desc
        self.date = date

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(data: dict):
        return Transaction(data['id'], data['type'], data['category'], data['amount'], data['desc'], data['date'])

class FinanceApp:
    def __init__(self):
        self.transactions: List[Transaction] = self.load_data()

    # ================= QUẢN LÝ FILE (I/O) =================
    def load_data(self) -> List[Transaction]:
        if not os.path.exists(DATA_FILE):
            return []
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert List[Dict] -> List[Transaction]
                return [Transaction.from_dict(item) for item in data]
        except Exception:
            return []

    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            # Convert List[Transaction] -> List[Dict] để lưu JSON
            json.dump([t.to_dict() for t in self.transactions], f, indent=4, ensure_ascii=False)

    # ================= VALIDATION HELPERS =================
    def get_new_id(self) -> int:
        if not self.transactions:
            return 1
       
        return max(t.id for t in self.transactions) + 1

    def input_positive_amount(self, message="Số tiền (VNĐ)") -> int:
        while True:
            amount = IntPrompt.ask(message)
            if amount > 0:
                return amount
            console.print("[red] Số tiền phải lớn hơn 0![/red]")

    # ================= CHỨC NĂNG CRUD =================
    def add_transaction(self):
        console.clear()
        console.print(Panel("[bold green]THÊM GIAO DỊCH MỚI[/bold green]", expand=False))

        # 1. Chọn loại 
        t_type = Prompt.ask("Loại giao dịch", choices=["Thu", "Chi"], default="Chi")
        
        # 2. Chọn danh mục 
        categories = ["Ăn uống", "Di chuyển", "Mua sắm", "Lương", "Thưởng", "Khác"]
        category = Prompt.ask("Danh mục", choices=categories, default="Khác")

        # 3. Nhập số tiền 
        amount = self.input_positive_amount()

        # 4. Nhập nội dung
        desc = Prompt.ask("Ghi chú")

        # 5. Ngày tháng 
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        new_trans = Transaction(self.get_new_id(), t_type, category, amount, desc, date_str)
        self.transactions.append(new_trans)
        self.save_data()
        console.print(f"[bold green]✔ Đã thêm thành công! ID: {new_trans.id}[/bold green]")

    def view_transactions(self, data_source=None):
        """Hiển thị danh sách, hỗ trợ nhận data từ nguồn tìm kiếm"""
        data = data_source if data_source is not None else self.transactions
        
        if not data:
            console.print("[yellow] Danh sách trống![/yellow]")
            return

        table = Table(title="SỔ THU CHI", box=box.DOUBLE_EDGE, header_style="bold cyan")
        
        table.add_column("ID", justify="center", style="dim", width=4)
        table.add_column("Ngày", justify="center", width=16)
        table.add_column("Loại", justify="center", width=8)
        table.add_column("Danh Mục", style="magenta")
        table.add_column("Nội Dung", style="white")
        table.add_column("Số Tiền", justify="right", style="bold")

        total_thu = 0
        total_chi = 0

        for t in data:
            # Logic màu sắc: Thu màu xanh, Chi màu đỏ
            color = "green" if t.type == "Thu" else "red"
            sign = "+" if t.type == "Thu" else "-"
            
            table.add_row(
                str(t.id),
                t.date,
                f"[{color}]{t.type}[/{color}]",
                t.category,
                t.desc,
                f"[{color}]{sign} {t.amount:,.0f} đ[/{color}]"
            )

            if t.type == "Thu": total_thu += t.amount
            else: total_chi += t.amount

        console.print(table)
        
       
        balance = total_thu - total_chi
        console.print(f" [dim]Tổng bản ghi: {len(data)}[/dim] | Dư: [bold yellow]{balance:,.0f} đ[/bold yellow]", justify="center")

    def update_transaction(self):
        self.view_transactions()
        if not self.transactions: return

        t_id = IntPrompt.ask("📝 Nhập ID muốn sửa (0 để hủy)")
        if t_id == 0: return

       
        target = next((t for t in self.transactions if t.id == t_id), None)

        if not target:
            console.print(f"[red]Không tìm thấy ID {t_id}[/red]")
            return

        console.print(Panel(f"Đang sửa ID: [bold]{t_id}[/bold] - Giữ nguyên ấn Enter", style="blue"))

    
        target.type = Prompt.ask("Loại", choices=["Thu", "Chi"], default=target.type)
        
        categories = ["Ăn uống", "Di chuyển", "Mua sắm", "Lương", "Thưởng", "Khác"]
        target.category = Prompt.ask("Danh mục", choices=categories, default=target.category)
        
        
        amt_input = Prompt.ask(f"Số tiền ({target.amount})", default=str(target.amount))
        if amt_input.isdigit():
            target.amount = int(amt_input)
        
        target.desc = Prompt.ask("Ghi chú", default=target.desc)

        self.save_data()
        console.print("[bold green]✔ Cập nhật thành công![/bold green]")

    def delete_transaction(self):
        self.view_transactions()
        if not self.transactions: return

        t_id = IntPrompt.ask(" Nhập ID muốn xóa (0 để hủy)")
        if t_id == 0: return

        target = next((t for t in self.transactions if t.id == t_id), None)
        if target:
            
            if Confirm.ask(f"Bạn chắc chắn muốn xóa mục '{target.desc}'?"):
                self.transactions.remove(target)
                self.save_data()
                console.print("[bold green]✔ Đã xóa![/bold green]")
        else:
            console.print("[red] ID không tồn tại![/red]")

    def search_transaction(self):
        console.print("[bold cyan]TÌM KIẾM DỮ LIỆU[/bold cyan]")
        keyword = Prompt.ask("Nhập từ khóa (nội dung hoặc danh mục)").lower()
        
        # List comprehension kết hợp tìm kiếm chuỗi
        result = [
            t for t in self.transactions 
            if keyword in t.desc.lower() or keyword in t.category.lower()
        ]
        
        if result:
            console.print(f"[green]🔍 Tìm thấy {len(result)} kết quả:[/green]")
            self.view_transactions(result)
        else:
            console.print("[yellow]Không tìm thấy kết quả nào![/yellow]")

    def show_report(self):
        """Báo cáo thống kê chi tiết theo danh mục"""
        if not self.transactions:
            console.print("[yellow]Chưa có dữ liệu để thống kê![/yellow]")
            return

        total_income = sum(t.amount for t in self.transactions if t.type == "Thu")
        total_expense = sum(t.amount for t in self.transactions if t.type == "Chi")
        balance = total_income - total_expense

        # 1. Bảng Tổng quan
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        
        grid.add_row(
            Panel(f"[green]{total_income:,.0f} đ[/green]", title="Tổng Thu", style="bold"),
            Panel(f"[red]{total_expense:,.0f} đ[/red]", title="Tổng Chi", style="bold"),
            Panel(f"[yellow]{balance:,.0f} đ[/yellow]", title="Số Dư", style="bold")
        )
        console.print(grid)

        category_stats = {}
        for t in self.transactions:
            if t.type == "Chi":
                category_stats[t.category] = category_stats.get(t.category, 0) + t.amount

        # Sắp xếp giảm dần theo số tiền chi
        sorted_stats = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)

        stats_table = Table(title=" PHÂN TÍCH CHI TIÊU", box=box.SIMPLE)
        stats_table.add_column("Danh mục", style="cyan")
        stats_table.add_column("Số tiền", justify="right", style="red")
        stats_table.add_column("Tỷ lệ", justify="right", style="yellow")

        for cat, amt in sorted_stats:
            percent = (amt / total_expense * 100) if total_expense > 0 else 0
            stats_table.add_row(
                cat, 
                f"{amt:,.0f} đ", 
                f"{percent:.1f}%"
            )

        console.print(stats_table)

    def run(self):
        while True:
            console.clear() # Xóa màn hình cho sạch mỗi lần lặp menu
            
            # Header đẹp
            console.print(Panel(
                Text("QUẢN LÝ TÀI CHÍNH CÁ NHÂN", justify="center", style="bold white on blue"),
                style="blue"
            ))

            menu = """
[bold cyan][1][/bold cyan] Thêm giao dịch      [bold cyan][4][/bold cyan] Xóa giao dịch
[bold cyan][2][/bold cyan] Xem danh sách       [bold cyan][5][/bold cyan] Tìm kiếm
[bold cyan][3][/bold cyan] Sửa giao dịch       [bold cyan][6][/bold cyan] Báo cáo Thống kê
[bold cyan][0][/bold cyan] Thoát chương trình
            """
            console.print(Panel(menu, title="CHỨC NĂNG", border_style="green"))

            choice = Prompt.ask("Chọn chức năng", choices=["0", "1", "2", "3", "4", "5", "6"])

            if choice == "0":
                console.print("[bold blue]Hẹn gặp lại![/bold blue]")
                break
            elif choice == "1": self.add_transaction()
            elif choice == "2": self.view_transactions()
            elif choice == "3": self.update_transaction()
            elif choice == "4": self.delete_transaction()
            elif choice == "5": self.search_transaction()
            elif choice == "6": self.show_report()
            
            Prompt.ask("\n[dim]Ấn Enter để quay lại menu...[/dim]", show_default=False)

if __name__ == "__main__":
    app = FinanceApp()
    app.run()
