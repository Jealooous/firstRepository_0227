import tkinter as tk
from tkinter import messagebox

BOARD_SIZE = 15
CELL_SIZE = 40
PADDING = 30
STONE_RADIUS = 16

WIDTH = CELL_SIZE * (BOARD_SIZE - 1) + PADDING * 2
HEIGHT = CELL_SIZE * (BOARD_SIZE - 1) + PADDING * 2

HUMAN = 1   # 黑棋
AI = 2      # 白棋

# 棋型评分表
SCORE = {
    (5, True):  1_000_000,   # 五连
    (4, True):    50_000,    # 活四
    (4, False):   10_000,    # 冲四
    (3, True):     2_000,    # 活三
    (3, False):      500,    # 眠三
    (2, True):       100,    # 活二
    (2, False):       20,    # 眠二
}


def evaluate_line(board, player, row, col, dr, dc):
    """评估从 (row,col) 出发某方向上的棋型分数"""
    count = 1
    blocked = 0

    for sign in (1, -1):
        r, c = row + sign * dr, col + sign * dc
        while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and board[r][c] == player:
            count += 1
            r += sign * dr
            c += sign * dc
        # 检查端点是否被堵住
        if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE) or board[r][c] != 0:
            blocked += 1

    if count >= 5:
        return SCORE[(5, True)]
    alive = blocked < 2
    return SCORE.get((count, alive), 0)


def score_position(board, row, col, player):
    """计算某位置落子后的综合分数"""
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    total = 0
    for dr, dc in directions:
        total += evaluate_line(board, player, row, col, dr, dc)
    return total


def ai_move(board):
    """AI选择最佳落子位置（启发式评分）"""
    best_score = -1
    best_pos = None

    # 若棋盘全空，走天元
    if all(board[r][c] == 0 for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)):
        return BOARD_SIZE // 2, BOARD_SIZE // 2

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] != 0:
                continue
            # 只考虑有邻居的位置（剪枝）
            has_neighbor = any(
                0 <= r + dr < BOARD_SIZE and 0 <= c + dc < BOARD_SIZE
                and board[r + dr][c + dc] != 0
                for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                if (dr, dc) != (0, 0)
            )
            if not has_neighbor:
                continue

            board[r][c] = AI
            ai_s = score_position(board, r, c, AI)
            board[r][c] = 0

            board[r][c] = HUMAN
            human_s = score_position(board, r, c, HUMAN)
            board[r][c] = 0

            # AI进攻权重略高于防守
            s = ai_s * 1.1 + human_s
            if s > best_score:
                best_score = s
                best_pos = (r, c)

    return best_pos


class Gomoku:
    def __init__(self, root):
        self.root = root
        self.root.title("五子棋 - 人机对战")
        self.root.resizable(False, False)

        self.board = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.current_player = HUMAN
        self.game_over = False

        self._build_ui()
        self._draw_board()

    def _build_ui(self):
        top = tk.Frame(self.root, bg="#d4a84b", pady=6)
        top.pack(fill=tk.X)

        self.status_var = tk.StringVar(value="你先行（黑棋）")
        tk.Label(top, textvariable=self.status_var, font=("微软雅黑", 14, "bold"),
                 bg="#d4a84b", fg="#222").pack(side=tk.LEFT, padx=16)

        tk.Button(top, text="重新开始", font=("微软雅黑", 11),
                  command=self.restart, bg="#8b4513", fg="white",
                  relief=tk.FLAT, padx=10).pack(side=tk.RIGHT, padx=12)

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT,
                                bg="#d4a84b", highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_hover)

        self.hover_item = None

    def _draw_board(self):
        self.canvas.delete("grid")
        for i in range(BOARD_SIZE):
            x = PADDING + i * CELL_SIZE
            y = PADDING + i * CELL_SIZE
            self.canvas.create_line(PADDING, y, PADDING + (BOARD_SIZE - 1) * CELL_SIZE, y,
                                    fill="#8b6914", width=1, tags="grid")
            self.canvas.create_line(x, PADDING, x, PADDING + (BOARD_SIZE - 1) * CELL_SIZE,
                                    fill="#8b6914", width=1, tags="grid")
        star_points = [3, 7, 11]
        for r in star_points:
            for c in star_points:
                cx = PADDING + c * CELL_SIZE
                cy = PADDING + r * CELL_SIZE
                self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                                        fill="#8b6914", tags="grid")

    def _pixel_to_grid(self, x, y):
        col = round((x - PADDING) / CELL_SIZE)
        row = round((y - PADDING) / CELL_SIZE)
        return row, col

    def _is_valid(self, row, col):
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

    def _draw_stone(self, row, col, player, tag="stone"):
        cx = PADDING + col * CELL_SIZE
        cy = PADDING + row * CELL_SIZE
        r = STONE_RADIUS
        if player == HUMAN:
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    fill="#111", outline="#444", width=1.5, tags=tag)
        else:
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    fill="#f5f5f0", outline="#aaa", width=1.5, tags=tag)

    def on_hover(self, event):
        if self.game_over or self.current_player != HUMAN:
            return
        row, col = self._pixel_to_grid(event.x, event.y)
        if not self._is_valid(row, col) or self.board[row][col] != 0:
            self.canvas.delete("hover")
            self.hover_item = None
            return
        self.canvas.delete("hover")
        cx = PADDING + col * CELL_SIZE
        cy = PADDING + row * CELL_SIZE
        r = STONE_RADIUS
        self.hover_item = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                                  fill="#333", outline="", stipple="gray50",
                                                  tags="hover")

    def on_click(self, event):
        if self.game_over or self.current_player != HUMAN:
            return
        row, col = self._pixel_to_grid(event.x, event.y)
        if not self._is_valid(row, col) or self.board[row][col] != 0:
            return

        self.canvas.delete("hover")
        self._place(row, col, HUMAN)

    def _place(self, row, col, player):
        self.board[row][col] = player
        self._draw_stone(row, col, player)

        if self._check_win(row, col):
            winner = "你赢了！" if player == HUMAN else "电脑赢了！"
            self.status_var.set(winner)
            self.game_over = True
            self._highlight_winner(row, col)
            messagebox.showinfo("游戏结束", f"{'🎉 ' if player == HUMAN else '🤖 '}{winner}")
            return

        if self._check_draw():
            self.status_var.set("平局！")
            self.game_over = True
            messagebox.showinfo("游戏结束", "棋盘已满，平局！")
            return

        self.current_player = AI if player == HUMAN else HUMAN
        if self.current_player == AI:
            self.status_var.set("电脑思考中...")
            self.root.update()
            self.root.after(100, self._ai_turn)
        else:
            self.status_var.set("轮到你落子（黑棋）")

    def _ai_turn(self):
        pos = ai_move(self.board)
        if pos:
            self._place(pos[0], pos[1], AI)

    def _check_win(self, row, col):
        player = self.board[row][col]
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            for sign in (1, -1):
                r, c = row + sign * dr, col + sign * dc
                while self._is_valid(r, c) and self.board[r][c] == player:
                    count += 1
                    r += sign * dr
                    c += sign * dc
            if count >= 5:
                return True
        return False

    def _highlight_winner(self, row, col):
        player = self.board[row][col]
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            cells = [(row, col)]
            for sign in (1, -1):
                r, c = row + sign * dr, col + sign * dc
                while self._is_valid(r, c) and self.board[r][c] == player:
                    cells.append((r, c))
                    r += sign * dr
                    c += sign * dc
            if len(cells) >= 5:
                for r, c in cells:
                    cx = PADDING + c * CELL_SIZE
                    cy = PADDING + r * CELL_SIZE
                    self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6,
                                            fill="red", outline="", tags="stone")
                break

    def _check_draw(self):
        return all(self.board[r][c] != 0
                   for r in range(BOARD_SIZE) for c in range(BOARD_SIZE))

    def restart(self):
        self.board = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.current_player = HUMAN
        self.game_over = False
        self.canvas.delete("stone")
        self.canvas.delete("hover")
        self.hover_item = None
        self.status_var.set("你先行（黑棋）")


if __name__ == "__main__":
    root = tk.Tk()
    Gomoku(root)
    root.mainloop()
