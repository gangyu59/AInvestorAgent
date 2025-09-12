#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
print_file_tree.py
用法示例：
  python tools/print_file_tree.py
  python tools/print_file_tree.py --root AInvestorAgent --max-depth 6 --include-files \
      --save-md docs/FILE_TREE.md --save-json docs/FILE_TREE.json
  python tools/print_file_tree.py --exclude "*.log" --exclude "frontend/dist" --ascii
"""
from __future__ import annotations
import os
import sys
import json
import fnmatch
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Iterable

DEFAULT_ROOT = "AInvestorAgent"

# 默认忽略的目录/文件（可用 --exclude 追加）
DEFAULT_IGNORES = [
    ".git", ".idea", ".vscode", ".DS_Store", "Thumbs.db",
    "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", "dist", "build", "coverage", ".coverage",
    ".venv", "venv", ".cache",
]

BRANCH = "├── "
LAST   = "└── "
PIPE   = "│   "
GAP    = "    "

@dataclass
class Node:
    name: str
    path: str
    is_dir: bool
    size: int = 0
    children: List["Node"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        if self.is_dir:
            return {
                "name": self.name,
                "path": self.path,
                "type": "dir",
                "children": [c.to_dict() for c in self.children],
            }
        else:
            return {
                "name": self.name,
                "path": self.path,
                "type": "file",
                "size": self.size,
            }

def load_gitignore(root: str) -> List[str]:
    """粗略读取 .gitignore，转为 fnmatch 模式（仅作简单忽略）。"""
    patterns: List[str] = []
    gi = os.path.join(root, ".gitignore")
    if os.path.isfile(gi):
        try:
            with open(gi, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    # 简化支持：把结尾的 / 去掉；保留原样作为全局匹配
                    if s.endswith("/"):
                        s = s[:-1]
                    patterns.append(s)
        except Exception:
            pass
    return patterns

def should_exclude(name: str, relpath: str, patterns: Iterable[str]) -> bool:
    """基于文件名或相对路径匹配忽略规则（fnmatch）。"""
    for p in patterns:
        if fnmatch.fnmatch(name, p) or fnmatch.fnmatch(relpath, p):
            return True
    return False

def build_tree(root: str, include_files: bool, max_depth: int,
               excludes: List[str], use_gitignore: bool) -> Node:
    git_ignores = load_gitignore(root) if use_gitignore else []
    patterns = set(DEFAULT_IGNORES + list(excludes) + git_ignores)

    def _walk(cur_path: str, depth: int) -> Optional[Node]:
        rel = os.path.relpath(cur_path, root)
        rel = "." if rel == "." else rel.replace("\\", "/")
        name = os.path.basename(cur_path) or rel

        # 根节点不过滤；其它节点按规则忽略
        if rel != ".":
            if should_exclude(name, rel, patterns):
                return None

        if os.path.isdir(cur_path):
            node = Node(name=name, path=rel, is_dir=True)
            if depth >= max_depth:
                return node
            try:
                entries = sorted(os.listdir(cur_path))
            except PermissionError:
                return node
            for e in entries:
                child_p = os.path.join(cur_path, e)
                ch = _walk(child_p, depth + 1)
                if ch is not None:
                    # 如果是文件但用户不展示文件，直接跳过
                    if (not include_files) and (not ch.is_dir):
                        continue
                    node.children.append(ch)
            return node
        else:
            try:
                sz = os.path.getsize(cur_path)
            except OSError:
                sz = 0
            return Node(name=name, path=rel, is_dir=False, size=sz)

    return _walk(root, 0) or Node(name=os.path.basename(root), path=".", is_dir=True)

def render_ascii(node: Node, show_files: bool, ascii_only: bool) -> str:
    """渲染为 ASCII/UTF-8 树状图。"""
    # 处理 Windows 终端兼容：--ascii 时用纯ASCII
    branch = "+-- " if ascii_only else BRANCH
    last   = "`-- " if ascii_only else LAST
    pipe   = "|   " if ascii_only else PIPE
    gap    = "    " if ascii_only else GAP

    lines: List[str] = []

    def _draw(n: Node, prefix: str = "", is_last: bool = True):
        connector = last if is_last else branch
        label = n.name + ("/" if n.is_dir else "")
        if n.path == ".":
            lines.append(n.name + "/")
        else:
            lines.append(prefix + connector + label)

        if n.is_dir:
            children = n.children
            if not show_files:
                children = [c for c in children if c.is_dir]
            for i, c in enumerate(children):
                nxt_pref = prefix + (gap if is_last else pipe)
                _draw(c, nxt_pref, i == len(children) - 1)

    root_label = os.path.basename(node.path) if node.path not in (".", "") else os.path.basename(os.path.abspath(DEFAULT_ROOT)) or "ROOT"
    # 主调
    _draw(Node(name=root_label, path=".", is_dir=True, children=node.children))
    return "\n".join(lines)

def ensure_parent(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def save_markdown(md_path: str, tree_text: str):
    ensure_parent(md_path)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 项目文件架构\n\n")
        f.write("```text\n")
        f.write(tree_text)
        f.write("\n```\n")

def save_json(json_path: str, root_node: Node):
    ensure_parent(json_path)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(root_node.to_dict(), f, ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser(description="绘制项目文件架构（树形图/Markdown/JSON）")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="项目根目录（默认：AInvestorAgent）")
    ap.add_argument("--max-depth", type=int, default=12, help="最大深度（默认：12）")
    ap.add_argument("--include-files", action="store_true", help="包含文件（默认只显示目录）")
    ap.add_argument("--exclude", action="append", default=[], help="追加忽略（可多次），支持通配符，如 '*.log'")
    ap.add_argument("--use-gitignore", action="store_true", help="同时读取根目录 .gitignore 作为忽略规则")
    ap.add_argument("--save-md", default="", help="保存为 Markdown（如 docs/FILE_TREE.md）")
    ap.add_argument("--save-json", default="", help="保存为 JSON（如 docs/FILE_TREE.json）")
    ap.add_argument("--ascii", action="store_true", help="使用纯 ASCII 画树（兼容部分终端）")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"[ERROR] 根路径不存在或不是目录：{root}", file=sys.stderr)
        sys.exit(1)

    tree = build_tree(root, include_files=args.include_files,
                      max_depth=args.max_depth, excludes=args.exclude,
                      use_gitignore=args.use_gitignore)

    text = render_ascii(tree, show_files=args.include_files, ascii_only=args.ascii)

    # 控制台输出
    print(text)

    # 导出
    if args.save_md:
        save_markdown(args.save_md, text)
        print(f"[OK] Markdown 已保存：{args.save_md}")
    if args.save_json:
        save_json(args.save_json, tree)
        print(f"[OK] JSON 已保存：{args.save_json}")

if __name__ == "__main__":
    main()
