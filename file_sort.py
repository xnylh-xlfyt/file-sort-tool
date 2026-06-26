"""
文件整理器 - CustomTkinter 现代化版本
功能：按文件类型 / 按月份自动分类整理文件
"""

import os, sys, shutil, time, json, threading, re
from enum import Enum
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, ttk, messagebox as mb
import customtkinter as ctk

# ============================================================
# 配置常量
# ============================================================

CATEGORY_COLORS = {
    "图片": {"bg": "#FF6B6B", "icon": "🖼️", "exts": [".jpg", ".png", ".jpeg", ".gif", ".bmp", ".webp"]},
    "文档": {"bg": "#4ECDC4", "icon": "📄", "exts": [".pdf", ".txt", ".docx", ".doc", ".xlsx", ".xls", ".ppt", ".pptx"]},
    "视频": {"bg": "#45B7D1", "icon": "🎬", "exts": [".mp4", ".mov", ".avi", ".mkv", ".flv"]},
    "音乐": {"bg": "#96CEB4", "icon": "🎵", "exts": [".mp3", ".wav", ".flac", ".ogg"]},
    "其他": {"bg": "#95A5A6", "icon": "📦", "exts": []},
}

def _get_config_dir():
    return os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

CONFIG_DIR = _get_config_dir()
EXCLUDE_RULES_FILE = os.path.join(CONFIG_DIR, "exclude_rules.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "sort_history.json")
THEME_FILE = os.path.join(CONFIG_DIR, "theme_pref.json")
SORT_MODE_FILE = os.path.join(CONFIG_DIR, "sort_mode_pref.json")

def _load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return default

def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

# ============================================================
# 枚举：分类方式
# ============================================================

class SortMode(Enum):
    BY_TYPE = "by_type"
    BY_MONTH = "by_month"

    def display_name(self):
        return {"by_type": "按文件类型", "by_month": "按月份"}[self.value]

    @staticmethod
    def from_display(name):
        return {"按文件类型": SortMode.BY_TYPE, "按月份": SortMode.BY_MONTH}.get(name, SortMode.BY_TYPE)

# ============================================================
# 核心功能函数
# ============================================================

def get_folder_name(ext, sort_mode=SortMode.BY_TYPE):
    if sort_mode == SortMode.BY_TYPE:
        ext = ext.lower()
        for category, info in CATEGORY_COLORS.items():
            if ext in info["exts"]:
                return category
        return "其他"
    return ""

def get_month_folder_name(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y年%m月")

def _is_category_folder_name(folder_name, sort_mode):
    if sort_mode == SortMode.BY_TYPE:
        return folder_name in CATEGORY_COLORS
    return bool(re.match(r'^\d{4}年\d{2}月$', folder_name))

def _parse_exclude_rules(rules):
    """解析排除规则，返回 (file_paths, folder_paths, exts, names)
    
    规则类型自动识别：
      - 存在的文件路径 → 按完整路径精确排除
      - 存在的文件夹路径 → 排除整个文件夹及其内容
      - 以 . 开头 → 按后缀排除（如 .exe）
      - 其他 → 按文件名排除（同时匹配纯名称和带后缀名）
    """
    file_paths, folder_paths, exts, names = [], [], [], []
    for r in rules:
        if os.path.isfile(r):
            file_paths.append(os.path.abspath(r).lower())
        elif os.path.isdir(r):
            folder_paths.append(os.path.abspath(r).lower())
        elif r.startswith("."):
            exts.append(r.lower())
        else:
            names.append(r.lower())
    return file_paths, folder_paths, exts, names


def _is_excluded(full_path, file_paths, folder_paths, exts, names):
    """统一排除检查，所有调用点使用此函数"""
    full_lower = os.path.abspath(full_path).lower()
    # 检查完整文件路径
    if full_lower in file_paths:
        return True
    # 检查是否在排除的文件夹内
    for fp in folder_paths:
        if full_lower.startswith(fp + os.sep) or full_lower == fp:
            return True
    name_only, ext = os.path.splitext(os.path.basename(full_path))
    file_name = os.path.basename(full_path)
    # 检查后缀
    if ext.lower() in exts:
        return True
    # 检查文件名（纯名称 或 完整文件名）
    if name_only.lower() in names or file_name.lower() in names:
        return True
    return False

def preview_categories(target_dir, exclude_rules, sort_mode=SortMode.BY_TYPE):
    file_paths, folder_paths, exclude_exts, exclude_names = _parse_exclude_rules(exclude_rules)
    counts = {}

    existing_category_dirs = set()
    try:
        for entry in os.listdir(target_dir):
            entry_path = os.path.join(target_dir, entry)
            if (
                os.path.isdir(entry_path)
                and _is_category_folder_name(entry, sort_mode)
                and not _is_excluded(entry_path, file_paths, folder_paths, exclude_exts, exclude_names)
            ):
                existing_category_dirs.add(entry)
    except:
        pass

    def _should_skip(root):
        rel = os.path.relpath(root, target_dir)
        if rel != ".":
            top = rel.split(os.sep)[0]
            return top in existing_category_dirs
        return False

    for root, dirs, files in os.walk(target_dir):
        if _should_skip(root):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if os.path.join(root, d).lower() not in folder_paths
                    and not any(os.path.join(root, d).lower().startswith(fp + os.sep) for fp in folder_paths)]
        for file_name in files:
            full_path = os.path.join(root, file_name)
            if _is_excluded(full_path, file_paths, folder_paths, exclude_exts, exclude_names):
                continue
            if sort_mode == SortMode.BY_TYPE:
                category = get_folder_name(os.path.splitext(file_name)[1], sort_mode)
            else:
                category = get_month_folder_name(os.path.getmtime(full_path))
            counts[category] = counts.get(category, 0) + 1
    return counts

def sort_files(target_dir, status_callback, progress_callback, exclude_rules, sort_mode=SortMode.BY_TYPE, undo_log=None):
    """整理文件。若 undo_log 为列表，则向其追加 (原始路径, 新路径) 用于回退"""
    start_time = time.time()
    file_count = 0
    category_move_counts = {}
    file_paths, folder_paths, exclude_exts, exclude_names = _parse_exclude_rules(exclude_rules)

    # 获取已有分类子目录（只跳过与当前分类方式匹配的文件夹）
    existing_subdirs = set()
    try:
        for entry in os.listdir(target_dir):
            entry_path = os.path.join(target_dir, entry)
            if os.path.isdir(entry_path) and not _is_excluded(entry_path, file_paths, folder_paths, exclude_exts, exclude_names):
                existing_subdirs.add(entry)
    except:
        pass

    def _should_skip(root):
        rel = os.path.relpath(root, target_dir)
        if rel != ".":
            top = rel.split(os.sep)[0]
            return top in existing_subdirs and _is_category_folder_name(top, sort_mode)
        return False

    total_files = 0
    for root, dirs, files in os.walk(target_dir):
        if _should_skip(root):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not any(
            os.path.join(root, d).lower() == fp or os.path.join(root, d).lower().startswith(fp + os.sep)
            for fp in folder_paths)]
        for file_name in files:
            full_path = os.path.join(root, file_name)
            if _is_excluded(full_path, file_paths, folder_paths, exclude_exts, exclude_names):
                continue
            total_files += 1

    if total_files == 0:
        return 0, time.time() - start_time, {}

    for root, dirs, files in os.walk(target_dir):
        if _should_skip(root):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not any(
            os.path.join(root, d).lower() == fp or os.path.join(root, d).lower().startswith(fp + os.sep)
            for fp in folder_paths)]
        for file_name in files:
            full_path = os.path.join(root, file_name)
            if _is_excluded(full_path, file_paths, folder_paths, exclude_exts, exclude_names):
                continue
            name_only, ext = os.path.splitext(file_name)
            folder_name = get_folder_name(ext, sort_mode) if sort_mode == SortMode.BY_TYPE else get_month_folder_name(os.path.getmtime(full_path))
            category_move_counts[folder_name] = category_move_counts.get(folder_name, 0) + 1
            category_path = os.path.join(target_dir, folder_name)
            if not os.path.exists(category_path):
                os.mkdir(category_path)
            new_path = os.path.join(category_path, file_name)
            if os.path.exists(new_path):
                count = 1
                while True:
                    new_name = f"{name_only}({count}){ext}"
                    new_path = os.path.join(category_path, new_name)
                    if not os.path.exists(new_path):
                        break
                    count += 1
            if undo_log is not None:
                undo_log.append((full_path, new_path))
            shutil.move(full_path, new_path)
            file_count += 1
            status_callback(f"正在整理: {file_name} ({file_count}/{total_files})")
            progress_callback(file_count / total_files)

    for root, dirs, files in os.walk(target_dir, topdown=False):
        if _should_skip(root):
            continue
        if not files and not dirs:
            try:
                os.rmdir(root)
            except:
                pass

    return file_count, time.time() - start_time, category_move_counts

# ============================================================
# 拆除文件夹功能
# ============================================================

def flatten_directory(target_dir, status_callback, progress_callback, exclude_rules):
    """将目标目录下所有子文件夹中的文件移动到根目录，然后删除空文件夹"""
    start_time = time.time()
    file_count = 0
    file_paths, folder_paths, exclude_exts, exclude_names = _parse_exclude_rules(exclude_rules)

    # 统计需要移动的文件数
    total_files = 0
    for root, dirs, files in os.walk(target_dir):
        if root == target_dir:
            continue
        dirs[:] = [d for d in dirs if not any(
            os.path.join(root, d).lower() == fp or os.path.join(root, d).lower().startswith(fp + os.sep)
            for fp in folder_paths)]
        for file_name in files:
            full_path = os.path.join(root, file_name)
            if _is_excluded(full_path, file_paths, folder_paths, exclude_exts, exclude_names):
                continue
            total_files += 1

    if total_files == 0:
        return 0, time.time() - start_time

    # 移动所有文件到根目录
    for root, dirs, files in os.walk(target_dir):
        if root == target_dir:
            continue
        dirs[:] = [d for d in dirs if not any(
            os.path.join(root, d).lower() == fp or os.path.join(root, d).lower().startswith(fp + os.sep)
            for fp in folder_paths)]
        for file_name in files:
            full_path = os.path.join(root, file_name)
            if _is_excluded(full_path, file_paths, folder_paths, exclude_exts, exclude_names):
                continue
            name_only, ext = os.path.splitext(file_name)
            new_path = os.path.join(target_dir, file_name)
            if os.path.exists(new_path):
                count = 1
                while True:
                    new_name = f"{name_only}({count}){ext}"
                    new_path = os.path.join(target_dir, new_name)
                    if not os.path.exists(new_path):
                        break
                    count += 1
            shutil.move(full_path, new_path)
            file_count += 1
            status_callback(f"正在拆除: {file_name} ({file_count}/{total_files})")
            progress_callback(file_count / total_files)

    # 从底层向上删除空文件夹
    for root, dirs, files in os.walk(target_dir, topdown=False):
        if root == target_dir:
            continue
        if not any(os.path.join(root).lower().startswith(fp) for fp in folder_paths):
            try:
                if not os.listdir(root):
                    os.rmdir(root)
                    status_callback(f"已删除空文件夹: {os.path.basename(root)}")
            except:
                pass

    return file_count, time.time() - start_time

# ============================================================
# 持久化函数
# ============================================================

def load_history():
    return _load_json(HISTORY_FILE, {"last_count": 0, "last_time": 0, "total_count": 0, "total_runs": 0})

def save_history(file_count, elapsed_time):
    history = load_history()
    history["last_count"] = file_count
    history["last_time"] = round(elapsed_time, 2)
    history["total_count"] += file_count
    history["total_runs"] += 1
    _save_json(HISTORY_FILE, history)

def load_theme_pref():
    return _load_json(THEME_FILE, {}).get("mode", "system")

def save_theme_pref(mode):
    _save_json(THEME_FILE, {"mode": mode})

def load_exclude_rules():
    return _load_json(EXCLUDE_RULES_FILE, [])

def save_exclude_rules(rules):
    _save_json(EXCLUDE_RULES_FILE, rules)

def load_sort_mode():
    return SortMode.from_display(_load_json(SORT_MODE_FILE, {}).get("mode", "按文件类型"))

def save_sort_mode(mode):
    _save_json(SORT_MODE_FILE, {"mode": mode.display_name()})

# ============================================================
# 文件搜索算法
# ============================================================

class FileSearcher:
    _cache = {}
    _CACHE_TTL = 30

    @staticmethod
    def _tree_signature(root_dir, exclude_dirs=None):
        if exclude_dirs is None:
            exclude_dirs = set()
        newest_mtime = 0
        entry_count = 0
        try:
            for root, dirs, files in os.walk(root_dir):
                rel = os.path.relpath(root, root_dir)
                if rel != ".":
                    top_dir = rel.split(os.sep)[0]
                    if top_dir in exclude_dirs:
                        dirs[:] = []
                        continue
                try:
                    newest_mtime = max(newest_mtime, os.path.getmtime(root))
                    entry_count += 1
                except OSError:
                    pass
                for name in files:
                    path = os.path.join(root, name)
                    try:
                        newest_mtime = max(newest_mtime, os.path.getmtime(path))
                        entry_count += 1
                    except OSError:
                        pass
        except (PermissionError, OSError):
            pass
        return newest_mtime, entry_count

    @staticmethod
    def _build_index(root_dir, exclude_dirs=None):
        if exclude_dirs is None:
            exclude_dirs = set()
        cache_key = os.path.abspath(root_dir)
        signature = FileSearcher._tree_signature(root_dir, exclude_dirs)
        cached = FileSearcher._cache.get(cache_key)
        if cached and time.time() - cached.get("time", 0) < FileSearcher._CACHE_TTL:
            if signature == cached.get("signature"):
                return cached["entries"]
        entries = []
        try:
            for root, dirs, _ in os.walk(root_dir):
                rel = os.path.relpath(root, root_dir)
                if rel != ".":
                    top_dir = rel.split(os.sep)[0]
                    if top_dir in exclude_dirs:
                        dirs[:] = []
                        continue
                for entry in os.scandir(root):
                    if entry.is_file():
                        name_only, ext = os.path.splitext(entry.name)
                        entries.append({"path": entry.path, "name": entry.name, "name_only": name_only, "ext": ext.lower(), "size": entry.stat().st_size, "type": "file"})
                    elif entry.is_dir():
                        entries.append({"path": entry.path, "name": entry.name, "name_only": entry.name, "ext": "", "size": 0, "type": "dir"})
        except (PermissionError, OSError):
            pass
        FileSearcher._cache[cache_key] = {"entries": entries, "time": time.time(), "signature": signature}
        return entries

    @staticmethod
    def clear_cache(root_dir=None):
        if root_dir:
            FileSearcher._cache.pop(os.path.abspath(root_dir), None)
        else:
            FileSearcher._cache.clear()

    @staticmethod
    def _boyer_moore_horspool(text, pattern):
        n, m = len(text), len(pattern)
        if m == 0:
            return 0
        if m > n:
            return -1
        skip = {pattern[i]: m - 1 - i for i in range(m - 1)}
        i = m - 1
        while i < n:
            j, k = m - 1, i
            while j >= 0 and text[k] == pattern[j]:
                j -= 1
                k -= 1
            if j < 0:
                return k + 1
            i += skip.get(text[i], m)
        return -1

    @staticmethod
    def search(root_dir, query, max_results=500, exclude_dirs=None):
        if not query or not root_dir or not os.path.exists(root_dir):
            return []
        query = query.strip().lower()
        if not query:
            return []
        entries = FileSearcher._build_index(root_dir, exclude_dirs)
        results, matched_set = [], set()
        for e in entries:
            if len(results) >= max_results:
                break
            if e["name_only"].lower() == query or e["name"].lower() == query:
                if e["path"] not in matched_set:
                    matched_set.add(e["path"])
                    results.append(e)
        for e in entries:
            if len(results) >= max_results:
                break
            if e["path"] in matched_set:
                continue
            if e["name_only"].lower().startswith(query) or e["name"].lower().startswith(query):
                matched_set.add(e["path"])
                results.append(e)
        for e in entries:
            if len(results) >= max_results:
                break
            if e["path"] in matched_set:
                continue
            name_lower = e["name_only"].lower()
            if FileSearcher._boyer_moore_horspool(name_lower, query) != -1 or FileSearcher._boyer_moore_horspool(e["name"].lower(), query) != -1:
                matched_set.add(e["path"])
                results.append(e)
        if len(query) <= 10:
            for e in entries:
                if len(results) >= max_results:
                    break
                if e["path"] in matched_set:
                    continue
                it = iter(e["name_only"].lower())
                if all(c in it for c in query):
                    matched_set.add(e["path"])
                    results.append(e)
        return results

# ============================================================
# 主窗口类
# ============================================================

class FileSorterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.theme_mode = load_theme_pref()
        ctk.set_appearance_mode(self.theme_mode)
        ctk.set_default_color_theme("blue")
        self.title("📁 文件整理器")
        self.geometry("620x720")
        self.minsize(580, 670)
        self.resizable(True, True)
        self.EXCLUDE_RULES = load_exclude_rules()
        self.is_sorting = False
        self.sort_mode = load_sort_mode()
        self.search_timer = None
        self.search_results = []
        self.is_searching = False
        self.last_sort_report = None
        self.undo_data = None
        self._build_ui()
        self._update_history_display()

    # ----------------------------------------------------------
    # UI 辅助方法
    # ----------------------------------------------------------

    @staticmethod
    def _label(parent, text, font_size=14, bold=True, **kw):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=font_size, weight="bold" if bold else "normal"), **kw)

    @staticmethod
    def _btn(parent, text, font_size=13, height=35, corner_radius=8, **kw):
        return ctk.CTkButton(parent, text=text, font=ctk.CTkFont(size=font_size), height=height, corner_radius=corner_radius, **kw)

    def _card(self, parent, color, icon, title, count_text, row, col):
        card = ctk.CTkFrame(parent, fg_color=color, corner_radius=10)
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=24), text_color="white").grid(row=0, column=0, pady=(8, 0))
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color="white").grid(row=1, column=0)
        cl = ctk.CTkLabel(card, text=count_text, font=ctk.CTkFont(size=11), text_color="white")
        cl.grid(row=2, column=0, pady=(0, 8))
        return cl

    # ----------------------------------------------------------
    # UI 构建
    # ----------------------------------------------------------

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 标题栏（固定顶部）
        tf = ctk.CTkFrame(self, corner_radius=0, height=50)
        tf.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        tf.grid_columnconfigure(0, weight=1)
        self._label(tf, "📁 文件整理器", font_size=20).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        labels = {"dark": "🌙 暗色", "light": "☀️ 亮色", "system": "🌓 跟随系统"}
        self.theme_btn = self._btn(tf, labels.get(self.theme_mode, "🌓 跟随系统"), width=100, height=30, corner_radius=15, command=self._toggle_theme)
        self.theme_btn.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="e")

        # 可滚动内容区域
        self.scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        sf = self.scroll_frame  # 简写

        # 目录选择
        ds = ctk.CTkFrame(sf)
        ds.grid(row=0, column=0, sticky="ew", padx=20, pady=(0, 10))
        ds.grid_columnconfigure(1, weight=1)
        self._label(ds, "📂 目标目录").grid(row=0, column=0, padx=(15, 10), pady=(12, 5), sticky="w")
        self.dir_entry = ctk.CTkEntry(ds, placeholder_text="请选择要整理的目录...", font=ctk.CTkFont(size=13), height=35)
        self.dir_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 5))
        self.dir_entry.insert(0, r"E:\ceshi")
        self.browse_btn = self._btn(ds, "📁 浏览文件夹", command=self._browse_directory)
        self.browse_btn.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 12))

        # 分类方式
        sms = ctk.CTkFrame(sf)
        sms.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        sms.grid_columnconfigure(1, weight=1)
        self._label(sms, "🏷️ 分类方式").grid(row=0, column=0, padx=(15, 10), pady=(10, 10), sticky="w")
        self.sort_mode_var = ctk.StringVar(value=self.sort_mode.display_name())
        self.sort_mode_menu = ctk.CTkOptionMenu(sms, values=["按文件类型", "按月份"], variable=self.sort_mode_var, command=self._on_sort_mode_change, font=ctk.CTkFont(size=13), height=32, corner_radius=6)
        self.sort_mode_menu.grid(row=0, column=1, padx=(0, 15), pady=(10, 10), sticky="w")

        # 统计卡片
        self.stats_section = ctk.CTkFrame(sf)
        self.stats_section.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.stats_section.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.stats_title_label = self._label(self.stats_section, "📊 文件分类统计")
        self.stats_title_label.grid(row=0, column=0, columnspan=5, padx=15, pady=(10, 5), sticky="w")
        self.category_cards = {}
        for i, (n, c, ic) in enumerate([("图片", "#FF6B6B", "🖼️"), ("文档", "#4ECDC4", "📄"), ("视频", "#45B7D1", "🎬"), ("音乐", "#96CEB4", "🎵"), ("其他", "#95A5A6", "📦")]):
            self.category_cards[n] = self._card(self.stats_section, c, ic, n, "0 个文件", 1, i)

        # 进度条
        ps = ctk.CTkFrame(sf)
        ps.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 10))
        ps.grid_columnconfigure(0, weight=1)
        self.progress_bar = ctk.CTkProgressBar(ps, height=12, corner_radius=6)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 5))
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(ps, text="💡 请选择目录后点击「开始整理」", font=ctk.CTkFont(size=12), text_color=("gray60", "gray70"))
        self.status_label.grid(row=1, column=0, padx=15, pady=(0, 12))

        # 操作按钮
        bs = ctk.CTkFrame(sf, fg_color="transparent")
        bs.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 10))
        bs.grid_columnconfigure((0, 1, 2), weight=1)
        self.settings_btn = self._btn(bs, "⚙️ 排除规则设置", command=self._open_settings, fg_color=("#FF9800", "#E65100"), hover_color=("#F57C00", "#BF360C"))
        self.settings_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self.sort_btn = self._btn(bs, "🚀 开始整理", font_size=14, command=self._start_sorting, fg_color=("#2196F3", "#1565C0"), hover_color=("#1976D2", "#0D47A1"))
        self.sort_btn.grid(row=0, column=1, sticky="ew", padx=(3, 3))
        self.flatten_btn = self._btn(bs, "📂 拆除文件夹", command=self._start_flatten, fg_color=("#607D8B", "#37474F"), hover_color=("#546E7A", "#263238"))
        self.flatten_btn.grid(row=0, column=2, sticky="ew", padx=(3, 0))

        # 文件搜索
        ss = ctk.CTkFrame(sf)
        ss.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 10))
        ss.grid_columnconfigure(1, weight=1)
        self._label(ss, "🔍 文件搜索").grid(row=0, column=0, padx=(15, 10), pady=(10, 5), sticky="w")
        self.search_entry = ctk.CTkEntry(ss, placeholder_text="输入文件名搜索（无需后缀）...", font=ctk.CTkFont(size=13), height=35)
        self.search_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0, 15), pady=(10, 5))
        self.search_entry.bind("<KeyRelease>", self._on_search_key_release)
        self.search_entry.bind("<Return>", self._on_search_enter)
        self.search_btn = self._btn(ss, "🔍 搜索", font_size=12, height=32, width=80, corner_radius=6, command=self._start_search_thread, fg_color=("#9C27B0", "#6A1B9A"), hover_color=("#7B1FA2", "#4A148C"))
        self.search_btn.grid(row=0, column=3, padx=(5, 15), pady=(10, 5))
        self.search_result_label = ctk.CTkLabel(ss, text="", font=ctk.CTkFont(size=11), text_color=("gray50", "gray60"))
        self.search_result_label.grid(row=1, column=0, columnspan=4, padx=15, pady=(0, 5), sticky="w")
        rf = ctk.CTkFrame(ss)
        rf.grid(row=2, column=0, columnspan=4, sticky="ew", padx=15, pady=(0, 10))
        rf.grid_columnconfigure(0, weight=1)
        rf.grid_rowconfigure(0, weight=1)
        is_dark = ctk.get_appearance_mode() == "Dark"
        self.search_listbox = tk.Listbox(rf, font=("Consolas", 10), bg="#2b2b2b" if is_dark else "#ffffff", fg="#ffffff" if is_dark else "#000000", selectbackground="#7B1FA2", selectforeground="white", relief="flat", highlightthickness=0, borderwidth=0, height=5)
        self.search_listbox.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(rf, orient="vertical", command=self.search_listbox.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.search_listbox.configure(yscrollcommand=sb.set)
        self.search_listbox.bind("<Double-Button-1>", lambda e: self._open_selected_file_location())
        self.search_context_menu = tk.Menu(self.search_listbox, tearoff=0)
        self.search_context_menu.add_command(label="📂 打开所在文件夹", command=self._open_selected_file_location)
        self.search_context_menu.add_command(label="📋 复制完整路径", command=self._copy_selected_file_path)
        self.search_listbox.bind("<Button-3>", self._on_search_right_click)

        # 历史记录 + 查看报告 + 撤销
        hs = ctk.CTkFrame(sf)
        hs.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 15))
        hs.grid_columnconfigure(0, weight=1)
        self.history_label = ctk.CTkLabel(hs, text="📜 历史记录：暂无", font=ctk.CTkFont(size=12), text_color=("gray50", "gray60"))
        self.history_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        btn_frame = ctk.CTkFrame(hs, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=(0, 15), pady=10, sticky="e")
        self.undo_btn = self._btn(btn_frame, "↩️ 撤销整理", font_size=12, height=30, width=100, corner_radius=6, command=self._undo_last_sort, fg_color=("#E53935", "#C62828"), hover_color=("#C62828", "#B71C1C"), state="disabled")
        self.undo_btn.pack(side="right", padx=(5, 0))
        self.report_btn = self._btn(btn_frame, "📊 查看报告", font_size=12, height=30, width=100, corner_radius=6, command=self._show_sort_report, fg_color=("#FF9800", "#E65100"), hover_color=("#F57C00", "#BF360C"), state="disabled")
        self.report_btn.pack(side="right")

    # ----------------------------------------------------------
    # 主题切换
    # ----------------------------------------------------------

    def _toggle_theme(self):
        modes = {"system": "light", "light": "dark", "dark": "system"}
        labels = {"system": "🌓 跟随系统", "light": "☀️ 亮色", "dark": "🌙 暗色"}
        self.theme_mode = modes.get(self.theme_mode, "system")
        ctk.set_appearance_mode(self.theme_mode)
        self.theme_btn.configure(text=labels.get(self.theme_mode, "🌓 跟随系统"))
        save_theme_pref(self.theme_mode)

    # ----------------------------------------------------------
    # 目录选择 & 预览
    # ----------------------------------------------------------

    def _browse_directory(self):
        d = filedialog.askdirectory(title="选择要整理的目录")
        if d:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, d)
            self._auto_preview()

    def _auto_preview(self):
        target = self.dir_entry.get().strip()
        if not target or not os.path.exists(target):
            return
        try:
            counts = preview_categories(target, self.EXCLUDE_RULES, self.sort_mode)
            total = sum(counts.values())
            self._refresh_stats_display(counts)
            self.status_label.configure(text=f"📊 共发现 {total} 个文件（{self.sort_mode.display_name()}），点击「开始整理」执行分类" if total else "📭 目录中没有需要整理的文件")
        except Exception as e:
            self.status_label.configure(text=f"❌ 预览出错：{str(e)}", text_color="red")

    # ----------------------------------------------------------
    # 分类方式切换
    # ----------------------------------------------------------

    def _on_sort_mode_change(self, choice):
        self.sort_mode = SortMode.from_display(choice)
        save_sort_mode(self.sort_mode)
        self._auto_preview()

    # ----------------------------------------------------------
    # 统计卡片刷新
    # ----------------------------------------------------------

    def _refresh_stats_display(self, counts):
        for w in self.stats_section.winfo_children():
            if w != self.stats_title_label:
                w.destroy()
        self.category_cards = {}

        if self.sort_mode == SortMode.BY_TYPE:
            self.stats_section.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
            self.stats_title_label.configure(text="📊 文件分类统计（按文件类型）")
            for i, (n, c, ic) in enumerate([("图片", "#FF6B6B", "🖼️"), ("文档", "#4ECDC4", "📄"), ("视频", "#45B7D1", "🎬"), ("音乐", "#96CEB4", "🎵"), ("其他", "#95A5A6", "📦")]):
                self.category_cards[n] = self._card(self.stats_section, c, ic, n, f"{counts.get(n, 0)} 个文件", 1, i)
        else:
            self.stats_title_label.configure(text="📊 文件分类统计（按月份）")
            if not counts:
                ctk.CTkLabel(self.stats_section, text="暂无文件", font=ctk.CTkFont(size=13), text_color=("gray50", "gray60")).grid(row=1, column=0, columnspan=5, pady=15)
                return
            months = sorted(counts.keys())
            colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFB74D", "#BA68C8", "#81C784", "#64B5F6", "#E57373", "#FFD54F", "#A1887F", "#90A4AE"]
            cols = min(len(months), 6)
            for c in range(cols):
                self.stats_section.grid_columnconfigure(c, weight=1)
            for i, m in enumerate(months):
                self.category_cards[m] = self._card(self.stats_section, colors[i % len(colors)], "📅", m, f"{counts.get(m, 0)} 个文件", 1 + i // cols, i % cols)

    # ----------------------------------------------------------
    # 开始整理
    # ----------------------------------------------------------

    def _start_sorting(self):
        target = self.dir_entry.get().strip()
        if not target:
            return self._show_warning("请先选择要整理的目录！")
        if not os.path.exists(target):
            return self._show_error(f"目录不存在：{target}")
        if not self._ask_yesno(f"确定要整理目录：\n{target}\n\n分类方式：{self.sort_mode.display_name()}\n这将移动所有文件到分类文件夹中！"):
            return

        self.sort_btn.configure(state="disabled", text="⏳ 整理中...")
        self.settings_btn.configure(state="disabled")
        self.browse_btn.configure(state="disabled")
        self.is_sorting = True
        self.progress_bar.set(0)

        try:
            preview_categories(target, self.EXCLUDE_RULES, self.sort_mode)
            def us(m): self.status_label.configure(text=m)
            def up(v): self.progress_bar.set(v); self.update_idletasks()
            # 记录撤销日志
            undo_log = []
            fc, et, cat_counts = sort_files(target, us, up, self.EXCLUDE_RULES, self.sort_mode, undo_log=undo_log)
            before_counts = preview_categories(target, self.EXCLUDE_RULES, self.sort_mode)
            self._refresh_stats_display(before_counts)
            save_history(fc, et)
            self._update_history_display()
            self.progress_bar.set(1)
            # 保存本次整理报告
            self.last_sort_report = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mode": self.sort_mode.display_name(),
                "target_dir": target,
                "total_moved": fc,
                "elapsed": round(et, 2),
                "category_details": dict(sorted(cat_counts.items(), key=lambda x: -x[1])),
            }
            self.report_btn.configure(state="normal")
            # 保存撤销数据
            if undo_log:
                self.undo_data = {
                    "target_dir": target,
                    "sort_mode": self.sort_mode.display_name(),
                    "files": undo_log[:],
                }
                self.undo_btn.configure(state="normal")
            else:
                self.undo_data = None
                self.undo_btn.configure(state="disabled")
            msg = f"✅ 整理完成！共整理 {fc} 个文件，用时 {et:.2f} 秒"
            self.status_label.configure(text=msg, text_color=("green", "#66BB6A"))
            self._show_info(msg)
        except Exception as e:
            msg = f"❌ 整理过程中出错：{str(e)}"
            self.status_label.configure(text=msg, text_color="red")
            self._show_error(msg)
        finally:
            self.sort_btn.configure(state="normal", text="🚀 开始整理")
            self.settings_btn.configure(state="normal")
            self.browse_btn.configure(state="normal")
            self.is_sorting = False

    # ----------------------------------------------------------
    # 拆除文件夹
    # ----------------------------------------------------------

    def _start_flatten(self):
        target = self.dir_entry.get().strip()
        if not target:
            return self._show_warning("请先选择要整理的目录！")
        if not os.path.exists(target):
            return self._show_error(f"目录不存在：{target}")
        if not self._ask_yesno(f"确定要拆除目录下所有子文件夹吗？\n\n目标目录：{target}\n\n所有子文件夹中的文件将被移动到根目录，空文件夹将被删除。"):
            return

        self.sort_btn.configure(state="disabled", text="⏳ 整理中...")
        self.settings_btn.configure(state="disabled")
        self.browse_btn.configure(state="disabled")
        self.flatten_btn.configure(state="disabled", text="⏳ 拆除中...")
        self.is_sorting = True
        self.progress_bar.set(0)

        try:
            def us(m): self.status_label.configure(text=m)
            def up(v): self.progress_bar.set(v); self.update_idletasks()
            fc, et = flatten_directory(target, us, up, self.EXCLUDE_RULES)
            # 刷新预览
            self._auto_preview()
            self.progress_bar.set(1)
            if fc > 0:
                msg = f"✅ 拆除完成！共移动 {fc} 个文件到根目录，用时 {et:.2f} 秒"
                self.status_label.configure(text=msg, text_color=("green", "#66BB6A"))
                self._show_info(msg)
            else:
                msg = "📭 没有需要拆除的子文件夹或文件"
                self.status_label.configure(text=msg)
        except Exception as e:
            msg = f"❌ 拆除过程中出错：{str(e)}"
            self.status_label.configure(text=msg, text_color="red")
            self._show_error(msg)
        finally:
            self.sort_btn.configure(state="normal", text="🚀 开始整理")
            self.settings_btn.configure(state="normal")
            self.browse_btn.configure(state="normal")
            self.flatten_btn.configure(state="normal", text="📂 拆除文件夹")
            self.is_sorting = False

    # ----------------------------------------------------------
    # 撤销整理
    # ----------------------------------------------------------

    def _undo_last_sort(self):
        if not self.undo_data or not self.undo_data.get("files"):
            return self._show_warning("没有可撤销的整理记录！")
        target = self.undo_data["target_dir"]
        count = len(self.undo_data["files"])
        if not self._ask_yesno(f"确定要撤销上次整理吗？\n\n目标目录：{target}\n分类方式：{self.undo_data['sort_mode']}\n涉及文件：{count} 个\n\n文件将恢复到整理前的位置。"):
            return

        self.undo_btn.configure(state="disabled", text="⏳ 撤销中...")
        self.sort_btn.configure(state="disabled")
        self.settings_btn.configure(state="disabled")
        self.browse_btn.configure(state="disabled")
        self.report_btn.configure(state="disabled")
        self.is_sorting = True
        self.progress_bar.set(0)

        try:
            total = len(self.undo_data["files"])
            self.status_label.configure(text=f"⏳ 正在撤销整理（共 {total} 个文件）...")
            self.update_idletasks()

            restored, errors = 0, 0
            for i, (orig_path, sorted_path) in enumerate(self.undo_data["files"]):
                # 更新状态
                self.status_label.configure(text=f"⏳ 正在恢复: {os.path.basename(sorted_path)} ({i+1}/{total})")
                self.progress_bar.set((i + 1) / total)
                self.update_idletasks()

                # 如果文件还在分类目录中，则移回原位置
                if os.path.exists(sorted_path):
                    # 确保原目录存在
                    orig_dir = os.path.dirname(orig_path)
                    if not os.path.exists(orig_dir):
                        try:
                            os.makedirs(orig_dir, exist_ok=True)
                        except:
                            pass
                    # 如果目标位置已有同名文件，重命名
                    if os.path.exists(orig_path):
                        name_only, ext = os.path.splitext(os.path.basename(orig_path))
                        counter = 1
                        while True:
                            new_name = f"{name_only}(还原){counter}{ext}"
                            alt_path = os.path.join(orig_dir, new_name)
                            if not os.path.exists(alt_path):
                                orig_path = alt_path
                                break
                            counter += 1
                    try:
                        shutil.move(sorted_path, orig_path)
                        restored += 1
                    except Exception:
                        errors += 1
                else:
                    errors += 1

            # 清理空的分类文件夹
            if os.path.exists(target):
                for entry in os.listdir(target):
                    entry_path = os.path.join(target, entry)
                    if os.path.isdir(entry_path):
                        try:
                            if not os.listdir(entry_path):
                                os.rmdir(entry_path)
                        except:
                            pass

            self.undo_data = None
            self.progress_bar.set(1)
            msg = f"✅ 撤销完成！成功恢复 {restored} 个文件" + (f"，{errors} 个失败" if errors else "")
            self.status_label.configure(text=msg, text_color=("green", "#66BB6A"))
            # 重新预览
            self._auto_preview()
            self._show_info(msg)
        except Exception as e:
            msg = f"❌ 撤销过程中出错：{str(e)}"
            self.status_label.configure(text=msg, text_color="red")
            self._show_error(msg)
        finally:
            self.undo_btn.configure(state="disabled", text="↩️ 撤销整理")
            self.sort_btn.configure(state="normal")
            self.settings_btn.configure(state="normal")
            self.browse_btn.configure(state="normal")
            self.is_sorting = False

    # ----------------------------------------------------------
    # 排除规则设置窗口
    # ----------------------------------------------------------

    def _open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("⚙️ 排除规则设置")
        win.geometry("580x520")
        win.minsize(520, 460)
        win.resizable(True, True)
        win.transient(self)
        win.grab_set()

        self._label(win, "⚙️ 排除规则设置", font_size=16).pack(pady=(15, 5))
        ctk.CTkLabel(win, text="以下项目将不会被整理", font=ctk.CTkFont(size=12), text_color=("gray50", "gray60")).pack()
        ctk.CTkLabel(win, text="后缀如 .exe  |  文件名如 readme  |  文件夹路径如 D:\\backup", font=ctk.CTkFont(size=11), text_color=("gray40", "gray50")).pack()

        # 输入区域
        inp = ctk.CTkFrame(win)
        inp.pack(fill="x", padx=20, pady=(10, 5))
        inp.grid_columnconfigure(0, weight=1)
        self._label(inp, "✏️ 手动输入排除规则（用逗号分隔）").grid(row=0, column=0, columnspan=3, padx=10, pady=(8, 5), sticky="w")
        entry = ctk.CTkEntry(inp, font=ctk.CTkFont(size=12), height=35)
        entry.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 5))
        entry.insert(0, ",".join(self.EXCLUDE_RULES))

        # 操作按钮
        af = ctk.CTkFrame(inp, fg_color="transparent")
        af.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 8))
        af.grid_columnconfigure((0, 1), weight=1)

        def add_from_entry(event=None):
            items = [x.strip() for x in entry.get().split(",") if x.strip()]
            if items:
                s = set(self.EXCLUDE_RULES)
                s.update(items)
                self.EXCLUDE_RULES = sorted(s, key=lambda x: (not x.startswith("."), x))
                save_exclude_rules(self.EXCLUDE_RULES)
                entry.delete(0, "end")
                entry.insert(0, ",".join(self.EXCLUDE_RULES))
                _refresh()
                self._auto_preview()

        entry.bind("<Return>", add_from_entry)

        def _browse(is_file):
            target = self.dir_entry.get().strip()
            if not target or not os.path.exists(target):
                return self._show_warning("请先选择有效的目标目录！")
            ta = os.path.abspath(target).lower().replace('\\', '/')
            sel = filedialog.askopenfilename(title="选择要排除的文件", initialdir=target, filetypes=[("所有文件", "*.*")]) if is_file else filedialog.askdirectory(title="选择要排除的文件夹", initialdir=target)
            if sel:
                sa = os.path.abspath(sel).lower().replace('\\', '/')
                if not (sa.startswith(ta + '/') or sa == ta):
                    return self._show_warning(f"只能选择目标目录内的{'文件' if is_file else '文件夹'}！\n目标目录：{target}")
                if sel not in self.EXCLUDE_RULES:
                    self.EXCLUDE_RULES.append(sel)
                    save_exclude_rules(self.EXCLUDE_RULES)
                    entry.delete(0, "end")
                    entry.insert(0, ",".join(self.EXCLUDE_RULES))
                    _refresh()
                    self._auto_preview()

        self._btn(af, "📄 选择文件", command=lambda: _browse(True), fg_color=("#2196F3", "#1565C0"), hover_color=("#1976D2", "#0D47A1")).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self._btn(af, "📁 选择文件夹", command=lambda: _browse(False), fg_color=("#4CAF50", "#2E7D32"), hover_color=("#388E3C", "#1B5E20")).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        # 排除项列表
        ls = ctk.CTkFrame(win)
        ls.pack(fill="both", padx=20, pady=(5, 10), expand=True)
        ls.grid_columnconfigure(0, weight=1)
        ls.grid_rowconfigure(1, weight=1)

        lh = ctk.CTkFrame(ls, fg_color="transparent")
        lh.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 5))
        lh.grid_columnconfigure(0, weight=1)
        self._label(lh, "📋 当前排除项（可多选）").grid(row=0, column=0, sticky="w")

        del_btn = ctk.CTkButton(lh, text="🗑️ 删除选中", font=ctk.CTkFont(size=12), height=30, width=100, corner_radius=6, fg_color="#666666", hover_color="#555555", state="disabled")
        del_btn.grid(row=0, column=1, padx=(5, 0))

        is_dark = ctk.get_appearance_mode() == "Dark"
        lb = tk.Listbox(ls, selectmode=tk.EXTENDED, font=("Microsoft YaHei", 11), bg="#2b2b2b" if is_dark else "#ffffff", fg="#ffffff" if is_dark else "#000000", selectbackground="#0078D7", selectforeground="white", relief="flat", highlightthickness=0, borderwidth=0)
        lb.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))

        def _refresh():
            lb.delete(0, tk.END)
            for r in self.EXCLUDE_RULES:
                lb.insert(tk.END, f"  {r}")
            _update_del_btn()

        def _update_del_btn():
            if lb.curselection():
                del_btn.configure(state="normal", fg_color=("#E53935", "#C62828"), hover_color=("#C62828", "#B71C1C"))
            else:
                del_btn.configure(state="disabled", fg_color="#666666", hover_color="#555555")

        lb.bind("<<ListboxSelect>>", lambda e: _update_del_btn())

        def _delete():
            idxs = lb.curselection()
            if not idxs:
                return
            for r in [self.EXCLUDE_RULES[i] for i in idxs]:
                self.EXCLUDE_RULES.remove(r)
            save_exclude_rules(self.EXCLUDE_RULES)
            entry.delete(0, "end")
            entry.insert(0, ",".join(self.EXCLUDE_RULES))
            _refresh()
            self._auto_preview()

        del_btn.configure(command=_delete)
        _refresh()

    # ----------------------------------------------------------
    # 文件搜索功能
    # ----------------------------------------------------------

    def _on_search_key_release(self, event):
        if self.search_timer is not None:
            self.after_cancel(self.search_timer)
            self.search_timer = None
        if not self.search_entry.get().strip():
            self.search_listbox.delete(0, tk.END)
            self.search_result_label.configure(text="")

    def _on_search_enter(self, event):
        self._start_search_thread()

    def _start_search_thread(self):
        q = self.search_entry.get().strip()
        if not q or self.is_searching:
            return
        target = self.dir_entry.get().strip()
        if not target or not os.path.exists(target):
            return self._show_warning("请先选择有效的目标目录！")
        self.is_searching = True
        self.search_btn.configure(state="disabled", text="⏳ 搜索中...")
        self.search_result_label.configure(text="⏳ 正在搜索...")
        threading.Thread(target=self._do_search, args=(target, q), daemon=True).start()

    def _do_search(self, target_dir, query):
        try:
            results = FileSearcher.search(target_dir, query, max_results=500, exclude_dirs=None)
            self.after(0, self._on_search_complete, results, None)
        except Exception as e:
            self.after(0, self._on_search_complete, [], str(e))

    def _on_search_complete(self, results, error):
        self.is_searching = False
        self.search_btn.configure(state="normal", text="🔍 搜索")
        if error:
            self.search_result_label.configure(text=f"❌ 搜索出错：{error}", text_color="red")
            return
        self.search_results = results
        self.search_listbox.delete(0, tk.END)
        if not results:
            self.search_result_label.configure(text="🔍 未找到匹配的文件或文件夹", text_color=("gray50", "gray60"))
            return
        fc = dc = 0
        for entry in results[:300]:
            if entry["type"] == "dir":
                dc += 1
                self.search_listbox.insert(tk.END, f"  📁  {entry['path']}")
            else:
                fc += 1
                self.search_listbox.insert(tk.END, f"  📄  {entry['path']}  ({self._format_size(entry['size'])})")
        total = len(results)
        parts = [f"{fc} 个文件" if fc else "", f"{dc} 个文件夹" if dc else ""]
        summary = "、".join(p for p in parts if p)
        self.search_result_label.configure(text=f"🔍 找到 {total} 个结果（{summary}）{'（仅显示前300个）' if total > 300 else ''}", text_color=("#7B1FA2", "#CE93D8"))

    @staticmethod
    def _format_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / 1024 / 1024:.1f}MB"
        else:
            return f"{size_bytes / 1024 / 1024 / 1024:.2f}GB"

    def _on_search_right_click(self, event):
        try:
            idx = self.search_listbox.nearest(event.y)
            self.search_listbox.selection_clear(0, tk.END)
            self.search_listbox.selection_set(idx)
            self.search_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.search_context_menu.grab_release()

    def _open_selected_file_location(self):
        sel = self.search_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self.search_results):
            entry = self.search_results[idx]
            try:
                os.startfile(entry["path"] if entry["type"] == "dir" else os.path.dirname(entry["path"]))
            except:
                pass

    def _copy_selected_file_path(self):
        sel = self.search_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self.search_results):
            path = self.search_results[idx]["path"]
            try:
                self.clipboard_clear()
                self.clipboard_append(path)
                self._show_info(f"已复制路径：\n{path}")
            except:
                pass

    # ----------------------------------------------------------
    # 整理报告查看
    # ----------------------------------------------------------

    def _show_sort_report(self):
        if not self.last_sort_report:
            return self._show_warning("暂无整理报告，请先执行一次整理操作！")
        r = self.last_sort_report
        win = ctk.CTkToplevel(self)
        win.title("📊 整理报告")
        win.geometry("560x500")
        win.minsize(500, 400)
        win.resizable(True, True)
        win.transient(self)
        win.grab_set()

        # 标题
        title_f = ctk.CTkFrame(win, corner_radius=0, height=50)
        title_f.pack(fill="x", padx=0, pady=(0, 10))
        ctk.CTkLabel(title_f, text="📊 文件整理报告", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(12, 5))

        # 概要信息
        summary_f = ctk.CTkFrame(win)
        summary_f.pack(fill="x", padx=20, pady=(0, 10))
        items = [
            ("🕐 整理时间", r["time"]),
            ("🏷️ 分类方式", r["mode"]),
            ("📂 目标目录", r["target_dir"]),
            ("📦 移动文件数", f"{r['total_moved']} 个"),
            ("⏱️ 总用时", f"{r['elapsed']} 秒"),
        ]
        for i, (label, value) in enumerate(items):
            row_f = ctk.CTkFrame(summary_f, fg_color="transparent")
            row_f.pack(fill="x", padx=15, pady=3)
            ctk.CTkLabel(row_f, text=label, font=ctk.CTkFont(size=13, weight="bold"), width=110, anchor="w").pack(side="left")
            ctk.CTkLabel(row_f, text=str(value), font=ctk.CTkFont(size=13), anchor="w").pack(side="left", padx=(5, 0))

        # 分类详情标题
        ctk.CTkLabel(summary_f, text="", height=2).pack(fill="x")
        ctk.CTkLabel(summary_f, text="📋 各分类文件数", font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(padx=15, pady=(5, 5), anchor="w")

        # 分类详情列表
        detail_f = ctk.CTkFrame(win)
        detail_f.pack(fill="both", padx=20, pady=(0, 15), expand=True)

        is_dark = ctk.get_appearance_mode() == "Dark"
        text_widget = tk.Text(detail_f, font=("Consolas", 12), bg="#2b2b2b" if is_dark else "#ffffff",
                              fg="#ffffff" if is_dark else "#000000", relief="flat", highlightthickness=0,
                              borderwidth=0, padx=10, pady=10, spacing1=4, height=10)
        text_widget.pack(fill="both", expand=True, side="left")

        sb = ttk.Scrollbar(detail_f, orient="vertical", command=text_widget.yview)
        sb.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=sb.set)
        text_widget.tag_configure("header", font=("Consolas", 12, "bold"))
        text_widget.tag_configure("number", font=("Consolas", 12))
        text_widget.tag_configure("total", font=("Consolas", 12, "bold"))

        text_widget.insert("end", f"{'📁 分类名称':<20}{'文件数量':>8}\n", "header")
        text_widget.insert("end", f"{'─'*30}\n")
        for cat, cnt in r["category_details"].items():
            text_widget.insert("end", f"{cat:<20}{cnt:>8}\n", "number")
        text_widget.insert("end", f"{'─'*30}\n", "number")
        text_widget.insert("end", f"{'合计':<20}{r['total_moved']:>8}\n", "total")
        text_widget.configure(state="disabled")

        # 关闭按钮
        close_btn = self._btn(win, "关闭", font_size=13, command=win.destroy,
                              fg_color=("#666666", "#555555"), hover_color=("#555555", "#444444"))
        close_btn.pack(pady=(0, 15))

    # ----------------------------------------------------------
    # 历史记录
    # ----------------------------------------------------------

    def _update_history_display(self):
        h = load_history()
        if h["total_runs"] > 0:
            text = f"📜 历史记录：共整理 {h['total_runs']} 次，累计 {h['total_count']} 个文件，上次整理 {h['last_count']} 个文件，用时 {h['last_time']} 秒"
        else:
            text = "📜 历史记录：暂无"
        self.history_label.configure(text=text)

    # ----------------------------------------------------------
    # 对话框辅助方法
    # ----------------------------------------------------------

    def _show_warning(self, msg): mb.showwarning("警告", msg)
    def _show_error(self, msg): mb.showerror("错误", msg)
    def _show_info(self, msg): mb.showinfo("信息", msg)
    def _ask_yesno(self, q): return mb.askyesno("确认", q)


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":
    app = FileSorterApp()
    app.mainloop()
