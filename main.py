import flet as ft
from datetime import datetime, timedelta, date
import calendar, json, os, asyncio

SAVE_FILE = os.path.join(os.path.expanduser("~"), "electricity_saved.json")

def _meter_key(n):  return f"meter{n}"

def _meter_defaults():
    return {"start_date": None, "start_reading": "",
            "curr_reading": "", "prev_reading": "", "meter_number": ""}

def load_all_saved():
    data = {_meter_key(n): _meter_defaults() for n in range(1, 5)}
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for n in range(1, 5):
                k = _meter_key(n)
                if k in saved:
                    data[k].update(saved[k])
    except Exception:
        pass
    return data

def save_meter(n, sd, sr, cr, pr, mn=""):
    try:
        all_data = {}
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                all_data = json.load(f)
        all_data[_meter_key(n)] = {
            "start_date": sd, "start_reading": str(sr),
            "curr_reading": str(cr), "prev_reading": str(pr),
            "meter_number": str(mn),
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_billing_start():
    today = date.today()
    m = today.month - 1 if today.month > 1 else 12
    y = today.year if today.month > 1 else today.year - 1
    return date(y, m, 13)

def calc_energy(units):
    if units <= 200:
        ctype = "Protected (<=200 units)"
        slabs = [(50, 12.0), (50, 14.0), (100, 18.0)]
    else:
        ctype = "Unprotected (>200 units)"
        slabs = [(100,16.0),(100,22.0),(100,24.5),(100,30.0),(100,32.0),(999999,35.0)]
    bill, rem = 0, units
    for limit, rate in slabs:
        if rem <= 0: break
        used = min(rem, limit)
        bill += used * rate
        rem  -= used
    return round(bill), ctype

def run_calc(start_r, curr_r, prev_r, bstart):
    total   = round(curr_r - start_r)
    lastday = round(curr_r - prev_r)
    rem_u   = max(0, 200 - total)
    elapsed = (date.today() - bstart).days
    rem_d   = max(0, 30 - elapsed)
    avg     = round(rem_u / rem_d) if rem_d > 0 else 0
    energy, ctype = calc_energy(total)
    fpa        = round(total * 2.50)
    fixed      = 55
    sub        = energy + fpa + fixed
    gst        = round(sub * 0.17)
    total_bill = sub + gst
    return dict(total=total, lastday=lastday, rem_u=rem_u, rem_d=rem_d,
                avg=avg, ctype=ctype, energy=energy, fpa=fpa,
                fixed=fixed, sub=sub, gst=gst, bill=total_bill)

MC   = {1:"#c0392b", 2:"#1a6fa8", 3:"#c0622b", 4:"#5b2d8e"}
BG   = "#0d1721"
CARD = "#1e2a38"
INP  = "#111d27"
ROW  = "#1a2b3a"
ACC  = "#6eb5ff"
GOLD = "#ffd700"
GRN  = "#27ae60"
PUR  = "#8e44ad"
TEAL = "#0e6655"

def main(page: ft.Page):
    page.title      = "Ecal_v24"
    page.bgcolor    = BG
    page.padding    = 10
    page.scroll     = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.DARK

    saved  = load_all_saved()
    cache  = {1:None, 2:None, 3:None, 4:None}
    active = [1]
    bstart = {"d": get_billing_start()}

    clk = ft.Text(datetime.now().strftime('%H:%M:%S | %d-%m-%Y | %A'), size=11, color=ACC)

    async def clock_loop():
        while True:
            clk.value = datetime.now().strftime('%H:%M:%S | %d-%m-%Y | %A')
            try:
                page.update()
            except Exception:
                break
            await asyncio.sleep(1)

    def tf(hint, val=""):
        return ft.TextField(
            value=val, hint_text=hint, bgcolor=CARD,
            color="white", border_color="#2a5080",
            focused_border_color=ACC, text_size=14, height=46,
            content_padding=ft.Padding(left=10, right=10, top=6, bottom=6),
        )

    f_acc = tf("Account No")
    f_st  = tf("Start Reading")
    f_cur = tf("Current Reading")
    f_pre = tf("Previous Reading")

    # ── btn_date: FilledButton + Text child (text update via .content.value) ──
    _btn_date_txt = ft.Text(bstart["d"].strftime("%d-%b"),
                            color="white", weight=ft.FontWeight.BOLD, size=13)
    btn_date = ft.FilledButton(
        content=_btn_date_txt,
        bgcolor="#c0392b", height=46,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
    )

    days_txt = ft.Text("", color="white", size=13)

    def upd_elapsed():
        e = (date.today() - bstart["d"]).days
        days_txt.value = f"{e} days elapsed  |  Remaining: {max(30-e,0)}"

    upd_elapsed()

    def mkcard(icon, title, start_val="--"):
        val = ft.Text(start_val, size=20, weight=ft.FontWeight.BOLD, color="white")
        sub = ft.Text("", size=10, color="#8faabf")
        box = ft.Container(
            content=ft.Column([
                ft.Text(f"{icon} {title}", size=9, color="#8faabf",
                        weight=ft.FontWeight.BOLD),
                val, sub,
            ], spacing=2, tight=True),
            bgcolor=CARD, border_radius=8,
            padding=ft.Padding(8, 8, 8, 8),
            border=ft.Border(bottom=ft.BorderSide(3, ACC)),
            expand=True,
        )
        return box, val, sub

    c1,v1,s1 = mkcard("⚡","Month Total")
    c2,v2,s2 = mkcard("📅","Yesterday")
    c3,v3,s3 = mkcard("🕐","Units Left")
    c4,v4,s4 = mkcard("📆","Days Left")
    c5,v5,s5 = mkcard("📊","Daily Avg")
    c6,v6,s6 = mkcard("💰","Est. Bill")
    c6.border = ft.Border(bottom=ft.BorderSide(3, GOLD))
    v6.color  = GOLD

    cat_box = ft.Container(
        ft.Text("CONSUMER CATEGORY : Press Calculate",
                color="white", size=12, weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER),
        bgcolor="#2e7d32", border_radius=6, padding=8,
    )

    bill_col = ft.Column([], spacing=2)
    bill_box = ft.Container(bill_col, bgcolor=INP, border_radius=8,
                            padding=6, visible=False)

    def brow(lbl, amt, lc="white", vc="white", bg=ROW, bold=False):
        return ft.Container(
            ft.Row([
                ft.Text(lbl, size=11, color=lc, expand=True,
                        weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL),
                ft.Text(f"Rs. {amt:,}", size=11, color=vc, weight=ft.FontWeight.BOLD),
            ]),
            bgcolor=bg, border_radius=4, padding=ft.Padding(10, 5, 10, 5),
        )

    rep_txt = ft.Text("", size=10, color=GOLD, selectable=True, font_family="monospace")

    def close_report():
        rep_box.visible = False
        page.update()

    rep_box = ft.Container(
        ft.Column([
            rep_txt,
            ft.Row([
                ft.FilledButton(
                    content=ft.Text("Copy", color="white", weight=ft.FontWeight.BOLD),
                    bgcolor="#0066cc",
                    on_click=lambda _: page.set_clipboard(rep_txt.value),
                ),
                ft.FilledButton(
                    content=ft.Text("Close", color="white", weight=ft.FontWeight.BOLD),
                    bgcolor="#cc0000",
                    on_click=lambda _: close_report(),
                ),
            ], alignment=ft.MainAxisAlignment.CENTER),
        ]),
        bgcolor="#0d1721", border_radius=8, padding=12, visible=False,
    )

    btn_rep = ft.FilledButton(
        content=ft.Text("📄  Print / Export Report", color="white",
                        weight=ft.FontWeight.BOLD),
        bgcolor=PUR, visible=False,
        on_click=lambda _: show_report(),
    )

    def show_report():
        d = cache.get(active[0])
        if not d: return
        W  = 40
        ln = lambda a, b: f"  {a:<24}: {b}"
        ct = "Protected" if "Protected" in d["ctype"] else "Unprotected"
        lines = [
            "=" * W,
            "  ELECTRICITY REPORT".center(W),
            f"  {datetime.now().strftime('%B %Y')}".center(W),
            "=" * W,
            ln("Units Consumed",    d["total"]),
            ln("Yesterday Usage",   d["lastday"]),
            ln("Remaining Units",   d["rem_u"]),
            ln("Days Remaining",    d["rem_d"]),
            ln("Daily Allowance",   d["avg"]),
            "-" * W,
            f"  Category: {ct}",
            "-" * W,
            ln("Energy Charges",    f"Rs. {d['energy']:,}"),
            ln("FPA Charges",       f"Rs. {d['fpa']:,}"),
            ln("Fixed (Rent+TV)",   f"Rs. {d['fixed']:,}"),
            ln("GST (17%)",         f"Rs. {d['gst']:,}"),
            "=" * W,
            ln("TOTAL BILL (EST.)", f"Rs. {d['bill']:,}"),
            "=" * W,
            "  Developed by: Syed Imran",
        ]
        rep_txt.value   = "\n".join(lines)
        rep_box.visible = True
        page.update()

    dp_y    = [bstart["d"].year]
    dp_m    = [bstart["d"].month]
    dp_hdr  = ft.Text("", color="white", size=14, weight=ft.FontWeight.BOLD)
    dp_grid = ft.GridView(runs_count=7, spacing=3, run_spacing=3,
                          max_extent=40, height=260)

    def dp_draw():
        dp_hdr.value = date(dp_y[0], dp_m[0], 1).strftime("%b %Y")
        dp_grid.controls.clear()
        for h in ["Mo","Tu","We","Th","Fr","Sa","Su"]:
            dp_grid.controls.append(
                ft.Container(ft.Text(h, size=9, color="#aaa",
                                     text_align=ft.TextAlign.CENTER),
                             alignment=ft.alignment.center))
        sel = bstart["d"]
        for week in calendar.monthcalendar(dp_y[0], dp_m[0]):
            for day in week:
                if day == 0:
                    dp_grid.controls.append(ft.Container())
                else:
                    is_s = (day == sel.day and dp_m[0] == sel.month
                            and dp_y[0] == sel.year)
                    dp_grid.controls.append(ft.Container(
                        ft.Text(str(day), size=12, color="white",
                                text_align=ft.TextAlign.CENTER,
                                weight=ft.FontWeight.BOLD if is_s
                                       else ft.FontWeight.NORMAL),
                        bgcolor="#c0392b" if is_s else "#2c3e50",
                        border_radius=5, alignment=ft.alignment.center,
                        height=34, on_click=lambda e, d=day: dp_pick(d),
                    ))
        try: page.update()
        except Exception: pass

    def dp_pick(day):
        picked = date(dp_y[0], dp_m[0], day)
        bstart["d"] = picked
        btn_date.content.value = picked.strftime("%d-%b")
        upd_elapsed()
        save_cur()
        dp_dlg.open = False
        page.update()

    def dp_prev(_):
        if dp_m[0] == 1: dp_m[0], dp_y[0] = 12, dp_y[0] - 1
        else: dp_m[0] -= 1
        dp_draw()

    def dp_next(_):
        if dp_m[0] == 12: dp_m[0], dp_y[0] = 1, dp_y[0] + 1
        else: dp_m[0] += 1
        dp_draw()

    dp_dlg = ft.AlertDialog(
        modal=True, bgcolor="#1e1e1e",
        content_padding=ft.Padding(0, 0, 0, 0),
        content=ft.Container(
            ft.Column([
                ft.Container(
                    ft.Row([
                        ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_color="white",
                                      icon_size=20, on_click=dp_prev),
                        dp_hdr,
                        ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_color="white",
                                      icon_size=20, on_click=dp_next),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    bgcolor="#c0392b", padding=ft.Padding(8, 6, 8, 6),
                ),
                ft.Container(dp_grid, padding=8),
            ], spacing=0, tight=True),
            width=300,
        ),
    )
    page.overlay.append(dp_dlg)

    def open_dp(_):
        dp_y[0] = bstart["d"].year
        dp_m[0] = bstart["d"].month
        dp_draw()
        dp_dlg.open = True
        page.update()

    btn_date.on_click = open_dp

    m_btns = {}

    def save_cur():
        n  = active[0]
        sd = bstart["d"].isoformat()
        d  = {
            "start_date":    sd,
            "start_reading": f_st.value.strip(),
            "curr_reading":  f_cur.value.strip(),
            "prev_reading":  f_pre.value.strip(),
            "meter_number":  f_acc.value.strip(),
        }
        saved[_meter_key(n)] = d
        save_meter(n, sd, d["start_reading"], d["curr_reading"],
                   d["prev_reading"], d["meter_number"])

    def load_meter(n):
        d  = saved[_meter_key(n)]
        sd = get_billing_start()
        if d["start_date"]:
            try: sd = date.fromisoformat(d["start_date"])
            except Exception: pass
        bstart["d"] = sd
        btn_date.content.value = sd.strftime("%d-%b")
        f_acc.value = d["meter_number"]
        f_st.value  = d["start_reading"]
        f_cur.value = d["curr_reading"]
        f_pre.value = d["prev_reading"]
        upd_elapsed()
        for i, b in m_btns.items():
            b.bgcolor = MC[i] if i == n else "#1e2a38"
            b.style   = ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
                side=ft.BorderSide(2, "white") if i == n else ft.BorderSide(0),
            )
        c = cache.get(n)
        if c: apply_res(c)
        else:  reset_ui()
        page.update()

    def on_m(n):
        save_cur()
        active[0] = n
        load_meter(n)

    for i in range(1, 5):
        b = ft.FilledButton(
            content=ft.Text(f"Meter {i}", color="white",
                            weight=ft.FontWeight.BOLD),
            bgcolor=MC[i] if i == 1 else "#1e2a38",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
                side=ft.BorderSide(2, "white") if i == 1 else ft.BorderSide(0),
            ),
            on_click=lambda e, n=i: on_m(n),
        )
        m_btns[i] = b

    def reset_ui():
        for v in (v1, v2, v3, v4, v5, v6):
            v.value = "--"
        cat_box.bgcolor       = "#2e7d32"
        cat_box.content.value = "CONSUMER CATEGORY : Press Calculate"
        bill_col.controls.clear()
        bill_box.visible = False
        btn_rep.visible  = False

    def apply_res(d):
        prot = "Protected" in d["ctype"]
        v1.value = f"{d['total']} Units"
        v2.value = f"{d['lastday']} Units"
        v3.value = f"{d['rem_u']} Units"
        v4.value = f"{d['rem_d']} Days"
        v5.value = f"{d['avg']} Units"
        v6.value = f"Rs. {d['bill']:,}"
        s6.value = "Protected" if prot else "Unprotected"
        cat_box.bgcolor       = "#2e7d32" if prot else "#b71c1c"
        cat_box.content.value = f"CONSUMER CATEGORY : {d['ctype']}"
        bill_col.controls = [
            ft.Container(
                ft.Row([
                    ft.Text("BILLING BREAKDOWN (EST.)", size=10,
                            weight=ft.FontWeight.BOLD, color="#8faabf", expand=True),
                    ft.Text("Estimated Cost", size=10,
                            weight=ft.FontWeight.BOLD, color="#8faabf"),
                ]),
                padding=ft.Padding(10, 5, 10, 5),
            ),
            brow("Energy Charges (Total)",         d["energy"]),
            brow("FPA  @  Rs.2.50/unit",           d["fpa"]),
            brow("Meter Rent + TV Fee",             d["fixed"]),
            brow("SUBTOTAL", d["sub"], lc=GOLD, vc=GOLD, bold=True),
            ft.Divider(color="#2a5080", height=1),
            brow("General Sales Tax  GST 17%",      d["gst"]),
            ft.Container(
                ft.Row([
                    ft.Text("  GRAND TOTAL (Est.)", size=13,
                            weight=ft.FontWeight.BOLD, color="white", expand=True),
                    ft.Text(f"Rs. {d['bill']:,}  *", size=13,
                            weight=ft.FontWeight.BOLD, color=GOLD),
                ]),
                bgcolor="#1b5e20", border_radius=6,
                padding=ft.Padding(10, 8, 10, 8),
            ),
        ]
        bill_box.visible = True
        btn_rep.visible  = True

    def do_calc(_):
        try:
            sr = float(f_st.value.strip()  or 0)
            cr = float(f_cur.value.strip() or 0)
            pr = float(f_pre.value.strip() or 0)
            r  = run_calc(sr, cr, pr, bstart["d"])
            n  = active[0]
            cache[n] = r
            apply_res(r)
            save_cur()
            page.update()
        except Exception as ex:
            page.overlay.append(ft.AlertDialog(
                open=True,
                title=ft.Text("Error"),
                content=ft.Text(f"Enter valid numbers!\n{ex}"),
                actions=[ft.TextButton("OK", on_click=lambda _: page.update())],
            ))
            page.update()

    calc_btn = ft.FilledButton(
        content=ft.Text("⚡  Calculate  /  حساب کریں", color="white",
                        weight=ft.FontWeight.BOLD, size=15),
        bgcolor=GRN, height=48,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=do_calc,
    )

    def inp_row(label_widget, field, hint_text):
        return ft.Container(
            ft.Row([
                ft.Container(label_widget, width=120,
                             alignment=ft.Alignment(-1, 0)),
                ft.Container(field, expand=True),
                ft.Container(ft.Text(hint_text, size=10, color="#8faabf"), width=140),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=INP, border_radius=6, padding=ft.Padding(4, 2, 4, 2),
        )

    def lbl(text, color):
        return ft.Container(
            ft.Text(text, color="white", size=11, weight=ft.FontWeight.BOLD),
            bgcolor=color, border_radius=5, padding=ft.Padding(8, 8, 8, 8),
        )

    inp_sec = ft.Container(
        ft.Column([
            inp_row(lbl("Account", TEAL), f_acc, "Account No."),
            inp_row(btn_date,             f_st,  "Start Reading"),
            inp_row(lbl((datetime.now()-timedelta(days=1)).strftime("%d-%b"), "#1a6fa8"),
                    f_cur, "Current Reading"),
            inp_row(lbl("Prev Read", "#c0622b"), f_pre, "Previous Reading"),
            ft.Container(
                ft.Row([
                    ft.Container(lbl("Days Elapsed", "#5b2d8e"), width=120),
                    ft.Container(days_txt, expand=True,
                                 padding=ft.Padding(8, 0, 0, 0)),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=INP, border_radius=6, padding=ft.Padding(4, 4, 4, 4),
            ),
        ], spacing=3),
        bgcolor=INP, border_radius=8, padding=6,
    )

    meter_bar = ft.Container(
        ft.Row(
            [ft.Text("Select Meter:", color="#8faabf", size=11,
                     weight=ft.FontWeight.BOLD)]
            + list(m_btns.values()),
            spacing=6, scroll=ft.ScrollMode.AUTO,
        ),
        bgcolor="#0a1520", padding=ft.Padding(12, 8, 12, 8), border_radius=8,
    )

    page.add(
        ft.Column([
            ft.Row([
                ft.Text("Ecal_v24", size=18, weight=ft.FontWeight.BOLD, color="white"),
                ft.Column([
                    clk,
                    ft.Text(datetime.now().strftime("%B %Y"), size=11, color=ACC),
                ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            meter_bar,
            inp_sec,
            ft.Row([calc_btn], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([c1, c2, c3], spacing=5),
            ft.Row([c4, c5, c6], spacing=5),
            cat_box,
            bill_box,
            ft.Row([btn_rep], alignment=ft.MainAxisAlignment.CENTER),
            rep_box,
        ], spacing=8)
    )

    m1 = saved[_meter_key(1)]
    if m1["start_date"]:
        try: bstart["d"] = date.fromisoformat(m1["start_date"])
        except Exception: pass
    btn_date.content.value = bstart["d"].strftime("%d-%b")
    f_acc.value = m1["meter_number"]
    f_st.value  = m1["start_reading"]
    f_cur.value = m1["curr_reading"]
    f_pre.value = m1["prev_reading"]
    upd_elapsed()
    page.update()
    page.run_task(clock_loop)


ft.app(main)
