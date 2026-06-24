"""
Portrait Background Remover — 人像抠图工具
依赖: pip install rembg pillow onnxruntime
运行: python portrait_bg_remover.py
"""

import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
import threading
import os
from pathlib import Path

from PIL import Image, ImageTk, ImageDraw

from everalbum.services.portrait_assets import PortraitAssetStore
from everalbum.services.portrait_removal import get_portrait_removal_service
from everalbum.services.workspace import get_default_portrait_library_path

PORTRAIT_SERVICE = get_portrait_removal_service()

def _load_model_bg(callback):
    """在后台线程加载 rembg，完成后调用 callback"""
    try:
        PORTRAIT_SERVICE.ensure_ready()
        callback(True, "")
    except Exception as e:
        callback(False, str(e))


# ══════════════════════════════════════════════
#  背景配置
# ══════════════════════════════════════════════
SOLID_BG = {
    "透明 PNG":                None,
    "哑光黑  Matte Black":     "#0D0D0D",
    "深空灰  Space Gray":      "#1C1C1E",
    "冰川白  Glacier White":   "#F5F5F0",
    "奶油米  Cream Ivory":     "#F2ECD8",
    "薄雾蓝  Misty Blue":      "#C5D5E8",
    "玫瑰金  Rose Gold":       "#E8C4B8",
    "墨绿色  Deep Forest":     "#1A3A2A",
    "暗金棕  Cognac":          "#3D2314",
    "紫夜色  Midnight Violet": "#1A0A2E",
    "自定义颜色 ＋":           "custom",
}

GRAD_BG = {
    "极光渐变  Aurora":     [(15,32,39),(32,58,67),(44,83,100)],
    "暮色渐变  Dusk":       [(255,94,77),(255,154,0)],
    "深海渐变  Deep Ocean": [(2,0,36),(9,9,121),(0,212,255)],
    "炭墨渐变  Charcoal":   [(30,30,30),(60,60,60)],
    "香槟渐变  Champagne":  [(247,238,215),(212,190,152)],
}

# 颜色主题
BG    = "#F4F3F0"
PANEL = "#FFFFFF"
BORD  = "#DDDBD6"
TITLE = "#1A1A1A"
SUB   = "#888888"
TEXT  = "#333333"
MUTED = "#AAAAAA"
ACC   = "#222222"
ACC_F = "#FFFFFF"
BTN2  = "#EEECEA"
BTN2F = "#333333"
PREV  = "#E8E7E4"
SEL   = "#F5F3EE"


# ══════════════════════════════════════════════
#  图像工具
# ══════════════════════════════════════════════
def make_gradient(w, h, colors):
    img  = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    steps = len(colors) - 1
    for s in range(steps):
        c1, c2 = colors[s], colors[s+1]
        y0 = int(h * s / steps)
        y1 = int(h * (s+1) / steps)
        for y in range(y0, y1):
            t = (y-y0) / max(y1-y0, 1)
            r = int(c1[0]+(c2[0]-c1[0])*t)
            g = int(c1[1]+(c2[1]-c1[1])*t)
            b = int(c1[2]+(c2[2]-c1[2])*t)
            draw.line([(0,y),(w,y)], fill=(r,g,b))
    return img


def make_checker(w, h, tile=14):
    img  = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    c1, c2 = (210,210,205), (190,190,185)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            draw.rectangle([x,y,x+tile,y+tile],
                           fill=(c1 if (x//tile+y//tile)%2==0 else c2))
    return img


def compose(fg: Image.Image, bg_name: str, custom_hex: str) -> Image.Image:
    if bg_name == "透明 PNG":
        return fg.copy()
    w, h = fg.size
    if bg_name in GRAD_BG:
        bg = make_gradient(w, h, GRAD_BG[bg_name]).convert("RGBA")
    elif bg_name == "自定义颜色 ＋":
        bg = Image.new("RGBA", (w, h), custom_hex)
    elif bg_name in SOLID_BG and SOLID_BG[bg_name]:
        bg = Image.new("RGBA", (w, h), SOLID_BG[bg_name])
    else:
        return fg.copy()
    return Image.alpha_composite(bg, fg)


def render_for_display(img: Image.Image, max_w: int, max_h: int,
                       use_checker: bool) -> Image.Image:
    ratio = min(max_w / max(img.width,1), max_h / max(img.height,1))
    nw = max(int(img.width*ratio), 1)
    nh = max(int(img.height*ratio), 1)
    thumb = img.resize((nw, nh), Image.LANCZOS)
    if thumb.mode != "RGBA":
        return thumb.convert("RGB")
    base = make_checker(nw,nh) if use_checker else Image.new("RGB",(nw,nh),"#FFF")
    base.paste(thumb, (0,0), thumb)
    return base


# ══════════════════════════════════════════════
#  PreviewCanvas
# ══════════════════════════════════════════════
class PreviewCanvas(tk.Canvas):
    def __init__(self, master, **kw):
        kw.setdefault("bg", PREV)
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("highlightbackground", BORD)
        super().__init__(master, **kw)
        self._photo   = None
        self._pending = None
        self._hint    = ""
        self.bind("<Configure>", self._on_resize)

    def set_hint(self, text):
        self._hint  = text
        self._photo = None
        self._pending = None
        self.after(10, self._draw)

    def set_image(self, img: Image.Image, checker=False):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 4 or h < 4:
            self._pending = (img, checker)
            self.after(60, self._flush)
            return
        self._pending = None
        rgb = render_for_display(img, w-4, h-4, checker)
        self._photo = ImageTk.PhotoImage(rgb)
        self._hint  = ""
        self._draw()

    def _flush(self):
        if self._pending:
            self.set_image(*self._pending)

    def _on_resize(self, e):
        if self._pending:
            self._flush()
        else:
            self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()  or 400
        h = self.winfo_height() or 400
        if self._photo:
            self.create_image(w//2, h//2, anchor="center", image=self._photo)
        elif self._hint:
            self.create_text(w//2, h//2, text=self._hint,
                             fill=MUTED, font=("Microsoft YaHei",10),
                             justify="center")


# ══════════════════════════════════════════════
#  启动加载画面
# ══════════════════════════════════════════════
class SplashScreen(tk.Toplevel):
    """程序启动时显示的加载窗口"""
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)   # 无边框
        self.configure(bg=PANEL)
        self.resizable(False, False)

        W, H = 360, 200
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        # 边框感：外层 Frame
        outer = tk.Frame(self, bg=BORD, padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg=PANEL)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text="人像抠图工具",
                 font=("Microsoft YaHei",16,"bold"),
                 fg=TITLE, bg=PANEL).pack(pady=(30,4))
        tk.Label(inner, text="Portrait Background Remover",
                 font=("Georgia",9,"italic"),
                 fg=MUTED, bg=PANEL).pack()

        self.lbl_status = tk.Label(inner, text="正在加载 AI 模型，请稍候…",
                                   font=("Microsoft YaHei",9),
                                   fg=SUB, bg=PANEL)
        self.lbl_status.pack(pady=(20,8))

        # 进度条
        self.bar_bg  = tk.Canvas(inner, bg="#EBEBEA", height=4,
                                  highlightthickness=0, width=280)
        self.bar_bg.pack()
        self._bx = 0
        self._bar_tick()

    def _bar_tick(self):
        if not self.winfo_exists():
            return
        w   = 280
        seg = 90
        self._bx = (self._bx + 4) % (w + seg)
        self.bar_bg.delete("all")
        self.bar_bg.create_rectangle(0,0,w,4, fill="#EBEBEA", outline="")
        self.bar_bg.create_rectangle(self._bx-seg,0,self._bx,4,
                                     fill=ACC, outline="")
        self.after(20, self._bar_tick)

    def set_status(self, text):
        if self.winfo_exists():
            self.lbl_status.config(text=text)


# ══════════════════════════════════════════════
#  主应用
# ══════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()   # 先隐藏主窗口

        self.title("人像抠图工具  Portrait BG Remover")
        self.geometry("1120x700")
        self.minsize(900,580)
        self.configure(bg=BG)
        self.resizable(True, True)

        self.source_path  = None
        self.source_image = None
        self.result_image = None
        self.custom_hex   = "#FFFFFF"
        self.sel_bg       = tk.StringVar(value="透明 PNG")
        self.processing   = False
        self._prog_job    = None
        self._prog_x      = 0
        self._resize_job  = None
        self.asset_store  = PortraitAssetStore(get_default_portrait_library_path())

        self._build_ui()

        # 显示启动画面，后台加载模型
        self._splash = SplashScreen(self)
        self._splash.lift()
        threading.Thread(target=_load_model_bg,
                         args=(self._on_model_loaded,),
                         daemon=True).start()

    def _on_model_loaded(self, ok, err):
        """模型加载完成回调（后台线程调用，用 after 回主线程）"""
        self.after(0, lambda: self._show_main(ok, err))

    def _show_main(self, ok, err):
        if hasattr(self, "_splash") and self._splash.winfo_exists():
            self._splash.destroy()
        if ok:
            self.deiconify()   # 显示主窗口
            self.lift()
        else:
            messagebox.showerror("加载失败",
                f"AI 模型加载失败：\n{err}\n\n"
                "请确认已安装：pip install rembg onnxruntime")
            self.destroy()

    # ──────────────────────────────────────────
    #  UI 构建
    # ──────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=28, pady=(16,0))
        tk.Label(hdr, text="人像抠图工具",
                 font=("Microsoft YaHei",18,"bold"),
                 fg=TITLE, bg=BG).pack(side="left")
        tk.Label(hdr, text="Portrait Background Remover",
                 font=("Georgia",10,"italic"),
                 fg=MUTED, bg=BG).pack(side="left", padx=10)
        tk.Frame(self, bg=BORD, height=1).pack(fill="x", padx=28, pady=(10,0))

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=12)
        self._build_sidebar(body)
        self._build_preview(body)

    # ── 侧栏 ──────────────────────────────────
    def _build_sidebar(self, parent):
        wrap = tk.Frame(parent, bg=PANEL,
                        highlightthickness=1, highlightbackground=BORD,
                        width=268)
        wrap.pack(side="left", fill="y", padx=(0,12))
        wrap.pack_propagate(False)

        sb = tk.Scrollbar(wrap, orient="vertical")
        sb.pack(side="right", fill="y")
        cv = tk.Canvas(wrap, bg=PANEL, highlightthickness=0,
                       yscrollcommand=sb.set, bd=0)
        cv.pack(side="left", fill="both", expand=True)
        sb.config(command=cv.yview)

        inner = tk.Frame(cv, bg=PANEL)
        wid   = cv.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.config(
            scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfig(wid, width=e.width))
        cv.bind_all("<MouseWheel>",
                    lambda e: cv.yview_scroll(int(-e.delta/120), "units"))

        self._sidebar_content(inner)

    def _sidebar_content(self, f):
        self._sec(f, "① 选择图片")
        self.lbl_file = tk.Label(f, text="未选择文件",
                                  font=("Microsoft YaHei",9),
                                  fg=MUTED, bg=PANEL,
                                  wraplength=215, justify="left")
        self.lbl_file.pack(anchor="w", padx=16, pady=(2,4))
        self._abtn(f, "📂  打开图片", self._pick_file).pack(
            fill="x", padx=16, pady=(2,10))
        self._hr(f)

        self._sec(f, "② 选择背景")
        tk.Label(f, text="纯色背景", font=("Microsoft YaHei",9,"bold"),
                 fg=SUB, bg=PANEL).pack(anchor="w", padx=16, pady=(4,1))
        for n in SOLID_BG:
            self._rb(f, n)

        self.swatch = tk.Label(f, bg=self.custom_hex,
                               width=4, height=1, relief="flat", bd=0)
        self.swatch.pack(anchor="w", padx=36, pady=(0,4))

        tk.Label(f, text="渐变背景", font=("Microsoft YaHei",9,"bold"),
                 fg=SUB, bg=PANEL).pack(anchor="w", padx=16, pady=(4,1))
        for n in GRAD_BG:
            self._rb(f, n)
        self._hr(f)

        self._sec(f, "③ 开始处理")
        self.btn_go   = self._abtn(f, "✂  开始抠图", self._run)
        self.btn_go.pack(fill="x", padx=16, pady=(4,5))

        self.btn_save = self._pbtn(f, "💾  保存图片", self._save)
        self.btn_save.pack(fill="x", padx=16, pady=(0,5))
        self.btn_save.config(state="disabled")

        self.btn_library = self._pbtn(f, "🧩  保存到相册素材库", self._save_to_library)
        self.btn_library.pack(fill="x", padx=16, pady=(0,5))
        self.btn_library.config(state="disabled")

        tk.Label(
            f,
            text=f"素材库目录：{self.asset_store.root_dir}",
            font=("Microsoft YaHei", 8),
            fg=MUTED,
            bg=PANEL,
            wraplength=215,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 4))

        self.var_st = tk.StringVar(value="就绪 · 请选择图片")
        tk.Label(f, textvariable=self.var_st,
                 font=("Microsoft YaHei",8), fg=MUTED, bg=PANEL
                 ).pack(anchor="w", padx=16, pady=(4,2))

        self.prog = tk.Canvas(f, bg=PANEL, height=5, highlightthickness=0)
        self.prog.pack(fill="x", padx=16, pady=(0,20))

    # ── 预览区 ────────────────────────────────
    def _build_preview(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        lrow = tk.Frame(right, bg=BG)
        lrow.pack(fill="x", pady=(0,5))
        tk.Label(lrow, text="原图预览", font=("Microsoft YaHei",9),
                 fg=SUB, bg=BG).pack(side="left")
        tk.Label(lrow, text="抠图结果", font=("Microsoft YaHei",9),
                 fg=SUB, bg=BG).pack(side="right")

        prow = tk.Frame(right, bg=BG)
        prow.pack(fill="both", expand=True)

        self.cv_orig = PreviewCanvas(prow)
        self.cv_orig.pack(side="left", fill="both", expand=True, padx=(0,6))
        self.cv_orig.set_hint("原图\n（选择图片后显示）")

        self.cv_res  = PreviewCanvas(prow)
        self.cv_res.pack(side="left", fill="both", expand=True, padx=(6,0))
        self.cv_res.set_hint("抠图结果\n（点击「开始抠图」后显示）")

        self.cv_res.bind("<Configure>", self._on_res_resize)

    # ──────────────────────────────────────────
    #  小组件
    # ──────────────────────────────────────────
    def _sec(self, p, t):
        tk.Label(p, text=t, font=("Microsoft YaHei",11,"bold"),
                 fg=TITLE, bg=PANEL).pack(anchor="w", padx=16, pady=(14,2))

    def _hr(self, p):
        tk.Frame(p, bg=BORD, height=1).pack(fill="x", padx=12, pady=6)

    def _abtn(self, p, t, cmd):
        return tk.Button(p, text=t, command=cmd,
                         bg=ACC, fg=ACC_F, relief="flat",
                         font=("Microsoft YaHei",10,"bold"), pady=9,
                         cursor="hand2", bd=0,
                         activebackground="#444", activeforeground="#FFF")

    def _pbtn(self, p, t, cmd):
        return tk.Button(p, text=t, command=cmd,
                         bg=BTN2, fg=BTN2F, relief="flat",
                         font=("Microsoft YaHei",10), pady=9,
                         cursor="hand2", bd=0,
                         activebackground="#DDDBD6", activeforeground="#111")

    def _rb(self, p, name):
        tk.Radiobutton(p, text=name, variable=self.sel_bg, value=name,
                       font=("Microsoft YaHei",9),
                       fg=TEXT, bg=PANEL, selectcolor=SEL,
                       activebackground=PANEL, activeforeground=TITLE,
                       cursor="hand2", command=self._bg_changed
                       ).pack(anchor="w", padx=16, pady=1)

    # ──────────────────────────────────────────
    #  进度条
    # ──────────────────────────────────────────
    def _prog_start(self):
        if self._prog_job:
            self.after_cancel(self._prog_job)
        self._prog_x = 0
        self._prog_tick()

    def _prog_tick(self):
        if not self.processing:
            w = self.prog.winfo_width() or 220
            self.prog.delete("all")
            self.prog.create_rectangle(0,0,w,5, fill="#4CAF50", outline="")
            return
        w   = self.prog.winfo_width() or 220
        seg = max(int(w*0.35), 40)
        self._prog_x = (self._prog_x+4) % (w+seg)
        self.prog.delete("all")
        self.prog.create_rectangle(0,0,w,5, fill=BORD, outline="")
        self.prog.create_rectangle(self._prog_x-seg,0,self._prog_x,5,
                                   fill=ACC, outline="")
        self._prog_job = self.after(22, self._prog_tick)

    # ──────────────────────────────────────────
    #  事件
    # ──────────────────────────────────────────
    def _pick_file(self):
        p = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件","*.jpg *.jpeg *.png *.webp *.bmp"),
                       ("所有文件","*.*")])
        if not p:
            return
        self.source_path = p
        self.lbl_file.config(text=os.path.basename(p), fg=TEXT)
        self.var_st.set("已选择图片，点击「开始抠图」")
        try:
            self.source_image = Image.open(p).convert("RGBA")
            self.after(100, lambda: self.cv_orig.set_image(
                self.source_image, checker=False))
        except Exception as e:
            messagebox.showerror("读取失败", str(e))

    def _bg_changed(self):
        name = self.sel_bg.get()
        if name == "自定义颜色 ＋":
            res = colorchooser.askcolor(color=self.custom_hex,
                                        title="选择自定义颜色")
            if res[1]:
                self.custom_hex = res[1]
                self.swatch.config(bg=self.custom_hex)
        if self.result_image:
            self._show_result()

    def _run(self):
        if not self.source_path:
            messagebox.showwarning("提示", "请先选择一张图片")
            return
        if self.processing:
            return
        self.processing = True
        self.btn_go.config(state="disabled", text="处理中…")
        self.btn_save.config(state="disabled")
        self.btn_library.config(state="disabled")
        self.var_st.set("AI 正在抠图，请稍候…")
        self._prog_start()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            with Image.open(self.source_path) as source:
                img = PORTRAIT_SERVICE.remove_image(source.convert("RGBA"))
            self.after(0, lambda: self._done(img))
        except Exception as e:
            self.after(0, lambda: self._fail(str(e)))

    def _done(self, img):
        self.result_image = img
        self.processing   = False
        self.btn_go.config(state="normal", text="✂  重新抠图")
        self.btn_save.config(state="normal")
        self.btn_library.config(state="normal")
        self.var_st.set("抠图完成 ✓  可更换背景后保存")
        self._show_result()

    def _fail(self, err):
        self.processing = False
        self.btn_go.config(state="normal", text="✂  开始抠图")
        self.var_st.set("处理失败")
        messagebox.showerror("处理失败", f"抠图时出错：\n{err}")

    def _show_result(self):
        if not self.result_image:
            return
        bg_name  = self.sel_bg.get()
        composed = compose(self.result_image, bg_name, self.custom_hex)
        self.cv_res.set_image(composed, checker=(bg_name=="透明 PNG"))

    def _on_res_resize(self, e):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(100, self._show_result)

    # ──────────────────────────────────────────
    #  保存
    # ──────────────────────────────────────────
    def _save(self):
        if not self.result_image:
            messagebox.showwarning("提示", "没有可保存的结果")
            return
        bg_name = self.sel_bg.get()
        ftypes  = [("PNG 图片","*.png")]
        if bg_name != "透明 PNG":
            ftypes.append(("JPEG 图片","*.jpg *.jpeg"))

        sp = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=ftypes, title="保存图片")
        if not sp:
            return

        out = compose(self.result_image, bg_name, self.custom_hex)
        if sp.lower().endswith((".jpg",".jpeg")):
            out.convert("RGB").save(sp, "JPEG", quality=95)
        else:
            out.save(sp, "PNG")

        self.var_st.set(f"已保存 → {os.path.basename(sp)}")
        messagebox.showinfo("保存成功", f"图片已保存至：\n{sp}")

    def _save_to_library(self):
        if not self.result_image:
            messagebox.showwarning("提示", "没有可保存的抠图结果")
            return

        asset = self.asset_store.save_asset(
            self.result_image,
            source_path=self.source_path or "",
            name=Path(self.source_path).stem if self.source_path else "portrait",
        )
        self.var_st.set(f"已加入素材库 → {asset.name}")
        messagebox.showinfo(
            "已加入素材库",
            f"透明 PNG 已保存到素材库：\n{asset.path}\n\n现在主程序可以直接把它作为相册元素使用。",
        )


# ══════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
