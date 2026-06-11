import tkinter as tk
from tkinter import ttk
import requests
import pandas as pd
import re
from datetime import datetime

year = datetime.now().strftime("%Y")
df = pd.DataFrame()
df_filter = pd.DataFrame()  # 用來儲存過濾後的資料

# 抓取資料的函數
def kfc():
    global df, df_filter
    df = pd.DataFrame()  # 每次抓取資料時清空舊的DataFrame
    for i in range(1, 4): 
        url = f'https://info.talk.tw/kfc{year}coupon/{i}/'
        resp = requests.get(url)

        # 正則表達式提取所需的資料
        links = re.findall(r'至(.*?)止.*?has-palette-color-1-color">(.*?)</mark>.*?優惠內容：.*?(.*?)\<br>', resp.text)
        links2 = []
        for date, code, text in links:
            # 統一等號
            text = text.replace('＝', '=')
        
            # 拆內容與價格
            content, price = text.split('=', 1)
        
            # 抽出數字價錢
            m = re.search(r'\d+', price)
            price_number = m.group(0) if m else ''
            links2.append((
                date,
                code,
                content,
                price_number
            ))
        df2 = pd.DataFrame()
        try:
            tables = pd.read_html(resp.text)
            dfs = []

            for tdf in tables:
                # 清理欄位名稱
                tdf = tdf.drop(columns=["說明"], errors="ignore")
                tdf.columns = tdf.columns.astype(str).str.strip()    

                # 判斷是否含「優惠代碼」欄位
                if any("優惠代碼" in col for col in tdf.columns):
                    tdf.columns = ["優惠代碼", "優惠內容", "優惠價", "1"]
                    dfs.append(tdf)
                    
                if tdf.shape[1] == 3 and tdf.columns[0] != "品項":
                    tdf.insert(0, "優惠代碼", "")
                    tdf.columns = ["優惠代碼", "優惠內容", "優惠價", "1"]
                    dfs.append(tdf)
            
            # 合併
            if dfs:
                df2 = pd.concat(dfs, ignore_index=True)
            else:
                df2 = pd.DataFrame()

            df2 = df2.iloc[:, :3]
            df2.columns = ["優惠代碼", "優惠內容", "優惠價"]
            df2["有效日期"] = ""
            df2 = df2[["優惠代碼", "優惠內容", "優惠價", "有效日期"]]
        except:
            print(i)
        
        # 轉換為DataFrame
        dfc = pd.DataFrame(links2, columns=['有效日期', '優惠代碼', '優惠內容', '優惠價'])
        dfc = dfc[['優惠代碼', '優惠內容', '優惠價', '有效日期']]
        df = pd.concat([df, dfc, df2], ignore_index=True)
        
    # 處理優惠價，提取數字部分並進行排序
    #df['優惠價'] = df['優惠價'].str.extract(r'(\d+)').astype(float)  # 提取數字並轉換為浮點數
    df['優惠價'] = (df['優惠價'].astype(str).str.replace(',', '', regex=False).str.extract(r'(\d+)').astype(float))
    df = df.sort_values(by='優惠價', ascending=True)  # 根據優惠價進行升冪排序，若需降冪，改為 False
    
    # 把 "元" 字串加回優惠價欄位
    df['優惠價'] = df['優惠價'].apply(lambda x: f'{x:.0f}元')  # 把數字格式化為「x元」
    df = df.drop_duplicates()
    df_filter = df.copy()  # 初始化篩選後的資料為完整資料

    # 更新表格顯示
    update_table()

# 更新UI中的表格
def update_table():
    # 清空舊的表格資料
    for row in table.get_children():
        table.delete(row)
    
    # 顯示最新的 df_filter 資料
    for _, row in df_filter.iterrows():
        table.insert('', 'end', values=row.tolist())

# 篩選按鈕的回調函數
def filter_data():
    global df_filter  # 更新篩選後的資料
    keywords = filter_entry.get().split()  # 根據空格分開關鍵字

    # 篩選功能
    if keywords:
        df_filter = df  # 保證篩選基於原始 df
        for keyword in keywords:
            df_filter = df_filter[df_filter['優惠內容'].str.contains(keyword, na=False)]
    else:
        df_filter = df.copy()  # 如果輸入為空，則顯示完整資料
    
    update_table()  # 更新表格顯示篩選後的結果

root = tk.Tk()
root.title("KFC 優惠資訊")
root.geometry("800x600")
FONT = ("微軟正黑體", 12)

# 框架容納篩選欄位和按鈕
frame = tk.Frame(root)
frame.pack(pady=20)

filter_entry = tk.Entry(frame, font=FONT, width=30)
filter_entry.pack(side=tk.LEFT, padx=5)
filter_entry.bind("<KeyRelease>", lambda event: filter_data())  # 偵測輸入

# Treeview 框架，方便滑動條管理
table_frame = tk.Frame(root)
table_frame.pack(pady=20, fill=tk.BOTH, expand=True)

# 定義欄位
columns = ['優惠代碼', '優惠內容', '優惠價', '有效日期']
table = ttk.Treeview(table_frame, columns=columns, show="headings")

# 設置欄位標題
for col in columns:
    table.heading(col, text=col)

# 設置每個欄位的寬度
table.column('優惠代碼', width=90, anchor='center')
table.column('優惠內容', width=450, anchor='w')
table.column('優惠價', width=70, anchor='center')
table.column('有效日期', width=120, anchor='center')

# 垂直滑動條
vsb = tk.Scrollbar(table_frame, orient="vertical", command=table.yview)
table.configure(yscrollcommand=vsb.set)
vsb.pack(side='right', fill='y')

# 水平滑動條（可選）
hsb = tk.Scrollbar(table_frame, orient="horizontal", command=table.xview)
table.configure(xscrollcommand=hsb.set)
hsb.pack(side='bottom', fill='x')

# 顯示 Treeview
table.pack(side='left', fill='both', expand=True)

# 啟動資料抓取函數
kfc()

root.mainloop()
