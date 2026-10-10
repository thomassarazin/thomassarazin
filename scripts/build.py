#!/usr/bin/env python3
"""Build every SVG asset of the profile README, in the nualt palette.

    python3 scripts/build.py

Type system: Outfit 300 for titles (OFL, free to embed), close to the Yellix of the site,
Inter 400 for body, Geist Pixel for labels. Never bold. Blue on ivory, square corners, 1px lines.
Fonts are embedded per card, only the faces the card uses, files untouched.
Data cards (activity, contributions, repo facts) need `gh` authenticated locally, or GH_TOKEN on CI.
"""
import datetime, html, json, os, re, subprocess, urllib.request

USER = os.environ.get("GH_USER", "thomassarazin")
BLUE, IVORY, MUTED = "#0755B5", "#F4F2E8", "#326DAA"    # --foreground, --background, --foreground-muted
BG, FG, LINE = IVORY, BLUE, BLUE
EMPTY, RAMP = "#E4E4E0", ["#B5C8E4", "#7A9FD3", "#3F76C4", BLUE]
W, HALF = 1000, 490                          # full README column, and a cell of a two column table

FONTS = json.load(open("scripts/fonts.json"))
FACES = {"outfit": ("Outfit", 300), "inter400": ("Inter", 400), "pixel": ("Geist Pixel", 400),
         "mono": ("Geist Mono", 400)}
TITLE = "Outfit,Helvetica,Arial,sans-serif"
BODY = "Inter,Helvetica,Arial,sans-serif"
PIXEL = "'Geist Pixel',ui-monospace,Menlo,monospace"
MONO = "'Geist Mono',ui-monospace,Menlo,monospace"
STYLE = {"title": (TITLE, 300, 0.52, "outfit"),     # family, weight, average advance (em), face key
         "body": (BODY, 400, 0.50, "inter400"),
         "label": (PIXEL, 400, 0.60, "pixel"),      # subheads, facts, dates
         "code": (MONO, 400, 0.60, "mono")}         # install commands
H1, H2, H3, TXT, LBL = 44, 32, 24, 16, 14            # the whole scale. Titles: Outfit. Text: Inter.

HEADLINE = ["Custom e-commerce on MedusaJS v2",
            "Payload CMS / Next.js",
            "Open source under @nualt"]
# Real width of each line at 44px, measured in Chrome with getComputedTextLength() on the
# embedded font. A line missing here falls back to the estimate and sits slightly off-centre.
HEADLINE_PX = {"Custom e-commerce on MedusaJS v2": 732,
               "Payload CMS / Next.js": 427,
               "Open source under @nualt": 510}

ABOUT = {
    "name": "Thomas Sarazin",
    "role": "nualt, micro-agence web. Paris & Valenciennes.",
    "body": [
        "I build custom e-commerce on MedusaJS v2 and content sites on Payload CMS, then I write "
        "down what they actually cost to run.",
        "",
        "Most jobs reach me after a redesign failed to move anything. The answer is usually in the "
        "architecture, the hosting bill or the checkout, rarely in the colours.",
        "",
        "I wrote a novel before I wrote a line of code. Same hard part: cutting what does not need "
        "to be there.",
    ],
    "facts": [("stack", "MedusaJS / Payload / Next.js"),
              ("writing", "nualt.fr/blog")],
}

REPOS = [
    {"name": "medusa-plugin-better-auth", "url": "https://github.com/nualt/medusa-plugin-better-auth",
     "desc": "The authentication brick Medusa v2 was missing. Better Auth wired into Medusa for "
             "modern, flexible auth. Every abandoned signup is a sale that goes elsewhere.",
     "icon": "betterauth-inverse-isometrique", "npm": "@nualt/medusa-plugin-better-auth"},
    {"name": "responsive-motion", "url": "https://github.com/nualt/responsive-motion",
     "desc": "Claude Code skill that makes scroll choreographies degrade cleanly on every device: "
             "pinned sections, sticky columns, reduced motion. No per-device hacks.",
     "icon": "appareils-isometriques"},
]

POSTS = [
    ("On a construit la brique d'authentification qui manquait à Medusa v2", "plugin-better-auth-medusa-v2"),
    ("Site animé qui casse sur mobile : notre méthode open source", "site-anime-responsive-methode-open-source"),
    ("Anatomie de deux failles de Next.js, et ce qu'elles disent du web", "failles-nextjs-securite-hebergement"),
    ("Shopify vs Medusa : quelle plateforme en 2026 ?", "shopify-vs-medusa-ecommerce"),
    ("Auto-hébergé ou PaaS : quel hébergement en 2026 ?", "auto-heberge-vs-paas"),
    ("Pourquoi votre site internet coûte plus cher que nécessaire", "pourquoi-site-internet-coute-cher"),
]

SECTIONS = [("about", "About"), ("open-source", "Open source"), ("writing", "Writing"),
            ("stack", "Stack"), ("activity", "GitHub activity"), ("elsewhere", "Elsewhere")]

LINKS = [("nualt.fr", "https://nualt.fr"), ("Behance", "https://behance.net/thomassarazin_nualt"),
         ("Instagram", "https://www.instagram.com/nualtstudio/"), ("thomas@nualt.fr", "mailto:thomas@nualt.fr")]

ICONS = ["typescript (1)", "javascript", "python (1)", "html-light", "css-light", "tailwind",
         "nextjs-light (1)", "expo-dark", "medusa-light (1)", "payloadcms-dark (1)", "vercel-light",
         "digital-ocean (1)", "dify"]
ICONS_CREAM = {"medusa-light (1)", "dify"}   # drawn with no fill of their own: painted FG
ICONS_WHITE = {"expo-dark", "medusa-light (1)", "payloadcms-dark (1)", "vercel-light"}  # white logos: black on ivory

# --------------------------------------------------------------------------- helpers
def esc(s):
    return html.escape(str(s), quote=False)

def text(x, y, s, size, style="body", fill=FG, anchor="start"):
    fam, weight, _, _ = STYLE[style]
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-family="{fam}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{esc(s)}</text>')

def width(s, size, style="body"):
    return len(s) * size * STYLE[style][2]

def wrap(s, width_px, size, style="body"):
    n = max(1, int(width_px / (size * STYLE[style][2])))
    lines, cur = [], ""
    for word in s.split():
        if len(cur) + len(word) + (1 if cur else 0) <= n:
            cur = f"{cur} {word}".strip()
        else:
            lines.append(cur); cur = word
    return lines + ([cur] if cur else [])

def faces(*styles):
    """@font-face rules for the given styles only, so each card carries just what it uses."""
    keys = sorted({STYLE[s][3] for s in styles})
    rules = "".join(f"@font-face{{font-family:'{FACES[k][0]}';font-style:normal;font-weight:{FACES[k][1]};"
                    f"src:url(data:font/woff2;base64,{FONTS[k]['b64']}) format('woff2');}}" for k in keys)
    return f"<style>{rules}</style>"

def card(w, h, label, styles=(), radius=0, fill=BG, stroke=None):
    s = f' stroke="{stroke}"' if stroke else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">'
            f'{faces(*styles) if styles else ""}'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{radius}" fill="{fill}"{s}/>')

def write(path, parts):
    open(path, "w").write("".join(parts) + "</svg>")

def inline_svg(path, i, cream=False):
    """(viewBox, inner markup, root fill) of an svg file, ids namespaced so several can share a document."""
    s = open(path).read()
    s = re.sub(r"<\?xml.*?\?>|<!DOCTYPE[^>]*>", "", s, flags=re.S)
    m = re.search(r"<svg([^>]*)>(.*)</svg>", s, re.S)
    attrs, inner = m.group(1), m.group(2)
    vb = re.search(r'viewBox="([^"]+)"', attrs)
    vb = vb.group(1) if vb else "0 0 %s %s" % (re.search(r'width="([\d.]+)"', attrs).group(1),
                                               re.search(r'height="([\d.]+)"', attrs).group(1))
    rf = re.search(r'fill="([^"]+)"', attrs)     # expo and payload carry their colour on the root tag
    fill = rf.group(1) if rf else (FG if cream else None)
    p = f"n{i}_"
    for pat, rep in ((r'id="([^"]+)"', lambda m: f'id="{p}{m.group(1)}"'),
                     (r"url\(#([^)]+)\)", lambda m: f"url(#{p}{m.group(1)})"),
                     (r'(xlink:href|href)="#([^"]+)"', lambda m: f'{m.group(1)}="#{p}{m.group(2)}"'),
                     (r"\.st(\d+)", lambda m: f".{p}st{m.group(1)}"),
                     (r'class="st(\d+)"', lambda m: f'class="{p}st{m.group(1)}"')):
        inner = re.sub(pat, rep, inner)
    return vb, inner, fill

def logo(x, y, w, color):
    """public/logo/nualt.svg (249 × 75) of the site, in one colour."""
    vb, inner, _ = inline_svg("assets/logo.svg", "logo")
    inner = inner.replace("fill:rgb(7,85,181)", f"fill:{color}")
    return f'<svg x="{x}" y="{y}" width="{w}" height="{w * 75 / 249:.1f}" viewBox="{vb}">{inner}</svg>'

# Block rows of the site footer (TetrisBorder): each block fills 95 % of its cell, ivory on blue.
BLOCKS = ["110001110011000111", "100111100010110001", "111001001110011100"]

def blocks(y, cols, cell, rows=BLOCKS):
    out = []
    for r, row in enumerate(rows):
        row = (row * 3)[:cols]
        for c, on in enumerate(row):
            if on == "1":
                out.append(f'<rect x="{c * cell + cell * 0.025:.1f}" y="{y + r * cell + cell * 0.025:.1f}" '
                           f'width="{cell * 0.95:.1f}" height="{cell * 0.95:.1f}" fill="{IVORY}"/>')
    return "".join(out)

# ------------------------------------------------------------------ header / footer
def build_header(path="assets/header.svg", cell=40, PAD=48, LOGO=360):
    w = W + 200
    H = 3 * cell + 2 * PAD + LOGO * 75 / 249
    write(path, [card(w, H, "nualt", fill=BLUE),
                 blocks(0, w // cell, cell),
                 logo(PAD, H - PAD - LOGO * 75 / 249, LOGO, IVORY)])

def build_footer(path="assets/footer.svg", cell=40):
    write(path, [card(W + 200, 3 * cell, "", fill=BLUE),
                 blocks(0, (W + 200) // cell, cell, BLOCKS[::-1])])

# --------------------------------------------------------------------------- headline
def build_headline(path="assets/headline.svg", size=H1, slot=4000):
    """Typewriter, h1 of the page. A growing <path> that the text rides with <textPath>: the glyphs
    that fit on the path are drawn. Same mechanism as readme-typing-svg, it runs inside an <img>."""
    H = 120
    out = [card(W, H, HEADLINE[0], styles=("title",))]
    last = f"d{len(HEADLINE) - 1}"
    for i, line in enumerate(HEADLINE):
        real = HEADLINE_PX.get(line, width(line, size, "title") * 1.08) * size / 44
        tw = real * 1.04                                # a little slack so the last glyph always lands
        x0, y = (W - real) / 2, H / 2 + size * 0.34
        begin = f"0s;{last}.end" if i == 0 else f"d{i - 1}.end"
        out.append(f"<path id='p{i}'><animate id='d{i}' attributeName='d' begin='{begin}' dur='{slot}ms' "
                   f"fill='remove' keyTimes='0;0.45;0.85;1' values='m{x0:.1f},{y:.1f} h0 ; "
                   f"m{x0:.1f},{y:.1f} h{tw:.1f} ; m{x0:.1f},{y:.1f} h{tw:.1f} ; m{x0:.1f},{y:.1f} h0'/></path>"
                   f"<text font-family=\"{TITLE}\" font-weight='300' font-size='{size}' fill='{FG}'>"
                   f"<textPath xlink:href='#p{i}'>{esc(line)}</textPath></text>")
    write(path, out)

# ------------------------------------------------------------------- section titles
def build_titles(H=72, PAD=24):
    for slug, label in SECTIONS:
        write(f"assets/title-{slug}.svg",
              [card(W, H, label, styles=("title",)),
               text(PAD, H - 24, label, H2, "title"),
               f'<rect x="0" y="{H - 1}" width="{W}" height="1" fill="{LINE}"/>'])

# ------------------------------------------------------------------------------ about
def build_about(path="assets/about.svg", PAD=30):
    size, lead = TXT, 26
    body = []
    for para in ABOUT["body"]:
        body += wrap(para, W - 2 * PAD - 60, size) if para else [""]
    top = PAD + 18                                     # baseline of the name
    y0 = top + 60                                      # first body line
    rule = y0 + len(body) * lead - 8
    H = rule + 66 + PAD - 10
    out = [card(W, H, "about", styles=("title", "body", "label")),
           text(PAD, top, ABOUT["name"], H3, "title"),
           text(PAD, top + 26, ABOUT["role"], TXT, "body", MUTED)]
    y = y0
    for line in body:
        if line:
            out.append(text(PAD, y, line, size, "body"))
        y += lead
    out.append(f'<rect x="{PAD}" y="{rule}" width="{W - 2 * PAD}" height="1" fill="{LINE}"/>')
    x = PAD
    for k, v in ABOUT["facts"]:
        out += [text(x, rule + 28, k, LBL, "label", MUTED), text(x, rule + 52, v, TXT, "body")]
        x += (W - 2 * PAD) / len(ABOUT["facts"])
    write(path, out)

# ------------------------------------------------------------------- project / posts
def repo_facts(r):
    """Topics, install command and facts (npm version, last push, licence), as nualt.fr/open-source shows them."""
    slug = r["url"].split("github.com/")[1]
    g = json.loads(subprocess.run(["gh", "api", f"repos/{slug}"], capture_output=True, text=True, check=True).stdout)
    version = None
    if r.get("npm"):
        with urllib.request.urlopen(f"https://registry.npmjs.org/{r['npm']}/latest") as res:
            version = json.load(res).get("version")
    topics = g.get("topics", [])
    if r.get("npm"):
        command = f"npm i {r['npm']}"
    elif {"claude-code-plugin", "agent-skills"} & set(topics):
        command = f"npx skills add {slug}"
    else:
        command = f"git clone {r['url']}"
    pushed = datetime.date.fromisoformat(g["pushed_at"][:10])
    licence = (g.get("license") or {}).get("spdx_id")
    facts = [f"v{version}" if version else None, f"{pushed:%b} {pushed.day}, {pushed.year}",
             licence if licence != "NOASSERTION" else None]
    return topics, command, [f for f in facts if f]

def iso_icon(name, x, y, size):
    """Isometric icon of the site, original variant: ivory faces, blue lines and hatching."""
    vb, inner, _ = inline_svg(f"assets/iso/nualt-{name}.svg", name)
    inner = inner.replace("var(--blue)", IVORY).replace("currentColor", BLUE)
    hatch = 0.25 if "betterauth" in name else 0.5
    return (f'<style>pattern path{{stroke-width:{hatch}}}</style>'
            f'<svg x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" viewBox="{vb}" fill="none" '
            f'stroke-linejoin="round" stroke-linecap="round" overflow="visible">{inner}</svg>')

def build_repo_cards(PAD=24, THUMB=128, ICON=88, CMD=48, DESC=15, LEAD=22):
    """Card of the open-source catalogue: icon cell on the left, topics, name, description, facts,
    then the install command in its own cell across the card."""
    x0 = THUMB + PAD
    tw = HALF - x0 - PAD
    rows = max(len(wrap(r["desc"], tw, DESC)) for r in REPOS)   # same height across a row of the table
    name_y = PAD + 50
    desc_y = name_y + 34
    facts_y = desc_y + (rows - 1) * LEAD + 40
    box = facts_y + PAD
    H = box + CMD
    for r in REPOS:
        topics, command, facts = repo_facts(r)
        shown = []
        for t in topics:                                         # as many topics as fit on one line
            if width(" · ".join(shown + [t]), LBL, "label") > tw:
                break
            shown.append(t)
        out = [card(HALF, H, r["name"], styles=("title", "body", "label", "code"), stroke=LINE),
               f'<rect x="{THUMB}" y="0" width="1" height="{box}" fill="{LINE}"/>',
               f'<rect x="0" y="{box}" width="{HALF}" height="1" fill="{LINE}"/>',
               iso_icon(r["icon"], (THUMB - ICON) / 2, (box - ICON) / 2, ICON),
               text(x0, PAD + 14, " · ".join(shown), LBL, "label"),
               text(x0, name_y, r["name"], H3, "title")]
        y = desc_y
        for line in wrap(r["desc"], tw, DESC):
            out.append(text(x0, y, line, DESC, "body")); y += LEAD
        x = x0
        for f in facts:
            out.append(text(x, facts_y, f, LBL, "label", MUTED))
            x += width(f, LBL, "label") + 16
        out.append(text(16, box + CMD / 2 + 5, command, LBL, "code"))
        write(f"assets/repo-{r['name']}.svg", out)

def build_post_cards(PAD=24):
    for i, (title, slug) in enumerate(POSTS):
        lines = wrap(title, HALF - 2 * PAD - 30, TXT)
        H = PAD + max(2, len(lines)) * 24 + PAD - 4      # same height across a row of the table
        out = [card(HALF, H, title, styles=("body",), stroke=LINE)]
        y = PAD + 16
        for line in lines:
            out.append(text(PAD, y, line, TXT, "body")); y += 24
        out.append(text(HALF - PAD, PAD + 16, "→", TXT, "body", MUTED, "end"))
        write(f"assets/post-{i}.svg", out)
    write("assets/post-all.svg",
          [card(W, 68, "Tous les articles", styles=("body",), stroke=LINE),
           text(30, 41, "Tous les articles sur nualt.fr/blog", TXT, "body"),
           text(W - 30, 41, "→", TXT, "body", MUTED, "end")])

# ------------------------------------------------------------------------------ links
def build_links(H=68, gap=14):
    w = (W - (len(LINKS) - 1) * gap) / len(LINKS)
    for i, (label, url) in enumerate(LINKS):
        write(f"assets/link-{i}.svg",
              [card(round(w), H, label, styles=("body",), stroke=LINE),
               text(w / 2, H / 2 + 6, label, TXT, "body", FG, "middle")])

# ------------------------------------------------------------------------------ stack
def build_stack(path="assets/stack.svg", tile=64, gap=14):
    n = len(ICONS)
    size = round(tile * 0.62)
    x0 = (W - (n * tile + (n - 1) * gap)) / 2
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{W}" height="{tile}" viewBox="0 0 {W} {tile}" role="img" aria-label="stack">']
    for i, name in enumerate(ICONS):
        vb, inner, fill = inline_svg(f"assets/icons/{name}.svg", i, name in ICONS_CREAM)
        if name in ICONS_WHITE:
            inner = re.sub(r"#fff(fff)?\b", "#000000", inner, flags=re.I)
            fill = "#000000" if fill and fill.lower() in ("#fff", "#ffffff") else fill
        x = x0 + i * (tile + gap)
        f = f' fill="{fill}"' if fill else ""
        out.append(f'<rect x="{x:.1f}" y="0" width="{tile}" height="{tile}" fill="{BG}" stroke="{LINE}"/>'
                   f'<svg x="{x + (tile - size) / 2:.1f}" y="{(tile - size) / 2:.1f}" width="{size}" '
                   f'height="{size}" viewBox="{vb}" preserveAspectRatio="xMidYMid meet"{f} '
                   f'overflow="visible">{inner}</svg>')
    write(path, out)

# ------------------------------------------------------------------------- GitHub data
def fetch():
    q = """
    { user(login: "%s") {
        followers { totalCount }
        contributionsCollection {
          totalCommitContributions totalPullRequestContributions
          totalIssueContributions totalPullRequestReviewContributions
          contributionCalendar { totalContributions
            weeks { contributionDays { date weekday contributionCount } } } }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          totalCount
          nodes { stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name color } } } } } } }
    """ % USER
    r = subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"gh api failed: {r.stderr.strip()}")
    return json.loads(r.stdout)["data"]["user"]

def build_contributions(cal, path="assets/contributions.svg", gap=3, pad=30, top=34):
    weeks = cal["weeks"]
    cell = (W - 2 * pad - (len(weeks) - 1) * gap) / len(weeks)
    H = top + 7 * (cell + gap) - gap + pad + 24
    total = cal["totalContributions"]
    out = [card(W, H, f"{total} contributions in the last year", styles=("label",))]
    seen = set()
    for wi, wk in enumerate(weeks):
        x = pad + wi * (cell + gap)
        for day in wk["contributionDays"]:
            n = day["contributionCount"]
            out.append(f'<rect x="{x:.2f}" y="{top + day["weekday"] * (cell + gap):.2f}" '
                       f'width="{cell:.2f}" height="{cell:.2f}" rx="3" '
                       f'fill="{EMPTY if n == 0 else RAMP[min(3, (n - 1) // 3)]}"/>')
        first = datetime.date.fromisoformat(wk["contributionDays"][0]["date"])
        if first.month not in seen and first.day <= 7:
            seen.add(first.month)
            out.append(text(x, top - 11, first.strftime("%b"), LBL, "label", MUTED))
    out.append(text(pad, H - 12, f"{total} contributions in the last year", LBL, "label", MUTED))
    write(path, out)

def streaks(cal):
    days = [d for wk in cal["weeks"] for d in wk["contributionDays"]
            if d["date"] <= datetime.date.today().isoformat()]
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"]:
            current += 1
        elif i:                                   # an empty today does not break the streak yet
            break
    return current, longest

def build_activity(user, path="assets/activity.svg", pad=30, gut=48, top=8):
    c = user["contributionsCollection"]
    cal = c["contributionCalendar"]
    cur, lng = streaks(cal)
    rows = [("Contributions", f'{cal["totalContributions"]:,}'.replace(",", " ")),
            ("Commits", c["totalCommitContributions"]),
            ("Pull requests", c["totalPullRequestContributions"]),
            ("Reviews", c["totalPullRequestReviewContributions"]),
            ("Issues", c["totalIssueContributions"]),
            ("Repositories", user["repositories"]["totalCount"]),
            ("Stars", sum(r["stargazerCount"] for r in user["repositories"]["nodes"])),
            ("Followers", user["followers"]["totalCount"])]
    rows = [r for r in rows if str(r[1]) != "0"]
    agg = {}
    for repo in user["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            agg.setdefault(e["node"]["name"], [0, e["node"]["color"] or MUTED])[0] += e["size"]
    grand = sum(v[0] for v in agg.values()) or 1
    ranked = [kv for kv in sorted(agg.items(), key=lambda kv: -kv[1][0])[:top] if kv[1][0] / grand >= 0.005]
    shown = sum(v[0] for _, v in ranked) or 1

    colw = (W - 2 * pad - gut) / 2
    rx = pad + colw + gut
    lead = 28
    H = max(pad + 60 + len(rows) * lead + 30, pad + 100 + ((len(ranked) + 1) // 2) * 30 + 24)
    out = [card(W, H, "GitHub activity", styles=("title", "body", "label")),
           f'<rect x="{rx - gut / 2:.1f}" y="{pad}" width="1" height="{H - 2 * pad}" fill="{LINE}"/>',
           text(pad, pad + 16, "GitHub stats", H3, "title"),
           text(rx, pad + 16, "Most used languages", H3, "title")]
    y = pad + 60
    for label, value in rows:
        out += [text(pad, y, label, TXT, "body", MUTED), text(pad + colw, y, value, TXT, "body", FG, "end")]
        y += lead
    out += [text(pad, H - pad + 6, f"current streak {cur} d", LBL, "label", MUTED),
            text(pad + colw, H - pad + 6, f"longest {lng} d", LBL, "label", MUTED, "end")]
    by, bh = pad + 46, 14
    out.append(f'<clipPath id="bar"><rect x="{rx}" y="{by}" width="{colw}" height="{bh}" rx="7"/></clipPath>')
    x = rx
    for name, (size, color) in ranked:
        w = colw * size / shown
        out.append(f'<rect x="{x:.2f}" y="{by}" width="{w:.2f}" height="{bh}" fill="{color}" clip-path="url(#bar)"/>')
        x += w
    ly = by + bh + 38
    for i, (name, (size, color)) in enumerate(ranked):
        cx = rx + (i % 2) * (colw / 2)
        cy = ly + (i // 2) * 30
        out += [f'<circle cx="{cx + 6:.1f}" cy="{cy - 5:.1f}" r="6" fill="{color}"/>',
                text(cx + 22, cy, name, TXT, "body"),
                text(cx + colw / 2 - 20, cy, f"{100 * size / shown:.1f}%", TXT, "body", MUTED, "end")]
    write(path, out)

if __name__ == "__main__":
    build_header(); build_footer(); build_headline(); build_titles(); build_about()
    build_repo_cards(); build_post_cards(); build_links(); build_stack()
    u = fetch()
    build_contributions(u["contributionsCollection"]["contributionCalendar"])
    build_activity(u)
    print("assets built")
