#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ======================== 用户配置区域 ========================

# 配置区域，使用 os.path.join 拼接
PDF_TEMPLATE = os.path.join(SCRIPT_DIR, "Template.pdf")
CSV_DATA = os.path.join(SCRIPT_DIR, "Guest_List.csv")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_badges_vector")

# ---------- 字体设置 ----------
FONT_PATH = os.path.join(SCRIPT_DIR, "msyhsb.ttc")
FONT_NAME = "MicrosoftYaHei"

# 字号
NAME_FONT_SIZE = 36        # 第一页姓名
UNIT_ORIGIN_FONT_SIZE = 20 # 单位原始字号（若宽度超限则会自动缩小）
PAGE2_NAME_FONT_SIZE = 28  # 第二页姓名（白色）

# 字距
CHAR_SPACING = 2.33

# 模拟加粗
ENABLE_BOLD = True
BOLD_STROKE_WIDTH = 0.8

# 坐标（中心点，单位：pt，左下角原点）
PAGE1_NAME_CENTER = (139, 131)
PAGE1_UNIT_CENTER = (139, 82)
PAGE2_NAME_CENTER = (139, 82)
PAGE2_NAME_COLOR = (1, 1, 1)   # 白色

# 单位文本最大允许宽度（点），超过则缩小字号
UNIT_MAX_WIDTH = 220
# 单位最小允许字号（pt）
UNIT_MIN_FONT_SIZE = 15

# ================== 辅助函数 ==================
def get_page_size(pdf_path, page_num=0):
    reader = PdfReader(pdf_path)
    page = reader.pages[page_num]
    mb = page.mediabox
    return float(mb.width), float(mb.height)

def get_text_width(text, font_name, font_size, char_spacing):
    if not text:
        return 0
    base = pdfmetrics.stringWidth(text, font_name, font_size)
    if len(text) > 1:
        base += char_spacing * (len(text) - 1)
    return base

def draw_centered_at(c, text, font_name, font_size, center_x, center_y,
                     char_spacing, text_color, enable_bold=True, stroke_width=0.5):
    if not text.strip():
        return
    c.setFont(font_name, font_size)
    c.setFillColorRGB(*text_color)
    text_width = get_text_width(text, font_name, font_size, char_spacing)
    x = center_x - text_width / 2.0
    ascent = pdfmetrics.getAscent(font_name, font_size)
    descent = pdfmetrics.getDescent(font_name, font_size)
    text_height = ascent - descent
    y = center_y - text_height / 2.0 + ascent

    if enable_bold:
        c._textRenderMode = 2
        c.setLineWidth(stroke_width)
        c.drawString(x, y, text, charSpace=char_spacing)
        c._textRenderMode = 0
    else:
        c.drawString(x, y, text, charSpace=char_spacing)

def get_fitted_font_size(text, font_name, max_width, char_spacing, prefer_size, min_size):
    """计算使文本宽度不超过 max_width 的字号（不小于 min_size）"""
    if not text:
        return prefer_size
    # 二分查找或简单线性递减
    size = prefer_size
    while size > min_size:
        width = get_text_width(text, font_name, size, char_spacing)
        if width <= max_width:
            return size
        size -=1  # 每次减1pt
    return min_size

# ================== 主程序 ==================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 注册字体
    if not os.path.exists(FONT_PATH):
        raise FileNotFoundError(f"字体文件不存在: {FONT_PATH}")
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))

    # 读取模板
    reader = PdfReader(PDF_TEMPLATE)
    if len(reader.pages) < 2:
        raise RuntimeError("模板PDF页数不足2页")
    template_page1 = reader.pages[0]
    template_page2 = reader.pages[1]

    page_width, page_height = get_page_size(PDF_TEMPLATE, 0)
    print(f"页面尺寸: {page_width} x {page_height} 点")

    # 读取CSV
    records = []
    with open(CSV_DATA, "r", encoding="gbk") as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            if len(row) >= 3:
                num, name, unit = row[0].strip(), row[1].strip(), row[2].strip()
                records.append((num, name, unit))
    print(f"共读取 {len(records)} 条人员数据")

    # 批量生成
    for idx, (num, name, unit) in enumerate(records, 1):
        print(f"处理 ({idx}/{len(records)})：{num}.{name}")
        writer = PdfWriter()

        # ---- 第1页 ----
        writer.add_page(template_page1)
        page1 = writer.pages[-1]

        # 计算单位合适字号（动态缩小）
        unit_font_size = get_fitted_font_size(unit, FONT_NAME, UNIT_MAX_WIDTH,
                                              CHAR_SPACING, UNIT_ORIGIN_FONT_SIZE, UNIT_MIN_FONT_SIZE)
        if unit_font_size < UNIT_ORIGIN_FONT_SIZE:
            print(f"   单位字号从 {UNIT_ORIGIN_FONT_SIZE} 缩小为 {unit_font_size}")

        packet1 = BytesIO()
        c1 = canvas.Canvas(packet1, pagesize=(page_width, page_height))
        # 姓名
        draw_centered_at(c1, name, FONT_NAME, NAME_FONT_SIZE,
                         PAGE1_NAME_CENTER[0], PAGE1_NAME_CENTER[1],
                         CHAR_SPACING, (0,0,0), ENABLE_BOLD, BOLD_STROKE_WIDTH)
        # 单位（使用动态字号）
        draw_centered_at(c1, unit, FONT_NAME, unit_font_size,
                         PAGE1_UNIT_CENTER[0], PAGE1_UNIT_CENTER[1],
                         CHAR_SPACING, (0,0,0), ENABLE_BOLD, BOLD_STROKE_WIDTH)
        c1.save()
        packet1.seek(0)
        text_pdf1 = PdfReader(packet1)
        page1.merge_page(text_pdf1.pages[0])

        # ---- 第2页 ----
        writer.add_page(template_page2)
        page2 = writer.pages[-1]

        packet2 = BytesIO()
        c2 = canvas.Canvas(packet2, pagesize=(page_width, page_height))
        draw_centered_at(c2, name, FONT_NAME, PAGE2_NAME_FONT_SIZE,
                         PAGE2_NAME_CENTER[0], PAGE2_NAME_CENTER[1],
                         CHAR_SPACING, PAGE2_NAME_COLOR, ENABLE_BOLD, BOLD_STROKE_WIDTH)
        c2.save()
        packet2.seek(0)
        text_pdf2 = PdfReader(packet2)
        page2.merge_page(text_pdf2.pages[0])

        # 保存
        output_path = os.path.join(OUTPUT_DIR, f"{num}.{name}.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)

    print(f"\n全部完成！共生成 {len(records)} 个胸牌（每人2页），保存在：{OUTPUT_DIR}")

if __name__ == "__main__":
    main()