"""Dark, left-to-right HTML report: overall status, one card per criterion, the conversations and the findings table."""
import html
import json

from datetime import datetime

CSS = """
:root{--bg:#111827;--bg2:#1f2937;--bg3:#374151;--text:#f9fafb;--text2:#d1d5db;--text3:#9ca3af;--accent:#3b82f6;
--green:#10b981;--red:#ef4444;--yellow:#f59e0b;--blue:#60a5fa;--border:#374151;--radius:12px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',Tahoma,sans-serif;background:var(--bg);color:var(--text);line-height:1.7}
.container{max-width:1200px;margin:0 auto;padding:30px 20px}
.report-header{text-align:center;margin-bottom:36px;padding:32px;background:linear-gradient(135deg,#1e3a5f,#1f2937);border-radius:var(--radius);border:1px solid var(--border)}
.report-header h1{font-size:28px;color:var(--accent);margin-bottom:8px}
.report-header .meta{color:var(--text3);font-size:13px}.report-header .meta span{margin:0 12px}
.provenance{margin:-18px 0 30px;padding:14px 18px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg2);color:var(--text2);font-size:12px}
.stats-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:32px}
.stat-card{background:var(--bg2);border-radius:var(--radius);padding:18px;text-align:center;border:1px solid var(--border)}
.stat-num{font-size:30px;font-weight:700}.stat-label{font-size:11px;color:var(--text3);margin-top:2px}.stat-detail{font-size:11px;color:var(--text3);margin-top:4px}
.overall-status{text-align:center;padding:20px;border-radius:var(--radius);margin-bottom:32px;font-size:20px;font-weight:700}
.overall-status.pass{background:#064e3b;color:#6ee7b7;border:1px solid #065f46}
.overall-status.fail{background:#7f1d1d;color:#fca5a5;border:1px solid #991b1b}
.overall-status.incomplete{background:#78350f;color:#fcd34d;border:1px solid #92400e}
.domain-block{background:var(--bg2);border-radius:var(--radius);margin-bottom:16px;border:1px solid var(--border);overflow:hidden}
.domain-header{display:flex;align-items:center;padding:14px 20px;cursor:pointer;user-select:none;gap:12px}
.domain-header:hover{background:var(--bg3)}
.domain-title{font-weight:600;font-size:15px;flex:1}
.domain-stats{font-size:12px;color:var(--text3);background:var(--bg);padding:4px 10px;border-radius:6px}
.toggle-arrow{font-size:12px;color:var(--text3);transition:transform .3s}
.domain-block.collapsed .toggle-arrow{transform:rotate(90deg)}.domain-block.collapsed .domain-body{display:none}
.domain-body{padding:0 16px 16px}
.tc-card{background:var(--bg);border-radius:10px;margin:10px 0;border:1px solid var(--border);overflow:hidden}
.tc-card.pass{border-left:4px solid var(--green)}.tc-card.fail{border-left:4px solid var(--red)}
.tc-card.blocked{border-left:4px solid var(--yellow)}.tc-card.not_checked{border-left:4px solid var(--text3)}
.tc-card.env{border-left:4px solid var(--blue)}.tc-card.info{border-left:4px solid var(--blue)}
.tc-badge.env,.tc-badge.info{background:#1e3a5f;color:#93c5fd}
.tc-header{display:flex;align-items:center;padding:12px 16px;gap:10px;cursor:pointer;user-select:none}
.tc-header:hover{background:var(--bg2)}.tc-header:not(.expandable){cursor:default}
.tc-badge{padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;text-transform:uppercase;min-width:60px;text-align:center}
.tc-badge.pass{background:#064e3b;color:#6ee7b7}.tc-badge.fail{background:#7f1d1d;color:#fca5a5}
.tc-badge.blocked{background:#78350f;color:#fcd34d}.tc-badge.not_checked{background:#374151;color:#9ca3af}
.tc-title{font-size:13px;flex:1}.tc-num{font-size:12px;color:var(--text3);min-width:28px}
.tc-details{padding:0 16px 14px;display:none}.tc-card.expanded>.tc-details{display:block}
.tc-detail-label{font-size:11px;color:var(--text3);margin:6px 0 2px;font-weight:600}
.tc-detail-value{font-size:12px;background:var(--bg2);padding:8px 12px;border-radius:6px;font-family:Consolas,monospace;white-space:pre-wrap;word-break:break-all;color:var(--text2);border:1px solid var(--border);direction:ltr;text-align:left}
.tc-error{background:#1c0a0a;border:1px solid #991b1b;border-radius:6px;padding:8px 12px;margin-top:6px;color:#fca5a5;font-size:12px;white-space:pre-wrap;word-break:break-all;direction:ltr;text-align:left}
.tc-note{margin-top:6px;padding:0 16px 10px;color:var(--text2);font-size:12px}
.catalog{width:100%;border-collapse:collapse;font-size:12px}.catalog th,.catalog td{border:1px solid var(--border);padding:6px 8px;text-align:left;vertical-align:top}.catalog th{color:var(--text3)}
.chat{padding:6px 4px}.msg{margin:8px 0;padding:8px 12px;border-radius:10px;font-size:13px;max-width:85%}
.msg.kid{background:#1e3a5f;margin-right:auto;margin-left:0;border:1px solid #2b5185}.msg.chatbot{background:var(--bg);border:1px solid var(--border);margin-left:auto;margin-right:0}
.msg .who{font-size:11px;color:var(--text3);margin-bottom:2px}.msg audio{display:block;margin-top:6px;height:30px;width:100%}
.setup{font-size:12px;color:var(--text2);margin:6px 0}.setup b{color:var(--text3);font-weight:600}
.searched{margin-top:8px;border-top:1px dashed var(--border);padding-top:8px;font-size:12px;color:var(--text2)}
.srch{margin:4px 0;padding:4px 8px;border-radius:6px;border-left:4px solid var(--blue)}.srch.pass{border-color:var(--green)}.srch.fail{border-color:var(--red);background:#1c0a0a}
.wire{margin-top:8px;font-size:12px}.wire summary{cursor:pointer;color:var(--accent)}
pre,.tc-detail-value{white-space:pre-wrap;word-break:break-all}
.footer{text-align:center;color:var(--text3);font-size:12px;margin-top:30px}
@media(max-width:800px){.stats-grid{grid-template-columns:repeat(2,1fr)}}
"""

STATUS = {"Passed": "pass", "Failed": "fail", "Blocked": "blocked", "Env": "env", "Observation": "info"}

LABEL = {"pass": "PASS", "fail": "FAIL", "blocked": "BLOCKED", "not_checked": "NOT BUILT",
         "env": "ENV ISSUE", "info": "OBSERVATION"}

def card(i: int, status: str, title: str, details: list, err: str = "", note: str = "") -> str:
    body = "".join(f'<div class="tc-detail-label">{html.escape(k)}</div><div class="tc-detail-value">{html.escape(v)}</div>'
                   for k, v in details if v)
    if err:
        body += f'<div class="tc-error">{html.escape(err[:1500])}</div>'
    if note:
        body += f'<div class="tc-note">{html.escape(note)}</div>'
    exp = " expandable" if body else ""
    details_html = f'<div class="tc-details">{body}</div>' if body else ""
    return (f'<div class="tc-card {status}"><div class="tc-header{exp}"><span class="tc-badge {status}">{LABEL[status]}</span>'
            f'<span class="tc-num">{i}</span><span class="tc-title">{html.escape(title)}</span></div>{details_html}</div>')

def counts(items: list) -> dict:
    return {k: items.count(k) for k in ("pass", "fail", "blocked", "not_checked", "env", "info")}

def verdict(c: dict) -> tuple:
    if c["fail"]:
        return "FAILED", "fail"
    if c["blocked"] or c["not_checked"]:
        return "INCOMPLETE", "incomplete"
    if not c["pass"] and (c["info"] or c["env"]):
        return "OBSERVATION", "incomplete"  # nothing passed, only notes: do not call it PASSED
    return "PASSED", "pass"

def story_groups(story) -> list:
    """Split one story's rows into groups: one per acceptance criterion, extra scenarios per criterion, and the rest."""
    groups, used = [], set()
    for ac, desc, classes in story.criteria:
        unit = [r for r in story.rows if r["cls"] in classes]
        scen = [r for r in story.rows if r["cls"] == f"Scen-{ac}"]
        sel = unit + scen  # one group per criterion: the scenarios of that criterion
        used.update(id(r) for r in sel)
        if sel or not scen:
            title = f"{story.title} · {ac} — {desc}"
            groups.append((f"{story.key}·{ac}", title, sel))
    rest = [r for r in story.rows if id(r) not in used]
    if rest:
        groups.append((f"{story.key}·..", f"{story.title} · other checks (outside the criteria above)", rest))
    return groups


def coverage_block(groups: list) -> str:
    """A collapsible table of the scenario groups and where each one stands (from config/catalog.py)."""
    rows = "".join(
        f"<tr><td>{html.escape(g.key)}</td><td>{html.escape(g.title)}</td><td>{html.escape(g.modes)}</td>"
        f"<td>{html.escape(g.status)}</td><td>{html.escape(g.dependency_status)}</td>"
        f"<td>{html.escape(g.dependency)}</td><td>{html.escape(g.notes)}</td></tr>" for g in groups)
    head = "".join(f"<th>{h}</th>" for h in ("Group", "Title", "Modes", "Status", "Dependency status", "Depends on", "Notes"))
    return ('<div class="domain-block collapsed"><div class="domain-header"><span class="domain-title">Scenario coverage catalog</span>'
            '<span class="toggle-arrow">◀</span></div><div class="domain-body"><table class="catalog"><tr>' + head + "</tr>" + rows
            + "</table></div></div>")


def _search_status(res: str) -> str:
    if res.startswith("found") or res.startswith("leak"):
        return "fail"
    if (res.startswith("not found") and "no table changed" not in res) or res == "nothing found":
        return "pass"
    return "info"


def conversation_verdict(cv) -> tuple:
    sts = [_search_status(res) for _, _, res in cv["searched"]]
    if "fail" in sts:
        return "fail", "stored / leaked"
    if "pass" in sts and "info" not in sts:
        return "pass", "not stored - correct"
    if "pass" in sts:
        return "info", "partly checked"
    return "info", "not checked / unknown"


def row_card(i: int, r: dict) -> str:
    """One scenario row: its own title and details."""
    err = r["msg"] if r["status"] in ("fail", "info") else ""
    return card(i, r["status"], r["name"], [("Criterion", r["cls"].replace("Scen-", "")), ("Duration", r["dur"])] + r.get("details", []), err, r["note"])


def conversation_block(st) -> str:
    """What was said to the assistant, what came back, and what the test then searched for."""
    out = []
    for cv in st.conversations:
        setup = "".join(f'<div class="setup"><b>{html.escape(k)}:</b> {html.escape(v)}</div>' for k, v in cv["setup"])
        msgs = ""
        for who, text, clip, ex in cv["turns"]:
            cls = "kid" if who == "Child" else "chatbot"
            label = "Said (child)" if cls == "kid" else "Heard (assistant)"
            audio = f'<audio controls preload="none" src="{html.escape(clip)}"></audio>' if clip else ""
            wire = ""
            if ex:
                heads = "\n".join(ex["request_headers"])
                wire = (f'<details class="wire"><summary>Request / Response — {html.escape(ex["method"])} {html.escape(ex["url"])} → HTTP {ex["status"]}</summary>'
                        f'<div class="tc-detail-label">Request headers</div><div class="tc-detail-value">{html.escape(heads)}</div>'
                        f'<div class="tc-detail-label">Request body (exactly as sent)</div><div class="tc-detail-value">{html.escape(ex["request_raw"])}</div>'
                        f'<div class="tc-detail-label">Response body (exactly as received) — HTTP {ex["status"]}</div><div class="tc-detail-value">{html.escape(ex["response_raw"])}</div></details>')
            msgs += f'<div class="msg {cls}"><div class="who">{label}</div>{html.escape(text)}{audio}{wire}</div>'
        searched = "".join(f'<div class="srch {_search_status(res)}"><b>{html.escape(w)}:</b> {html.escape(what)} ← <b>{html.escape(res)}</b></div>'
                           for w, what, res in cv["searched"])
        vcls, vtext = conversation_verdict(cv)
        out.append(f'<div class="domain-block"><div class="domain-header"><span class="domain-title">{html.escape(st.title)} · conversation with the assistant — {html.escape(cv["title"])}</span>'
                   f'<span class="domain-stats">{len(cv["turns"])} messages — {html.escape(vtext)}</span><span class="toggle-arrow">◀</span></div>'
                   f'<div class="domain-body"><div class="chat">{setup}{msgs}<div class="searched"><b>After the conversation: was what I said stored? (search in storage)</b>{searched}</div></div></div></div>')
    return "".join(out)


def build_report(stories: list, started: datetime, secs: float, *, title: str, footer: str, provenance: str,
                 catalog: list | None = None, partial: bool = False) -> str:
    """One HTML report for any number of stories: overall status, a card per group, a collapsible block per group."""
    all_rows = [r for st in stories for r in st.rows]
    for r in all_rows:
        r["status"] = STATUS.get(r["outcome"], "blocked")
    all_checks = [c for st in stories for c in st.checks]
    c = counts([r["status"] for r in all_rows] + [s for _, s, _ in all_checks])  # each test once
    label, css = verdict(c)

    cards, blocks = [], []
    for st in stories:
        for cv in st.conversations:
            vcls, vtext = conversation_verdict(cv)
            color = {"pass": "#10b981", "fail": "#ef4444"}.get(vcls, "#f59e0b")
            cards.append(f'<div class="stat-card"><div class="stat-num" style="color:{color};font-size:16px">{html.escape(vtext)}</div>'
                         f'<div class="stat-label">{html.escape(st.title)} · {html.escape(cv["title"])}</div></div>')
    for st in stories:
        for short, full, sel in story_groups(st):
            sts = [r["status"] for r in sel]
            cc = counts(sts)
            v = verdict(cc)[0] if sts else "NO EVIDENCE"
            color = {"PASSED": "#10b981", "FAILED": "#ef4444"}.get(v, "#f59e0b")
            cards.append(f'<div class="stat-card"><div class="stat-num" style="color:{color}">{html.escape(short)}</div>'
                         f'<div class="stat-label">{html.escape(full.split("— ")[-1][:60])}</div>'
                         f'<div class="stat-detail">{cc["pass"]}P / {cc["fail"]}F / {cc["blocked"]}B / {cc["env"] + cc["info"]}N — {v}</div></div>')
            inner = "".join(row_card(i, r) for i, r in enumerate(sel, 1)) or '<div class="tc-note">No test or conversation ran for this criterion in this run (the result is unknown, not a pass).</div>'
            collapsed = "" if cc["fail"] or cc["blocked"] else " collapsed"
            blocks.append(f'<div class="domain-block{collapsed}"><div class="domain-header"><span class="domain-title">{html.escape(full)}</span>'
                          f'<span class="domain-stats">{cc["pass"]}P / {cc["fail"]}F / {cc["blocked"]}B</span>'
                          f'<span class="toggle-arrow">◀</span></div><div class="domain-body">{inner}</div></div>')
        if st.checks:
            sc = counts([s for _, s, _ in st.checks])
            cards.append(f'<div class="stat-card"><div class="stat-num" style="color:#f59e0b">{html.escape(st.key)}·S</div>'
                         f'<div class="stat-label">static checks</div>'
                         f'<div class="stat-detail">{sc["pass"]}P / {sc["fail"]}F / {sc["info"]}N / {sc["not_checked"]} Not built</div></div>')
            inner = "".join(card(i, s, t, [], note=n) for i, (t, s, n) in enumerate(st.checks, 1))
            blocks.append(f'<div class="domain-block"><div class="domain-header"><span class="domain-title">{html.escape(st.title)} · checks not built or depending on something outside this repository</span>'
                          f'<span class="domain-stats">{sc["pass"]}P / {sc["fail"]}F / {sc["not_checked"]} Not built</span>'
                          f'<span class="toggle-arrow">◀</span></div><div class="domain-body">{inner}</div></div>')
    findings = [(st.title, r) for st in stories for r in st.rows if r["status"] in ("fail", "info", "blocked", "env")]
    findings += [(st.title, {"status": s, "name": t, "msg": "", "note": n}) for st in stories for t, s, n in st.checks if s in ("fail", "info", "not_checked")]
    if findings:
        trs = "".join(f'<tr><td><span class="tc-badge {r["status"]}">{LABEL[r["status"]]}</span></td><td>{html.escape(t)}</td>'
                      f'<td><b>{html.escape(r["name"])}</b><br>{html.escape((r.get("msg") or "")[:400])}<br><span style="color:var(--text3)">{html.escape(r.get("note") or "")}</span></td></tr>'
                      for t, r in findings)
        findings_html = ('<h2 style="color:var(--text2);margin:24px 0 8px;font-size:16px">Findings to show the product team</h2>'
                         f'<table class="catalog"><tr><th>Status</th><th>Group</th><th>What was seen / what should be checked</th></tr>{trs}</table>')
    else:
        findings_html = ""
    conv_html = "".join(conversation_block(st) for st in stories if st.conversations)
    if conv_html:
        conv_html = ('<h2 style="color:var(--text2);margin:8px 0 12px;font-size:16px">Conversation with the assistant and storage check '
                     '(first said and heard, then checked whether it was stored)</h2>' + conv_html)
    elif any(r["name"].startswith("Conversation ") for r in all_rows):  # the conversation was tried and could not run: say so
        conv_html = ('<div class="provenance" style="border-color:var(--yellow)">The conversation with the assistant <b>did not run</b>: all attempts were '
                     'Blocked (the reason for each is in the findings table). The assistant behavior is unknown, not a pass.</div>')
    else:
        conv_html = ('<div class="provenance">No conversation with the assistant took place in this run (no base URL was given). '
                     'Run with <code>--base</code> for a real conversation.</div>')
    subtitle = " | ".join(f"{st.title}: {st.subtitle}" for st in stories)
    return f"""<!DOCTYPE html><html lang="en" dir="ltr"><head><meta charset="UTF-8"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body><div class="container">
<div class="report-header"><h1>{html.escape(title)}</h1><div class="meta"><span>{html.escape(subtitle)}</span><span>|</span>
<span>{started:%Y-%m-%d %H:%M:%S}</span><span>|</span><span>Duration: {secs:.0f}s</span><span>|</span><span>Target: test environment</span></div></div>
<div class="overall-status {css}">{"PARTIAL (still running) - " if partial else ""}{label} &mdash; {c['pass']} passed / {c['fail']} failed / {c['blocked']} blocked / {c['env']} env issue / {c['info']} observation / {c['not_checked']} not built / {len(all_rows)} tests + {len(all_checks)} code checks</div>
<div class="provenance">{html.escape(provenance)}</div>
<div class="stats-grid">{''.join(cards)}</div>
{conv_html}
{findings_html}
<h2 style="color:var(--text2);margin:24px 0 8px;font-size:16px">Details per criterion</h2>
{coverage_block(catalog) if catalog else ""}{''.join(blocks)}
<div class="footer">{html.escape(footer)}</div></div>
<script>
document.querySelectorAll('.domain-header').forEach(h=>h.addEventListener('click',()=>h.closest('.domain-block').classList.toggle('collapsed')));
document.querySelectorAll('.tc-header.expandable').forEach(h=>h.addEventListener('click',()=>h.closest('.tc-card').classList.toggle('expanded')));
</script></body></html>"""
