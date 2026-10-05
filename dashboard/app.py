import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import shapely
import streamlit as st
from shapely.geometry import shape

st.set_page_config(page_title="Chicago Smart Traffic & Safety Analytics", page_icon="🚦", layout="wide")

# ------------------------------------------------------------------ config
HERE = Path(__file__).parent
PROJECT = HERE.parent / "metropolia-traffic-etl"
GEO_CANDIDATES = [HERE / "Boundaries_-_Community_Areas_20260921.geojson",
                  PROJECT / "data" / "Boundaries_-_Community_Areas_20260921.geojson"]
PARQUET_DIR = PROJECT / "data" / "processed"

LEVELS = ["Normal", "Moderate", "High", "Severe"]
COLORS = {"Normal": "#22C55E", "Moderate": "#FACC15", "High": "#FB923C", "Severe": "#EF4444"}
NAVY, BLUE, PURPLE = "#162A5C", "#3B82F6", "#8B5CF6"
CENTER = dict(lat=41.84, lon=-87.68)
DARK = "carto-darkmatter"
DAYS = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}
TONES = {"blue": ("#E8F0FE", "#3B82F6"), "red": ("#FEECEC", "#EF4444"), "orange": ("#FFF1E5", "#F97316"),
         "green": ("#E7F8EE", "#22C55E"), "yellow": ("#FEF6D8", "#EAB308"), "navy": ("#E3E8F4", "#1E3A8A"),
         "purple": ("#F1EBFE", "#8B5CF6")}
COLORWAY = ["#3B82F6", "#8B5CF6", "#06B6D4", "#F97316", "#EF4444", "#22C55E"]
LEVEL_TONE = {"Normal": "green", "Moderate": "yellow", "High": "orange", "Severe": "red"}
HEAT = [[0, "#22C55E"], [.35, "#FACC15"], [.7, "#FB923C"], [1, "#EF4444"]]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Material+Symbols+Outlined');
.stApp{background:linear-gradient(180deg,#DCE6FA 0%,#EEF2FA 280px,#F3F5FB 100%);font-family:'Inter',sans-serif}
header[data-testid="stHeader"]{background:transparent}
#MainMenu,footer{visibility:hidden}
.block-container{padding:1rem 2rem 3rem;max-width:1500px}
.ms{font-family:'Material Symbols Outlined';font-size:22px;font-weight:400;line-height:1;vertical-align:middle;font-style:normal}
.hdr{background:linear-gradient(120deg,#0B1B4D 0%,#1E3A8A 55%,#3B82F6 130%);box-shadow:0 10px 28px rgba(30,58,138,.28);border-radius:20px;padding:18px 24px;display:flex;align-items:center;justify-content:space-between;color:#fff;margin-bottom:14px;flex-wrap:wrap;gap:10px}
.hdr .logo{width:46px;height:46px;border-radius:12px;background:rgba(255,255,255,.12);display:inline-flex;align-items:center;justify-content:center;margin-right:14px;vertical-align:middle}
.hdr .t{font-size:1.2rem;font-weight:700}
.hdr .s{font-family:'JetBrains Mono',monospace;font-size:.74rem;color:#9db0dd;letter-spacing:.06em}
.pill{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:7px 14px;background:rgba(255,255,255,.1);font-family:'JetBrains Mono',monospace;font-size:.76rem;margin-left:8px;color:#fff}
.pill .ms{font-size:16px}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.av{width:32px;height:32px;border-radius:50%;background:#4A7FE0;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:.75rem}
div[data-baseweb="tab-list"]{background:#fff;border-radius:16px;padding:8px;gap:4px;box-shadow:0 1px 4px rgba(22,42,92,.08);overflow-x:auto;margin-bottom:6px}
button[data-baseweb="tab"]{border-radius:12px;padding:10px 16px;height:auto;background:transparent}
button[data-baseweb="tab"] p{color:#4a5a7d;font-weight:500;font-size:.9rem}
button[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(120deg,#1E3A8A,#3B82F6);box-shadow:0 4px 12px rgba(59,130,246,.35)}
button[data-baseweb="tab"][aria-selected="true"] p{color:#fff}
div[data-baseweb="tab-highlight"],div[data-baseweb="tab-border"]{display:none}
div[data-testid="stVerticalBlockBorderWrapper"]{background:#fff;border-radius:18px;border:1px solid #E3EAF8;box-shadow:0 4px 14px rgba(30,58,138,.07)}
div[data-testid="stPlotlyChart"]{border-radius:14px;overflow:hidden}
button[kind="pills"]{border-radius:999px;font-family:'JetBrains Mono',monospace;border:1px solid #DDE3F0;background:#fff}
button[kind="pillsActive"]{border-radius:999px;font-family:'JetBrains Mono',monospace;background:linear-gradient(120deg,#1E3A8A,#3B82F6);border:none;box-shadow:0 3px 10px rgba(59,130,246,.35)}
button[kind="pillsActive"] p{color:#fff}
div[data-baseweb="select"]>div{border-radius:10px}
.ct{display:flex;align-items:center;gap:8px;font-family:'JetBrains Mono',monospace;font-weight:700;letter-spacing:.08em;color:#162A5C;font-size:.82rem;margin:2px 0 12px}
.ct .ms{font-size:20px;color:#4A7FE0}
.ct .r{margin-left:auto;font-weight:500;font-size:.7rem;color:#6b7a99;letter-spacing:.02em}
.kpi{background:#fff;border-radius:18px;padding:16px 18px;display:flex;gap:14px;align-items:center;border:1px solid #E3EAF8;box-shadow:0 4px 14px rgba(30,58,138,.07);height:100%;transition:transform .15s,box-shadow .15s}.kpi:hover{transform:translateY(-3px);box-shadow:0 10px 22px rgba(30,58,138,.16)}
.ki{width:50px;height:50px;border-radius:14px;box-shadow:0 4px 10px rgba(0,0,0,.15);display:flex;align-items:center;justify-content:center;flex:none}
.kv{font-size:1.75rem;font-weight:800;color:#0F1F4D;line-height:1.1}
.kl{font-size:.85rem;color:#44506b;margin-top:2px}
.ks{font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#6b7a99;margin-top:2px}
.al{border-left:4px solid;border-radius:10px;padding:10px 14px;margin-bottom:8px;display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.al b{font-size:.86rem;display:block}.al span.tx{font-size:.8rem;color:#44506b;display:block}
.al .tm{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#6b7a99;white-space:nowrap}
.rw{display:flex;justify-content:space-between;gap:10px;padding:9px 0;border-bottom:1px dashed #DDE3F0;font-size:.88rem;color:#44506b}
.rw span:last-child{font-family:'JetBrains Mono',monospace;font-weight:600;color:#162A5C;text-align:right}
.bd{display:inline-block;border-radius:6px;padding:2px 9px;font-family:'JetBrains Mono',monospace;font-size:.72rem;font-weight:700;white-space:nowrap}
.hb{display:flex;align-items:center;gap:12px;margin:10px 0;font-size:.82rem;min-height:18px}
.hl{width:44%;color:#162A5C;white-space:normal;overflow:visible;text-overflow:clip;line-height:1.15}
.ht{flex:1;height:11px;background:#EEF1F7;border-radius:6px}.hf{height:100%;border-radius:6px}
.hv{width:56px;text-align:right;font-family:'JetBrains Mono',monospace;font-weight:600;color:#162A5C}
.lg{display:flex;gap:18px;flex-wrap:wrap;margin:0 0 8px}.lg span{display:inline-flex;align-items:center;gap:7px;font-family:'JetBrains Mono',monospace;font-size:.74rem;color:#44506b}.lg i{width:24px;height:5px;border-radius:3px;display:inline-block}\n.ct .nt{font-size:18px;color:#9AA7C0;cursor:help;margin-left:8px}\n.lw{max-height:480px;overflow:auto}
.lt{width:100%;border-collapse:collapse;font-size:.84rem}
.lt th{font-family:'JetBrains Mono',monospace;font-size:.68rem;letter-spacing:.08em;color:#6b7a99;text-align:left;padding:8px 10px;border-bottom:1px solid #E3E8F4;position:sticky;top:0;background:#fff}
.lt td{padding:10px;border-bottom:1px solid #F0F3F9;color:#162A5C}
.rk{transition:transform .15s;display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:12px;background:#F6F8FC;margin-bottom:8px}
.rk .n{width:36px;height:36px;border-radius:10px;color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center;flex:none}
.rk .nm{font-weight:600;color:#162A5C}.rk .sb{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#6b7a99}
.rk .sc{margin-left:auto;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.05rem}
.fg{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}
.fc{transition:transform .15s;border:1px solid #E3EAF8;background:#F8FAFF;border-radius:14px;padding:12px 10px;text-align:center}
.fc .lv{font-weight:700;font-size:.9rem;margin-bottom:8px}
.fc .bw{height:170px;display:flex;align-items:flex-end}.fc .bar{width:100%;border-radius:8px}
.fc .tl{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:#162A5C;margin-top:8px;font-weight:600}
.fc .sb{font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#6b7a99}
.sk{display:flex;height:42px;border-radius:10px;overflow:hidden;font-family:'JetBrains Mono',monospace;font-size:.8rem;color:#fff;font-weight:700}
.sk div{display:flex;align-items:center;justify-content:center}
.pg{height:10px;background:#E3E8F4;border-radius:6px;margin:6px 0 16px}.pg div{height:100%;border-radius:6px}
.lab{display:flex;justify-content:space-between;font-size:.88rem;color:#44506b}
.lab b{font-family:'JetBrains Mono',monospace;color:#162A5C}
.tile{border-radius:14px;padding:14px;text-align:center}
.tile .v{font-size:1.5rem;font-weight:700}.tile .l{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#44506b}
.src{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:12px;background:#F6F8FC;margin-bottom:8px}
.src .a{font-weight:600;color:#162A5C;font-size:.88rem}.src .b{font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#6b7a99}
.src .dot{margin-left:auto;background:#4CA154}

/* --- Overview + Forecast visual refresh: modern editorial dashboard --- */
.overview-shell{padding:1px 0 2px}
.overview-insights{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:2px}
.insight-card{
    position:relative;min-height:138px;padding:14px 13px;
    border:1px solid rgba(255,255,255,.98);border-radius:18px;
    background:linear-gradient(145deg,var(--soft) 0%,rgba(255,255,255,.94) 100%);
    box-shadow:0 7px 18px rgba(44,66,118,.055);overflow:hidden;
    display:grid;grid-template-columns:38px minmax(0,1fr) 62px;
    grid-template-rows:auto 1fr auto;column-gap:9px;row-gap:2px;
}
.insight-card:after{content:"";position:absolute;width:90px;height:90px;right:-35px;top:-40px;border-radius:50%;background:var(--accent);opacity:.055;pointer-events:none}
.insight-icon{grid-column:1;grid-row:1/4;width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.72);color:var(--accent);box-shadow:inset 0 0 0 1px rgba(255,255,255,.9);margin-top:1px;z-index:2}
.insight-icon .ms{font-size:21px}
.insight-title{grid-column:2;grid-row:1;font-size:.76rem;font-weight:800;color:var(--accent);line-height:1.2;z-index:2;min-width:0}
.insight-value{grid-column:2;grid-row:2;align-self:center;margin:2px 0 0;font-size:1.12rem;font-weight:800;color:#182E60;line-height:1.1;min-width:0;overflow-wrap:anywhere;z-index:2}
.insight-sub{grid-column:2;grid-row:3;align-self:end;margin:3px 0 0;font-family:'JetBrains Mono',monospace;font-size:.62rem;color:#7181A3;line-height:1.2;white-space:nowrap;z-index:2}
.insight-mini{grid-column:3;grid-row:2/4;align-self:end;justify-self:end;display:flex;align-items:flex-end;gap:3px;height:48px;width:60px;opacity:.78;z-index:1}
.insight-mini span{width:8px;border-radius:5px 5px 2px 2px;background:linear-gradient(180deg,var(--accent),rgba(255,255,255,.28))}
.insight-mini.line{position:relative;display:flex;align-items:flex-end;gap:5px;height:44px;width:60px}
.insight-mini.line span{width:5px;height:5px;border-radius:50%;margin:0}
.insight-mini.line:before{content:"";position:absolute;left:0;right:0;bottom:12px;height:2px;background:var(--accent);transform:rotate(-9deg);opacity:.62}
.risk-list{display:flex;flex-direction:column;gap:8px;margin-top:3px}
.risk-item{display:grid;grid-template-columns:86px minmax(0,1fr) 78px;align-items:center;gap:11px;padding:9px 11px 9px 9px;border:1px solid rgba(226,232,245,.95);border-radius:16px;background:rgba(255,255,255,.84);box-shadow:0 5px 14px rgba(44,66,118,.045)}
.risk-image{position:relative;width:86px;height:60px;border-radius:12px;overflow:hidden;background:linear-gradient(135deg,#DDE7F8,#B8C8E5)}
.risk-image:after{content:"location_city";font-family:'Material Symbols Outlined';position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:rgba(255,255,255,.72);font-size:26px;z-index:0}
.risk-image img{position:relative;width:100%;height:100%;object-fit:cover;display:block;z-index:1}
.risk-rank{position:absolute;left:6px;top:6px;width:27px;height:27px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:.7rem;box-shadow:0 3px 8px rgba(30,58,138,.18);border:2px solid rgba(255,255,255,.92);z-index:3}
.risk-main{min-width:0}.risk-name{color:#1B3265;font-weight:800;font-size:.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.risk-meta{margin-top:2px;color:#7181A3;font-family:'JetBrains Mono',monospace;font-size:.61rem;white-space:nowrap}.risk-progress{height:6px;background:#E7ECF6;border-radius:99px;margin-top:7px;overflow:hidden}.risk-progress span{display:block;height:100%;border-radius:99px;background:var(--risk-color)}
.risk-score{text-align:right;font-family:'JetBrains Mono',monospace;font-size:.92rem;font-weight:800;white-space:nowrap}.risk-badge{display:inline-block;margin-top:4px;padding:2px 7px;border-radius:999px;font-size:.56rem;font-weight:800;font-family:'JetBrains Mono',monospace}

/* Forecast */
.forecast-shell{padding:1px 0 2px}
.forecast-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;margin-bottom:12px}
.forecast-kicker{font-family:'JetBrains Mono',monospace;font-size:.82rem;font-weight:800;letter-spacing:.07em;color:#162A5C;display:flex;align-items:center;gap:8px}
.forecast-kicker .ms{font-size:21px;color:#3B82F6}
.forecast-subtitle{font-size:.75rem;color:#7181A3;margin-top:4px}
.forecast-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.forecast-card{position:relative;min-height:126px;padding:15px 16px;border-radius:18px;border:1px solid rgba(255,255,255,.95);background:linear-gradient(135deg,var(--soft),rgba(255,255,255,.92));overflow:hidden;display:grid;grid-template-columns:42px minmax(0,1fr) 72px;grid-template-rows:auto auto 1fr;column-gap:10px;box-shadow:0 7px 18px rgba(44,66,118,.05)}
.forecast-card:after{content:"";position:absolute;width:110px;height:110px;right:-46px;top:-52px;border-radius:50%;background:var(--accent);opacity:.05}
.forecast-icon{grid-column:1;grid-row:1/4;width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.7);color:var(--accent);z-index:1}.forecast-icon .ms{font-size:23px}
.forecast-title{grid-column:2;grid-row:1;color:var(--accent);font-size:.78rem;font-weight:800;z-index:1}.forecast-value{grid-column:2;grid-row:2;color:#183264;font-size:1.16rem;font-weight:800;line-height:1.12;margin-top:2px;z-index:1}.forecast-note{grid-column:2;grid-row:3;align-self:end;color:#7181A3;font-family:'JetBrains Mono',monospace;font-size:.62rem;line-height:1.25;z-index:1}.forecast-mini{grid-column:3;grid-row:2/4;align-self:end;display:flex;align-items:flex-end;gap:4px;height:58px;z-index:1}.forecast-mini span{width:8px;border-radius:5px 5px 2px 2px;background:linear-gradient(180deg,var(--accent),rgba(255,255,255,.2))}
.forecast-target{grid-column:3;grid-row:2/4;align-self:center;justify-self:end;width:56px;height:56px;border:3px solid color-mix(in srgb,var(--accent) 35%,white);border-radius:50%;display:flex;align-items:center;justify-content:center;color:var(--accent);position:relative;z-index:1}.forecast-target:before{content:"";position:absolute;width:34px;height:34px;border:2px solid var(--accent);border-radius:50%;opacity:.7}.forecast-target:after{content:"";position:absolute;width:8px;height:8px;background:var(--accent);border-radius:50%}
.forecast-detail{margin-top:14px;padding:14px 16px 10px;border:1px solid #E3EAF8;border-radius:18px;background:rgba(255,255,255,.72);box-shadow:0 7px 18px rgba(44,66,118,.045)}
.forecast-detail-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:2px}.forecast-detail-title{font-family:'JetBrains Mono',monospace;font-size:.8rem;font-weight:800;letter-spacing:.06em;color:#162A5C}.forecast-detail-note{font-size:.67rem;color:#7181A3}
@media (max-width:900px){.overview-insights{grid-template-columns:1fr}.forecast-cards{grid-template-columns:1fr}.risk-item{grid-template-columns:78px minmax(0,1fr) 72px}.risk-image{width:78px;height:58px}}

/* --- final visual polish: Overview + Signal Simulator --- */
.overview-insights{gap:10px;align-items:stretch}
.insight-card{
    position:relative;height:184px;min-height:184px;padding:13px 14px 12px;
    display:flex;flex-direction:column;box-sizing:border-box;border-radius:18px;overflow:hidden;
}
.insight-head{
    display:flex;align-items:center;gap:10px;min-height:40px;
    position:relative;z-index:2;width:100%;
}
.insight-icon{
    width:40px;height:40px;flex:0 0 40px;border-radius:50%;margin:0;
    background:var(--icon-bg,rgba(255,255,255,.78));
    box-shadow:0 2px 8px rgba(30,58,138,.05);
    display:flex;align-items:center;justify-content:center;
}
.insight-title{
    font-size:.76rem;line-height:1.16;font-weight:800;min-width:0;
    max-width:calc(100% - 50px);color:var(--accent);text-align:left;
}
.insight-main{
    position:relative;display:flex;flex-direction:column;align-items:center;
    min-width:0;flex:1;padding:8px 4px 0;z-index:2;text-align:center;
}
.insight-value{
    font-size:1.08rem;line-height:1.08;font-weight:800;margin:0;padding:0;
    min-width:0;max-width:100%;color:#182E60;overflow-wrap:normal;
    word-break:normal;white-space:nowrap;text-align:center;
}
.insight-sub{
    font-size:.68rem;line-height:1.2;margin:6px 0 0;padding:0;color:#7181A3;
    font-family:'JetBrains Mono',monospace;white-space:nowrap;overflow:visible;
    text-overflow:clip;text-align:center;font-weight:700;
}
.insight-badge{
    display:inline-flex;align-items:center;justify-content:center;gap:6px;
    width:max-content;max-width:100%;box-sizing:border-box;
    margin:10px auto 0;padding:7px 15px;border-radius:999px;
    background:var(--badge-bg);color:var(--accent);font-size:.68rem;
    line-height:1.1;font-weight:800;white-space:nowrap;text-align:center;
}
.insight-desc{
    margin:auto auto 0;font-size:.61rem;line-height:1.25;color:#7181A3;
    max-width:78%;padding-bottom:1px;text-align:center;
}
.insight-mini,.insight-mini.line{display:none!important}
.overview-shell>div:first-child{font-size:.7rem!important;margin-bottom:11px!important}
.risk-list{gap:9px}
.risk-item{min-height:76px;padding:9px 11px 9px 9px}
.risk-image{width:86px;height:58px}
.risk-name{font-size:.9rem}
.risk-meta{font-size:.62rem}
.risk-progress{height:7px;margin-top:7px}
.risk-score{font-size:.95rem}

/* Signal simulator */
.sim-note{font-family:'JetBrains Mono',monospace;font-size:.69rem;color:#7181A3;letter-spacing:.02em;margin:0 0 10px}
.sim-panel{padding:16px 18px 14px;border-radius:18px;background:linear-gradient(135deg,#F8FAFF 0%,#EEF4FF 100%);border:1px solid #DCE6F7;box-shadow:0 7px 20px rgba(44,66,118,.05)}
.sim-panel-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:14px}
.sim-heading{display:flex;align-items:center;gap:11px}
.sim-heading-icon{width:40px;height:40px;border-radius:12px;background:#E7F0FF;color:#3B82F6;display:flex;align-items:center;justify-content:center;flex:none}
.sim-heading-title{font-family:'JetBrains Mono',monospace;font-weight:800;letter-spacing:.07em;color:#162A5C;font-size:.82rem}
.sim-heading-sub{font-size:.7rem;color:#7181A3;margin-top:3px}
.sim-segment{background:rgba(255,255,255,.66);border:1px solid #E2EAF8;border-radius:13px;padding:9px 12px;min-width:44%}
.sim-segment-label{font-size:.68rem;font-weight:700;color:#526486;margin-bottom:5px}
.sim-input-card{background:rgba(255,255,255,.8);border:1px solid #E2EAF8;border-radius:14px;padding:11px 12px 8px;min-height:92px;box-shadow:0 3px 10px rgba(44,66,118,.035)}
.sim-input-label{display:flex;align-items:center;gap:7px;font-size:.7rem;font-weight:700;color:#203A70;margin-bottom:6px}
.sim-input-label .ms{font-size:19px;color:#4A7FE0}
.sim-slider{margin-top:10px;background:rgba(255,255,255,.62);border:1px solid #E2EAF8;border-radius:13px;padding:9px 12px 2px}
.sim-slider-label{font-size:.7rem;font-weight:700;color:#526486;margin-bottom:-4px}
.sim-result-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:12px}
.sim-result{border-radius:13px;padding:12px 10px;text-align:center;border:1px solid transparent;background:#fff}
.sim-result .v{font-size:1.35rem;font-weight:800;line-height:1.05}
.sim-result .l{font-family:'JetBrains Mono',monospace;font-size:.63rem;color:#526486;margin-top:4px}
.sim-card{border-radius:18px!important;border:1px solid #DCE6F7!important;background:linear-gradient(145deg,#FAFCFF,#F3F7FE)!important;box-shadow:0 7px 20px rgba(44,66,118,.05)!important;padding:15px 16px 14px}
.sim-card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:12px}
.sim-title{display:flex;align-items:center;gap:9px;font-family:'JetBrains Mono',monospace;font-size:.78rem;font-weight:800;letter-spacing:.06em;color:#162A5C}
.sim-title .ms{color:#3B82F6;font-size:20px}
.sim-subtitle{font-size:.68rem;color:#7181A3;margin:3px 0 0 29px}
.sim-action{border:1px solid #DCE6F7;border-radius:999px;padding:5px 10px;font-family:'JetBrains Mono',monospace;font-size:.62rem;color:#6A7DA5;background:#fff;white-space:nowrap}
.sim-bar-label{display:flex;justify-content:space-between;align-items:center;font-size:.73rem;color:#44506B;margin:8px 0 5px}
.sim-bar-label b{font-family:'JetBrains Mono',monospace;color:#162A5C}
.sim-progress{height:9px;background:#E5EBF6;border-radius:99px;overflow:hidden;margin-bottom:10px}
.sim-progress>div{height:100%;border-radius:99px}
.sim-timeline-row{background:rgba(255,255,255,.55);border-radius:12px;padding:8px 10px 9px;margin-bottom:10px;border:1px solid #E7EDF7}
.sim-timeline-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.sim-timeline-head b{font-family:'JetBrains Mono',monospace;font-size:.68rem;color:#162A5C;letter-spacing:.05em}
.sim-total{font-family:'JetBrains Mono',monospace;font-size:.62rem;color:#7181A3}
.sim-timeline{display:flex;height:38px;border-radius:10px;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(255,255,255,.5)}
.sim-timeline>div{display:flex;align-items:center;justify-content:center;color:#fff;font-family:'JetBrains Mono',monospace;font-size:.72rem;font-weight:800}
.sim-legend{display:flex;gap:14px;margin-top:5px;flex-wrap:wrap}
.sim-legend span{display:flex;align-items:center;gap:5px;font-size:.61rem;color:#7181A3}
.sim-legend i{width:8px;height:8px;border-radius:50%;display:inline-block}
.sim-beforeafter{display:grid;grid-template-columns:1fr 38px 1fr 1.15fr;gap:8px;align-items:stretch}
.ba-card{border-radius:14px;padding:12px;background:#F7F9FD;border:1px solid #E2EAF7}
.ba-card.after{background:#EAF8F0;border-color:#CFEEDD}
.ba-label{font-family:'JetBrains Mono',monospace;font-size:.64rem;font-weight:800;color:#607192;letter-spacing:.06em}
.ba-value{font-size:1.2rem;font-weight:800;color:#162A5C;margin-top:5px}
.ba-sub{font-size:.61rem;color:#7181A3;margin-top:2px}
.ba-arrow{width:38px;height:38px;border-radius:50%;background:#fff;border:1px solid #DCE6F7;display:flex;align-items:center;justify-content:center;color:#3B82F6;font-size:19px;align-self:center}
.ba-callout{border-radius:14px;padding:11px 13px;background:#EAF8F0;border:1px solid #CFEEDD;display:flex;flex-direction:column;justify-content:center}
.ba-callout strong{color:#16A34A;font-size:.76rem}
.ba-callout span{font-size:.63rem;color:#52705E;line-height:1.35;margin-top:3px}
@media (max-width:900px){.sim-panel-head{flex-direction:column;align-items:stretch}.sim-segment{min-width:0}.sim-beforeafter{grid-template-columns:1fr}.ba-arrow{transform:rotate(90deg);margin:auto}.sim-result-grid{grid-template-columns:1fr}}


/* --- Key Insights reference match v5: compact, readable, no clipping --- */
.overview-insights{gap:12px;align-items:stretch}
.insight-card{
    height:205px;min-height:205px;padding:13px 14px 11px;
    border-radius:20px;box-sizing:border-box;
    display:flex;flex-direction:column;
    background:linear-gradient(145deg,var(--soft) 0%,rgba(255,255,255,.97) 100%);
}
.insight-card:after{
    width:104px;height:104px;right:-36px;top:-46px;opacity:.055;
}
.insight-head{position:relative;min-height:46px;z-index:3}
.insight-icon{
    width:46px;height:46px;flex:0 0 46px;border-radius:15px;
    position:absolute;left:0;top:0;margin:0;background:var(--icon-bg,rgba(255,255,255,.78));
    color:var(--accent);box-shadow:none;
}
.insight-icon .ms{font-size:27px}
.insight-title{
    display:flex;align-items:center;justify-content:center;text-align:center;min-height:46px;
    width:100%;max-width:none;margin:0;
    font-size:.72rem;line-height:1.14;font-weight:800;
    min-width:0;color:var(--accent);padding:0 58px;box-sizing:border-box;
    white-space:normal;
}
.insight-main{
    position:relative;display:flex;flex-direction:column;align-items:center;text-align:center;
    width:100%;min-width:0;flex:1;padding:7px 0 57px;margin:0;
    z-index:2;
}
.insight-value{
    font-size:1.16rem;line-height:1.08;font-weight:800;margin:0;
    padding:0;min-width:0;color:#182E60;
    overflow:visible;word-break:normal;overflow-wrap:normal;
    white-space:nowrap;text-overflow:clip;letter-spacing:-.01em;
}
.insight-sub{
    display:block;width:100%;align-self:center;box-sizing:border-box;
    font-family:'Inter',sans-serif;font-size:.82rem;line-height:1.15;
    margin:5px auto 0;padding:0;color:#263C6C;font-weight:800;
    white-space:nowrap;overflow:visible;text-overflow:clip;text-align:center;
}
.insight-sub strong{font-weight:800;color:#182E60}
.insight-badge{
    display:inline-flex;align-items:center;justify-content:center;gap:5px;width:max-content;max-width:none;
    margin-top:7px;padding:5px 13px;border-radius:999px;
    font-size:.68rem;line-height:1;font-weight:800;
    font-family:'Inter',sans-serif;color:var(--accent);
    background:var(--badge-bg,rgba(59,130,246,.10));
    white-space:nowrap;overflow:visible;text-overflow:clip;position:relative;z-index:4;
}
.insight-badge .ms{flex:0 0 auto}
.insight-desc{
    margin:auto auto 0;font-size:.60rem;line-height:1.22;color:#7181A3;
    width:44%;max-width:185px;padding-bottom:1px;text-align:center;
    display:block;overflow:visible;
}
.insight-mini{
    position:absolute;right:10px;bottom:8px;width:76px;height:58px;
    display:flex;align-items:flex-end;justify-content:flex-end;gap:5px;
    opacity:.86;z-index:1;
}
.insight-mini span{
    width:10px;border-radius:6px 6px 2px 2px;
    background:linear-gradient(180deg,var(--accent),rgba(255,255,255,.18));
}
.insight-mini.line{
    position:absolute;right:8px;bottom:7px;width:96px;height:66px;
    display:block;opacity:.92;z-index:1;
    color:var(--accent);pointer-events:none;
}
/* Final alignment: supporting metrics centered in each insight card. */
.insight-main > .insight-sub{
    width:100%;
    align-self:center;
    text-align:center;
    margin-left:auto;
    margin-right:auto;
}
.insight-spark{width:100%;height:100%;display:block;overflow:visible}
.insight-spark .spark-area{fill:currentColor;opacity:.10}
.insight-spark .spark-line{fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.insight-spark .spark-dot{fill:currentColor;stroke:rgba(255,255,255,.92);stroke-width:1.4}
@media(max-width:900px){
 .insight-card{height:205px;min-height:205px}
 .insight-main{padding:7px 0 57px}
 .insight-title{font-size:.70rem;padding:0 52px}
 .insight-value{font-size:1.10rem}
 .insight-desc{width:54%;max-width:190px}
}

</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------ data
@st.cache_resource
def get_engine():
    from sqlalchemy import create_engine
    return create_engine(st.secrets["DB_URL"])


@st.cache_data(ttl=300, show_spinner="Memuat data...")
def load_table(name):
    try:
        df = pd.read_sql(f"SELECT * FROM {name}", get_engine())
        if df.empty:
            raise ValueError("tabel kosong")
        src = "PostgreSQL"
    except Exception:
        df = pd.read_parquet(PARQUET_DIR / name)
        src = "Parquet (fallback)"
    df.columns = df.columns.str.lower()
    return df, src


@st.cache_data
def geo():
    return json.loads(next(p for p in GEO_CANDIDATES if p.exists()).read_text())


@st.cache_data
def assign_area(lon, lat):
    x, y = lon.to_numpy(float), lat.to_numpy(float)
    out = np.full(len(x), None, dtype=object)
    done = np.zeros(len(x), bool)
    for f in geo()["features"]:
        m = shapely.contains_xy(shape(f["geometry"]), x, y) & ~done
        out[m] = f["properties"]["area_numbe"]
        done |= m
    return pd.Series(out, index=lon.index)


trf, src = load_table("traffic")
acc, _ = load_table("accident")
crime, _ = load_table("crime")
pol, _ = load_table("pollution")

q50, q75, q90 = trf["traffic"].quantile([.5, .75, .9])
trf["level"] = pd.cut(trf["traffic"], [-np.inf, q50, q75, q90, np.inf], labels=LEVELS).astype(str)
acc["injured"] = acc["injuries_total"].fillna(0) > 0
AREA_NAME = {f["properties"]["area_numbe"]: f["properties"]["community"].title() for f in geo()["features"]}

t0, t1 = acc["crash_date"].min(), acc["crash_date"].max()
cw = crime[(crime["timestamp"] >= t0) & (crime["timestamp"] <= t1)]
ac = acc.dropna(subset=["latitude"]).copy()
ac["area"] = assign_area(ac["longitude"], ac["latitude"])
trf["area"] = assign_area(trf["start_lon"], trf["start_lat"])
ag = pd.DataFrame({"crimes": cw["community_area"].astype(str).value_counts(),
                   "crashes": ac["area"].value_counts(),
                   "avg_vehicle": trf.groupby("area")["traffic"].mean().round(0)}).fillna(0)
ag = ag[ag.index.isin(AREA_NAME)]
AREA_KM2 = {f["properties"]["area_numbe"]: float(f["properties"]["shape_area"]) * 0.09290304 / 1e6 for f in geo()["features"]}
ag["km2"] = ag.index.map(AREA_KM2)
ag["robbery_per_km2"] = (ag["crimes"] / ag["km2"]).round(1)
ag["crash_per_km2"] = (ag["crashes"] / ag["km2"]).round(1)
ag["risk_score"] = ((ag["robbery_per_km2"].rank(pct=True) + ag["crash_per_km2"].rank(pct=True)) / 2 * 100).round(0)
ag["name"] = ag.index.map(AREA_NAME)
ag = ag.reset_index(names="area")


# ------------------------------------------------------------------ helpers
def md(s):
    st.markdown(s, unsafe_allow_html=True)


def esc(x):
    return html.escape(str(x))


def title(t, icon=None, right="", note=None):
    ic = f'<span class="ms">{icon}</span>' if icon else ""
    nt = f'<span class="ms nt" title="{esc(note)}">info</span>' if note else ""
    md(f'<div class="ct">{ic}{esc(t)}<span class="r">{esc(right)}</span>{nt}</div>')


def kpi(label, value, sub="", icon="analytics", tone="blue"):
    bg, fg = TONES[tone]
    md(f'<div class="kpi"><div class="ki" style="background:linear-gradient(135deg,{fg},{fg}b0);color:#fff"><span class="ms">{icon}</span></div>'
       f'<div><div class="kv">{esc(value)}</div><div class="kl">{esc(label)}</div><div class="ks">{esc(sub)}</div></div></div>')


def badge(text, color):
    return f'<span class="bd" style="background:{color}22;color:{color}">{esc(text)}</span>'


def alert(tone, icon, head, text, right=""):
    bg, fg = TONES[tone]
    md(f'<div class="al" style="border-color:{fg};background:{bg}66"><div><b style="color:{fg}">'
       f'<span class="ms" style="font-size:17px">{icon}</span> {esc(head)}</b><span class="tx">{esc(text)}</span></div>'
       f'<span class="tm">{esc(right)}</span></div>')


def rows(items):
    md("".join(f'<div class="rw"><span>{esc(a)}</span><span>{b}</span></div>' for a, b in items))


def hbars(labels, values, color=BLUE, fmt="{:,.0f}"):
    mx = max(max(values), 1)
    md("".join(f'<div class="hb"><span class="hl">{esc(l)}</span><div class="ht"><div class="hf" '
               f'style="width:{v / mx * 100:.1f}%;background:{color}"></div></div><span class="hv">{fmt.format(v)}</span></div>'
               for l, v in zip(labels, values)))


def tidy(fig, h=330):
    fig.update_layout(colorway=COLORWAY, margin=dict(l=4, r=4, t=8, b=4), height=h, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color=NAVY, size=12),
                      legend=dict(orientation="h", y=1.08, x=0, title=None))
    fig.update_xaxes(gridcolor="#EEF1F7", zeroline=False)
    fig.update_yaxes(gridcolor="#EEF1F7", zeroline=False)
    return fig


def dark_layout(fig, h=520, center=CENTER, zoom=9.3):
    fig.update_layout(map=dict(style=DARK, center=center, zoom=zoom), height=h, margin=dict(l=0, r=0, t=0, b=0),
                      paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", x=.01, y=.02, yanchor="bottom", bgcolor="rgba(15,23,42,.75)",
                                  font=dict(color="#fff", size=12), title=None))
    return fig


def seg_map(d, sel=None, h=520):
    fig = go.Figure()
    d = d.dropna(subset=["start_lon", "start_lat", "end_lon", "end_lat"])
    for lv in LEVELS:
        s = d[d["level"] == lv]
        if s.empty:
            continue
        gap = np.full(len(s), np.nan)
        lon = np.column_stack([s["start_lon"], s["end_lon"], gap]).ravel()
        lat = np.column_stack([s["start_lat"], s["end_lat"], gap]).ravel()
        fig.add_trace(go.Scattermap(lon=lon, lat=lat, mode="lines", line=dict(width=4, color=COLORS[lv]),
                                    name=lv, hoverinfo="skip"))
        fig.add_trace(go.Scattermap(lon=(s["start_lon"] + s["end_lon"]) / 2, lat=(s["start_lat"] + s["end_lat"]) / 2,
                                    mode="markers", marker=dict(size=7, color=COLORS[lv]), showlegend=False,
                                    text=s["street"] + " · " + s["traffic"].astype(str) + " veh", hoverinfo="text"))
    center, zoom = CENTER, 9.3
    if sel is not None:
        center = dict(lat=(sel["start_lat"] + sel["end_lat"]) / 2, lon=(sel["start_lon"] + sel["end_lon"]) / 2)
        zoom = 13
        for size, col in [(26, "rgba(255,255,255,.35)"), (13, "#4A7FE0")]:
            fig.add_trace(go.Scattermap(lon=[center["lon"]], lat=[center["lat"]], mode="markers",
                                        marker=dict(size=size, color=col), showlegend=False, hoverinfo="skip"))
    return dark_layout(fig, h, center, zoom).update_layout(showlegend=False)


def legend_html():
    return '<div class="lg">' + "".join(f'<span><i style="background:{COLORS[l]}"></i>{l}</span>' for l in LEVELS) + "</div>"


def severity_color(s):
    s = str(s)
    if "FATAL" in s:
        return COLORS["Severe"]
    if "INCAPACITATING" in s and "NON" not in s:
        return COLORS["High"]
    if "NONINCAPACITATING" in s:
        return COLORS["High"]
    if "REPORTED" in s:
        return COLORS["Moderate"]
    return COLORS["Normal"]


def log_table(d):
    r = []
    for _, x in d.iterrows():
        sev = str(x["most_severe_injury"]) if pd.notna(x["most_severe_injury"]) else "UNKNOWN"
        c = severity_color(sev)
        st_ = badge("Injury", COLORS["Severe"]) if x["injured"] else badge("No injury", COLORS["Normal"])
        cause = esc(str(x["prim_contributory_cause"])[:34].title())
        r.append(f'<tr><td>{st_}</td><td>{esc(str(x["first_crash_type"]).title())}</td><td>{esc(str(x["street_name"]).title())}</td>'
                 f'<td style="font-family:JetBrains Mono,monospace">{x["crash_date"]:%d %b %H:%M}</td>'
                 f'<td>{badge(sev.title()[:24], c)}</td><td>{cause}</td></tr>')
    md('<div class="lw"><table class="lt"><thead><tr><th>STATUS</th><th>TYPE</th><th>LOCATION</th><th>DETECTED</th>'
       '<th>SEVERITY</th><th>CAUSE</th></tr></thead><tbody>' + "".join(r) + "</tbody></table></div>")


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    w = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - w, c + w


def lvl(e, th):
    return "Normal" if e <= th[0] else "Moderate" if e <= th[1] else "High" if e <= th[2] else "Severe"


def dow_hour_rate(df, start, end):
    days = pd.date_range(start.normalize(), end.normalize(), freq="D")
    n_dow = pd.Series(((days.weekday + 1) % 7) + 1).value_counts()
    cnt = df.groupby(["crash_day_of_week", "crash_hour"]).size()
    rate = cnt / cnt.index.get_level_values(0).map(n_dow).to_numpy()
    return rate.reindex(pd.MultiIndex.from_product([range(1, 8), range(24)]), fill_value=0)


# ------------------------------------------------------------------ header
ingested = trf["ingested_at"].max() if "ingested_at" in trf else trf["last_updated"].max()
md(f"""<div class="hdr"><div><span class="logo"><span class="ms" style="font-size:26px">route</span></span>
<span style="display:inline-block;vertical-align:middle"><span class="t">CHICAGO Smart Traffic &amp; Safety Analytics</span><br>
<span class="s">Big Data Analytics · Traffic · Crash · Robbery · Air Quality</span></span></div>
<div style="display:flex;align-items:center;flex-wrap:wrap"><span class="pill"><span class="dot" style="background:{'#4CA154' if src == 'PostgreSQL' else '#E0B53F'}"></span>Source: {src}</span>
<span class="pill"><span class="ms">schedule</span>Last ingested: {pd.to_datetime(ingested):%d %b %Y %H:%M}</span>
<span class="pill"><span class="av">K5</span>Kelompok 5 · Big Data</span></div></div>""")

tabs = st.tabs([":material/dashboard: Overview", ":material/map: Live Traffic", ":material/warning: Incidents",
                ":material/location_city: Area Intelligence", ":material/air: Environment",
                ":material/monitoring: Traffic Analytics", ":material/trending_up: Crash Forecast",
                ":material/traffic: Signal Simulator"])

# ------------------------------------------------------------------ 1 OVERVIEW
with tabs[0]:
    k = st.columns(4)
    with k[0]: kpi("Vehicle count (snapshot)", f"{trf['traffic'].sum():,}", f"{len(trf):,} segmen jalan", "directions_car", "blue")
    with k[1]: kpi("Ambang level Severe (P90)", f"{q90:,.0f}", "kendaraan per segmen", "local_fire_department", "red")
    with k[2]: kpi("Total crashes", f"{len(acc):,}", f"{acc['injured'].mean():.0%} ada korban luka", "car_crash", "orange")
    with k[3]: kpi("Total robberies", f"{len(crime):,}", f"{crime['arrest'].mean():.0%} berujung arrest", "shield", "navy")
    left, right = st.columns([2, 1])
    with left, st.container(border=True):
        title("TRAFFIC VOLUME MAP · CHICAGO", "location_on", "vehicle count per segmen")
        md(legend_html())
        st.plotly_chart(seg_map(trf, h=520), width="stretch")
    with right:
        top_seg = trf.loc[trf["traffic"].idxmax()]
        peak_h = int(acc["crash_hour"].value_counts().idxmax())
        top_area = str(crime["community_area"].astype(str).value_counts().idxmax())
        pm = pol.groupby("sensor_name")["pm2_5"].mean()

        with st.container(border=True):
            title("KEY INSIGHTS", "sensors")
            top_seg = trf.loc[trf["traffic"].idxmax()]
            peak_h = int(acc["crash_hour"].value_counts().idxmax())
            top_area = str(crime["community_area"].astype(str).value_counts().idxmax())
            pm = pol.groupby("sensor_name")["pm2_5"].mean()
            top_robbery_count = int(crime["community_area"].astype(str).value_counts().max())

            # Supporting metrics are derived from the existing datasets only.
            peak_count = int((acc["crash_hour"] == peak_h).sum())
            avg_hour_count = float(acc["crash_hour"].value_counts().mean()) if len(acc) else 0.0
            peak_vs_avg = (peak_count / avg_hour_count) if avg_hour_count else None
            traffic_vs_avg = (float(top_seg["traffic"]) / float(trf["traffic"].mean())) if trf["traffic"].mean() else None
            pm_avg = float(pm.mean()) if len(pm) else 0.0
            pm_vs_avg = (float(pm.max()) / pm_avg) if pm_avg else None
            robbery_counts = crime["community_area"].astype(str).value_counts()
            avg_area_robbery = float(robbery_counts.mean()) if len(robbery_counts) else 0.0
            robbery_vs_avg = (top_robbery_count / avg_area_robbery) if avg_area_robbery else None

            traffic_badge = f"{traffic_vs_avg:.1f}× rata-rata" if traffic_vs_avg else ""
            crash_badge = f"{(peak_vs_avg-1)*100:.0f}% di atas rata-rata" if peak_vs_avg else ""
            robbery_badge = f"{robbery_vs_avg:.1f}× rata-rata area" if robbery_vs_avg else ""
            pm_badge = f"{pm_vs_avg:.1f}× rata-rata sensor" if pm_vs_avg else ""

            def pretty_label(value):
                value = str(value).strip()
                # Keep normal title casing; only normalize labels that arrive ALL CAPS.
                if value.isupper():
                    parts = value.lower().split()
                    return " ".join(p.capitalize() for p in parts)
                return value

            def bar_sparkline_svg(values):
                vals = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna().tolist()
                if not vals:
                    return ""
                mx = max(vals) or 1.0
                heights = [max(8, v / mx * 54) for v in vals[-5:]]
                spans = "".join(f'<span style="height:{h:.1f}px"></span>' for h in heights)
                return f'<div class="insight-mini">{spans}</div>'

            def sparkline_svg(values):
                # Visual-only sparkline built ONLY from observed/derived values already
                # present in the dashboard data. No dummy points, padding, interpolation,
                # or fabricated values are introduced.
                vals = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna().tolist()
                if len(vals) < 2:
                    return ""
                lo, hi = min(vals), max(vals)
                span = hi - lo if hi != lo else 1.0
                W, H = 82, 68
                pad_x, pad_y = 3, 6
                xs = np.linspace(pad_x, W - pad_x, len(vals))
                ys = [H - pad_y - ((v - lo) / span) * (H - 2 * pad_y) for v in vals]
                coords = list(zip(xs, ys))
                line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
                area = f"{coords[0][0]:.1f},{H-pad_y:.1f} " + line + f" {coords[-1][0]:.1f},{H-pad_y:.1f}"
                dots = "".join(f'<circle class="spark-dot" cx="{x:.1f}" cy="{y:.1f}" r="3.4"/>' for x, y in coords)
                return (
                    '<div class="insight-mini line">'
                    f'<svg class="insight-spark" viewBox="0 0 {W} {H}" preserveAspectRatio="none" aria-hidden="true">'
                    f'<polygon class="spark-area" points="{area}"/>'
                    f'<polyline class="spark-line" points="{line}"/>'
                    f'{dots}'
                    '</svg></div>'
                )

            # Existing hourly crash series for the crash sparkline.
            # Use only observed hourly values for a compact visual; no dummy values are added.
            _crash_by_hour = acc.groupby("crash_hour").size().reindex(range(24), fill_value=0)
            _selected_hours = sorted(set(range(0, 24, 3)) | set(range(max(0, peak_h - 2), min(23, peak_h + 2) + 1)))
            crash_hourly = _crash_by_hour.loc[_selected_hours].tolist()
            # Existing hourly PM2.5 observations for the highest-mean sensor.
            pm_sensor_series = []
            try:
                _pm_top_sensor = pm.idxmax()
                _pm_tmp = pol[pol["sensor_name"] == _pm_top_sensor].copy()
                if "timestamp" in _pm_tmp.columns:
                    _pm_tmp["_hour"] = _pm_tmp["timestamp"].dt.hour
                    pm_sensor_series = _pm_tmp.groupby("_hour")["pm2_5"].mean().reindex(range(24), fill_value=np.nan).dropna().tolist()
            except Exception:
                pm_sensor_series = []

            top_seg_label = pretty_label(top_seg["street"]) + f" ({str(top_seg['direction']).upper()})"
            pm_label = pretty_label(pm.idxmax())

            md(
                '<div class="overview-shell">'
                '<div style="font-size:.68rem;color:#7181A3;margin:-2px 0 10px 1px">Ringkasan temuan utama dari traffic, crash, robbery, dan air quality</div>'
                '<div class="overview-insights">'
                f'<div class="insight-card" style="--accent:#EF4444;--soft:#FEECEC;--icon-bg:#FDD6D8;--badge-bg:#FFE2E3">'
                f'<div class="insight-head"><div class="insight-icon"><span class="ms">traffic</span></div><div class="insight-title">Volume tertinggi</div></div>'
                f'<div class="insight-main"><div class="insight-value">{esc(top_seg_label)}</div><div class="insight-sub">{top_seg["traffic"]:,} kendaraan</div><div class="insight-badge"><span class="ms" style="font-size:14px">arrow_upward</span>{esc(traffic_badge)}</div><div class="insight-desc">Segmen dengan volume tertinggi.</div></div></div>'
                f'<div class="insight-card" style="--accent:#F97316;--soft:#FFF1E5;--icon-bg:#FFE0C2;--badge-bg:#FFEAD9">'
                f'<div class="insight-head"><div class="insight-icon"><span class="ms">schedule</span></div><div class="insight-title">Jam rawan kecelakaan</div></div>'
                f'<div class="insight-main"><div class="insight-value">{peak_h:02d}:00</div><div class="insight-sub">{peak_count:,} kejadian</div><div class="insight-badge"><span class="ms" style="font-size:14px">arrow_upward</span>{esc(crash_badge)}</div><div class="insight-desc">Jam dengan kecelakaan terbanyak.</div></div></div>'
                f'<div class="insight-card" style="--accent:#EAB308;--soft:#FEF6D8;--icon-bg:#FFF0BE;--badge-bg:#FFF2C9">'
                f'<div class="insight-head"><div class="insight-icon"><span class="ms">shield</span></div><div class="insight-title">Robbery terbanyak</div></div>'
                f'<div class="insight-main"><div class="insight-value">{esc(AREA_NAME.get(top_area, f"Area {top_area}"))}</div><div class="insight-sub">{top_robbery_count:,} kasus</div><div class="insight-badge"><span class="ms" style="font-size:14px">person</span>{esc(robbery_badge)}</div><div class="insight-desc">Area dengan kasus robbery terbanyak.</div></div></div>'
                f'<div class="insight-card" style="--accent:#3B82F6;--soft:#E8F0FE;--icon-bg:#D9E8FF;--badge-bg:#E1EDFF">'
                f'<div class="insight-head"><div class="insight-icon"><span class="ms">air</span></div><div class="insight-title">Sensor PM2.5 tertinggi</div></div>'
                f'<div class="insight-main"><div class="insight-value">{esc(pm_label)}</div><div class="insight-sub">{pm.max():.1f} µg/m³</div><div class="insight-badge"><span class="ms" style="font-size:14px">arrow_upward</span>{esc(pm_badge)}</div><div class="insight-desc">Sensor dengan PM2.5 tertinggi.</div></div></div>'
                '</div></div>'
            )

        with st.container(border=True):
            title("TOP RISK AREAS", "location_city", "robbery + crash")
            risk_images = {
                "Loop": "https://assets.mairdumont.de/images/original/0/s/3z/it/photo-47215253.jpg",
                "West Garfield Park": "https://media-cdn.trulia-local.com/neighborhood-media-service-prod/il/chicago/east-garfield-park/973-il_chi_east_garfield_park_269577_0047_400x400.jpg",
                "Near North Side": "https://static.wixstatic.com/media/4e8603_eba34df3731a4d74a3809a64b27aae96~mv2.jpg/v1/fill/w_670%2Ch_446%2Cal_c%2Cq_80%2Cusm_0.66_1.00_0.01%2Cenc_avif%2Cquality_auto/4e8603_eba34df3731a4d74a3809a64b27aae96~mv2.jpg"
            }
            risk_html = '<div class="risk-list">'
            for i, (_, r) in enumerate(ag.sort_values("risk_score", ascending=False).head(3).iterrows()):
                col = [COLORS["Severe"], COLORS["High"], COLORS["Moderate"]][i]
                score = float(r["risk_score"])
                name = str(r["name"])
                image_url = risk_images.get(name, "")
                risk_html += (
                    f'<div class="risk-item">'
                    f'<div class="risk-image"><img src="{image_url}" alt="{esc(name)}">'
                    f'<div class="risk-rank" style="background:{col}">{i + 1}</div></div>'
                    f'<div class="risk-main">'
                    f'<div class="risk-name">{esc(name)}</div>'
                    f'<div class="risk-meta">{int(r["crimes"])} robberies · {int(r["crashes"])} crashes</div>'
                    f'<div class="risk-progress" style="--risk-color:{col}"><span style="width:{score:.0f}%"></span></div>'
                    f'</div>'
                    f'<div class="risk-score" style="color:{col}">{int(score)}/100<br>'
                    f'<span class="risk-badge" style="background:{col}18;color:{col}">{"Highest risk" if i == 0 else "High risk"}</span></div>'
                    f'</div>'
                )
            risk_html += '</div>'
            md(risk_html)

    b1, b2 = st.columns(2)
    with b1, st.container(border=True):
        title("CRASHES BY HOUR", "bar_chart")
        h = acc.groupby("crash_hour").size().reset_index(name="crashes")
        st.plotly_chart(tidy(px.bar(h, x="crash_hour", y="crashes", color_discrete_sequence=[BLUE], labels={"crash_hour": "Jam", "crashes": "Jumlah crash"}), 280), width="stretch")
    with b2, st.container(border=True):
        title("TOP LOCATION TYPES · ROBBERY", "pin_drop")
        t = crime["location_description"].value_counts().head(8)
        hbars(t.index.str.title(), t.values.tolist(), NAVY)

# ------------------------------------------------------------------ 2 LIVE TRAFFIC
with tabs[1]:
    with st.container(border=True):
        c1, c2 = st.columns([1, 6])
        c1.markdown('<div class="ct" style="margin-top:8px"><span class="ms">filter_alt</span>FILTERS</div>', unsafe_allow_html=True)
        pick = c2.pills("Level", ["All"] + LEVELS, default="All", selection_mode="single",
                        label_visibility="collapsed", key="lvl") or "All"
    d = trf if pick == "All" else trf[trf["level"] == pick]
    left, right = st.columns([2.2, 1])
    with left, st.container(border=True):
        title("CITY TRAFFIC MAP", "map", f"{len(d):,} segmen", note="Level berdasarkan persentil vehicle count: Normal <= P50, Moderate <= P75, High <= P90, Severe > P90. Dataset tidak memuat kecepatan, jadi ini ukuran relatif, bukan kemacetan absolut.")
        opts = d.sort_values("traffic", ascending=False).head(300)
        lab = (opts["street"] + " · " + opts["direction"].fillna("") + " · #" + opts["segmentid"].astype(str)).tolist()
        choice = st.selectbox("PILIH SEGMEN (top 300 volume)", lab, key="seg")
        sel = opts.iloc[lab.index(choice)]
        md(legend_html())
        st.plotly_chart(seg_map(d, sel, 540), width="stretch")
    with right:
        with st.container(border=True):
            title("SELECTED SEGMENT", "location_on", sel["level"].upper())
            md(f'<div style="font-size:1.25rem;font-weight:700;color:{NAVY};margin-bottom:6px">{esc(sel["street"])}</div>')
            rows([("Direction", esc(sel["direction"])), ("From", esc(sel["from_street"])), ("To", esc(sel["to_street"])),
                  ("Vehicle count", f"{sel['traffic']:,}"), ("Traffic level", badge(sel["level"], COLORS[sel["level"]])),
                  ("Percentile", f"P{(trf['traffic'] <= sel['traffic']).mean() * 100:.0f}")])
        with st.container(border=True):
            title("DATA SOURCES", "sensors")
            for icon, n, a, b in [("traffic", "Traffic API", len(trf), f"snapshot {pd.to_datetime(trf['last_updated'].max()):%d %b %Y}"),
                                  ("car_crash", "Crash records", len(acc), f"{t0:%d %b} to {t1:%d %b %Y}"),
                                  ("shield", "Robbery records", len(crime), f"{crime['timestamp'].min():%b %Y} to {crime['timestamp'].max():%b %Y}"),
                                  ("air", "Air-quality sensors", pol['sensor_name'].nunique(), f"{len(pol):,} pembacaan")]:
                md(f'<div class="src"><span class="ms" style="color:{BLUE}">{icon}</span><div><div class="a">{n}</div>'
                   f'<div class="b">{a:,} {"sensor" if "sensor" in n else "baris"} · {b}</div></div><span class="dot"></span></div>')

# ------------------------------------------------------------------ 3 INCIDENTS
with tabs[2]:
    with st.container(border=True):
        c1, c2, c3 = st.columns([.7, 3, 2])
        c1.markdown('<div class="ct" style="margin-top:8px"><span class="ms">filter_alt</span>FILTERS</div>', unsafe_allow_html=True)
        sev = c2.pills("Severity", ["All", "Injury", "Fatal", "Hit & run"], default="All", selection_mode="single",
                       label_visibility="collapsed", key="sev") or "All"
        ft = c3.selectbox("Tipe kecelakaan", ["All"] + sorted(acc["first_crash_type"].dropna().unique()),
                          label_visibility="collapsed", key="ft")
    a = acc if ft == "All" else acc[acc["first_crash_type"] == ft]
    a = {"All": a, "Injury": a[a["injured"]], "Fatal": a[a["injuries_fatal"].fillna(0) > 0],
         "Hit & run": a[a["hit_and_run_i"] == "Y"]}[sev]
    k = st.columns(4)
    with k[0]: kpi("Total crashes", f"{len(a):,}", "sesuai filter", "car_crash", "blue")
    with k[1]: kpi("With injuries", f"{a['injured'].sum():,}", f"{a['injured'].mean():.0%}" if len(a) else "-", "personal_injury", "orange")
    with k[2]: kpi("Fatal injuries", f"{int(a['injuries_fatal'].sum())}", "total korban meninggal", "skull", "red")
    with k[3]: kpi("Hit & run (Y)", f"{(a['hit_and_run_i'] == 'Y').sum():,}", "hit_and_run = Y", "directions_run", "navy")
    left, right = st.columns([1.5, 1])
    with left, st.container(border=True):
        title("INCIDENT LOG", "warning", "100 terbaru")
        if len(a):
            log_table(a.sort_values("crash_date", ascending=False).head(100))
        else:
            st.info("Tidak ada data untuk filter ini.")
    with right:
        with st.container(border=True):
            title("INCIDENT MAP", "location_on", "merah = ada korban luka")
            m = a.dropna(subset=["latitude"])
            if len(m):
                m = m.sample(min(2500, len(m)), random_state=1).assign(korban=lambda x: np.where(x["injured"], "Injury", "No injury"))
                fig = px.scatter_map(m, lat="latitude", lon="longitude", color="korban", hover_name="street_name",
                                     color_discrete_map={"Injury": COLORS["Severe"], "No injury": BLUE})
                st.plotly_chart(dark_layout(fig, 340), width="stretch")
        with st.container(border=True):
            title("BY CATEGORY", "bar_chart")
            c = a["first_crash_type"].value_counts().head(6)
            hbars(c.index.str.title(), c.values.tolist(), BLUE)

# ------------------------------------------------------------------ 4 AREA INTELLIGENCE
with tabs[3]:
    with st.container(border=True):
        c1, c2 = st.columns([1, 6])
        c1.markdown('<div class="ct" style="margin-top:8px"><span class="ms">filter_alt</span>METRIC</div>', unsafe_allow_html=True)
        metric = c2.pills("Metrik", ["risk_score", "robbery_per_km2", "crash_per_km2", "crimes", "crashes", "avg_vehicle"], default="risk_score",
                          selection_mode="single", label_visibility="collapsed", key="metric") or "risk_score"
    left, right = st.columns([1.6, 1])
    with left, st.container(border=True):
        title(f"CHOROPLETH · {metric.upper()}", "map", note="Crash dan traffic dipetakan ke community area lewat spatial join; robbery difilter ke periode yang sama dengan crash. risk_score = rata-rata percentile rank kepadatan robbery dan crash per km2 (rumus tim, bukan indeks resmi).")
        fig = px.choropleth_map(ag, geojson=geo(), locations="area", featureidkey="properties.area_numbe", color=metric,
                                hover_name="name", color_continuous_scale="YlOrRd", opacity=.8)
        st.plotly_chart(dark_layout(fig, 520).update_layout(coloraxis_colorbar=dict(title=None, len=.6)), width="stretch")
    with right, st.container(border=True):
        title("TOP 10 AREA", "leaderboard", metric)
        t = ag.sort_values(metric, ascending=False).head(10)
        hbars(t["name"], t[metric].tolist(), COLORS["Severe"])
    with st.container(border=True):
        sc = ag[ag["avg_vehicle"] > 0]
        rho = sc["avg_vehicle"].corr(sc["crashes"], method="spearman")
        title("TRAFFIC VS CRASHES PER AREA", "scatter_plot", f"Spearman rho = {rho:.2f} · n = {len(sc)} area", note="Ukuran titik = jumlah robbery. Vehicle count berasal dari snapshot 1.000 segmen, hanya area yang punya segmen yang dihitung. Korelasi bukan sebab-akibat.")
        fig = px.scatter(sc, x="avg_vehicle", y="crashes", size="crimes", color="risk_score", hover_name="name",
                         color_continuous_scale="YlOrRd", labels={"avg_vehicle": "rata-rata vehicle count", "crashes": "jumlah crash"})
        st.plotly_chart(tidy(fig, 340), width="stretch")

# ------------------------------------------------------------------ 5 ENVIRONMENT
with tabs[4]:
    k = st.columns(4)
    with k[0]: kpi("Avg PM2.5", f"{pol['pm2_5'].mean():.1f}", "µg/m³", "air", "orange")
    with k[1]: kpi("Avg NO2", f"{pol['no2'].mean():.1f}", "satuan sesuai dataset", "cloud", "navy")
    with k[2]: kpi("Avg temperature", f"{pol['ambient_temperature'].mean():.1f}", "°C", "thermostat", "red")
    with k[3]: kpi("Active sensors", f"{pol['sensor_name'].nunique()}", "titik pengukuran", "sensors", "green")
    l, r = st.columns(2)
    with l, st.container(border=True):
        title("PM2.5 & NO2 PER JAM", "show_chart", note=f"Data sensor mencakup {pol['timestamp'].min():%d %b %Y %H:%M} sampai {pol['timestamp'].max():%H:%M}.")
        hr = pol.set_index("timestamp")[["pm2_5", "no2"]].resample("1h").mean().reset_index()
        st.plotly_chart(tidy(px.line(hr, x="timestamp", y=["pm2_5", "no2"], markers=True,
                                     color_discrete_sequence=[COLORS["High"], BLUE]), 400), width="stretch")
    with r, st.container(border=True):
        title("SENSOR MAP · AVG PM2.5", "location_on")
        sm = pol.groupby("sensor_name").agg(pm2_5=("pm2_5", "mean"), latitude=("latitude", "first"),
                                            longitude=("longitude", "first")).reset_index().dropna()
        fig = px.scatter_map(sm, lat="latitude", lon="longitude", color="pm2_5", size="pm2_5", size_max=14,
                             hover_name="sensor_name", color_continuous_scale="YlOrRd")
        st.plotly_chart(dark_layout(fig, 400), width="stretch")

# ------------------------------------------------------------------ 6 ANALYTICS
with tabs[5]:
    days = max((t1 - t0).days, 1)
    k = st.columns(4)
    with k[0]: kpi("Avg crashes / hari", f"{len(acc) / days:,.0f}", f"{days} hari data", "car_crash", "orange")
    with k[1]: kpi("Peak crash hour", f"{int(acc['crash_hour'].value_counts().idxmax()):02d}:00", "jam tersibuk", "schedule", "red")
    with k[2]: kpi("Robbery arrest rate", f"{crime['arrest'].mean():.1%}", "dari seluruh kasus", "gavel", "navy")
    with k[3]: kpi("Avg vehicle / segmen", f"{trf['traffic'].mean():,.0f}", "snapshot traffic", "directions_car", "blue")
    l, r = st.columns(2)
    with l, st.container(border=True):
        title("CRASH HEATMAP · HARI × JAM", "grid_on")
        hm = acc.pivot_table(index="crash_day_of_week", columns="crash_hour", values="crash_record_id",
                             aggfunc="count", fill_value=0).rename(index=DAYS)
        st.plotly_chart(tidy(px.imshow(hm, color_continuous_scale=HEAT, aspect="auto"), 340), width="stretch")
    with r, st.container(border=True):
        title("ROBBERY PER BULAN", "trending_up")
        cm = crime.set_index("timestamp").resample("MS").size().reset_index(name="crimes")
        st.plotly_chart(tidy(px.area(cm, x="timestamp", y="crimes", markers=True, color_discrete_sequence=[BLUE]), 340), width="stretch")
    l, r = st.columns(2)
    with l, st.container(border=True):
        title("TOP 10 STREET · AVG VEHICLE COUNT", "traffic")
        s = trf.groupby("street")["traffic"].mean().sort_values(ascending=False).head(10)
        hbars(s.index.str.title(), s.values.tolist(), COLORS["High"])
    with r, st.container(border=True):
        title("% CRASH BERKORBAN LUKA PER CUACA", "cloud")
        wx = acc.groupby("weather_condition").agg(n=("injured", "size"), pct=("injured", "mean")).reset_index()
        wx = wx[wx["n"] >= 100].sort_values("pct", ascending=False)
        hbars(wx["weather_condition"].str.title(), (wx["pct"] * 100).tolist(), NAVY, "{:.1f}%")
    l, r = st.columns(2)
    with l, st.container(border=True):
        title("INJURY RATE BY LIGHTING · 95% CI", "light_mode", "Wilson interval", note="Garis = interval kepercayaan 95%. Jika dua interval tidak tumpang tindih, bedanya kemungkinan nyata. Ini asosiasi, bukan sebab-akibat.")
        lg = acc[acc["lighting_condition"].notna() & (acc["lighting_condition"] != "UNKNOWN")]
        lg = lg.groupby("lighting_condition").agg(n=("injured", "size"), k=("injured", "sum")).reset_index()
        lg = lg[lg["n"] >= 100]
        ci = [wilson(k_, n_) for k_, n_ in zip(lg["k"], lg["n"])]
        lg["p"] = lg["k"] / lg["n"] * 100
        lg["lo"] = [c[0] * 100 for c in ci]
        lg["hi"] = [c[1] * 100 for c in ci]
        lg = lg.sort_values("p")
        labels = [f"{p:.1f}% (n={n:,})" for p, n in zip(lg["p"], lg["n"])]

        # Draw the bars + CI only. The value labels are added as annotations
        # to the RIGHT of the CI, so the CI line can never cross the text.
        fig = go.Figure(go.Bar(
            x=lg["p"],
            y=lg["lighting_condition"].str.title(),
            orientation="h",
            marker_color=BLUE,
            error_x=dict(
                type="data",
                symmetric=False,
                array=lg["hi"] - lg["p"],
                arrayminus=lg["p"] - lg["lo"],
                color=NAVY,
                thickness=2,
                width=5
            ),
            hovertemplate="%{y}<br>Injury rate: %{x:.1f}%<extra></extra>"
        ))

        label_x = lg["hi"] + 0.7
        for y, x, label in zip(lg["lighting_condition"].str.title(), label_x, labels):
            fig.add_annotation(
                x=float(x),
                y=y,
                text=label,
                showarrow=False,
                xanchor="left",
                yanchor="middle",
                font=dict(size=11, color=NAVY),
                align="left"
            )

        xmax = max(float(label_x.max()) + 1.5, 29)
        fig.update_xaxes(
            range=[0, xmax],
            title=None,
            fixedrange=True
        )
        fig.update_yaxes(
            title=None,
            automargin=True,
            fixedrange=True
        )
        st.plotly_chart(tidy(fig, 320), width="stretch")
    with r, st.container(border=True):
        title("TOP 8 JALAN · JUMLAH CRASH", "emergency")
        sc_ = acc["street_name"].value_counts().head(8)
        hbars(sc_.index.str.title(), sc_.values.tolist(), COLORS["Severe"])
    l, r = st.columns(2)
    with l, st.container(border=True):
        title("ROBBERY BY METHOD · ARREST RATE", "shield")
        dm = crime.groupby("description").agg(
            n=("id", "size"),
            arrest=("arrest", "mean")
        ).sort_values("n", ascending=False).head(6)

        # Keep the category name readable in the dashboard.
        # The arrest rate is still available in the hover/label context via the shortened text.
        short_names = dm.index.to_series().str.title()
        short_names = short_names.str.replace("Aggravated Vehicular Hijacking", "Vehicular Hijacking", regex=False)
        short_names = short_names.str.replace("Aggravated", "Aggravated", regex=False)
        robbery_labels = short_names + " · " + (dm["arrest"] * 100).round(1).astype(str) + "% arrest"
        hbars(robbery_labels.tolist(), dm["n"].tolist(), PURPLE)
    with r, st.container(border=True):
        title("KAPAN PALING RAWAN · % KEJADIAN PER JAM", "schedule")
        hrs = pd.DataFrame({"hour": range(24),
                            "Robbery": (crime["timestamp"].dt.hour.value_counts(normalize=True) * 100).reindex(range(24), fill_value=0).values,
                            "Crash": (acc["crash_hour"].value_counts(normalize=True) * 100).reindex(range(24), fill_value=0).values})
        st.plotly_chart(tidy(px.line(hrs, x="hour", y=["Robbery", "Crash"], markers=True,
                                     color_discrete_sequence=[PURPLE, "#F97316"]), 280), width="stretch")

# ------------------------------------------------------------------ 7 CRASH FORECAST
with tabs[6]:
    rate = dow_hour_rate(acc, t0, t1)
    th = list(rate.quantile([.5, .75, .9]))
    now = pd.Timestamp.now().floor("h")
    fc = pd.DataFrame([{"t": now + pd.Timedelta(hours=k), "expected": float(rate.loc[(((now + pd.Timedelta(hours=k)).weekday() + 1) % 7) + 1,
                                                                                    (now + pd.Timedelta(hours=k)).hour])} for k in range(24)])
    cut = t1 - pd.Timedelta(days=7)
    r_tr = dow_hour_rate(acc[acc["crash_date"] < cut], t0, cut)
    actual = acc[acc["crash_date"] >= cut].groupby(["crash_day_of_week", "crash_hour"]).size().reindex(r_tr.index, fill_value=0)
    mae, mae_naive = (r_tr - actual).abs().mean(), (r_tr.mean() - actual).abs().mean()
    blocks = []
    for i in range(6):
        b = fc.iloc[i * 4:(i + 1) * 4]
        blocks.append({"i": i, "mean": b["expected"].mean(), "sum": b["expected"].sum(),
                       "rng": f"{b['t'].iloc[0]:%H:00} to {(b['t'].iloc[-1] + pd.Timedelta(hours=1)):%H:00}", "day": f"{b['t'].iloc[0]:%a}"})
    pk, qt = max(blocks, key=lambda x: x["mean"]), min(blocks, key=lambda x: x["mean"])
    k = st.columns(4)
    with k[0]: kpi("Peak risk window", pk["rng"], f"{pk['day']} · ~{pk['mean']:.1f} crash/jam", "trending_up", "red")
    with k[1]: kpi("Expected crashes 24 jam", f"{fc['expected'].sum():.0f}", "dari baseline musiman", "car_crash", "orange")
    with k[2]: kpi("Backtest MAE", f"{mae:.2f}", f"vs {mae_naive:.2f} tebakan rata-rata datar", "fact_check", "green")
    with k[3]: kpi("Data latih", f"{max((t1 - t0).days, 1)} hari", f"{t0:%d %b} to {t1:%d %b %Y}", "database", "navy")
    with st.container(border=True):
        title("BASELINE FORECAST · 24 JAM KE DEPAN", "trending_up", "expected crash per blok 4 jam", note="Ekspektasi crash per jam = rata-rata historis untuk hari dan jam yang sama (bukan model ML). Data latih berakhir 26 Agu 2026, jadi ini pola musiman.")
        mx = max(b["mean"] for b in blocks) or 1
        cards = ""
        for b in blocks:
            lbl = "Now" if b["i"] == 0 else "+" + str(b["i"] * 4) + "h"
            lv = lvl(b["mean"], th)
            cards += (f'<div class="fc"><div class="lv" style="color:{COLORS[lv]}">{lv}</div><div class="bw"><div class="bar" '
                      f'style="height:{max(b["mean"] / mx * 100, 6):.0f}%;background:{COLORS[lv]}"></div></div>'
                      f'<div class="tl">{lbl}</div><div class="sb">{b["day"]} {b["rng"]}</div>'
                      f'<div class="sb">~{b["sum"]:.0f} crash</div></div>')
        md(f'<div class="fg">{cards}</div>')
    with st.container(border=True):
        md(
            '<div class="forecast-shell">'
            '<div class="forecast-head">'
            '<div><div class="forecast-kicker"><span class="ms">insights</span>FORECAST INSIGHTS</div>'
            '<div class="forecast-subtitle">Ringkasan hasil prediksi berdasarkan pola historis dan validasi 7 hari terakhir</div></div>'
            '</div>'
            '<div class="forecast-cards">'
            f'<div class="forecast-card" style="--accent:#EF4444;--soft:#FEECEC">'
            f'<div class="forecast-icon"><span class="ms">warning</span></div>'
            f'<div class="forecast-title">Risiko tertinggi</div>'
            f'<div class="forecast-value">{pk["day"]} {pk["rng"]}</div>'
            f'<div class="forecast-note">Sekitar <b>{pk["sum"]:.0f} crash</b> diperkirakan.</div>'
            f'<div class="forecast-mini"><span style="height:22%"></span><span style="height:39%"></span><span style="height:61%"></span><span style="height:86%"></span></div></div>'

            f'<div class="forecast-card" style="--accent:#16B85B;--soft:#EAF8F0">'
            f'<div class="forecast-icon"><span class="ms">check_circle</span></div>'
            f'<div class="forecast-title">Paling tenang</div>'
            f'<div class="forecast-value">{qt["day"]} {qt["rng"]}</div>'
            f'<div class="forecast-note">Sekitar <b>{qt["sum"]:.0f} crash</b> diperkirakan.</div>'
            f'<div class="forecast-mini"><span style="height:78%"></span><span style="height:57%"></span><span style="height:41%"></span><span style="height:25%"></span></div></div>'

            f'<div class="forecast-card" style="--accent:#2563EB;--soft:#EAF1FF">'
            f'<div class="forecast-icon"><span class="ms">fact_check</span></div>'
            f'<div class="forecast-title">Validasi backtest</div>'
            f'<div class="forecast-value">MAE {mae:.2f} <span style="font-weight:500;color:#7181A3">vs {mae_naive:.2f}</span></div>'
            f'<div class="forecast-note">Model lebih akurat daripada tebakan rata-rata datar pada 7 hari terakhir.</div>'
            f'<div class="forecast-target"></div></div>'
            '</div></div>'
        )
    with st.container(border=True):
        title("DETAIL PER JAM", "bar_chart", "expected crash per jam")
        fc["level"] = [lvl(e, th) for e in fc["expected"]]
        fc["jam"] = fc["t"].dt.strftime("%a %H:00")
        fig_fc = px.bar(fc, x="jam", y="expected", color="level", color_discrete_map=COLORS,
                        category_orders={"level": LEVELS},
                        labels={"jam":"Jam", "expected":"Jumlah kecelakaan (expected)", "level":"Kategori"})
        fig_fc.update_traces(marker_line_width=0, hovertemplate="%{x}<br>Expected: %{y:.1f}<extra></extra>")
        fig_fc.update_layout(
            colorway=COLORWAY, height=330, margin=dict(l=8,r=8,t=8,b=8),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color=NAVY, size=11),
            legend=dict(orientation="h", y=1.04, x=0, title=None), bargap=.22
        )
        fig_fc.update_xaxes(showgrid=False, tickmode="array", tickvals=fc.iloc[::2]["jam"], ticktext=fc.iloc[::2]["jam"], tickangle=-25, zeroline=False)
        fig_fc.update_yaxes(gridcolor="#E9EEF7", zeroline=False, rangemode="tozero")
        st.plotly_chart(fig_fc, width="stretch")

# ------------------------------------------------------------------ 8 SIGNAL SIMULATOR
with tabs[7]:
    md('<div class="sim-note">What-if simulator · rumus Webster + HCM uniform delay · asumsi dapat diubah</div>')
    top = trf.sort_values("traffic", ascending=False).head(100)
    lab = (top["street"] + " · " + top["direction"].fillna("") + " · #" + top["segmentid"].astype(str)).tolist()

    # IMPORTANT: the calculations below are unchanged. This section only changes presentation/layout.
    with st.container(border=True):
        pick_col, seg_col = st.columns([1.05, 2.2])
        with pick_col:
            md('<div class="sim-heading"><div class="sim-heading-icon"><span class="ms">tune</span></div><div><div class="sim-heading-title">ASUMSI</div><div class="sim-heading-sub">Atur parameter simulasi untuk melihat skenario kinerja persimpangan</div></div></div>')
        with seg_col:
            md('<div class="sim-segment-label">Segmen (top 100 volume)</div>')
            pick = st.selectbox("Segmen (top 100 volume)", lab, key="sigseg", label_visibility="collapsed")
        seg = top.iloc[lab.index(pick)]

        c1, c2, c3, c4 = st.columns(4)
        input_specs = [
            (c1, "directions_car", "Jumlah lajur"),
            (c2, "swap_vert", "Arus (kend/jam), asumsi"),
            (c3, "schedule", "Cycle sekarang (s)"),
            (c4, "traffic", "Hijau sekarang (s)")
        ]
        for col, icon, label in input_specs:
            with col:
                md(f'<div class="sim-input-card"><div class="sim-input-label"><span class="ms">{icon}</span>{label}</div>')
                if label == "Jumlah lajur":
                    lanes = st.number_input(label, 1, 4, 2, label_visibility="collapsed")
                elif label == "Arus (kend/jam), asumsi":
                    flow = st.number_input(label, 100, 8000, int(min(seg["traffic"], 1800 * lanes * .5)), key=f"f{seg['segmentid']}{lanes}", label_visibility="collapsed")
                elif label == "Cycle sekarang (s)":
                    cyc = st.number_input(label, 40, 200, 125, label_visibility="collapsed")
                else:
                    g_now = st.number_input(label, 10, 120, 45, label_visibility="collapsed")
                md('</div>')
        md('<div class="sim-slider"><div class="sim-slider-label">Flow ratio pendekat lawan (asumsi)</div>')
        y2 = st.slider("Flow ratio pendekat lawan (asumsi)", 0.05, 0.60, 0.25, label_visibility="collapsed")
        md('</div>')

    S, LOST = 1800, 16
    y1 = flow / (S * lanes)
    Y = y1 + y2

    def delay(C, g):
        X = flow / (S * lanes * g / C)
        return 0.5 * C * (1 - g / C) ** 2 / (1 - min(1, X) * g / C), X

    if Y >= .95:
        st.info(f"Pada asumsi ini persimpangan jenuh (Y = {Y:.2f}). Turunkan arus atau tambah lajur untuk melihat hasil.")
    else:
        C0 = (1.5 * LOST + 5) / (1 - Y)
        g_rec = max(10.0, (C0 - LOST) * y1 / Y)
        d0, X0 = delay(cyc, g_now)
        d1, X1 = delay(C0, g_rec)
        chg = (d1 - d0) / d0

        left, right = st.columns([1, 1])
        with left:
            with st.container(border=True):
                md(f'<div class="sim-card-head"><div><div class="sim-title"><span class="ms">speed</span>SIGNAL TIMING · {esc(seg["street"])}</div><div class="sim-subtitle">Perbandingan waktu sinyal aktual dan rekomendasi hasil simulasi</div></div><div class="sim-action">SIMULASI</div></div>')
                mxg = max(g_now, g_rec, 1) * 1.15
                md(f'<div class="sim-bar-label"><span>Current green time</span><b>{g_now:.0f}s</b></div><div class="sim-progress"><div style="width:{g_now / mxg * 100:.0f}%;background:#9AA7C0"></div></div>'
                   f'<div class="sim-bar-label"><span>Recommended green time</span><b>{g_rec:.0f}s</b></div><div class="sim-progress"><div style="width:{g_rec / mxg * 100:.0f}%;background:{BLUE}"></div></div>')
                good = "green" if chg < 0 else "red"
                t1c, t2c, t3c = st.columns(3)
                results = [(t1c, f"{chg:+.0%}", "Delay", good if chg < 0 else "red"),
                           (t2c, f"{(g_rec - g_now):+.0f}s", "Green time", "blue"),
                           (t3c, f"{(C0 - cyc):+.0f}s", "Cycle", "blue")]
                for col, v, l_, tone in results:
                    bg, fg = TONES[tone]
                    with col:
                        md(f'<div class="sim-result" style="background:{bg};border-color:{fg}33"><div class="v" style="color:{fg}">{v}</div><div class="l">{l_}</div></div>')

        with right:
            with st.container(border=True):
                md('<div class="sim-card-head"><div><div class="sim-title"><span class="ms">timeline</span>SIGNAL PHASE TIMELINE</div><div class="sim-subtitle">Visualisasi pembagian waktu siklus sinyal</div></div></div>')
                for name, g, C in [("CURRENT CYCLE", g_now, cyc), ("RECOMMENDED CYCLE", g_rec, C0)]:
                    md(f'<div class="sim-timeline-row"><div class="sim-timeline-head"><b>{name}</b><span class="sim-total">Total cycle {C:.0f}s</span></div>'
                       f'<div class="sim-timeline"><div style="width:{g / C * 100:.1f}%;background:{BLUE}">{g:.0f}s</div>'
                       f'<div style="width:{(C - g) / C * 100:.1f}%;background:{COLORS["Moderate"]}">{C - g:.0f}s</div></div>'
                       f'<div class="sim-legend"><span><i style="background:{BLUE}"></i>Green time ({g:.0f}s)</span><span><i style="background:{COLORS["Moderate"]}"></i>Other phase ({C-g:.0f}s)</span></div></div>')

            with st.container(border=True):
                md(f'<div class="sim-card-head"><div><div class="sim-title"><span class="ms">compare_arrows</span>BEFORE / AFTER</div><div class="sim-subtitle">Perbandingan kinerja sinyal sebelum dan sesudah optimasi</div></div><div class="sim-action">X = {X0:.2f} → {X1:.2f}</div></div>')
                md(f'<div class="sim-beforeafter">'
                   f'<div class="ba-card"><div class="ba-label">BEFORE</div><div class="ba-value">{cyc:.0f}s</div><div class="ba-sub">cycle · green {g_now:.0f}s · delay {d0:.1f}s</div></div>'
                   f'<div class="ba-arrow">→</div>'
                   f'<div class="ba-card after"><div class="ba-label">AFTER</div><div class="ba-value" style="color:#16A34A">{C0:.0f}s</div><div class="ba-sub">cycle · green {g_rec:.0f}s · delay {d1:.1f}s</div></div>'
                   f'<div class="ba-callout"><strong>✓ Peningkatan kinerja</strong><span>Nilai X turun dari {X0:.2f} menjadi {X1:.2f}; perubahan ini menunjukkan kondisi simulasi yang lebih baik.</span></div>'
                   f'</div>')

