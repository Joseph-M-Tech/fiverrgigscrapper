import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re
import webbrowser
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from advanced_fiverr_scraper import AdvancedFiverrScraper

class FiverrScraperUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Fiverr Gig Scraper Pro")
        self.root.geometry("1400x800")
        self.root.configure(bg='#f0f0f0')
        
        self.scraper = None
        self.scraping_thread = None
        self.scraping_queue = queue.Queue()
        self.is_scraping = False
        self.gigs_data = []
        self.current_df = None
        
        self.setup_styles()
        self.create_widgets()
        self.check_queue()
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
    def create_widgets(self):
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(title_frame, text="🎯 Fiverr Gig Scraper Pro", font=('Arial', 16, 'bold')).pack()
        ttk.Label(title_frame, text="Extract detailed gig information with advanced filters").pack()
        
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.create_search_tab()
        self.create_filters_tab()
        self.create_results_tab()
        self.create_analytics_tab()
        
        self.status_bar = ttk.Label(main_container, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, pady=(10, 0))
        
        self.progress = ttk.Progressbar(main_container, mode='indeterminate')
        
    def create_search_tab(self):
        search_tab = ttk.Frame(self.notebook)
        self.notebook.add(search_tab, text='🔍 Search')
        
        left_panel = ttk.Frame(search_tab)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        ttk.Label(left_panel, text="Keywords (comma-separated):", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        self.keywords_entry = tk.Text(left_panel, height=3, width=40, font=('Arial', 10))
        self.keywords_entry.pack(fill=tk.X, pady=(0, 15))
        self.keywords_entry.insert('1.0', 'website design, logo, wordpress')
        
        ttk.Label(left_panel, text="Category:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        self.category_var = tk.StringVar()
        categories = ["Graphics & Design", "Digital Marketing", "Writing & Translation",
                     "Video & Animation", "Music & Audio", "Programming & Tech",
                     "Business", "Lifestyle", "Custom Websites"]
        self.category_combo = ttk.Combobox(left_panel, textvariable=self.category_var, 
                                          values=categories, state='readonly', font=('Arial', 10))
        self.category_combo.pack(fill=tk.X, pady=(0, 15))
        self.category_combo.set("Custom Websites")
        
        ttk.Label(left_panel, text="Max Pages to Scrape:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        pages_frame = ttk.Frame(left_panel)
        pages_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.pages_var = tk.IntVar(value=3)
        ttk.Scale(pages_frame, from_=1, to=20, variable=self.pages_var, orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.pages_label = ttk.Label(pages_frame, text="3")
        self.pages_label.pack(side=tk.RIGHT)
        self.pages_var.trace('w', lambda *args: self.pages_label.config(text=str(self.pages_var.get())))
        
        button_frame = ttk.Frame(left_panel)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="🚀 Start Scraping", command=self.start_scraping).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="⏹️ Stop", command=self.stop_scraping).pack(side=tk.LEFT)
        
        right_panel = ttk.Frame(search_tab)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(right_panel, text="Scraping Log:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        self.log_text = scrolledtext.ScrolledText(right_panel, width=60, height=25, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log("Application started. Ready to scrape.")
        
    def create_filters_tab(self):
        filters_tab = ttk.Frame(self.notebook)
        self.notebook.add(filters_tab, text='⚙️ Filters')
        
        canvas = tk.Canvas(filters_tab, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(filters_tab, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        price_frame = ttk.LabelFrame(scrollable_frame, text="💰 Price Filter", padding=10)
        price_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(price_frame, text="Min Price ($):").grid(row=0, column=0, padx=(0, 10))
        self.min_price_var = tk.DoubleVar(value=0)
        ttk.Entry(price_frame, textvariable=self.min_price_var, width=10).grid(row=0, column=1, padx=(0, 20))
        
        ttk.Label(price_frame, text="Max Price ($):").grid(row=0, column=2, padx=(0, 10))
        self.max_price_var = tk.DoubleVar(value=1000)
        ttk.Entry(price_frame, textvariable=self.max_price_var, width=10).grid(row=0, column=3)
        
        rating_frame = ttk.LabelFrame(scrollable_frame, text="⭐ Rating Filter", padding=10)
        rating_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(rating_frame, text="Min Rating:").grid(row=0, column=0, padx=(0, 10))
        self.min_rating_var = tk.DoubleVar(value=4.0)
        ttk.Scale(rating_frame, from_=0, to=5, variable=self.min_rating_var, orient=tk.HORIZONTAL).grid(row=0, column=1, padx=(0, 10))
        self.rating_label = ttk.Label(rating_frame, text="4.0")
        self.rating_label.grid(row=0, column=2)
        self.min_rating_var.trace('w', lambda *args: self.rating_label.config(text=f"{self.min_rating_var.get():.1f}"))
        
        delivery_frame = ttk.LabelFrame(scrollable_frame, text="⏱️ Delivery Time", padding=10)
        delivery_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.delivery_var = tk.StringVar(value="any")
        deliveries = [("Any", "any"), ("24 Hours", "1"), ("3 Days", "3"), 
                     ("7 Days", "7"), ("14 Days", "14"), ("30 Days", "30")]
        
        for i, (text, value) in enumerate(deliveries):
            ttk.Radiobutton(delivery_frame, text=text, variable=self.delivery_var, value=value).grid(
                row=i//3, column=i%3, padx=10, pady=5, sticky=tk.W)
        
        seller_frame = ttk.LabelFrame(scrollable_frame, text="👤 Seller Filters", padding=10)
        seller_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.online_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(seller_frame, text="Online Sellers Only", variable=self.online_only_var).pack(anchor=tk.W)
        
        self.top_rated_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(seller_frame, text="Top Rated Sellers Only", variable=self.top_rated_var).pack(anchor=tk.W)
        
    def create_results_tab(self):
        results_tab = ttk.Frame(self.notebook)
        self.notebook.add(results_tab, text='📋 Results')
        
        button_frame = ttk.Frame(results_tab)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="📥 Export to CSV", command=self.export_csv).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="📊 Export to Excel", command=self.export_excel).pack(side=tk.LEFT)
        
        self.results_label = ttk.Label(button_frame, text="Total Gigs: 0")
        self.results_label.pack(side=tk.RIGHT)
        
        columns = ('Title', 'Freelancer', 'Rating', 'Price', 'Delivery', 'Jobs', 'Level', 'Status')
        self.tree = ttk.Treeview(results_tab, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(results_tab, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 0), pady=(0, 20))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 20), pady=(0, 20))
        
        self.tree.bind('<Double-1>', self.open_selected_url)
        
    def create_analytics_tab(self):
        analytics_tab = ttk.Frame(self.notebook)
        self.notebook.add(analytics_tab, text='📈 Analytics')
        
        self.charts_frame = ttk.Frame(analytics_tab)
        self.charts_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(self.charts_frame, text="Charts will appear here after scraping", font=('Arial', 12)).pack(expand=True)
        
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_status(self, message):
        self.status_bar.config(text=message)
        
    def start_scraping(self):
        if self.is_scraping:
            messagebox.showwarning("Warning", "Scraping already in progress!")
            return
        
        keywords_text = self.keywords_entry.get('1.0', tk.END).strip()
        keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
        
        if not keywords:
            messagebox.showwarning("Warning", "Please enter at least one keyword!")
            return
        
        category = self.category_var.get()
        max_pages = self.pages_var.get()
        sort_by = "relevant"
        
        min_price = self.min_price_var.get() if self.min_price_var.get() > 0 else None
        max_price = self.max_price_var.get() if self.max_price_var.get() < 1000 else None
        min_rating = self.min_rating_var.get() if self.min_rating_var.get() > 0 else None
        delivery_time = self.delivery_var.get() if self.delivery_var.get() != "any" else None
        online_only = self.online_only_var.get()
        top_rated_seller = self.top_rated_var.get()
        
        try:
            self.scraper = AdvancedFiverrScraper(headless=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize scraper: {e}")
            return
        
        self.is_scraping = True
        self.progress.pack(fill=tk.X, pady=(10, 0))
        self.progress.start()
        
        self.scraping_thread = threading.Thread(
            target=self._scrape_worker,
            args=(keywords, category, min_price, max_price, min_rating,
                  max_pages, sort_by, delivery_time, online_only, top_rated_seller),
            daemon=True
        )
        self.scraping_thread.start()
        
        self.log(f"Started scraping: {keywords} in {category}")
        self.update_status(f"Scraping {keywords}...")
        
    def _scrape_worker(self, keywords, category, min_price, max_price, min_rating,
                      max_pages, sort_by, delivery_time, online_only, top_rated_seller):
        try:
            gigs_data = self.scraper.search_gigs_advanced(
                keywords=keywords,
                category=category,
                min_price=min_price,
                max_price=max_price,
                min_rating=min_rating,
                max_pages=max_pages,
                sort_by=sort_by,
                delivery_time=delivery_time,
                online_only=online_only,
                top_rated_seller=top_rated_seller
            )
            
            for gig in gigs_data:
                gig.category = category
            
            self.scraping_queue.put(('success', gigs_data))
            
        except Exception as e:
            self.scraping_queue.put(('error', str(e)))
        finally:
            self.scraping_queue.put(('finished', None))
            
    def check_queue(self):
        try:
            while True:
                msg_type, data = self.scraping_queue.get_nowait()
                
                if msg_type == 'success':
                    self.gigs_data = data
                    self.display_results(data)
                    self.update_analytics(data)
                    self.log(f"Scraping completed! Found {len(data)} gigs.")
                    
                elif msg_type == 'error':
                    messagebox.showerror("Error", f"Scraping failed: {data}")
                    self.log(f"Error: {data}")
                    
                elif msg_type == 'finished':
                    self.is_scraping = False
                    self.progress.stop()
                    self.progress.pack_forget()
                    self.update_status("Ready")
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_queue)
        
    def display_results(self, gigs_data):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for gig in gigs_data:
            self.tree.insert('', tk.END, values=(
                gig.title[:50] + '...' if len(gig.title) > 50 else gig.title,
                gig.freelancer,
                f"{gig.rating:.1f} ⭐" if gig.rating > 0 else "N/A",
                gig.price,
                gig.delivery_time,
                f"{gig.completed_jobs:,}" if gig.completed_jobs > 0 else "N/A",
                gig.level,
                "🟢" if gig.online_status else "⚫"
            ))
        
        self.results_label.config(text=f"Total Gigs: {len(gigs_data)}")
        
        data = []
        for gig in gigs_data:
            data.append({
                'Title': gig.title,
                'URL': gig.url,
                'Freelancer': gig.freelancer,
                'Rating': gig.rating,
                'Reviews': gig.reviews,
                'Price': gig.price,
                'Delivery_Time': gig.delivery_time,
                'Completed_Jobs': gig.completed_jobs,
                'Category': gig.category,
                'Description': gig.description,
                'Tags': ', '.join(gig.tags),
                'Seller_Level': gig.level,
                'Online_Status': 'Online' if gig.online_status else 'Offline',
                'Response_Time': gig.response_time
            })
        
        self.current_df = pd.DataFrame(data)
        
    def update_analytics(self, gigs_data):
        if not gigs_data:
            return
        
        for widget in self.charts_frame.winfo_children():
            widget.destroy()
        
        try:
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            fig.suptitle('Fiverr Gigs Analytics', fontsize=16, fontweight='bold')
            
            ratings = [g.rating for g in gigs_data if g.rating > 0]
            prices = []
            for gig in gigs_data:
                try:
                    price_str = gig.price.replace('$', '').replace(',', '').strip()
                    if 'k' in price_str.lower():
                        price_val = float(price_str.lower().replace('k', '')) * 1000
                    else:
                        price_val = float(re.search(r'\d+\.?\d*', price_str).group())
                    prices.append(price_val)
                except:
                    continue
            
            completed_jobs = [g.completed_jobs for g in gigs_data if g.completed_jobs > 0]
            levels = [g.level for g in gigs_data]
            
            if ratings:
                axes[0, 0].hist(ratings, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
                axes[0, 0].set_xlabel('Rating')
                axes[0, 0].set_ylabel('Frequency')
                axes[0, 0].set_title('Rating Distribution')
                axes[0, 0].grid(True, alpha=0.3)
            
            if prices:
                axes[0, 1].hist(prices, bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
                axes[0, 1].set_xlabel('Price ($)')
                axes[0, 1].set_ylabel('Frequency')
                axes[0, 1].set_title('Price Distribution')
                axes[0, 1].grid(True, alpha=0.3)
            
            if completed_jobs:
                axes[1, 0].hist(completed_jobs, bins=20, alpha=0.7, color='salmon', edgecolor='black', log=True)
                axes[1, 0].set_xlabel('Completed Jobs')
                axes[1, 0].set_ylabel('Frequency (log)')
                axes[1, 0].set_title('Completed Jobs Distribution')
                axes[1, 0].grid(True, alpha=0.3)
            
            if levels:
                level_counts = pd.Series(levels).value_counts()
                axes[1, 1].pie(level_counts.values, labels=level_counts.index, autopct='%1.1f%%',
                              startangle=90, colors=plt.cm.Set3.colors)
                axes[1, 1].set_title('Seller Levels Distribution')
            
            plt.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=self.charts_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            self.log(f"Error creating charts: {e}")
            
    def stop_scraping(self):
        if not self.is_scraping:
            messagebox.showinfo("Info", "No scraping in progress.")
            return
        
        self.is_scraping = False
        if self.scraper:
            self.scraper.close()
        
        self.log("Scraping stopped by user")
        self.update_status("Stopped")
        self.progress.stop()
        self.progress.pack_forget()
        
    def export_csv(self):
        if self.current_df is None or self.current_df.empty:
            messagebox.showwarning("Warning", "No data to export!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"fiverr_gigs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if filename:
            try:
                self.current_df.to_csv(filename, index=False, encoding='utf-8')
                messagebox.showinfo("Success", f"Data exported to {filename}")
                self.log(f"Data exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")
                
    def export_excel(self):
        if self.current_df is None or self.current_df.empty:
            messagebox.showwarning("Warning", "No data to export!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"fiverr_gigs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        
        if filename:
            try:
                self.current_df.to_excel(filename, index=False)
                messagebox.showinfo("Success", f"Data exported to {filename}")
                self.log(f"Data exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")
                
    def open_selected_url(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        values = item['values']
        
        title_to_find = values[0]
        for gig in self.gigs_data:
            if gig.title.startswith(title_to_find.replace('...', '').strip()):
                if gig.url and gig.url != "N/A":
                    webbrowser.open(gig.url)
                else:
                    messagebox.showwarning("Warning", "No URL available for this gig")
                break
    
    def on_closing(self):
        if self.is_scraping:
            if messagebox.askyesno("Quit", "Scraping in progress. Are you sure you want to quit?"):
                self.stop_scraping()
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = FiverrScraperUI(root)
    
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()