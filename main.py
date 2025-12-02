# main.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from PIL import Image, ImageTk, ImageOps
from io import BytesIO
import requests
import os

# импортируем локальные модули (api.py и utils.py должны быть в той же папке)
from api import (
    search_meal, get_random_meal, get_categories, get_areas,
    filter_meals, get_meal_by_id
)
from utils import add_to_favorites, load_favorites, remove_from_favorites

# ---------------- Theme (dark purple) ----------------
BG = "#241B35"
PANEL = "#2F2447"
CARD = "#34283F"
PRIMARY = "#A876F5"
PRIMARY_HOVER = "#8D63E0"
TEXT = "#FFFFFF"
MUTED = "#C9C9D9"
IMAGE_SIZE = (300, 300)

# ---------------- simple thread runner ----------------
def run_async(fn):
    t = threading.Thread(target=fn, daemon=True)
    t.start()

# ---------------- image cache ----------------
_image_cache = {}

def fetch_image_tk(url):
    if not url:
        return None
    if url in _image_cache:
        return _image_cache[url]
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        img = ImageOps.fit(img, IMAGE_SIZE, Image.LANCZOS)
    except Exception:
        img = Image.new("RGBA", IMAGE_SIZE, (60,60,80,255))
    tkimg = ImageTk.PhotoImage(img)
    _image_cache[url] = tkimg
    return tkimg

# ---------------- Main window ----------------
root = tk.Tk()
root.title("MealFinder — Dark Purple")
root.geometry("1200x800")
root.configure(bg=BG)

style = ttk.Style(root)
style.theme_use("clam")
style.configure("TNotebook", background=BG)
style.configure("TNotebook.Tab", background=PANEL, foreground=TEXT, padding=(8,6))
style.map("TNotebook.Tab", background=[("selected", PRIMARY)])

# ---------------- Notebook / Tabs ----------------
notebook = ttk.Notebook(root)
tab_search = ttk.Frame(notebook, padding=6)
tab_fav = ttk.Frame(notebook, padding=6)
notebook.add(tab_search, text="Поиск")
notebook.add(tab_fav, text="Избранное")
notebook.pack(expand=True, fill="both")

# ---------------- SEARCH LAYOUT ----------------
# Left column: filters + results
left = tk.Frame(tab_search, bg=PANEL, width=360, padx=12, pady=12)
left.pack(side="left", fill="y")

tk.Label(left, text="MealFinder", bg=PANEL, fg=TEXT, font=("Segoe UI", 24, "bold")).pack(anchor="w")
tk.Label(left, text="Поиск и фильтрация рецептов", bg=PANEL, fg=MUTED).pack(anchor="w", pady=(0,8))

# Search entry
search_var = tk.StringVar()
search_entry = ttk.Entry(left, textvariable=search_var, width=30)
search_entry.pack(pady=(4,8), fill="x")

def on_search_clicked():
    q = search_var.get().strip()
    if not q:
        messagebox.showinfo("Внимание", "Введите название блюда")
        return
    def task():
        meal = search_meal(q)
        root.after(0, lambda: show_main_meal(meal))
    run_async(task)

ttk.Button(left, text="🔍 Найти", command=on_search_clicked).pack(fill="x", pady=4)

def on_random_clicked():
    def task():
        meal = get_random_meal()
        root.after(0, lambda: show_main_meal(meal))
    run_async(task)

ttk.Button(left, text="🎲 Случайный", command=on_random_clicked).pack(fill="x", pady=4)

# Filters
tk.Label(left, text="Категория:", bg=PANEL, fg=TEXT).pack(anchor="w", pady=(12,0))
cat_cb = ttk.Combobox(left, state="readonly")
cat_cb.pack(fill="x", pady=4)

tk.Label(left, text="Страна:", bg=PANEL, fg=TEXT).pack(anchor="w", pady=(6,0))
area_cb = ttk.Combobox(left, state="readonly")
area_cb.pack(fill="x", pady=4)

def on_apply_filter():
    cat = cat_cb.get().strip() or None
    area = area_cb.get().strip() or None
    if not cat and not area:
        messagebox.showinfo("Фильтр", "Выберите категорию или страну")
        return
    def task():
        meals = filter_meals(category=cat, area=area)
        root.after(0, lambda: populate_result_list(meals))
    run_async(task)

ttk.Button(left, text="Применить фильтр", command=on_apply_filter).pack(fill="x", pady=8)

# Result list
results_lb = tk.Listbox(left, bg=CARD, fg=TEXT, width=40, height=18, activestyle="none", selectbackground=PRIMARY)
results_lb.pack(fill="both", expand=True, pady=(8,0))

_current_results = []

def populate_result_list(meals):
    global _current_results
    _current_results = meals or []
    results_lb.delete(0, tk.END)
    for m in _current_results:
        results_lb.insert(tk.END, m.get("strMeal", "—"))

def on_result_selected(evt):
    sel = results_lb.curselection()
    if not sel:
        return
    idx = sel[0]
    item = _current_results[idx]
    meal_id = item.get("idMeal")
    def task():
        meal = get_meal_by_id(meal_id)
        root.after(0, lambda: show_main_meal(meal))
    run_async(task)

results_lb.bind("<<ListboxSelect>>", on_result_selected)

# ---------------- RIGHT: main detail area (scrollable) ----------------
right_container = tk.Frame(tab_search, bg=BG)
right_container.pack(side="left", fill="both", expand=True, padx=12, pady=12)

# Scrollable canvas
canvas = tk.Canvas(right_container, bg=BG, highlightthickness=0)
vsb = ttk.Scrollbar(right_container, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=vsb.set)
vsb.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

detail_frame = tk.Frame(canvas, bg=BG)
canvas.create_window((0,0), window=detail_frame, anchor="nw")

def on_detail_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))
detail_frame.bind("<Configure>", on_detail_configure)

# Inside detail_frame: fixed layout: image block at top-left, texts below/right
image_block = tk.Frame(detail_frame, bg=BG)
image_block.pack(anchor="nw", pady=(6,12))

meal_img_label = tk.Label(image_block, bg=BG)
meal_img_label.pack()

addfav_btn = tk.Button(image_block, text="⭐ Добавить в избранное", bg=PRIMARY, fg="white",
                       font=("Segoe UI", 11, "bold"), relief="flat")
addfav_btn.pack(pady=(8,0))

# Title and meta
title_label = tk.Label(detail_frame, text="Выберите блюдо", bg=BG, fg=TEXT, font=("Segoe UI", 20, "bold"), anchor="w")
title_label.pack(anchor="nw", pady=(6,4))
meta_label = tk.Label(detail_frame, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10), anchor="w")
meta_label.pack(anchor="nw", pady=(0,12))

# Ingredients (Text with own scrollbar)
ing_frame = tk.Frame(detail_frame, bg=BG)
ing_frame.pack(fill="x", padx=(0,0), pady=(0,12))
tk.Label(ing_frame, text="Ингредиенты:", bg=BG, fg=TEXT).pack(anchor="nw")
ing_text = tk.Text(ing_frame, height=8, wrap="word", bg=CARD, fg=TEXT, bd=0)
ing_scroll = ttk.Scrollbar(ing_frame, orient="vertical", command=ing_text.yview)
ing_text.configure(yscrollcommand=ing_scroll.set)
ing_scroll.pack(side="right", fill="y")
ing_text.pack(side="left", fill="both", expand=True)

# Instructions (Text with own scrollbar)
instr_frame = tk.Frame(detail_frame, bg=BG)
instr_frame.pack(fill="both", expand=True, pady=(0,20))
tk.Label(instr_frame, text="Инструкция:", bg=BG, fg=TEXT).pack(anchor="nw")
instr_text = tk.Text(instr_frame, height=12, wrap="word", bg=CARD, fg=TEXT, bd=0)
instr_scroll = ttk.Scrollbar(instr_frame, orient="vertical", command=instr_text.yview)
instr_text.configure(yscrollcommand=instr_scroll.set)
instr_scroll.pack(side="right", fill="y")
instr_text.pack(side="left", fill="both", expand=True)

# Make text widgets read-only style (we will enable/disable when updating)
def set_readonly_text(widget, content):
    widget.config(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", content)
    widget.config(state="disabled")

current_main_meal = None
current_main_img = None

def show_main_meal(meal):
    global current_main_meal, current_main_img
    if not meal:
        messagebox.showinfo("Результат", "Блюдо не найдено")
        return
    current_main_meal = meal
    title_label.config(text=meal.get("strMeal", "—"))
    meta_label.config(text=f"{meal.get('strCategory','—')}  •  {meal.get('strArea','—')}")

    # ingredients build
    ingredients_lines = []
    for i in range(1, 21):
        ing = meal.get(f"strIngredient{i}")
        meas = meal.get(f"strMeasure{i}")
        if ing and ing.strip():
            if meas and meas.strip():
                ingredients_lines.append(f"• {ing} — {meas}")
            else:
                ingredients_lines.append(f"• {ing}")
    set_readonly_text(ing_text, "\n".join(ingredients_lines))

    # instructions
    set_readonly_text(instr_text, meal.get("strInstructions", ""))

    # image load async
    def task():
        tkimg = fetch_image_tk(meal.get("strMealThumb", ""))
        root.after(0, lambda: update_main_image(tkimg))
    run_async(task)

    # fav button state and command
    favs = load_favorites()
    if any(m.get("idMeal") == meal.get("idMeal") for m in favs):
        addfav_btn.config(text="✓ В избранном", state="disabled")
    else:
        addfav_btn.config(text="⭐ Добавить в избранное", state="normal")

    def do_add():
        if add_to_favorites(meal):
            addfav_btn.config(text="✓ В избранном", state="disabled")
            populate_favorites_tab()
            messagebox.showinfo("Избранное", "Добавлено в избранное")
        else:
            messagebox.showinfo("Избранное", "Уже в избранном")
    addfav_btn.config(command=do_add)

def update_main_image(tkimg):
    global current_main_img
    if tkimg:
        current_main_img = tkimg
        meal_img_label.config(image=current_main_img)
        meal_img_label.image = current_main_img

# ---------------- Populate initial filters ----------------
def initial_load():
    def task():
        cats = get_categories()
        areas = get_areas()
        root.after(0, lambda: cat_cb.config(values=[""] + (cats or [])))
        root.after(0, lambda: area_cb.config(values=[""] + (areas or [])))
        # sample initial list
        if cats:
            samples = filter_meals(category=cats[0])
            root.after(0, lambda: populate_result_list(samples))
    run_async(task)

initial_load()

# ---------------- FAVORITES TAB ----------------
fav_left = tk.Frame(tab_fav, bg=PANEL, width=320, padx=12, pady=12)
fav_left.pack(side="left", fill="y")

tk.Label(fav_left, text="Избранное", bg=PANEL, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0,8))
tk.Label(fav_left, text="Список сохранённых блюд", bg=PANEL, fg=MUTED).pack(anchor="w", pady=(0,12))

fav_listbox = tk.Listbox(fav_left, bg=CARD, fg=TEXT, width=40, height=30, selectbackground=PRIMARY)
fav_listbox.pack(fill="both", expand=True)

# Buttons under list
fav_btn_frame = tk.Frame(fav_left, bg=PANEL)
fav_btn_frame.pack(fill="x", pady=(8,0))
open_btn = ttk.Button(fav_btn_frame, text="Открыть")
del_btn = ttk.Button(fav_btn_frame, text="Удалить")
view_toggle_var = tk.BooleanVar(value=False)  # False = Full view, True = Compact (compact = like mobile)
view_toggle = ttk.Checkbutton(fav_btn_frame, text="Compact view (мобильный)", variable=view_toggle_var)

open_btn.pack(side="left", fill="x", expand=True, padx=(0,6))
del_btn.pack(side="left", fill="x", expand=True, padx=(0,6))
view_toggle.pack(side="left", fill="x")

# Right side in favorites: scrollable detail (same structure as main detail)
fav_right_container = tk.Frame(tab_fav, bg=BG)
fav_right_container.pack(side="left", fill="both", expand=True, padx=12, pady=12)

fav_canvas = tk.Canvas(fav_right_container, bg=BG, highlightthickness=0)
fav_vsb = ttk.Scrollbar(fav_right_container, orient="vertical", command=fav_canvas.yview)
fav_canvas.configure(yscrollcommand=fav_vsb.set)
fav_vsb.pack(side="right", fill="y")
fav_canvas.pack(side="left", fill="both", expand=True)

fav_frame = tk.Frame(fav_canvas, bg=BG)
fav_canvas.create_window((0,0), window=fav_frame, anchor="nw")
def fav_config(e): fav_canvas.configure(scrollregion=fav_canvas.bbox("all"))
fav_frame.bind("<Configure>", fav_config)

# inside fav_frame: image block + info
fav_image_block = tk.Frame(fav_frame, bg=BG)
fav_image_block.pack(anchor="nw", pady=(6,12))

fav_img_label = tk.Label(fav_image_block, bg=BG)
fav_img_label.pack()
fav_open_btn = tk.Button(fav_image_block, text="Открыть рецепт", bg=PRIMARY, fg="white", relief="flat")
fav_open_btn.pack(pady=(8,6))
fav_delete_btn = tk.Button(fav_image_block, text="Удалить из избранного", bg="#E04E4E", fg="white", relief="flat")
fav_delete_btn.pack()

fav_title_label = tk.Label(fav_frame, text="", bg=BG, fg=TEXT, font=("Segoe UI", 18, "bold"), anchor="w")
fav_title_label.pack(anchor="nw", pady=(6,4))
fav_meta_label = tk.Label(fav_frame, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10), anchor="w")
fav_meta_label.pack(anchor="nw", pady=(0,12))

fav_ing_label = tk.Label(fav_frame, text="Ингредиенты:", bg=BG, fg=TEXT)
fav_ing_label.pack(anchor="nw")
fav_ing_text = tk.Text(fav_frame, height=8, wrap="word", bg=CARD, fg=TEXT, bd=0)
fav_ing_scroll = ttk.Scrollbar(fav_frame, orient="vertical", command=fav_ing_text.yview)
fav_ing_text.configure(yscrollcommand=fav_ing_scroll.set)
fav_ing_scroll.pack(side="right", fill="y")
fav_ing_text.pack(fill="both", padx=(0,0), pady=(0,8))

fav_instr_label = tk.Label(fav_frame, text="Инструкция:", bg=BG, fg=TEXT)
fav_instr_label.pack(anchor="nw")
fav_instr_text = tk.Text(fav_frame, height=12, wrap="word", bg=CARD, fg=TEXT, bd=0)
fav_instr_scroll = ttk.Scrollbar(fav_frame, orient="vertical", command=fav_instr_text.yview)
fav_instr_text.configure(yscrollcommand=fav_instr_scroll.set)
fav_instr_scroll.pack(side="right", fill="y")
fav_instr_text.pack(fill="both", pady=(0,8))

# ---------------- Favorites logic ----------------
_favs_data = []

def populate_favorites_tab():
    global _favs_data
    _favs_data = load_favorites() or []
    fav_listbox.delete(0, tk.END)
    for m in _favs_data:
        fav_listbox.insert(tk.END, m.get("strMeal", "—"))

    # clear right details
    clear_fav_detail()

def clear_fav_detail():
    fav_img_label.config(image="")
    fav_img_label.image = None
    fav_title_label.config(text="")
    fav_meta_label.config(text="")
    fav_ing_text.config(state="normal"); fav_ing_text.delete("1.0", "end"); fav_ing_text.config(state="disabled")
    fav_instr_text.config(state="normal"); fav_instr_text.delete("1.0", "end"); fav_instr_text.config(state="disabled")

def on_fav_list_select(evt):
    sel = fav_listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    if idx >= len(_favs_data): return
    meal = _favs_data[idx]
    show_fav_detail(meal)

fav_listbox.bind("<<ListboxSelect>>", on_fav_list_select)

def show_fav_detail(meal):
    # if compact view is ON, hide texts and show only title+buttons
    compact = view_toggle_var.get()
    fav_title_label.config(text=meal.get("strMeal","—"))
    fav_meta_label.config(text=f"{meal.get('strCategory','—')}  •  {meal.get('strArea','—')}")
    # ingredients & instructions
    ingredients_lines = []
    for i in range(1,21):
        ing = meal.get(f"strIngredient{i}")
        ms = meal.get(f"strMeasure{i}")
        if ing and ing.strip():
            if ms and ms.strip():
                ingredients_lines.append(f"• {ing} — {ms}")
            else:
                ingredients_lines.append(f"• {ing}")
    fav_ing_text.config(state="normal"); fav_ing_text.delete("1.0","end"); fav_ing_text.insert("1.0", "\n".join(ingredients_lines)); fav_ing_text.config(state="disabled")
    fav_instr_text.config(state="normal"); fav_instr_text.delete("1.0","end"); fav_instr_text.insert("1.0", meal.get("strInstructions","")); fav_instr_text.config(state="disabled")

    # image async
    def task():
        tkimg = fetch_image_tk(meal.get("strMealThumb",""))
        root.after(0, lambda: fav_img_label.config(image=tkimg))
        fav_img_label.image = tkimg
    run_async(task)

    # button actions
    def open_recipe():
        # switch to main tab and show meal there
        notebook.select(tab_search)
        def task2():
            full = get_meal_by_id(meal.get("idMeal"))
            root.after(0, lambda: show_main_meal(full))
        run_async(task2)

    def delete_recipe():
        if messagebox.askyesno("Удалить", f"Удалить {meal.get('strMeal')} из избранного?"):
            remove_from_favorites(meal.get("idMeal"))
            populate_favorites_tab()

    fav_open_btn.config(command=open_recipe)
    fav_delete_btn.config(command=delete_recipe)

    # compact: hide ing/instr if compact True
    if view_toggle_var.get():
        fav_ing_text.pack_forget()
        fav_ing_scroll.pack_forget()
        fav_ing_label.pack_forget()
        fav_instr_text.pack_forget()
        fav_instr_scroll.pack_forget()
        fav_instr_label.pack_forget()
    else:
        # ensure packed
        fav_ing_label.pack(anchor="nw")
        fav_ing_scroll.pack(side="right", fill="y")
        fav_ing_text.pack(fill="both", padx=(0,0), pady=(0,8))
        fav_instr_label.pack(anchor="nw")
        fav_instr_scroll.pack(side="right", fill="y")
        fav_instr_text.pack(fill="both", pady=(0,8))

# open/delete buttons on left for convenience
def left_open():
    sel = fav_listbox.curselection()
    if not sel: return
    meal = _favs_data[sel[0]]
    show_fav_detail(meal)

def left_delete():
    sel = fav_listbox.curselection()
    if not sel: return
    meal = _favs_data[sel[0]]
    if messagebox.askyesno("Удалить", f"Удалить {meal.get('strMeal')}?"):
        remove_from_favorites(meal.get("idMeal"))
        populate_favorites_tab()

open_btn.config(command=left_open)
del_btn.config(command=left_delete)

# ---------------- Start / initial population ----------------
populate_favorites_tab()
initial_load()

# keep canvas scrolled to top when switching tabs
def on_tab_changed(event):
    tab = event.widget.select()
    # small safety: update scrollregion
    canvas.yview_moveto(0)
    fav_canvas.yview_moveto(0)

notebook.bind("<<NotebookTabChanged>>", on_tab_changed)

root.mainloop()
