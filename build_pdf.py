#!/usr/bin/env python3
"""build_pdf.py (v2) -> weekly_note.pdf, designed one-pager from pulse_data.json."""
import json, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"output"; OUT.mkdir(exist_ok=True)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT

VIOLET=HexColor("#5A31F4"); VIOLET_D=HexColor("#3B1FA8")
INK=HexColor("#15131F"); MUTE=HexColor("#6B6780"); LINE=HexColor("#E6E3F0")
NEG=HexColor("#D7263D"); WARN=HexColor("#D88A00"); POS=HexColor("#1B998B")
SOFT=HexColor("#F4F1FF"); WHITE=HexColor("#FFFFFF")

d=json.load(open(OUT/"pulse_data.json"))
W,H=A4; M=15*mm
c=canvas.Canvas(str(OUT/"weekly_note.pdf"), pagesize=A4)

def ps(sz,col,lead=None,bold=False):
    return ParagraphStyle("s",fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=sz,textColor=col,leading=lead or sz*1.3,alignment=TA_LEFT)
def para(t,style,x,y,w):
    p=Paragraph(t,style); _,ph=p.wrap(w,1000); p.drawOn(c,x,y-ph); return ph
def negcol(p): return NEG if p>=60 else (WARN if p>=40 else POS)

# header
c.setFillColor(VIOLET); c.rect(0,H-30*mm,W,30*mm,fill=1,stroke=0)
c.setFillColor(VIOLET_D); c.rect(0,H-30*mm,5*mm,30*mm,fill=1,stroke=0)
c.setFillColor(WHITE); c.setFont("Helvetica-Bold",20)
c.drawString(M,H-15*mm,"INDmoney — Weekly Review Pulse")
c.setFillColor(HexColor("#E7E1FF")); c.setFont("Helvetica",10)
c.drawString(M,H-22*mm,f"Week of {d['pulse_week']}, 2026  ·  App Store + Play Store")
k=d["kpi"]; arr="▲" if k["delta"]>0 else ("▼" if k["delta"]<0 else "=")
chip=f"Avg {k['avg']:.2f} {arr}  ({k['delta']:+.2f} WoW)"
cw=c.stringWidth(chip,"Helvetica-Bold",10)+9*mm
c.setFillColor(WHITE); c.roundRect(W-M-cw,H-21*mm,cw,7.5*mm,2*mm,fill=1,stroke=0)
c.setFillColor(VIOLET_D); c.setFont("Helvetica-Bold",10)
c.drawCentredString(W-M-cw/2,H-18.4*mm,chip)

y=H-30*mm-7*mm
# headline band
c.setFillColor(SOFT); c.roundRect(M,y-12*mm,W-2*M,12*mm,2.5*mm,fill=1,stroke=0)
c.setFillColor(VIOLET); c.setFont("Helvetica-Bold",8)
c.drawString(M+4*mm,y-4.6*mm,"HEADLINE")
para(d["headline"], ps(9.7,INK,12), M+4*mm, y-5.2*mm, W-2*M-8*mm)
y-=12*mm+6*mm

# KPI strip
kpis=[(str(k["n"]),"reviews this week"),(f"{k['negPct']}%","negative (1–2★)"),
      (str(k["src"].get("App Store",0)),"App Store"),(str(k["src"].get("Play Store",0)),"Play Store")]
kw=(W-2*M-9*mm)/4
for i,(big,small) in enumerate(kpis):
    x=M+i*(kw+3*mm)
    c.setFillColor(SOFT); c.roundRect(x,y-16*mm,kw,16*mm,2*mm,fill=1,stroke=0)
    c.setFillColor(VIOLET); c.setFont("Helvetica-Bold",17); c.drawString(x+4*mm,y-8.5*mm,big)
    c.setFillColor(MUTE); c.setFont("Helvetica",7.5); c.drawString(x+4*mm,y-13*mm,small)
y-=16*mm+7*mm

def section(txt,y):
    c.setFillColor(VIOLET); c.rect(M,y-1*mm,1.5*mm,3.5*mm,fill=1,stroke=0)
    c.setFillColor(INK); c.setFont("Helvetica-Bold",12); c.drawString(M+4*mm,y-1*mm,txt)
    c.setStrokeColor(LINE); c.setLineWidth(0.6); c.line(M,y-4*mm,W-M,y-4*mm)
    return y-10*mm

# 12-week pulse sparkline (avg rating, auto-zoomed)
y=section("12-week pulse",y)
sx,sw,sh=M, W-2*M, 16*mm
av=d["pulse_avg"]; n=len(av)
lo=max(1.0, min(av)-0.2); hi=min(5.0, max(av)+0.2)
if hi-lo < 0.4: hi=lo+0.4
def xx(i): return sx+i*(sw/(n-1))
def yy(v): return (y-sh) + (v-lo)/(hi-lo)*sh
c.setStrokeColor(LINE); c.setLineWidth(0.5); c.setFillColor(MUTE); c.setFont("Helvetica",6)
import math
g=lo
while g<=hi+1e-6:
    gy=yy(g); c.line(sx,gy,sx+sw,gy); c.drawRightString(sx-1.5*mm,gy-1.2,f"{g:.1f}"); g+=round((hi-lo)/2,1) or 0.2
c.setStrokeColor(VIOLET); c.setLineWidth(1.8)
path=c.beginPath(); path.moveTo(xx(0),yy(av[0]))
for i in range(1,n): path.lineTo(xx(i),yy(av[i]))
c.drawPath(path,stroke=1,fill=0)
for i in range(n):
    r=2.4 if i==n-1 else 1.2
    c.setFillColor(VIOLET); c.circle(xx(i),yy(av[i]),r,fill=1,stroke=0)
c.setFillColor(MUTE); c.setFont("Helvetica",6.3)
for i in range(0,n,2):
    c.drawCentredString(xx(i),y-sh-3*mm,d["weeks"][i].split("-")[0])
c.drawString(sx,y-sh-3*mm-3.5*mm,"avg rating per week — declining over the window (latest week highlighted)")
y-=sh+10*mm

# Top 3 themes with priority + mini trend
y=section("Top 3 themes (by priority)",y)
for i,t in enumerate(d["top_themes"],1):
    wow=t["wow"]; wows=f"+{wow}" if wow>0 else str(wow)
    c.setFillColor(VIOLET); c.circle(M+3*mm,y-1.5*mm,3*mm,fill=1,stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",9); c.drawCentredString(M+3*mm,y-3*mm,str(i))
    c.setFillColor(INK); c.setFont("Helvetica-Bold",10.5); c.drawString(M+9*mm,y-3*mm,t["theme"])
    nmw=c.stringWidth(t["theme"],"Helvetica-Bold",10.5)
    # priority badge
    pb=f"priority {t['priority']}/100"
    c.setFont("Helvetica-Bold",7.5); pbw=c.stringWidth(pb,"Helvetica-Bold",7.5)+5*mm
    bx0=M+9*mm+nmw+3*mm
    c.setFillColor(SOFT); c.roundRect(bx0,y-4*mm,pbw,5*mm,1.5*mm,fill=1,stroke=0)
    c.setFillColor(VIOLET); c.drawString(bx0+2.5*mm,y-2.7*mm,pb)
    c.setFillColor(MUTE); c.setFont("Helvetica",8.3)
    c.drawString(M+9*mm,y-8*mm,f"{t['count']} mentions · {wows} WoW · avg {t['avg']:.2f}★ · {t['negPct']}% negative")
    # right side: negativity bar (top) + 12-week mention trend (below), clearly separated
    bx,bw=W-M-44*mm,44*mm
    c.setFillColor(MUTE); c.setFont("Helvetica",6); c.drawString(bx,y-0.2*mm,"negativity")
    c.setFillColor(LINE); c.roundRect(bx,y-3.2*mm,bw,2.2*mm,1*mm,fill=1,stroke=0)
    c.setFillColor(negcol(t["negPct"])); c.roundRect(bx,y-3.2*mm,bw*t["negPct"]/100,2.2*mm,1*mm,fill=1,stroke=0)
    tr=d["trend"][t["theme"]]["counts"]; mx=max(tr) or 1
    c.setFillColor(MUTE); c.setFont("Helvetica",6); c.drawString(bx,y-6.4*mm,"12-wk mentions")
    th=3.6*mm; topy=y-8.0*mm
    c.setStrokeColor(VIOLET); c.setLineWidth(0.9); pth=c.beginPath()
    for j,vv in enumerate(tr):
        px=bx+j*(bw/(len(tr)-1)); py=topy-th + (vv/mx)*th
        (pth.moveTo if j==0 else pth.lineTo)(px,py)
    c.drawPath(pth,stroke=1,fill=0)
    y-=12.5*mm

# quotes
y=section("In users' words",y)
for q in d["quotes"]:
    c.setFillColor(VIOLET); c.rect(M,y-8*mm,1.2*mm,8*mm,fill=1,stroke=0)
    ph=para(f"“{q['text']}”", ps(9.3,INK,12), M+4*mm, y, W-2*M-4*mm)
    c.setFillColor(MUTE); c.setFont("Helvetica-Oblique",7.6)
    c.drawString(M+4*mm,y-ph-3.2*mm,f"{q['rating']}★ · {q['source']} · {q['theme']}")
    y-=ph+8.5*mm

# actions
y=section("Three action ideas",y)
for i,a in enumerate(d["actions"],1):
    c.setFillColor(VIOLET); c.setFont("Helvetica-Bold",10); c.drawString(M,y-3*mm,f"{i}.")
    ph=para(a, ps(9.3,INK,12), M+6*mm, y, W-2*M-6*mm)
    y-=max(ph,5*mm)+3*mm

# footer
c.setStrokeColor(LINE); c.setLineWidth(0.6); c.line(M,M+8*mm,W-M,M+8*mm)
c.setFillColor(MUTE); c.setFont("Helvetica",7)
c.drawString(M,M+4.5*mm,"Source: public App Store + Play Store review exports (redacted sample, 12-week window). No PII.")
c.drawString(M,M+1.8*mm,f"Max 5 themes · priority = negativity × volume × momentum · Generated {datetime.date.today().isoformat()} · Review Pulse")
c.showPage(); c.save()
print("Wrote weekly_note.pdf")
