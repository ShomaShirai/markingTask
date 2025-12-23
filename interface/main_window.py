import os
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
import random

from services.ui_actions import (
    browse_path,
    blend_and_get_image,
    resize_for_canvas,
    save_with_canvas,
    append_metrics_for_image,
)
from services.metrix_service import MetricsService
from domain.type import MIP_LINE_COLOR, VEIN_LINE_COLOR, LINE_WIDTH, Stroke
from services.user_service import set_current_user


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("3画像重畳マーキングタスク用ツール")
        self.geometry("1350x740")

        # ファイルパスの初期値（assetsがあれば推測）
        base_dir = os.path.dirname(os.path.abspath(__file__))
        proj_root = os.path.dirname(base_dir)
        assets_dir = os.path.join(proj_root, "assets")
        self.bg_path = (
            os.path.join(assets_dir, "woman.png") if os.path.isdir(assets_dir) else ""
        )
        self.mid_path = (
            os.path.join(assets_dir, "compositionMip.png")
            if os.path.isdir(assets_dir)
            else ""
        )
        self.fg_path = (
            os.path.join(assets_dir, "vein_white.png")
            if os.path.isdir(assets_dir)
            else ""
        )

        self.result_image = None  # PIL Image
        self.photo = None  # ImageTk.PhotoImage（参照保持用）
        self.canvas_img_id = None  # キャンバス上の画像アイテムID
        self.display_image = None  # 表示用にリサイズしたPIL画像
        self.rotation_angle = 0.0  # 現在の回転角度（度）
        self.rotation_step = 10.0  # 次へで回す角度ステップ（度）

        # 計測トラッカー（servicesへ委譲）
        self.metrics = MetricsService()

        # 描画状態
        self.current_draw_color = None
        self.last_xy = None
        self.drawn_items = []  # キャンバスに描いたラインIDの管理

        self._build_ui()
        self._prompt_username()

    def _build_ui(self):
        # メイン2ペイン（左: キャンバス / 右: コントロール）
        root = tk.Frame(self)
        root.pack(fill=tk.BOTH, expand=True)

        # 左ペイン: キャンバス
        left = tk.Frame(root)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(left, bg="#222222", width=960, height=700)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 右ペイン: コントロール群（固定幅）
        right = tk.Frame(root, width=320)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=8, pady=8)
        right.pack_propagate(False)  # 固定幅を保つ

        # ファイル選択（右ペイン内）
        top = tk.LabelFrame(right, text="入力ファイル")
        top.pack(fill=tk.X, pady=(0, 8))

        tk.Label(top, text="背景 (IR/基礎):").grid(row=0, column=0, sticky=tk.W)
        self.bg_var = tk.StringVar(value=self.bg_path)
        tk.Entry(top, textvariable=self.bg_var, width=28).grid(row=0, column=1, padx=4)
        tk.Button(top, text="参照", command=lambda: browse_path(self.bg_var)).grid(
            row=0, column=2
        )

        tk.Label(top, text="中間 (MIP):").grid(row=1, column=0, sticky=tk.W)
        self.mid_var = tk.StringVar(value=self.mid_path)
        tk.Entry(top, textvariable=self.mid_var, width=28).grid(row=1, column=1, padx=4)
        tk.Button(top, text="参照", command=lambda: browse_path(self.mid_var)).grid(
            row=1, column=2
        )

        tk.Label(top, text="前景 (血管マスク):").grid(row=2, column=0, sticky=tk.W)
        self.fg_var = tk.StringVar(value=self.fg_path)
        tk.Entry(top, textvariable=self.fg_var, width=28).grid(row=2, column=1, padx=4)
        tk.Button(top, text="参照", command=lambda: browse_path(self.fg_var)).grid(
            row=2, column=2
        )

        blendBtns = tk.Frame(right)
        blendBtns.pack(fill=tk.X, pady=8)
        tk.Button(blendBtns, text="重畳して表示", command=self._on_blend).pack(
            side=tk.LEFT
        )

        # パラメータ（右ペイン内）
        params_frame = tk.LabelFrame(right, text="ブレンドパラメータ")
        params_frame.pack(fill=tk.X)

        tk.Label(params_frame, text="alpha_mid").grid(row=0, column=0, sticky=tk.W)
        self.alpha_mid = tk.DoubleVar(value=0.3)
        tk.Scale(
            params_frame,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            variable=self.alpha_mid,
            length=100,
        ).grid(row=0, column=1, padx=4)

        tk.Label(params_frame, text="alpha_fg").grid(row=1, column=0, sticky=tk.W)
        self.alpha_fg = tk.DoubleVar(value=0.3)
        tk.Scale(
            params_frame,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            variable=self.alpha_fg,
            length=100,
        ).grid(row=1, column=1, padx=4)

        # 描画モードボタン（右ペイン内）
        draw_frame = tk.LabelFrame(right, text="描画モード")
        draw_frame.pack(fill=tk.X)
        self.btn_mip = tk.Button(draw_frame, text="MIP", command=self._set_mode_mip)
        self.btn_mip.pack(side=tk.LEFT, padx=4)
        self.btn_vein = tk.Button(
            draw_frame, text="血管抽出", command=self._set_mode_vein
        )
        self.btn_vein.pack(side=tk.LEFT, padx=4)
        self.btn_clear = tk.Button(draw_frame, text="クリア", command=self._on_clear)
        self.btn_clear.pack(side=tk.LEFT, padx=8)

        # ボタン（右ペイン内）
        saveNextBtns = tk.Frame(right)
        saveNextBtns.pack(fill=tk.X, pady=12)
        tk.Button(
            saveNextBtns,
            text="    保存    ",
            command=self._on_save,
            bg="#4CAF50",
            fg="#FFFFFF",
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            saveNextBtns,
            text="  次へ行く  ",
            command=self._on_next,
            bg="#2196F3",
            fg="#FFFFFF",
        ).pack(side=tk.LEFT, padx=6)

        # ボタンのデフォルト色を保持
        self._default_btn_bg = self.btn_mip.cget("bg")
        self._default_btn_fg = self.btn_mip.cget("fg")

        # キャンバスの描画イベントをバインド
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_down)
        self.canvas.bind("<B1-Motion>", self._on_canvas_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_up)

    def _on_blend(self):
        bg = self.bg_var.get().strip()
        mid = self.mid_var.get().strip()
        fg = self.fg_var.get().strip()
        try:
            self.result_image = blend_and_get_image(
                bg,
                mid,
                fg,
                float(self.alpha_mid.get()),
                float(self.alpha_fg.get()),
                rotation_deg=self.rotation_angle,
            )
            self._show_image(self.result_image)
        except Exception as e:
            messagebox.showerror("処理失敗", str(e))

    def _on_next(self):
        # 回転角度をランダムに（10度刻み）選択して再ブレンド
        candidates = list(range(0, 360, 10))
        self.rotation_angle = float(random.choice(candidates))
        # 計測（次へ押下）
        self.metrics.start_task()
        # 既存の手描きラインをクリア
        self._on_clear()
        self._on_blend()

    def _show_image(self, pil_img: Image.Image):
        # キャンバスに収まるよう簡易リサイズ
        canvas_w = int(self.canvas["width"]) if self.canvas["width"] else 1280
        canvas_h = int(self.canvas["height"]) if self.canvas["height"] else 760
        pil_img = resize_for_canvas(pil_img, canvas_w, canvas_h)
        self.display_image = pil_img
        self.photo = ImageTk.PhotoImage(pil_img)
        if self.canvas_img_id is None:
            self.canvas_img_id = self.canvas.create_image(
                canvas_w // 2, canvas_h // 2, image=self.photo, anchor=tk.CENTER
            )
        else:
            self.canvas.itemconfig(self.canvas_img_id, image=self.photo)

    def _on_save(self):
        if self.result_image is None:
            messagebox.showinfo("保存", "まず重畳して表示してください。")
            return
        # キャンバス描画を画像座標へ変換してServicesへ委譲
        strokes = self._collect_strokes()
        base_img = (
            self.display_image if self.display_image is not None else self.result_image
        )
        path = save_with_canvas(base_img, strokes)
        if path:
            # 計測CSVへ追記（モードごとに1行）
            try:
                rows = self.metrics.build_rows(rotation_deg=self.rotation_angle)
                append_metrics_for_image(path, rows)
            except Exception as e:
                messagebox.showwarning("計測保存", f"計測結果の保存に失敗: {e}")
            messagebox.showinfo("保存", f"保存しました: {path}")

    def _prompt_username(self):
        try:
            # ウィンドウが表示可能になるまで待機（モーダル入力の前に可視化）
            self.wait_visibility()
        except Exception:
            pass
        name = simpledialog.askstring(
            "ユーザー名", "ユーザー名を入力してください：", parent=self
        )
        set_current_user(name)

    # --- 描画モードとキャンバスイベントハンドラ ---
    def _set_mode_mip(self):
        # すでにMIPモードならトグルで停止
        if self.current_draw_color == MIP_LINE_COLOR:
            self.current_draw_color = None
            self.last_xy = None
            self._update_mode_buttons(active=None)
            self.metrics.set_mode(None)
        else:
            self.current_draw_color = MIP_LINE_COLOR
            self._update_mode_buttons(active="mip")
            self.metrics.set_mode("mip")

    def _set_mode_vein(self):
        # すでに血管モードならトグルで停止
        if self.current_draw_color == VEIN_LINE_COLOR:
            self.current_draw_color = None
            self.last_xy = None
            self._update_mode_buttons(active=None)
            self.metrics.set_mode(None)
        else:
            self.current_draw_color = VEIN_LINE_COLOR
            self._update_mode_buttons(active="vein")
            self.metrics.set_mode("vein")

    def _on_canvas_down(self, event):
        if not self.current_draw_color:
            return
        # 計測（開始点）
        self.metrics.on_canvas_down()
        self.last_xy = (event.x, event.y)

    def _on_canvas_move(self, event):
        if not self.current_draw_color or self.last_xy is None:
            return
        x0, y0 = self.last_xy
        x1, y1 = event.x, event.y
        item_id = self.canvas.create_line(
            x0,
            y0,
            x1,
            y1,
            fill=self.current_draw_color,
            width=LINE_WIDTH,
            capstyle=tk.ROUND,
            smooth=True,
        )
        self.drawn_items.append(item_id)
        self.last_xy = (x1, y1)

    def _on_canvas_up(self, event):
        # 計測（ストローク終了）
        self.metrics.on_canvas_up()
        self.last_xy = None

    def _on_clear(self):
        # 画像アイテム以外（記録しているライン）を削除
        for item_id in self.drawn_items:
            try:
                self.canvas.delete(item_id)
            except Exception:
                pass
        self.drawn_items.clear()

    def _update_mode_buttons(self, active: str | None):
        # すべてリセット
        for btn in (self.btn_mip, self.btn_vein):
            btn.configure(bg=self._default_btn_bg, fg=self._default_btn_fg)
        # アクティブを強調（赤）
        if active == "mip":
            self.btn_mip.configure(bg="#FF4D4D", fg="#FFFFFF")
        elif active == "vein":
            self.btn_vein.configure(bg="#FF4D4D", fg="#FFFFFF")

    def _collect_strokes(self) -> list[Stroke]:
        # Canvasの画像中心座標と表示サイズから画像の左上（原点）を推定
        try:
            cx, cy = self.canvas.coords(self.canvas_img_id)
        except Exception:
            cx, cy = (self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2)
        img_w = self.photo.width() if self.photo else 0
        img_h = self.photo.height() if self.photo else 0
        x0 = int(cx - img_w / 2)
        y0 = int(cy - img_h / 2)

        strokes: list[Stroke] = []
        for item_id in self.drawn_items:
            coords = self.canvas.coords(item_id)
            if not coords or len(coords) < 4:
                continue
            pts = []
            for i in range(0, len(coords), 2):
                px = coords[i] - x0
                py = coords[i + 1] - y0
                pts.append((px, py))
            color = self.canvas.itemcget(item_id, "fill") or "#FF0000"
            width_str = self.canvas.itemcget(item_id, "width")
            try:
                width = int(float(width_str)) if width_str else LINE_WIDTH
            except Exception:
                width = LINE_WIDTH
            strokes.append(Stroke(points=pts, color=color, width=width))
        return strokes


def run():
    app = MainWindow()
    app.mainloop()
