"""Visual system for the industrial incident dashboard."""

from __future__ import annotations

from html import escape

import streamlit as st

INK = "#252A27"
MUTED = "#858D87"
GRAPH_DARK = "#505652"
GRAPH_MID = "#858C86"
GRAPH_LIGHT = "#BFC5BF"
GRID = "#ECEFEC"
SEVERITY_COLORS = (GRAPH_DARK, GRAPH_MID, GRAPH_LIGHT)


def apply_styles() -> None:
    st.markdown(
        """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');
:root { color-scheme:light; --font-ui:'Pretendard Variable','Pretendard','Noto Sans KR','Malgun Gothic',sans-serif; --font-mono:ui-monospace,'SFMono-Regular',Consolas,monospace; --ink:#252A27; --muted:#858D87; --line:#E5E8E4; --canvas:#F8F9F7; --sage:#638B73; }
html,body,#root,[data-testid="stScreencast"] { background:#D9DEDB !important; }
[data-testid="stApp"] { top:24px !important; right:auto !important; bottom:auto !important; left:50% !important; width:min(1360px,calc(100vw - 96px)) !important; height:calc(100vh - 48px) !important; transform:translateX(-50%); border:1px solid #E7EAE6; border-radius:12px; box-shadow:0 18px 55px rgba(44,55,47,.14),0 2px 8px rgba(44,55,47,.05); overflow:hidden; }
html,body,[data-testid="stAppViewContainer"],[data-testid="stSidebar"],[data-testid="stMarkdownContainer"],[data-testid="stWidgetLabel"],button,input,textarea { font-family:var(--font-ui) !important; }
html,body,[data-testid="stAppViewContainer"] { color:var(--ink); font-size:15px; line-height:1.58; }
[data-testid="stAppViewContainer"],[data-testid="stHeader"] { background:var(--canvas); }
.block-container { max-width:1530px; padding:52px 30px 64px; }
@media(max-width:900px) {
  [data-testid="stApp"] { top:0 !important; left:0 !important; width:100vw !important; height:100dvh !important; transform:none; border:0; border-radius:0; box-shadow:none; }
  [data-testid="stSidebar"] { width:min(250px,78vw) !important; min-width:min(250px,78vw) !important; max-width:min(250px,78vw) !important; }
  .block-container { max-width:none; padding:42px 18px 58px; }
}
@media(max-width:560px) {
  .block-container { padding:38px 13px 52px; }
  .scroll-top-link { right:12px; bottom:12px; }
  .workspace-bar { align-items:flex-start; }
}
.scroll-top-link { position:fixed; right:28px; bottom:24px; z-index:999; display:flex; align-items:center; gap:7px; padding:9px 13px; border:1px solid #D6DFD6; border-radius:7px; background:#FFFFFFF2; box-shadow:0 5px 18px rgba(34,48,37,.12); color:#405A46 !important; font-size:11px; font-weight:560; text-decoration:none !important; backdrop-filter:blur(8px); transition:background .16s,border-color .16s,transform .16s; }
.scroll-top-link:hover { background:#F1F6F0; border-color:#B8CCBA; transform:translateY(-2px); }
.scroll-top-link:focus-visible { outline:2px solid #73947A; outline-offset:3px; }
@media(max-width:640px) { .scroll-top-link { right:13px; bottom:14px; padding:8px 11px; } }
@media(prefers-reduced-motion:reduce) { .scroll-top-link { transition:none; } }
[data-testid="stMarkdownContainer"] p { line-height:1.58; }
[data-testid="stSidebar"] { background:#ECEFEB; border-right:1px solid #DDE2DC; width:clamp(172px,18.5vw,250px) !important; min-width:clamp(172px,18.5vw,250px) !important; max-width:clamp(172px,18.5vw,250px) !important; }
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding:22px 13px 25px; }
[data-testid="stSidebar"] hr { border-color:var(--line); margin:15px 0; }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color:#67716A; font-size:12px; font-weight:500; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color:var(--muted); font-size:11px; }
.sidebar-brand { display:flex; align-items:center; gap:9px; padding:0 4px 19px; border-bottom:1px solid var(--line); }
.sidebar-brand-icon { display:grid; place-items:center; width:31px; height:31px; border-radius:6px; background:#202521; color:white; font:600 17px var(--font-mono); }
.sidebar-brand-name { color:var(--ink); font-size:12px; font-weight:650; letter-spacing:-.025em; line-height:1.1; white-space:nowrap; }
.sidebar-brand-sub { color:#9AA19B; font:10px/1.2 var(--font-mono); margin-top:3px; }
.sidebar-section { color:#9AA19B; font:10px/1.2 var(--font-mono); letter-spacing:.06em; text-transform:uppercase; margin:20px 8px 9px; }
.sidebar-help { color:#9AA19B; font-size:11px; line-height:1.5; margin:5px 8px 0; }
[class*="st-key-nav_"] button { width:100%; min-height:36px; justify-content:flex-start; padding:7px 10px; border:1px solid transparent !important; border-radius:7px; background:transparent !important; color:#79817B !important; font-size:12px; font-weight:450; box-shadow:none !important; }
[class*="st-key-nav_"] button:hover { background:#E8EBE7 !important; color:var(--ink) !important; }
.sidebar-recent { display:flex; flex-direction:column; margin:1px 6px 0; }
.recent-row { display:flex; align-items:center; gap:8px; padding:7px 2px; border-bottom:1px solid #EAEBE9; min-width:0; }
.recent-dot { width:5px; height:5px; border-radius:50%; background:#9FB2A3; flex:none; }
.recent-title { font-size:11px; color:#676F69; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.recent-date { margin-left:auto; color:#AAB0AA; font:10px var(--font-mono); flex:none; }
.sidebar-foot { margin:25px 6px 0; padding-top:15px; border-top:1px solid var(--line); color:#9EA69F; font:10px/1.6 var(--font-mono); }
[data-testid="stSidebar"] [data-testid="stExpander"] { border-color:var(--line); background:#F8F9F7; border-radius:8px; }
[data-testid="stSidebar"] [data-testid="stExpander"] summary { font-size:11px; color:#6A736C; }
[data-testid="stSidebar"] [data-testid="stFileUploader"] section { background:white; border:1px dashed #D5DAD4; border-radius:7px; }
[data-testid="stSidebar"] [data-testid="stFileUploader"] section * { font-size:11px; }
[data-testid="stSidebar"] [data-testid="stButton"] button,[data-testid="stSidebar"] [data-testid="stDownloadButton"] button { font-size:11px; }
.workspace-bar { display:flex; align-items:center; justify-content:space-between; min-height:29px; margin:0 0 16px; gap:14px; }
.crumbs { display:flex; align-items:center; gap:10px; color:#959C96; font:11px var(--font-mono); }
.crumb-back { display:grid; place-items:center; width:25px; height:25px; border:1px solid var(--line); border-radius:6px; color:#7D867E; background:white; font:18px/1 var(--font-ui); }
.crumb-current { color:#4F5952; }
.workspace-right { display:flex; align-items:center; gap:8px; color:#8D968E; font:10px var(--font-mono); }
.toolbar-badge { padding:6px 9px; border:1px solid var(--line); border-radius:7px; background:white; white-space:nowrap; }
.toolbar-count { padding:6px 9px; border-radius:7px; background:#262C27; color:white; white-space:nowrap; }
.hero { position:relative; min-height:185px; overflow:hidden; border:1px solid var(--line); border-radius:12px; background:#F9FAF7 url('/app/static/hero-industrial.png') center right/cover no-repeat; }
.hero:before { content:''; position:absolute; inset:0; background:linear-gradient(90deg,rgba(255,255,255,.96) 0%,rgba(255,255,255,.90) 35%,rgba(255,255,255,.20) 62%,rgba(255,255,255,0) 85%); }
.hero-content { position:relative; z-index:1; padding:26px 30px 25px; max-width:650px; }
.hero-overline { color:#638B73; font:600 10px/1.2 var(--font-mono); letter-spacing:.06em; }
.hero h1 { font-size:clamp(27px,2.5vw,38px); letter-spacing:-.045em; line-height:1.25; font-weight:650; color:#202622; margin:9px 0 5px; }
.hero p { color:#6F7970; font-size:13px; line-height:1.6; margin:0; }
.st-key-hero_ctas { position:relative; z-index:2; width:310px; margin:-50px 0 9px 30px; }
.st-key-hero_ctas [data-testid="stHorizontalBlock"] { gap:8px; }
.st-key-hero_ctas button { min-height:32px; padding:0 9px; font-size:11px; white-space:nowrap; }
.st-key-hero_primary button { background:#262C27 !important; border-color:#262C27 !important; color:white !important; box-shadow:0 3px 8px #252B2733; }
.st-key-hero_secondary button { background:#FFFFFFEE !important; border-color:#E6E9E4 !important; color:#465047 !important; }
.data-notice { margin:9px 0 0; color:#8A9189; font-size:11px; line-height:1.5; }
.filter-strip { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:9px 18px; margin:15px 0 8px; }
.filter-tabs { display:inline-flex; align-items:center; gap:3px; padding:3px; border:1px solid var(--line); border-radius:8px; background:#F0F2EF; }
.filter-tab { padding:6px 12px; color:#89918A; font:10px var(--font-mono); white-space:nowrap; }
.filter-tab.active { background:white; color:#313A33; border-radius:6px; box-shadow:0 1px 2px #2B322C0E; }
.period-chip { padding:7px 10px; border:1px solid var(--line); border-radius:7px; color:#69736B; background:white; font:10px var(--font-mono); white-space:nowrap; }
.dashboard-row-label { display:flex; align-items:center; justify-content:space-between; margin:9px 0 8px; gap:10px; }
.dashboard-row-label h2 { font-size:13px !important; font-weight:600 !important; letter-spacing:-.02em; color:#343C35; margin:0 !important; line-height:1.4 !important; }
.dashboard-row-label h2:before { content:'◉'; color:#8F9D91; font-size:12px; margin-right:7px; }
.dashboard-row-label span { color:#A1A9A1; font:10px var(--font-mono); }
.feature-card { min-height:183px; padding:15px 15px 9px; border:1px solid var(--line); border-radius:10px; background:#F7F9F7; overflow:hidden; }
.feature-card,.distribution-card { transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease; }
.feature-card:hover,.distribution-card:hover { transform:translateY(-2px); border-color:#CDD5CD; box-shadow:0 9px 18px #3641380B; }
.feature-card-top { display:flex; align-items:flex-start; justify-content:space-between; gap:8px; }
.feature-card-title { font:600 11px/1.2 var(--font-mono); color:#333C34; letter-spacing:-.02em; }
.feature-card-sub { font:9px/1.3 var(--font-mono); color:#9BA59C; margin-top:3px; text-transform:uppercase; }
.card-icon { display:grid; place-items:center; width:22px; height:22px; border:1px solid #EAEEEA; border-radius:6px; color:#89908A; font:12px var(--font-ui); }
.feature-value { color:#222A23; font:650 30px/1.15 var(--font-ui); letter-spacing:-.045em; margin:18px 0 0; }
.feature-unit { color:#8C968D; font:10px var(--font-mono); margin-top:2px; }
.sparkline { width:100%; height:48px; display:block; margin-top:6px; }
.spark-wrap { position:relative; width:100%; margin-top:6px; }
.spark-wrap .sparkline { margin-top:0; }
.spark-popover { position:absolute; z-index:2; bottom:43px; min-width:96px; padding:5px 7px; border:1px solid #4A534B; border-radius:5px; background:#303A32; box-shadow:0 4px 12px #28332A26; color:white; font:10px var(--font-mono); text-align:center; white-space:nowrap; pointer-events:none; visibility:hidden; opacity:0; transform:translateX(-50%); transition:opacity .16s ease; }
.sparkline polyline { transition:stroke-width .2s ease,stroke .2s ease; }
.feature-card:hover .sparkline polyline { stroke-width:2.5; stroke:#505A51; }
.spark-point,.spark-bar { cursor:crosshair; outline:none; }
.spark-guide { stroke:#AAB3AA; stroke-width:1; stroke-dasharray:2 3; opacity:0; transition:opacity .18s ease; }
.spark-point:hover .spark-guide,.spark-point:focus-visible .spark-guide { opacity:1; }
.spark-bar { transition:opacity .18s ease,filter .18s ease; }
.spark-bar:hover,.spark-bar:focus-visible { filter:brightness(.78); }
.pillar-panel { border:1px solid var(--line); border-radius:10px; padding:8px 10px; background:white; }
.pillar-row { display:flex; align-items:center; gap:8px; padding:8px 2px; border-bottom:1px solid #EFF1EE; }
.pillar-row:last-child { border-bottom:0; }
.pillar-icon { display:grid; place-items:center; flex:none; width:29px; height:29px; border:1px solid #E8ECE8; border-radius:6px; color:#858C86; font-size:14px; }
.pillar-name { font:600 11px/1.3 var(--font-mono); color:#444D45; }
.pillar-sub { color:#A0A9A0; font:9px/1.3 var(--font-mono); margin-top:2px; }
.pillar-count { margin-left:auto; color:#67756B; background:#F4F6F3; padding:4px 6px; border-radius:4px; font:10px var(--font-mono); }
.quick-stat { min-height:70px; display:flex; align-items:center; gap:10px; padding:11px; border:1px solid var(--line); border-radius:8px; background:white; }
.quick-icon { color:#A1A7A1; font-size:16px; }
.quick-num { color:#39443B; font:600 16px/1.1 var(--font-mono); }
.quick-label { color:#9CA59D; font:9px/1.3 var(--font-mono); margin-top:3px; }
.distribution-card { min-height:170px; border:1px solid var(--line); border-radius:9px; overflow:hidden; background:white; }
.distribution-visual { position:relative; height:83px; background:#F0F2EF; display:flex; align-items:end; gap:5px; padding:14px 17px 0; overflow:visible; }
.distribution-bar { flex:1; min-width:4px; max-width:33px; background:#919892; border-radius:2px 2px 0 0; opacity:.76; }
.distribution-bar { cursor:crosshair; outline:none; }
.distribution-bar::after { content:attr(data-label); position:absolute; z-index:2; top:7px; left:50%; padding:5px 7px; border:1px solid #4A534B; border-radius:5px; background:#303A32; box-shadow:0 4px 12px #28332A26; color:white; font:10px var(--font-ui); white-space:nowrap; pointer-events:none; visibility:hidden; opacity:0; transform:translateX(-50%); transition:opacity .16s ease; }
.distribution-bar:hover::after,.distribution-bar:focus-visible::after { visibility:visible; opacity:1; }
.distribution-bar { transition:opacity .2s ease,transform .2s ease; }
.distribution-card:hover .distribution-bar { opacity:.92; }
.distribution-bar:hover { transform:translateY(-4px); opacity:1 !important; }
.distribution-bar:nth-child(even) { background:#C0C5C0; }
.distribution-content { padding:11px 12px 12px; }
.distribution-title { font:600 11px/1.3 var(--font-mono); color:#414A42; }
.distribution-description { color:#969F97; font-size:10px; line-height:1.45; margin-top:4px; }
.distribution-meta { color:#A9B0A9; font:9px var(--font-mono); margin-top:11px; }
.section-heading { display:flex; align-items:baseline; justify-content:space-between; gap:14px; margin:30px 0 12px; }
.section-heading-left { display:flex; align-items:baseline; gap:8px; min-width:0; }
.section-index { color:#A0ADA2; font:10px var(--font-mono); }
.section-heading h2.section-title { color:#354037; font-size:16px !important; font-weight:600 !important; letter-spacing:-.02em; line-height:1.4 !important; margin:0 !important; }
.section-description { color:#9AA39A; font-size:11px; }
.panel-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:8px; }
.panel-overline { color:#A3ACA3; font:9px var(--font-mono); letter-spacing:.04em; }
.panel-heading h3.panel-title { color:#3C463D; font-size:13px !important; font-weight:600 !important; line-height:1.4 !important; margin:3px 0 0 !important; }
.panel-subtitle { color:#9AA49A; font-size:10px; line-height:1.5; margin-top:3px; }
.panel-chip { color:#8E9B90; font:9px var(--font-mono); padding:4px 6px; border:1px solid var(--line); border-radius:5px; white-space:nowrap; }
[data-testid="stVerticalBlockBorderWrapper"] { background:white; border:1px solid var(--line); border-radius:10px; box-shadow:none; }
.infographic-panel { min-height:328px; padding:18px 19px; border:1px solid var(--line); border-radius:10px; background:white; overflow:hidden; }
.infographic-head { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
.infographic-kicker { color:#9AA29B; font:10px/1.2 var(--font-mono); letter-spacing:.04em; }
.infographic-panel h3 { color:#303731; font-size:17px !important; font-weight:600 !important; line-height:1.35 !important; letter-spacing:-.025em; margin:7px 0 3px !important; }
.infographic-panel p { color:#9BA39C; font-size:11px; margin:0; line-height:1.5; }
.infographic-highlight { display:flex; flex-direction:column; align-items:flex-end; white-space:nowrap; }
.infographic-highlight strong { color:#333A34; font:650 29px/1 var(--font-ui); letter-spacing:-.04em; }
.infographic-highlight span { color:#9CA49D; font:9px/1.3 var(--font-mono); margin-top:5px; }
.infographic-chart { position:relative; margin-top:20px; }
.trend-svg { display:block; width:100%; height:210px; }
.chart-axis { fill:#A1A9A2; font:10px var(--font-mono); }
.timeline-period { cursor:crosshair; outline:none; }
.period-focus { opacity:0; pointer-events:none; transition:opacity .18s ease; }
.period-hit { pointer-events:all; }
.period-column { transition:filter .18s ease; }
.period-axis { transition:fill .18s ease; }
.timeline-period:hover .period-focus,.timeline-period:focus-visible .period-focus { opacity:1; }
.timeline-period:hover .period-column,.timeline-period:focus-visible .period-column { filter:brightness(1.06) drop-shadow(0 2px 2px #38423A40); }
.timeline-period:hover .period-axis,.timeline-period:focus-visible .period-axis { fill:#3B453C; }
.month-popover { position:absolute; z-index:3; top:3px; display:flex; flex-direction:column; gap:3px; min-width:166px; padding:9px 11px; border:1px solid #4B544C; border-radius:7px; background:#303A32; box-shadow:0 7px 18px #28332A30; color:#FFFFFF; pointer-events:none; visibility:hidden; opacity:0; transform:translateX(-50%); transition:opacity .16s ease; }
.month-popover span { color:#CFD9CF; font:10px var(--font-mono); }
.month-popover strong { color:white; font:600 15px/1.1 var(--font-ui); }
.month-popover small { color:#D5DDD5; font:9px var(--font-ui); white-space:nowrap; }
.infographic-footer { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:7px 12px; padding-top:11px; border-top:1px solid #F0F2EF; color:#A0A8A0; font-size:10px; }
.chart-legend { display:flex; align-items:center; flex-wrap:wrap; gap:12px; }
.chart-legend span { display:inline-flex; align-items:center; gap:5px; color:#848D85; font-size:10px; }
.chart-legend i,.severity-legend-row i { display:inline-block; width:7px; height:7px; border-radius:2px; flex:none; }
.chart-footnote { color:#9BA49C; font:10px var(--font-mono); }
.chart-footnote b { margin:0 5px; font-weight:400; color:#C3C8C3; }
.severity-visual { display:flex; align-items:center; justify-content:center; gap:12px; min-height:226px; }
.donut-svg { width:46%; max-width:180px; flex:none; }
.donut-segment { cursor:pointer; outline:none; transition:stroke-width .22s ease,opacity .22s ease,filter .22s ease; }
.severity-visual:has(.donut-segment:hover) .donut-segment:not(:hover),.severity-visual:has(.donut-segment:focus-visible) .donut-segment:not(:focus-visible) { opacity:.45; }
.donut-segment:hover,.donut-segment:focus-visible { stroke-width:27; filter:drop-shadow(0 2px 3px #39423A40); }
.donut-default,.donut-hover-value { pointer-events:none; transition:opacity .18s ease; }
.donut-hover-value { opacity:0; }
.severity-visual:has(.donut-segment:hover) .donut-default,.severity-visual:has(.donut-segment:focus-visible) .donut-default,.severity-visual:has(.severity-legend-row:hover) .donut-default,.severity-visual:has(.severity-legend-row:focus-visible) .donut-default { opacity:0; }
.severity-visual:has(.donut-segment.tone-0:hover) .donut-hover-value.tone-0,.severity-visual:has(.donut-segment.tone-0:focus-visible) .donut-hover-value.tone-0,.severity-visual:has(.severity-legend-row.tone-0:hover) .donut-hover-value.tone-0,.severity-visual:has(.severity-legend-row.tone-0:focus-visible) .donut-hover-value.tone-0,.severity-visual:has(.donut-segment.tone-1:hover) .donut-hover-value.tone-1,.severity-visual:has(.donut-segment.tone-1:focus-visible) .donut-hover-value.tone-1,.severity-visual:has(.severity-legend-row.tone-1:hover) .donut-hover-value.tone-1,.severity-visual:has(.severity-legend-row.tone-1:focus-visible) .donut-hover-value.tone-1,.severity-visual:has(.donut-segment.tone-2:hover) .donut-hover-value.tone-2,.severity-visual:has(.donut-segment.tone-2:focus-visible) .donut-hover-value.tone-2,.severity-visual:has(.severity-legend-row.tone-2:hover) .donut-hover-value.tone-2,.severity-visual:has(.severity-legend-row.tone-2:focus-visible) .donut-hover-value.tone-2 { opacity:1; }
.severity-visual:has(.severity-legend-row.tone-0:hover) .donut-segment.tone-0,.severity-visual:has(.severity-legend-row.tone-0:focus-visible) .donut-segment.tone-0,.severity-visual:has(.severity-legend-row.tone-1:hover) .donut-segment.tone-1,.severity-visual:has(.severity-legend-row.tone-1:focus-visible) .donut-segment.tone-1,.severity-visual:has(.severity-legend-row.tone-2:hover) .donut-segment.tone-2,.severity-visual:has(.severity-legend-row.tone-2:focus-visible) .donut-segment.tone-2 { stroke-width:27; filter:drop-shadow(0 2px 3px #39423A40); }
.donut-total { fill:#343B35; font:650 29px var(--font-ui); letter-spacing:-.04em; }
.donut-label { fill:#A0A9A0; font:9px var(--font-mono); letter-spacing:.07em; }
.severity-legend { flex:1; min-width:112px; }
.severity-legend-row { display:grid; grid-template-columns:8px 1fr auto; align-items:center; gap:5px; padding:8px 0; border-bottom:1px solid #F0F2EF; }
.severity-legend-row { border-radius:5px; cursor:pointer; outline:none; transition:background .18s ease,padding .18s ease; }
.severity-legend-row:hover,.severity-legend-row:focus-visible { background:#F4F6F3; padding-left:5px; padding-right:5px; }
.severity-visual:has(.donut-segment.tone-0:hover) .severity-legend-row.tone-0,.severity-visual:has(.donut-segment.tone-0:focus-visible) .severity-legend-row.tone-0,.severity-visual:has(.donut-segment.tone-1:hover) .severity-legend-row.tone-1,.severity-visual:has(.donut-segment.tone-1:focus-visible) .severity-legend-row.tone-1,.severity-visual:has(.donut-segment.tone-2:hover) .severity-legend-row.tone-2,.severity-visual:has(.donut-segment.tone-2:focus-visible) .severity-legend-row.tone-2 { background:#F4F6F3; padding-left:5px; padding-right:5px; }
.severity-legend-row:last-child { border:0; }
.severity-legend-row span { color:#626C63; font-size:11px; }
.severity-legend-row strong { color:#414A42; font:600 12px var(--font-mono); }
.severity-legend-row small { font:9px var(--font-mono); color:#A5ADA5; margin-left:2px; }
.severity-legend-row em { grid-column:2/4; color:#9CA59C; font:9px var(--font-mono); font-style:normal; margin-top:-4px; }
.severity-share-track { grid-column:2/4; height:3px; margin-top:1px; border-radius:3px; overflow:hidden; background:#EDF0EC; }
.severity-share-track span { display:block; height:100%; border-radius:3px; }
.rank-panel { min-height:485px; }
.rank-description { margin-top:2px !important; }
.rank-leader { display:flex; align-items:flex-end; justify-content:space-between; gap:8px; margin-top:14px; padding:12px 13px; border:1px solid #E9ECE8; border-radius:8px; background:#F5F7F4; }
.rank-leader div { display:flex; flex-direction:column; gap:4px; min-width:0; }
.rank-leader span { color:#9BA49C; font:9px/1.2 var(--font-mono); letter-spacing:.04em; }
.rank-leader strong { color:#414A42; font-size:15px; font-weight:600; line-height:1.2; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.rank-leader em { color:#414942; font:600 17px/1.1 var(--font-mono); font-style:normal; white-space:nowrap; text-align:right; }
.rank-leader small { display:block; margin-top:4px; color:#9FA79F; font:9px/1.2 var(--font-mono); }
.rank-list { margin-top:17px; }
.rank-row { margin-bottom:14px; }
.rank-row { border-radius:6px; outline:none; transition:transform .18s ease,background .18s ease; }
.rank-row:hover,.rank-row:focus-visible { transform:translateX(3px); background:#F7F9F6; }
.rank-row:last-child { margin-bottom:0; }
.rank-line { display:flex; align-items:baseline; gap:7px; min-width:0; }
.rank-order { color:#ADB4AD; font:10px var(--font-mono); }
.rank-name { color:#535C54; font-size:11px; font-weight:550; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.rank-count { color:#414942; font:600 11px var(--font-mono); margin-left:auto; white-space:nowrap; }
.rank-count small { color:#9DA69D; font:9px var(--font-mono); margin-left:2px; }
.rank-track { height:6px; margin:6px 0 2px 22px; border-radius:4px; background:#F0F2EF; overflow:hidden; }
.rank-track span { display:block; height:100%; background:linear-gradient(90deg,#5F6660,#9AA19B); border-radius:4px; }
.rank-track span { transform-origin:left center; transition:filter .18s ease,transform .18s ease; }
.rank-row:hover .rank-track span,.rank-row:focus-visible .rank-track span { filter:brightness(.83); transform:scaleY(1.2); }
.rank-share { margin-left:22px; color:#B0B7B0; font:8px var(--font-mono); text-align:right; }
.interpret-note { margin:14px 0 0; color:#9BA59C; font-size:11px; line-height:1.55; }
.hero h1,.simple-intro h1,.dashboard-row-label h2,.section-heading h2.section-title,.infographic-panel h3 { padding:0 !important; }
.simple-intro { position:relative; display:flex; flex-direction:column; justify-content:center; min-height:180px; padding:26px 29px; overflow:hidden; border:1px solid var(--line); border-radius:10px; background:white center right/cover no-repeat; }
.simple-intro.records { background-image:url('/app/static/hero-records.png'); }
.simple-intro.guide { background-image:url('/app/static/hero-guide.png'); }
.simple-intro.chat { background-image:url('/app/static/hero-guide.png'); }
.simple-intro::before { content:''; position:absolute; inset:0; background:linear-gradient(90deg,rgba(255,255,255,.97) 0%,rgba(255,255,255,.88) 42%,rgba(255,255,255,.08) 82%); }
.simple-intro > * { position:relative; z-index:1; max-width:62%; }
.simple-intro h1 { color:#29332B; font-size:29px !important; font-weight:650 !important; letter-spacing:-.04em; margin:8px 0 4px !important; }
.simple-intro p { color:#8E998F; font-size:12px; margin:0; }
.context-line { margin:12px 0 0; color:#929B92; font:10px/1.6 var(--font-mono); }
.chat-page-heading { display:flex; align-items:end; justify-content:space-between; gap:16px; margin:23px 0 17px; }
.chat-page-heading span,.chat-options-kicker,.chat-conversation-head span { color:#788E7C; font:600 10px/1.3 var(--font-mono); letter-spacing:.07em; }
.chat-page-heading h2 { color:#29332B; font-size:20px !important; font-weight:600 !important; letter-spacing:-.035em; line-height:1.35 !important; margin:7px 0 5px !important; padding:0 !important; }
.chat-page-heading p { color:#89938A; font-size:12px; line-height:1.65; margin:0; }
.chat-source-mark { flex:none; padding:7px 10px; background:#EFF3EE; border:1px solid #E2E9E0; border-radius:6px; color:#6C8370; font:10px var(--font-mono); }
.st-key-chat_options,.st-key-chat_reference { background:white; border-color:var(--line) !important; border-radius:10px !important; padding:17px !important; }
.st-key-chat_options h3,.st-key-chat_reference h3,.chat-conversation-head h3 { color:#2D352F; font-size:15px !important; font-weight:600 !important; letter-spacing:-.025em; margin:5px 0 10px !important; padding:0 !important; }
.st-key-chat_options [data-testid="stWidgetLabel"] p { color:#6B746D; font-size:11px; font-weight:500; }
.st-key-chat_options [data-testid="stCaptionContainer"],.st-key-chat_reference [data-testid="stCaptionContainer"] { color:#939B93; font-size:11px; line-height:1.55; }
.chat-conversation-head { display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid var(--line); padding:4px 0 7px; margin:0 0 15px; }
.chat-conversation-head h3 { margin-bottom:0 !important; }
.chat-empty { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:220px; margin-bottom:15px; padding:25px; border:1px solid #E4EAE3; border-radius:10px; background:radial-gradient(circle at 50% 15%,#F0F5EF,white 64%); text-align:center; }
.chat-empty > span { display:grid; place-items:center; width:40px; height:40px; border:1px solid #D9E5D9; border-radius:11px; background:white; color:#64866A; font-size:19px; }
.chat-empty h3 { margin:15px 0 5px !important; color:#364139; font-size:17px !important; font-weight:600 !important; letter-spacing:-.025em; }
.chat-empty p { max-width:390px; margin:0; color:#919C92; font-size:12px; line-height:1.65; }
.chat-source-item { margin:7px 0; padding:10px 12px; border:1px solid var(--line); border-radius:7px; background:#FAFBF9; }
.chat-source-item strong { color:#39463B; font-size:12px; font-weight:600; }
.chat-source-item p { margin:3px 0 0 !important; color:#879188; font-size:11px; }
.chat-source-item a { color:#5D7C62; font-size:11px; text-decoration:underline; text-underline-offset:2px; }
[data-testid="stChatMessage"] { background:#F7F9F7; border:1px solid #E7ECE6; border-radius:9px; }
[data-testid="stChatMessage"] h3 { color:#354037; font-size:15px !important; font-weight:600 !important; line-height:1.45 !important; letter-spacing:-.025em; margin:10px 0 7px !important; }
[data-testid="stChatMessage"] li { color:#4E5A50; font-size:12px; line-height:1.7; margin:3px 0; }
[data-testid="stChatMessage"] .infographic-panel { margin-top:13px; min-height:0; padding:14px; }
[data-testid="stChatMessage"] .infographic-head { gap:8px; }
[data-testid="stChatMessage"] .infographic-panel h3 { margin:6px 0 3px !important; font-size:14px !important; }
[data-testid="stChatMessage"] .infographic-highlight strong { font-size:22px; }
[data-testid="stChatMessage"] .trend-svg { height:185px; }
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:8px; overflow:hidden; }
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button { border-radius:7px; font-weight:500; }
button:focus-visible,input:focus-visible,textarea:focus-visible,[role="combobox"]:focus-visible,a:focus-visible { outline:2px solid #638B73 !important; outline-offset:2px !important; }
hr { border-color:var(--line); }
@media (max-width:1100px) { [data-testid="stApp"] { width:calc(100vw - 80px) !important; top:24px !important; height:calc(100vh - 48px) !important; } .block-container { padding-left:18px; padding-right:18px; } .hero { min-height:209px; } .hero-content { padding:23px; } }
@media (max-width:780px) { .block-container { padding:10px 14px 45px; } .workspace-right { display:none; } .hero { min-height:190px; background-position:60% center; } .hero:before { background:linear-gradient(90deg,#FFFFFFF7 0%,#FFFFFFE8 52%,#FFFFFF55 100%); } .hero-content { padding:20px; } .hero h1 { font-size:27px; } .st-key-hero_ctas { width:100%; margin:8px 0 0; } .st-key-dashboard_main [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; } .st-key-dashboard_main [data-testid="stColumn"] { flex:1 1 100% !important; width:100% !important; } .section-description { display:none; } }
@media (max-width:780px) { html,body,#root,[data-testid="stScreencast"] { background:var(--canvas) !important; } [data-testid="stApp"] { top:0 !important; left:0 !important; width:100vw !important; height:100vh !important; transform:none; border:0; border-radius:0; box-shadow:none; } [data-testid="stSidebar"] { width:min(300px,80vw) !important; min-width:min(300px,80vw) !important; max-width:min(300px,80vw) !important; } }
@media (max-width:580px) { .severity-visual { justify-content:flex-start; } .donut-svg { width:43%; } .infographic-panel { padding:15px; } .infographic-highlight strong { font-size:24px; } .simple-intro { min-height:160px; padding:20px; background-position:62% center; } .simple-intro > * { max-width:76%; } .simple-intro::before { background:linear-gradient(90deg,#FFFFFFF8 0%,#FFFFFFE9 55%,#FFFFFF55 100%); } }
@media (max-width:580px) { .st-key-feature_grid [data-testid="stHorizontalBlock"],.st-key-distribution_grid [data-testid="stHorizontalBlock"],.st-key-quick_grid [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; } .st-key-feature_grid [data-testid="stColumn"],.st-key-distribution_grid [data-testid="stColumn"] { flex:1 1 100% !important; width:100% !important; } .st-key-quick_grid [data-testid="stColumn"] { flex:1 1 44% !important; width:44% !important; } .hero { background-position:68% center; } .hero p { max-width:215px; } .filter-strip { align-items:flex-start; } .filter-tabs { max-width:100%; overflow:auto; } }
@media (max-width:780px) { .chat-page-heading { align-items:flex-start; flex-direction:column; } .chat-source-mark { display:none; } }
@media (max-width:780px) { [data-testid="stHorizontalBlock"]:has(.st-key-chat_options) { flex-wrap:wrap !important; } [data-testid="stHorizontalBlock"]:has(.st-key-chat_options) > [data-testid="stColumn"] { flex:1 1 100% !important; width:100% !important; } }
@media (max-width:580px) { .st-key-chat_field_shortcuts [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; } .st-key-chat_field_shortcuts [data-testid="stColumn"] { flex:1 1 calc(50% - 5px) !important; width:calc(50% - 5px) !important; } }
@media (prefers-reduced-motion:reduce) { .feature-card,.distribution-card,.distribution-bar,.distribution-bar::after,.sparkline polyline,.spark-guide,.spark-bar,.spark-popover,.period-focus,.period-column,.period-axis,.month-popover,.donut-segment,.donut-default,.donut-hover-value,.severity-legend-row,.rank-row,.rank-track span { transition:none !important; } }
</style>
""",
        unsafe_allow_html=True,
    )


def render_back_to_top() -> None:
    st.markdown('<a class="scroll-top-link" href="#page-top" aria-label="페이지 맨 위로 이동">↑ <span>맨 위로</span></a>', unsafe_allow_html=True)


def render_sidebar_brand() -> None:
    st.markdown(
        '<div class="sidebar-brand"><div class="sidebar-brand-icon">✳</div><div>'
        '<div class="sidebar-brand-name">Safety Atlas</div>'
        '<div class="sidebar-brand-sub">INCIDENT OS</div></div></div>',
        unsafe_allow_html=True,
    )


def _navigate(view: str) -> None:
    st.session_state["view"] = view
    st.query_params["page"] = view


def render_header(
    source: str, period: str, rows: int, latest_date: str, is_sample: bool, view: str
) -> None:
    source, period, latest_date = map(escape, (source, period, latest_date))
    page_label = {"overview": "현황 분석", "records": "사고 기록", "guide": "데이터 안내", "chat": "근거 챗봇"}[view]
    if view == "chat":
        st.markdown(
            '<div class="workspace-bar"><div class="crumbs"><span class="crumb-back">‹</span>'
            '<span>Safety Atlas</span><span>/</span><span class="crumb-current">근거 챗봇</span></div>'
            '<div class="workspace-right"><span class="toolbar-badge">SANUP-P RAG</span></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="simple-intro chat"><div class="hero-overline">SAFETY INTELLIGENCE / ASSISTANT</div>'
            '<h1>산업재해 챗봇</h1><p>사고 기록을 살펴보고 안전 지침의 근거를 확인합니다.</p></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="context-line">현재 사고 CSV 집계 · SANUP-P 검색 색인 · SIF 사례 · KOSHA GUIDE</div>',
            unsafe_allow_html=True,
        )
        return
    st.markdown(
        f'<div class="workspace-bar"><div class="crumbs"><span class="crumb-back">‹</span>'
        f'<span>Safety Atlas</span><span>/</span><span class="crumb-current">{page_label}</span></div>'
        f'<div class="workspace-right"><span class="toolbar-badge">{latest_date} 기준</span>'
        f'<span class="toolbar-count">{rows:,} RECORDS</span></div></div>',
        unsafe_allow_html=True,
    )
    if view == "overview":
        st.markdown(
            '<div class="hero"><div class="hero-content">'
            '<div class="hero-overline">SAFETY INTELLIGENCE / OVERVIEW</div>'
            '<h1>산업재해 현황</h1>'
            '<p>사고 기록에서 오늘의 위험 신호와 발생 패턴을 살펴보세요.</p>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        with st.container(key="hero_ctas"):
            first, second = st.columns([1.3, 1], gap="small")
            with first:
                with st.container(key="hero_primary"):
                    st.button("＋ 사고 기록 보기", on_click=_navigate, args=("records",), width="stretch")
            with second:
                with st.container(key="hero_secondary"):
                    st.button("◉ 데이터 기준", on_click=_navigate, args=("guide",), width="stretch")
    else:
        overline = "INCIDENT RECORDS / EXPLORER" if view == "records" else "DATA SOURCE / METHODOLOGY"
        description = (
            "필터 결과에서 개별 사고를 찾고 필요한 기록을 내려받습니다."
            if view == "records" else "데이터 상태, 집계 기준, 해석 범위를 확인합니다."
        )
        st.markdown(
            f'<div class="simple-intro {view}"><div class="hero-overline">{overline}</div>'
            f'<h1>{page_label}</h1><p>{description}</p></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="context-line">{source} · {period} · '
        f'{"시연용 가상 데이터" if is_sample else "업로드한 데이터"}</div>',
        unsafe_allow_html=True,
    )
    if is_sample:
        st.markdown(
            '<div class="data-notice">현재 수치는 시연용 가상 데이터이며 실제 산업재해 통계가 아닙니다.</div>',
            unsafe_allow_html=True,
        )


def section_heading(index: str, title: str, description: str = "") -> None:
    st.markdown(
        f'<div class="section-heading"><div class="section-heading-left">'
        f'<span class="section-index">{escape(index)}</span>'
        f'<h2 class="section-title">{escape(title)}</h2></div>'
        f'<span class="section-description">{escape(description)}</span></div>',
        unsafe_allow_html=True,
    )


def panel_heading(overline: str, title: str, subtitle: str, chip: str) -> None:
    st.markdown(
        f'<div class="panel-heading"><div><div class="panel-overline">{escape(overline)}</div>'
        f'<h3 class="panel-title">{escape(title)}</h3>'
        f'<div class="panel-subtitle">{escape(subtitle)}</div></div>'
        f'<span class="panel-chip">{escape(chip)}</span></div>',
        unsafe_allow_html=True,
    )
