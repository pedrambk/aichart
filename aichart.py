
import ccxt
import pandas as pd
import matplotlib.pyplot as plt
from mplfinance.original_flavor import candlestick_ohlc
import matplotlib.dates as mdates
import openai

# کلید API OpenAI خود را وارد کنید
openai.api_key = 'XXXXXXXXXXX'  # کلید API خود را اینجا وارد کنید

# انتخاب صرافی و جفت ارز
exchange = ccxt.binance()  # می‌توانید صرافی دیگری انتخاب کنید
symbol = 'BTC/USDT'
timeframe = '1d'  # تایم‌فریم کندل‌ها

# دریافت داده‌های تاریخی
since = exchange.parse8601('2024-10-01T00:00:00Z')  # زمان شروع داده‌ها
candles = exchange.fetch_ohlcv(symbol, timeframe, since)

# تبدیل داده‌ها به یک DataFrame برای پردازش آسان‌تر
columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
df = pd.DataFrame(candles, columns=columns)
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df['timestamp_num'] = df['timestamp'].apply(mdates.date2num)  # تبدیل به فرمت عددی برای رسم کندل‌ها

# آماده‌سازی داده‌ها برای نمودار کندل شمعی
ohlc = df[['timestamp_num', 'open', 'high', 'low', 'close']].copy()

# لیست برای ذخیره نقاط انتخاب شده
selected_points = []
highlight_patch = None  # برای ذخیره پچ‌های رنگی

# تابع برای ثبت نقاط و انجام عمل ذخیره‌سازی داده‌ها پس از انتخاب دو نقطه
def onclick(event):
    global highlight_patch
    # ثبت نقاط کلیک شده
    if len(selected_points) < 2:
        selected_points.append(event.xdata)
        print(f"Selected point: {event.xdata}")

        # نمایش نقطه‌ها روی نمودار
        ax.plot(event.xdata, event.ydata, 'ro')  # نقطه‌ها با رنگ قرمز

    # زمانی که دو نقطه انتخاب شدند، داده‌ها را ذخیره می‌کنیم
    if len(selected_points) == 2:
        xmin, xmax = min(selected_points), max(selected_points)
        selected_df = df[(df['timestamp_num'] >= xmin) & (df['timestamp_num'] <= xmax)]
        
        # نمایش تعداد کندل‌های انتخاب شده
        print(f"Selected candles count: {len(selected_df)}")
        
        # ذخیره داده‌ها در فایل
        selected_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].to_csv('selected_candles.txt', index=False)
        print(f"Selected candles saved to 'selected_candles.txt':\n{selected_df}")

        # رنگ‌آمیزی ناحیه انتخاب شده
        if highlight_patch:
            highlight_patch.remove()  # حذف پچ قبلی (در صورت وجود)

        # ایجاد مستطیل رنگی روی ناحیه انتخاب شده
        highlight_patch = ax.axvspan(xmin, xmax, color='red', alpha=0.2)  # رنگ قرمز کمرنگ

        # بازنشانی نقاط برای انتخاب جدید
        selected_points.clear()

    # نمایش مجدد نمودار
    plt.draw()

    # وقتی دو نقطه انتخاب شده، سوال از کاربر برای ارسال به تحلیل
    if len(selected_points) == 0:
        print("\nSelection complete. The data has been saved to 'selected_candles.txt'.")
        user_input = input("Do you want to analyze the selected data? (yes/no): ").strip().lower()
        if user_input == 'yes':
            # خواندن داده‌ها
            data = read_selected_data()
            
            if data:
                print("Sending data to GPT for analysis...\n")
                analysis = analyze_with_gpt(data)
                print("\nGPT Analysis Result:")
                print(analysis)
            else:
                print("No data found to analyze.")
        else:
            print("No analysis requested.")

# تابع برای ارسال داده‌ها به GPT و دریافت پاسخ
def analyze_with_gpt(data):
    prompt = f"""
شما یک کارشناس مالی هستید. داده‌های بازار ارزهای دیجیتال زیر را تحلیل کنید و نکات قابل توجه را ارائه دهید. داده‌ها شامل قیمت‌های باز، بسته، بالاترین، پایین‌ترین و حجم معاملات برای هر روز هستند:

{data}

آیا میتونی نمودار RSI رو در تایم روزانه بررسی کنی و بهم بگی چه وضعیتی داریم .
آیا بر مبنای الگو های کندل استیک پیش بینی برای انتهاب یک پزیشن منطقی داری؟ و اگر داری سک پزیشن دقیق رو برام مشخص کن.
آیا میتونی در تایم یک ساعته هم چارت قیمتی بیتکوین رو بررسی کنی؟

    """

    try:
        # ارسال پرامپت به مدل GPT-4
        response = openai.ChatCompletion.create(
            model="gpt-4",  # یا gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "You are a financial expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()

    except Exception as e:
        return f"Error: {str(e)}"

# خواندن داده‌های انتخابی از فایل
def read_selected_data():
    # داده‌ها را از فایل `selected_candles.txt` می‌خوانیم
    try:
        df = pd.read_csv('selected_candles.txt')
        # نمایش داده‌های انتخابی
        data = df.to_string(index=False)
        return data
    except FileNotFoundError:
        print("The file 'selected_candles.txt' was not found.")
        return None

# اصلی‌ترین برنامه که انتخاب محدوده و تحلیل را مدیریت می‌کند
def main():
    # رسم چارت
    global ax
    fig, ax = plt.subplots(figsize=(12, 6))
    candlestick_ohlc(ax, ohlc.values, width=0.6, colorup='green', colordown='red')
    ax.xaxis_date()  # تنظیم محور x برای نمایش تاریخ
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

    # افزودن تعامل کلیک
    fig.canvas.mpl_connect('button_press_event', onclick)

    plt.title(f'{symbol} Candlestick Chart')
    plt.xlabel('Date')
    plt.ylabel('Price (USDT)')
    plt.grid()
    plt.show()

if __name__ == "__main__":
    main()

