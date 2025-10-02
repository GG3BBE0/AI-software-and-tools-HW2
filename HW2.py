import tkinter as tk
from tkinter import messagebox, font
import yfinance as yf
import threading
import time

# --- 全域變數 ---
# 用於儲存當前查詢的股票物件
current_ticker = None
# 用於控制價格更新線程的開關
is_running = False


# --- 核心功能 ---

def fetch_stock_data():
    """
    根據輸入框中的股票代號獲取股票數據並更新UI。
    """
    global current_ticker, is_running

    # 停止之前的自動更新
    if is_running:
        is_running = False
        time.sleep(1.1)  # 等待舊線程結束

    ticker_symbol = entry_ticker.get().upper()
    if not ticker_symbol:
        messagebox.showwarning("輸入錯誤", "請輸入股票代號")
        return

    try:
        # 顯示正在加載
        price_status_label.config(text=f"正在查詢 {ticker_symbol}...")
        timestamp_label.config(text="")
        app.update_idletasks()  # 強制更新UI

        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        # 檢查是否為有效的股票數據 (只要有公司名稱就視為有效)
        if not info or info.get('longName') is None:
            raise ValueError("找不到該股票代號或數據不完整")

        current_ticker = ticker
        update_ui_with_data(info)

        # 成功獲取數據後，啟動即時更新
        is_running = True
        thread = threading.Thread(target=live_update_price, daemon=True)
        thread.start()

    except Exception as e:
        clear_labels()
        messagebox.showerror("查詢失敗",
                             f"無法獲取 {ticker_symbol} 的數據。\n請檢查股票代號是否正確，或稍後再試。\n錯誤: {e}")
        current_ticker = None


def update_ui_with_data(info):
    """
    將獲取到的股票資訊更新到UI介面上。
    """
    # --- 核心邏輯：決定要顯示哪個價格 ---
    price_status = ""
    market_price = 'N/A'

    # 優先順序: 盤中價 > 盤後價 > 盤前價 > 昨日收盤價
    if info.get('regularMarketPrice') is not None:
        market_price = info.get('regularMarketPrice')
        price_status = "(盤中)"
    elif info.get('postMarketPrice') is not None:
        market_price = info.get('postMarketPrice')
        price_status = "(盤後)"
    elif info.get('preMarketPrice') is not None:
        market_price = info.get('preMarketPrice')
        price_status = "(盤前)"
    elif info.get('regularMarketPreviousClose') is not None:
        market_price = info.get('regularMarketPreviousClose')
        price_status = "(昨收)"

    # --- 從 info 字典中安全地獲取數據 ---
    long_name = info.get('longName', 'N/A')
    prev_close = info.get('regularMarketPreviousClose', 1)  # 漲跌幅計算基準不變
    day_high = info.get('regularMarketDayHigh', 'N/A')
    day_low = info.get('regularMarketDayLow', 'N/A')
    volume = info.get('regularMarketVolume', 'N/A')

    # 計算漲跌幅 (基準為昨日收盤價)
    change = 0
    change_percent = 0
    if isinstance(market_price, (int, float)) and isinstance(prev_close, (int, float)):
        change = market_price - prev_close
        change_percent = (change / prev_close) * 100

    # 格式化顯示
    price_str = f"{market_price:.2f}" if isinstance(market_price, float) else "N/A"
    volume_str = f"{volume:,}" if isinstance(volume, int) else "N/A"

    # 判斷漲跌顏色
    if change >= 0:
        price_color = "red"
        change_str = f"▲ {change:.2f} ({change_percent:+.2f}%)"
    else:
        price_color = "green"
        change_str = f"▼ {change:.2f} ({change_percent:+.2f}%)"

    # 更新UI標籤
    name_label.config(text=f"{long_name} ({info.get('symbol', 'N/A')})")
    price_label.config(text=price_str, fg=price_color)
    change_label.config(text=change_str, fg=price_color)
    high_label.config(text=f"最高: {day_high:.2f}" if isinstance(day_high, float) else "最高: N/A")
    low_label.config(text=f"最低: {day_low:.2f}" if isinstance(day_low, float) else "最低: N/A")
    volume_label.config(text=f"成交量: {volume_str}")
    price_status_label.config(text=f"價格類型: {price_status}")
    timestamp_label.config(text=f"上次更新: {time.strftime('%H:%M:%S')}")


def live_update_price():
    """
    在背景線程中定時更新股價，使用完整的數據獲取邏輯以確保一致性。
    """
    global is_running
    while is_running:
        # 將更新間隔放在迴圈開頭，避免因網路延遲導致更新時間不準
        time.sleep(1)
        if not is_running:  # 在睡眠後再次檢查，確保在等待時沒有被停止
            break

        try:
            if current_ticker:
                # **重要修改**: 重新獲取完整的 info 字典，確保數據來源和初始查詢一致
                info = current_ticker.info

                # **重要修改**: 直接呼叫主更新函式，重複使用相同的顯示邏輯
                update_ui_with_data(info)

        except Exception as e:
            print(f"背景更新失敗: {e}")  # 在控制台打印錯誤，不打擾用戶
            price_status_label.config(text="背景更新失敗")


def clear_labels():
    """
    清空所有顯示數據的標籤。
    """
    name_label.config(text="公司名稱 (代號)")
    price_label.config(text="0.00", fg="black")
    change_label.config(text="▲ 0.00 (+0.00%)", fg="black")
    high_label.config(text="最高: N/A")
    low_label.config(text="最低: N/A")
    volume_label.config(text="成交量: N/A")
    price_status_label.config(text="請輸入股票代號開始查詢")
    timestamp_label.config(text="")


# --- GUI 設定 ---
app = tk.Tk()
app.title("美股即時看盤 App")
app.geometry("450x450")
app.configure(bg="#f0f0f0")

# --- 字體設定 ---
title_font = font.Font(family="Helvetica", size=16, weight="bold")
price_font = font.Font(family="Arial", size=48, weight="bold")
change_font = font.Font(family="Arial", size=18)
info_font = font.Font(family="Helvetica", size=12)

# --- UI 框架 ---
main_frame = tk.Frame(app, padx=20, pady=20, bg="#f0f0f0")
main_frame.pack(expand=True, fill="both")

# --- UI 元件 ---

# 頂部查詢區域
top_frame = tk.Frame(main_frame, bg="#f0f0f0")
top_frame.pack(fill="x", pady=(0, 20))

tk.Label(top_frame, text="輸入美股代號:", font=info_font, bg="#f0f0f0").pack(side="left", padx=(0, 10))
entry_ticker = tk.Entry(top_frame, font=info_font, width=15)
entry_ticker.pack(side="left", expand=True, fill="x")
entry_ticker.bind("<Return>", lambda event: fetch_stock_data())  # 綁定Enter鍵

search_button = tk.Button(top_frame, text="查詢", command=fetch_stock_data, font=info_font)
search_button.pack(side="left", padx=(10, 0))

# 股票資訊顯示區域
info_frame = tk.Frame(main_frame, bg="white", padx=15, pady=15, relief="sunken", borderwidth=1)
info_frame.pack(fill="both", expand=True)

name_label = tk.Label(info_frame, text="公司名稱 (代號)", font=title_font, bg="white", wraplength=350, justify="center")
name_label.pack(pady=(0, 10))

price_label = tk.Label(info_frame, text="0.00", font=price_font, bg="white")
price_label.pack(pady=(5, 0))

change_label = tk.Label(info_frame, text="▲ 0.00 (+0.00%)", font=change_font, bg="white")
change_label.pack()

details_frame = tk.Frame(info_frame, bg="white")
details_frame.pack(pady=20)

high_label = tk.Label(details_frame, text="最高: N/A", font=info_font, bg="white")
high_label.grid(row=0, column=0, padx=10)

low_label = tk.Label(details_frame, text="最低: N/A", font=info_font, bg="white")
low_label.grid(row=0, column=1, padx=10)

volume_label = tk.Label(info_frame, text="成交量: N/A", font=info_font, bg="white")
volume_label.pack(pady=(10, 0))

# 狀態欄
status_frame = tk.Frame(app, bd=1, relief="sunken")
status_frame.pack(side="bottom", fill="x")

price_status_label = tk.Label(status_frame, text="請輸入股票代號開始查詢", anchor="w", padx=5)
price_status_label.pack(side="left")

timestamp_label = tk.Label(status_frame, text="", anchor="e", padx=5)
timestamp_label.pack(side="right")

app.mainloop()

