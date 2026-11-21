import io
from datetime import date
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE

NAVY = RGBColor(0x12, 0x26, 0x3F)
INK = RGBColor(0x0F, 0x1C, 0x2E)
MUTED = RGBColor(0x56, 0x66, 0x78)
POS = RGBColor(0x2F, 0x9E, 0x5B)
NEG = RGBColor(0xD6, 0x45, 0x45)
NEU = RGBColor(0xE8, 0xA3, 0x3D)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PALE = RGBColor(0xC5, 0xD6, 0xEC)

MAX_TABLE_ROWS = 12


def _text(slide, text, x, y, w, h, size=18, bold=False, color=INK):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    run = tf.paragraphs[0].add_run()
    run.text = str(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return box


def _bullets(slide, items, x, y, w, h, size=16):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(8)
        run = p.add_run()
        run.text = "\u2022 " + str(item)
        run.font.size = Pt(size)
        run.font.color.rgb = INK
    return box


def _header(slide, title):
    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(1.1))
    band.fill.solid()
    band.fill.fore_color.rgb = NAVY
    band.line.fill.background()
    _text(slide, title, 0.7, 0.2, 12, 0.7, 28, True, WHITE)
    _text(slide, "Numbers are calculated by Python from the uploaded CSV. Written text is AI-generated: please verify before sharing.",
          0.7, 7.0, 12, 0.35, 11, False, MUTED)


def _style_cells(table, size, header=True):
    for r_idx, row in enumerate(table.rows):
        for cell in row.cells:
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(size)
                    if header and r_idx == 0:
                        run.font.bold = True


def build_deck(kpis, products, report):
    """Returns a BytesIO holding the .pptx. report may be None (AI unavailable)."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    # 1. Title
    s = prs.slides.add_slide(blank)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = NAVY
    _text(s, "Customer Feedback Report", 0.8, 2.3, 11.5, 1.2, 44, True, WHITE)
    _text(s, str(kpis["total"]) + " reviews analyzed across " + str(len(products)) + " products",
          0.8, 3.6, 11.5, 0.6, 22, False, PALE)
    _text(s, date.today().strftime("%d %B %Y"), 0.8, 4.3, 11.5, 0.5, 16, False, PALE)

    # 2. Key numbers
    s = prs.slides.add_slide(blank)
    _header(s, "Key numbers")
    blocks = [
        (str(kpis["total"]), "Reviews analyzed", INK),
        (str(kpis["positive_pct"]) + "%", "Positive (" + str(kpis["positive"]) + ")", POS),
        (str(kpis["negative_pct"]) + "%", "Negative (" + str(kpis["negative"]) + ")", NEG),
        (str(kpis["neutral_pct"]) + "%", "Neutral (" + str(kpis["neutral"]) + ")", NEU),
        ("%+.2f" % kpis["avg_score"], "Average score (-1 to +1)", INK),
    ]
    for i, (value, label, color) in enumerate(blocks):
        x = 0.7 + i * 2.5
        _text(s, value, x, 2.6, 2.4, 1.1, 44, True, color)
        _text(s, label, x, 3.8, 2.4, 0.6, 16, False, MUTED)

    # 3. Charts
    s = prs.slides.add_slide(blank)
    _header(s, "Sentiment overview")
    cd = CategoryChartData()
    cd.categories = ["Positive", "Negative", "Neutral"]
    cd.add_series("Reviews", (kpis["positive"], kpis["negative"], kpis["neutral"]))
    chart = s.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(0.6), Inches(1.4),
                               Inches(5.6), Inches(5.4), cd).chart
    chart.has_title = False
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    plot = chart.plots[0]
    plot.has_data_labels = True
    plot.data_labels.show_value = True
    plot.data_labels.font.size = Pt(14)
    for i, color in enumerate((POS, NEG, NEU)):
        pt = plot.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = color

    shown = products[:MAX_TABLE_ROWS]
    cd2 = CategoryChartData()
    cd2.categories = [str(p["product"]) for p in shown]
    cd2.add_series("Positive", [p["positive"] for p in shown])
    cd2.add_series("Negative", [p["negative"] for p in shown])
    cd2.add_series("Neutral", [p["neutral"] for p in shown])
    chart2 = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED, Inches(6.5), Inches(1.4),
                                Inches(6.3), Inches(5.4), cd2).chart
    chart2.has_title = False
    chart2.has_legend = True
    top = max([p["total"] for p in shown] or [1])
    chart2.value_axis.minimum_scale = 0
    chart2.value_axis.major_unit = max(1, -(-top // 6))
    chart2.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart2.legend.include_in_layout = False
    for ser, color in zip(chart2.plots[0].series, (POS, NEG, NEU)):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = color

    # 4. Product table
    s = prs.slides.add_slide(blank)
    _header(s, "Product performance")
    heads = ["Product", "Reviews", "Positive", "Negative", "Neutral", "% Negative", "Avg score"]
    rows = len(shown) + 1
    table = s.shapes.add_table(rows, len(heads), Inches(0.7), Inches(1.5),
                               Inches(11.9), Inches(0.42 * rows)).table
    for c, h in enumerate(heads):
        table.cell(0, c).text = h
    for r, p in enumerate(shown, start=1):
        vals = [p["product"], p["total"], p["positive"], p["negative"], p["neutral"],
                str(p["negative_pct"]) + "%", "%+.2f" % p["avg_score"]]
        for c, v in enumerate(vals):
            table.cell(r, c).text = str(v)
    _style_cells(table, 14)
    if len(products) > MAX_TABLE_ROWS:
        _text(s, "Showing the first " + str(MAX_TABLE_ROWS) + " of " + str(len(products)) + " products.",
              0.7, 6.6, 11, 0.4, 12, False, MUTED)

    # 5-6. AI insights
    if report:
        s = prs.slides.add_slide(blank)
        _header(s, "Executive summary")
        _text(s, report.get("summary", ""), 0.8, 1.6, 11.7, 5.0, 20)

        s = prs.slides.add_slide(blank)
        _header(s, "Complaints and recommendations")
        _text(s, "Key complaints", 0.7, 1.4, 5.8, 0.5, 20, True)
        _bullets(s, report.get("complaints", []) or ["No complaints listed."], 0.7, 2.0, 5.8, 4.8, 15)
        _text(s, "Recommendations", 6.9, 1.4, 5.8, 0.5, 20, True)
        recs = ["%s: %s" % (r.get("product", ""), r.get("action", "")) for r in report.get("recommendations", [])]
        _bullets(s, recs or ["No recommendations listed."], 6.9, 2.0, 5.8, 4.8, 15)
    else:
        s = prs.slides.add_slide(blank)
        _header(s, "Executive summary")
        _text(s, "The AI-written summary was not available when this report was created. "
                 "The numbers in this deck are still calculated from your data.", 0.8, 1.8, 11.5, 1.5, 20, False, MUTED)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf
