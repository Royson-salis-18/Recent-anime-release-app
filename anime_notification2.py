import asyncio
import aiohttp
import requests
import re
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from io import BytesIO
import threading
import subprocess
from urllib.parse import quote
import time
from bs4 import BeautifulSoup
COLORS = {
    'bg': "#1A1B26",
    'card_bg': "#1F2937",
    'accent': "#88CCCA",
    'text': "#E5E7EB",
    'text_secondary': "#9CA3AF"
}

PADDING = {
    'small': 5,
    'medium': 10,
    'large': 15
}

class PosterFetcher:
    def __init__(self):
        self.cache = {}

    def clean_title(self, title):
        cleaners = [
            r'\s*\([^)]*\)',
            r'\s*-\s*Episode\s*\d+.*$',
            r'\s*Season\s*\d+.*$',
            r'\s*Part\s*\d+.*$',
            r'\s*\[[^\]]*\]',
            r'\s*:\s*[^:]*$'
        ]
        
        cleaned = title
        for pattern in cleaners:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()

    async def fetch_kitsu_poster(self, title):
        if title in self.cache:
            return self.cache[title]

        try:
            url = f"https://kitsu.io/api/edge/anime?filter[text]={quote(title)}&page[limit]=1"
            headers = {
                'Accept': 'application/vnd.api+json',
                'Content-Type': 'application/vnd.api+json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data') and len(data['data']) > 0:
                            poster_url = data['data'][0]['attributes']['posterImage'].get('medium')
                            if poster_url:
                                self.cache[title] = poster_url
                                return poster_url
        except Exception as e:
            print(f"Kitsu API error for {title}: {e}")
        return None

    async def get_poster(self, title):
        clean_title = self.clean_title(title)
        return await self.fetch_kitsu_poster(clean_title)

def fetch_recent_anime():
    url = "https://hianime.to/recently-updated"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        anime_list = []
        film_details = soup.find_all('div', class_='film-detail')
        
        for film in film_details:
            try:
                film_name = film.find('h3', class_='film-name')
                if not film_name or not film_name.find('a'):
                    continue
                    
                title_link = film_name.find('a')
                title = title_link.text.strip()
                link = title_link.get('href', '')
                
                fd_infor = film.find('div', class_='fd-infor')
                release_time = "Unknown Time"
                if fd_infor:
                    time_span = fd_infor.find('span', class_='fdi-item')
                    if time_span:
                        release_time = time_span.text.strip()
                
                if title and link:
                    anime_list.append((title, release_time, link))
                
            except Exception as e:
                print(f"Error processing anime item: {e}")
                continue

        return anime_list

    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def open_in_opera(url):
    try:
        base_url = "https://hianime.to"
        full_url = f"{base_url}{url}" if url.startswith('/') else url
        opera_path = r"C:\Users\royso\AppData\Local\Programs\Opera\opera.exe"
        subprocess.run([opera_path, full_url], check=True)
    except Exception as e:
        print(f"Error opening in Opera: {e}")

class AnimeCard(tk.Frame):
    def __init__(self, master, anime_title, release_time, link, poster_fetcher, loop, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(
            bg=COLORS['card_bg'],
            padx=PADDING['medium'],
            pady=PADDING['small'],
            highlightbackground=COLORS['accent'],
            highlightthickness=1
        )
        
        # Container for poster and content
        container = tk.Frame(self, bg=COLORS['card_bg'])
        container.pack(fill=tk.BOTH, expand=True, padx=PADDING['small'], pady=PADDING['small'])
        
        # Poster frame
        poster_frame = tk.Frame(
            container,
            bg=COLORS['card_bg'],
            width=140,
            height=200
        )
        poster_frame.pack_propagate(False)
        poster_frame.pack(side=tk.LEFT, padx=PADDING['small'])
        
        # Poster placeholder
        self.poster_label = tk.Label(
            poster_frame,
            text="Loading...",
            bg=COLORS['card_bg'],
            fg=COLORS['text']
        )
        self.poster_label.pack(fill=tk.BOTH, expand=True)
        
        # Content frame
        content_frame = tk.Frame(container, bg=COLORS['card_bg'])
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=PADDING['medium'])
        
        # Title
        title_label = tk.Label(
            content_frame,
            text=anime_title,
            font=("Segoe UI", 12, "bold"),
            fg=COLORS['text'],
            bg=COLORS['card_bg'],
            wraplength=400,
            justify=tk.LEFT
        )
        title_label.pack(anchor="w", pady=(PADDING['small'], PADDING['small']))
        
        # Release time
        time_label = tk.Label(
            content_frame,
            text=f"Released: {release_time}",
            font=("Segoe UI", 10),
            fg=COLORS['text_secondary'],
            bg=COLORS['card_bg']
        )
        time_label.pack(anchor="w")
        
        # Watch button
        watch_button = tk.Button(
            content_frame,
            text="Watch Now",
            command=lambda: open_in_opera(link),
            bg=COLORS['accent'],
            fg=COLORS['bg'],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=PADDING['medium'],
            pady=PADDING['small'],
            cursor="hand2"
        )
        watch_button.pack(anchor="w", pady=PADDING['medium'])
        
        # Load poster asynchronously
        asyncio.run_coroutine_threadsafe(
            self._load_poster(anime_title, poster_fetcher),
            loop
        )

    async def _load_poster(self, title, poster_fetcher):
        try:
            poster_url = await poster_fetcher.get_poster(title)
            if poster_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(poster_url) as response:
                        if response.status == 200:
                            data = await response.read()
                            img = Image.open(BytesIO(data))
                            
                            # Resize with aspect ratio preservation
                            target_width, target_height = 140, 200
                            img_ratio = img.width / img.height
                            target_ratio = target_width / target_height
                            
                            if img_ratio > target_ratio:
                                resize_width = int(target_height * img_ratio)
                                resize_height = target_height
                                img = img.resize((resize_width, resize_height), Image.Resampling.LANCZOS)
                                left = (resize_width - target_width) // 2
                                img = img.crop((left, 0, left + target_width, target_height))
                            else:
                                resize_width = target_width
                                resize_height = int(target_width / img_ratio)
                                img = img.resize((resize_width, resize_height), Image.Resampling.LANCZOS)
                                top = (resize_height - target_height) // 2
                                img = img.crop((0, top, target_width, top + target_height))
                            
                            photo = ImageTk.PhotoImage(img)
                            self.poster_label.configure(image=photo, text="")
                            self.poster_label.image = photo
                            return
            self.poster_label.configure(text="No image")
        except Exception as e:
            print(f"Error loading poster for {title}: {e}")
            self.poster_label.configure(text="No image")

def show_gui():
    root = tk.Tk()
    root.title("Enhanced Anime Tracker")
    root.geometry("1000x800")
    root.configure(bg=COLORS['bg'])
    
    # Create event loop in a separate thread
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=lambda: loop.run_forever(), daemon=True)
    thread.start()
    
    poster_fetcher = PosterFetcher()
    
    # Title
    title_frame = tk.Frame(root, bg=COLORS['bg'])
    title_frame.pack(fill=tk.X, pady=PADDING['large'])
    
    tk.Label(
        title_frame,
        text="Recent Anime Releases",
        font=("Segoe UI", 20, "bold"),
        fg=COLORS['accent'],
        bg=COLORS['bg'],
        pady=PADDING['medium']
    ).pack()
    
    # Search frame
    search_frame = tk.Frame(root, bg=COLORS['bg'])
    search_frame.pack(fill=tk.X, padx=PADDING['medium'], pady=PADDING['small'])
    
    search_entry = tk.Entry(
        search_frame,
        width=40,
        font=("Segoe UI", 11),
        bd=0,
        relief="flat",
        bg=COLORS['card_bg'],
        fg=COLORS['text'],
        insertbackground=COLORS['text']
    )
    search_entry.pack(side=tk.LEFT, padx=PADDING['small'], ipady=PADDING['small'])
    
    # Container for scrollable content
    container = tk.Frame(root, bg=COLORS['bg'])
    container.pack(fill=tk.BOTH, expand=True, padx=PADDING['medium'], pady=PADDING['small'])
    
    canvas = tk.Canvas(
        container,
        bg=COLORS['bg'],
        highlightthickness=0
    )
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    content_frame = tk.Frame(canvas, bg=COLORS['bg'])
    
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas_window = canvas.create_window(
        (0, 0),
        window=content_frame,
        anchor="nw",
        width=960
    )
    
    def refresh_anime_list(filtered_list=None):
        for widget in content_frame.winfo_children():
            widget.destroy()
            
        loading_label = tk.Label(
            content_frame,
            text="Loading...",
            font=("Segoe UI", 12),
            fg=COLORS['text'],
            bg=COLORS['bg']
        )
        loading_label.pack(pady=PADDING['large'])
        content_frame.update()
        
        try:
            anime_list = fetch_recent_anime() if filtered_list is None else filtered_list
            loading_label.destroy()
            
            if not anime_list:
                tk.Label(
                    content_frame,
                    text="No anime found",
                    font=("Segoe UI", 12),
                    fg=COLORS['text'],
                    bg=COLORS['bg']
                ).pack(pady=PADDING['large'])
                return
            
            for title, release_time, link in anime_list[:30]:
                card = AnimeCard(
                    content_frame,
                    title,
                    release_time,
                    link,
                    poster_fetcher,
                    loop
                )
                card.pack(fill=tk.X, pady=PADDING['small'])
                
        except Exception as e:
            print(f"Error refreshing anime list: {e}")
            loading_label.config(text="Error loading data")
    
    def search_anime():
        search_term = search_entry.get().lower()
        anime_list = fetch_recent_anime()
        filtered_list = [anime for anime in anime_list if search_term in anime[0].lower()]
        refresh_anime_list(filtered_list)
    
    # Buttons
    button_style = {
        'bg': COLORS['accent'],
        'fg': COLORS['bg'],
        'font': ("Segoe UI", 10, "bold"),
        'relief': "flat",
        'padx': PADDING['medium'],
        'pady': PADDING['small'],
        'cursor': "hand2"
    }
    
    tk.Button(
        search_frame,
        text="Search",
        command=search_anime,
        **button_style
    ).pack(side=tk.LEFT, padx=PADDING['small'])
    
    tk.Button(
        search_frame,
        text="Refresh",
        command=lambda: refresh_anime_list(),
        **button_style
    ).pack(side=tk.LEFT, padx=PADDING['small'])
    
    # Configure scrolling
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    def on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width-10)
    
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    content_frame.bind("<Configure>", on_frame_configure)
    canvas.bind("<Configure>", on_canvas_configure)
    canvas.bind_all("<MouseWheel>", on_mousewheel)
    
    # Initial load
    refresh_anime_list()
    
    def on_closing():
        loop.call_soon_threadsafe(loop.stop)
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    show_gui()