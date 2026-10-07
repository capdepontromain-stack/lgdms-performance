#!/usr/bin/env python3
"""
publier-article.py : génère un article du blog LGDMS Performance à partir d'un fichier .md,
régénère la liste du blog, le bloc « Conseils auto » de l'accueil, le sitemap et le flux RSS.

Usage :
  python3 outils/publier-article.py outils/articles/mon-article.md            # génère seulement
  python3 outils/publier-article.py outils/articles/mon-article.md --publier  # + git push + vérif HTTP 200
  python3 outils/publier-article.py --regenerer [--publier]                   # régénère tout depuis outils/articles.json

Format du .md (en-tête puis corps) :
---
titre: Voyant moteur allumé : que faire ?
description: meta description, 158 caractères maximum
slug: voyant-moteur-allume-que-faire
date: 2026-10-07
image: diagnostic-electronique-valise-obd-reunion.jpg   (fichier dans /photos/)
alt: Diagnostic électronique avec une valise OBD
---
Corps en Markdown simple : ## titres, ### sous-titres, paragraphes, listes « - », **gras**, [liens](url).
Un premier paragraphe commençant par « **En bref.** » devient l'encadré « En bref » (réponse directe reprise par les IA).
Une section « ## Questions fréquentes » avec des paragraphes « **Question ?** Réponse. » produit un schéma FAQPage.

Règles vérifiées avant écriture : pas de tiret cadratin, meta <= 158, titre <= 70, slug unique, pas de montant en euros,
pas de conseil dangereux évident (le script ne vérifie que la forme : le fond reste à relire).

Quand le domaine définitif sera acheté : changer SITE ci-dessous puis lancer --regenerer --publier.
"""
import json, re, sys, subprocess, html, datetime, pathlib, urllib.request

RACINE = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://capdepontromain-stack.github.io/lgdms-performance"   # sans barre finale
REG = RACINE / "outils" / "articles.json"
TEL_AFF, TEL_LIEN, WA = "06 92 72 34 00", "+262692723400", "https://wa.me/262692723400"
MAIL = "damis97K@icloud.com"
NOM_BLOG = "Conseils auto LGDMS Performance"

ICONE_TEL = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25c1.1.37 2.3.57 3.6.57a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1L6.6 10.8z"/></svg>'

HEADER = f"""<header class="topbar">
  <div class="wrap">
    <a class="logo" href="{SITE}/" aria-label="LGDMS Performance, accueil"><img src="{SITE}/logo-lgdms.jpg" alt="LGDMS Performance" width="113" height="52"></a>
    <nav class="nav">
      <a href="{SITE}/#services">Prestations</a>
      <a href="{SITE}/#domicile">À domicile</a>
      <a href="{SITE}/#zone">Zone</a>
      <a class="actif" href="{SITE}/blog/">Conseils</a>
      <a href="{SITE}/#contact">Devis</a>
      <a href="tel:{TEL_LIEN}" class="btn btn-bleu">{ICONE_TEL}{TEL_AFF}</a>
    </nav>
  </div>
</header>
"""

FOOTER = f"""<footer>
  <div class="wrap">
    <img src="{SITE}/logo-lgdms.jpg" alt="LGDMS Performance">
    <nav>
      <a href="{SITE}/#services">Prestations</a>
      <a href="{SITE}/#domicile">À domicile</a>
      <a href="{SITE}/#zone">Zone</a>
      <a href="{SITE}/blog/">Conseils auto</a>
      <a href="{SITE}/#faq">FAQ</a>
      <a href="{SITE}/#contact">Contact</a>
    </nav>
    <div>© {datetime.date.today().year} LGDMS Performance, Anthony Ligdamis. La Saline les Hauts, La Réunion. Plus qu'un garage, une passion. Photos d'illustration.</div>
  </div>
</footer>
<div class="appel-mobile">
  <a class="tel" href="tel:{TEL_LIEN}">{ICONE_TEL}Appeler</a>
  <a class="wa" href="{WA}?text=Bonjour%20Anthony%2C%20je%20souhaite%20un%20devis%20pour%20ma%20voiture." target="_blank" rel="noopener">WhatsApp</a>
</div>
"""

ENCART = f"""<div class="encart">
  <b>Un souci sur votre voiture dans l'Ouest de La Réunion ?</b>
  <p>Anthony vient chez vous ou vous accueille au garage LGDMS à La Saline les Hauts. Devis gratuit avant toute intervention.</p>
  <a class="btn btn-bleu" href="tel:{TEL_LIEN}">{ICONE_TEL}Appeler le {TEL_AFF}</a>
  <a class="btn btn-ghost" href="{WA}" target="_blank" rel="noopener">WhatsApp</a>
</div>
"""

AUTEUR = f"""<div class="auteur"><img src="{SITE}/favicon.png" alt="LGDMS Performance" width="72" height="72"><div><b>Anthony Ligdamis</b><span>Mécanicien à La Saline les Hauts, à domicile dans tout l'Ouest de La Réunion ou au garage LGDMS Performance. <a href="{SITE}/#services">Voir les prestations</a>.</span></div></div>"""

FONTS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Exo+2:ital,wght@0,500;0,700;1,700;1,800;1,900&family=Barlow:wght@400;500;600&display=swap" rel="stylesheet">"""

MOIS = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]

def date_fr(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {MOIS[d.month-1]} {d.year}"

def lire_md(chemin):
    txt = pathlib.Path(chemin).read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", txt, re.S)
    if not m: sys.exit("En-tête --- manquant")
    meta = {}
    for ligne in m.group(1).splitlines():
        if ":" in ligne:
            k, v = ligne.split(":", 1); meta[k.strip()] = v.strip()
    return meta, m.group(2).strip()

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', t)
    return t

def md_vers_html(corps):
    """Markdown minimal -> HTML. Retourne (html, faq[(q,r)], texte_brut)."""
    out, faq, brut = [], [], []
    en_faq, liste, premier = False, None, True
    def fermer_liste():
        nonlocal liste
        if liste: out.append(f"</{liste}>"); liste = None
    for bloc in re.split(r"\n\s*\n", corps):
        bloc = bloc.strip()
        if not bloc: continue
        if bloc.startswith("### "):
            fermer_liste(); out.append(f"<h3>{inline(bloc[4:])}</h3>"); brut.append(bloc[4:]); premier = False; continue
        if bloc.startswith("## "):
            fermer_liste(); titre = bloc[3:]; en_faq = "question" in titre.lower()
            out.append(f"<h2>{inline(titre)}</h2>"); brut.append(titre); premier = False; continue
        if all(l.strip().startswith("- ") for l in bloc.splitlines()):
            fermer_liste(); out.append("<ul>" + "".join(f"<li>{inline(l.strip()[2:])}</li>" for l in bloc.splitlines()) + "</ul>")
            brut.extend(l.strip()[2:] for l in bloc.splitlines()); premier = False; continue
        if re.match(r"^\d+\. ", bloc.splitlines()[0]):
            fermer_liste(); out.append("<ol>" + "".join(f"<li>{inline(re.sub(r'^\d+\. ', '', l.strip()))}</li>" for l in bloc.splitlines()) + "</ol>")
            brut.extend(re.sub(r'^\d+\. ', '', l.strip()) for l in bloc.splitlines()); premier = False; continue
        fermer_liste()
        texte = " ".join(l.strip() for l in bloc.splitlines())
        if premier and texte.startswith("**En bref.**"):
            out.append(f'<div class="en-bref"><b>En bref</b>{inline(texte[len("**En bref.**"):].strip())}</div>'); brut.append(texte); premier = False; continue
        premier = False
        if en_faq:
            m = re.match(r"\*\*(.+?\?)\*\*\s*(.+)", texte)
            if m: faq.append((m.group(1), m.group(2)))
        out.append(f"<p>{inline(texte)}</p>"); brut.append(texte)
    fermer_liste()
    return "\n".join(out), faq, " ".join(brut)

def verifier(meta, corps):
    erreurs = []
    tout = " ".join(meta.values()) + corps
    if "—" in tout or "–" in tout: erreurs.append("tiret cadratin ou demi-cadratin présent")
    if len(meta.get("description","")) > 158: erreurs.append(f"meta trop longue ({len(meta['description'])} > 158)")
    if len(meta.get("titre","")) > 70: erreurs.append(f"titre trop long ({len(meta['titre'])} > 70)")
    for k in ("titre","description","slug","date","image","alt"):
        if not meta.get(k): erreurs.append(f"champ manquant : {k}")
    if re.search(r"\d\s?(€|euros?)\b", tout): erreurs.append("montant en euros : interdit (pas de prix inventé)")
    if not re.fullmatch(r"[a-z0-9-]+", meta.get("slug","")): erreurs.append("slug invalide (a-z, 0-9, tirets)")
    if not (RACINE / "photos" / meta.get("image","")).exists(): erreurs.append(f"image introuvable : photos/{meta.get('image')}")
    if not corps.startswith("**En bref.**"): erreurs.append("l'article doit commencer par un paragraphe « **En bref.** »")
    mots = len(re.findall(r"\w+", corps))
    if mots < 450: erreurs.append(f"article trop court ({mots} mots, minimum 450)")
    if erreurs: sys.exit("REFUSÉ : " + " ; ".join(erreurs))
    return mots

def charger_reg():
    return json.loads(REG.read_text(encoding="utf-8")) if REG.exists() else []

def sauver_reg(reg):
    reg.sort(key=lambda a: a["date"], reverse=True)
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")

def carte(a):
    return (f'<a class="carte-art" href="{SITE}/blog/{a["slug"]}/"><img src="{SITE}/photos/{a["image"]}" alt="{html.escape(a["alt"])}" loading="lazy" width="1400" height="875">'
            f'<div class="txt"><time datetime="{a["date"]}">{date_fr(a["date"])}</time><h3>{html.escape(a["titre"])}</h3><p>{html.escape(a["description"])}</p></div></a>')

def tete(titre, description, canonical, image, og_type="website", date=None):
    extra = f'\n<meta property="article:published_time" content="{date}">' if date else ""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titre)} | LGDMS Performance</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/png" href="{SITE}/favicon.png">
<link rel="alternate" type="application/rss+xml" title="{NOM_BLOG}" href="{SITE}/blog/flux.xml">
<meta name="geo.region" content="FR-974">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="fr_FR">
<meta property="og:title" content="{html.escape(titre)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:image" content="{image}">
<meta property="og:url" content="{canonical}">{extra}
{FONTS}
<link rel="stylesheet" href="{SITE}/blog.css?v=1">"""

def page_article(a, corps_html, faq, reg):
    autres = [x for x in reg if x["slug"] != a["slug"]][:3]
    url = f"{SITE}/blog/{a['slug']}/"
    schema = {"@context":"https://schema.org","@graph":[
        {"@type":"BlogPosting","@id":f"{url}#article","headline":a["titre"],"description":a["description"],
         "datePublished":a["date"],"dateModified":a.get("modifie",a["date"]),"inLanguage":"fr-FR",
         "image":f"{SITE}/photos/{a['image']}","wordCount":a["mots"],
         "author":{"@type":"Person","name":"Anthony Ligdamis","url":f"{SITE}/","jobTitle":"Mécanicien automobile"},
         "publisher":{"@type":"Organization","name":"LGDMS Performance","logo":{"@type":"ImageObject","url":f"{SITE}/logo-lgdms.jpg"}},
         "mainEntityOfPage":url,"about":{"@id":f"{SITE}/#garage"},
         "keywords":"garage, mécanicien à domicile, entretien auto, réparation, pneus, diagnostic, La Saline les Hauts, Saint-Paul, Ouest, La Réunion"},
        {"@type":"BreadcrumbList","itemListElement":[
            {"@type":"ListItem","position":1,"name":"Accueil","item":f"{SITE}/"},
            {"@type":"ListItem","position":2,"name":"Conseils auto","item":f"{SITE}/blog/"},
            {"@type":"ListItem","position":3,"name":a["titre"],"item":url}]}]}
    if faq:
        schema["@graph"].append({"@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":r}} for q,r in faq]})
    lire = ""
    if autres:
        lire = '<section class="lire-aussi"><div class="wrap"><h2 class="chrome">À lire aussi</h2><div class="cartes">' + "".join(carte(x) for x in autres) + '</div></div></section>'
    return tete(a["titre"], a["description"], url, f"{SITE}/photos/{a['image']}", "article", a["date"]) + f"""
<script type="application/ld+json">
{json.dumps(schema, ensure_ascii=False, indent=1)}
</script>
</head>
<body>
{HEADER}
<div class="page-tete">
  <div class="wrap">
    <p class="fil"><a href="{SITE}/">Accueil</a> › <a href="{SITE}/blog/">Conseils auto</a></p>
    <h1 class="chrome">{html.escape(a["titre"])}</h1>
    <p class="meta">Par Anthony, mécanicien à La Saline les Hauts · <time datetime="{a["date"]}">{date_fr(a["date"])}</time> · {a["mots"]} mots</p>
  </div>
</div>
<div class="article-couv"><img src="{SITE}/photos/{a["image"]}" alt="{html.escape(a["alt"])}" width="1400" height="600"></div>

<article class="article">
{corps_html}
{ENCART}
{AUTEUR}
</article>

{lire}
{FOOTER}
</body>
</html>
"""

def page_liste(reg):
    schema = {"@context":"https://schema.org","@type":"Blog","@id":f"{SITE}/blog/#blog","name":NOM_BLOG,
              "description":"Conseils d'entretien, de réparation et de dépannage auto à La Réunion par Anthony Ligdamis, mécanicien à La Saline les Hauts.",
              "url":f"{SITE}/blog/","publisher":{"@id":f"{SITE}/#garage"},
              "blogPost":[{"@type":"BlogPosting","headline":a["titre"],"url":f"{SITE}/blog/{a['slug']}/","datePublished":a["date"]} for a in reg]}
    titre = "Conseils auto : entretien, réparation et dépannage à La Réunion"
    desc = "Entretien, pannes, pneus, diagnostic, préparation : les conseils d'Anthony, mécanicien à domicile et au garage LGDMS Performance à La Saline les Hauts."
    return tete(titre, desc, f"{SITE}/blog/", f"{SITE}/og-image.jpg") + f"""
<script type="application/ld+json">
{json.dumps(schema, ensure_ascii=False, indent=1)}
</script>
</head>
<body>
{HEADER}
<div class="page-tete">
  <div class="wrap">
    <p class="fil"><a href="{SITE}/">Accueil</a> › Conseils auto</p>
    <h1 class="chrome">Conseils auto pour rouler tranquille à La Réunion</h1>
    <p class="meta">Entretien, pannes, pneus, diagnostic, préparation : les réponses d'Anthony, mécanicien à domicile dans l'Ouest et au garage LGDMS Performance à La Saline les Hauts.</p>
  </div>
</div>
<section class="liste">
  <div class="wrap">
    <div class="cartes" style="margin-top:0">
{"".join(carte(a) for a in reg)}
    </div>
  </div>
</section>
{FOOTER}
</body>
</html>
"""

def bloc_accueil(reg):
    if not reg: return ""
    cartes = "".join(carte(a).replace(f'href="{SITE}/blog/', 'href="blog/').replace(f'src="{SITE}/photos/', 'src="photos/') for a in reg[:3])
    return ('<section class="conseils" id="conseils">\n  <div class="conteneur">\n    <div class="rv"><div class="sur">Conseils auto</div>\n    <h2 class="chrome">Les réponses d\'Anthony à vos questions</h2>\n'
            '    <p class="intro">Entretien, pannes, pneus, diagnostic : des conseils de terrain pour rouler tranquille à La Réunion.</p></div>\n    <div class="cartes rv">'
            + cartes + '</div>\n    <p class="rv" style="margin-top:30px"><a class="btn btn-ghost" href="blog/">Tous les conseils auto</a></p>\n  </div>\n</section>')

def ecrire_accueil(reg):
    p = RACINE / "index.html"; s = p.read_text(encoding="utf-8")
    if "<!-- DERNIERS-ARTICLES -->" not in s: sys.exit("Repère <!-- DERNIERS-ARTICLES --> absent de index.html")
    s = re.sub(r"<!-- DERNIERS-ARTICLES -->.*?<!-- /DERNIERS-ARTICLES -->",
               "<!-- DERNIERS-ARTICLES -->\n" + bloc_accueil(reg) + "\n<!-- /DERNIERS-ARTICLES -->", s, flags=re.S)
    p.write_text(s, encoding="utf-8")

def ecrire_sitemap(reg):
    auj = datetime.date.today().isoformat()
    urls = [f"  <url><loc>{SITE}/</loc><lastmod>{auj}</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>",
            f"  <url><loc>{SITE}/blog/</loc><lastmod>{auj}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>"]
    for a in reg:
        urls.append(f"  <url><loc>{SITE}/blog/{a['slug']}/</loc><lastmod>{a.get('modifie',a['date'])}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority>"
                    f"<image:image><image:loc>{SITE}/photos/{a['image']}</image:loc><image:title>{html.escape(a['alt'])}</image:title></image:image></url>")
    (RACINE / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")

def ecrire_rss(reg):
    items = "".join(f"<item><title>{html.escape(a['titre'])}</title><link>{SITE}/blog/{a['slug']}/</link><guid>{SITE}/blog/{a['slug']}/</guid>"
                    f"<pubDate>{datetime.datetime.fromisoformat(a['date']).strftime('%a, %d %b %Y 07:00:00 +0400')}</pubDate><description>{html.escape(a['description'])}</description></item>\n" for a in reg[:30])
    (RACINE / "blog" / "flux.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{NOM_BLOG}</title><link>{SITE}/blog/</link><description>Conseils auto à La Réunion par Anthony Ligdamis, mécanicien à La Saline les Hauts.</description><language>fr</language>\n{items}</channel></rss>\n', encoding="utf-8")

def generer_tout(reg):
    (RACINE / "blog").mkdir(exist_ok=True)
    for a in reg:
        meta, corps = lire_md(RACINE / "outils" / "articles" / f"{a['slug']}.md")
        corps_html, faq, _ = md_vers_html(corps)
        d = RACINE / "blog" / a["slug"]; d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page_article(a, corps_html, faq, reg), encoding="utf-8")
    (RACINE / "blog" / "index.html").write_text(page_liste(reg), encoding="utf-8")
    ecrire_accueil(reg); ecrire_sitemap(reg); ecrire_rss(reg)

def publier(urls):
    sh = lambda c: subprocess.run(c, shell=True, cwd=RACINE, check=True)
    sh('git add -A && git -c user.name="Romain Capdepont" -c user.email="capdepontromain@gmail.com" commit -q -m "Blog : ' + ", ".join(u.rsplit("/",2)[-2] for u in urls) + '\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" || true')
    sh("git push -q origin main")
    import time
    ok = True
    for u in urls + [f"{SITE}/blog/", f"{SITE}/", f"{SITE}/sitemap.xml"]:
        code = 0
        for essai in range(12):           # GitHub Pages met une à deux minutes à publier
            try:
                code = urllib.request.urlopen(urllib.request.Request(u + ("?" if "?" not in u else "&") + f"v={int(time.time())}", headers={"User-Agent":"Mozilla/5.0"}), timeout=20).status
            except Exception as e:
                code = getattr(e, "code", 0)
            if code == 200: break
            time.sleep(10)
        print(f"{'OK ' if code==200 else 'KO '} {code} {u}"); ok = ok and code == 200
    # IndexNow : impossible tant que le site est sous github.io (la clé doit être à la racine du domaine).
    # Quand le domaine .re sera en place : subprocess.run(f"bash ~/seo/indexnow-submit.sh {' '.join(urls + [SITE + '/blog/'])}", shell=True)
    with open(RACINE / "outils" / "urls-a-indexer.txt", "a", encoding="utf-8") as f:
        for u in urls: f.write(u + "\n")
    if not ok: sys.exit("Une URL ne répond pas 200 après publication")

def main():
    args = sys.argv[1:]
    pub = "--publier" in args; args = [a for a in args if a != "--publier"]
    reg = charger_reg(); nouveaux = []
    if "--regenerer" in args:
        generer_tout(reg)
    else:
        for chemin in args:
            meta, corps = lire_md(chemin)
            mots = verifier(meta, corps)
            if any(a["slug"] == meta["slug"] for a in reg) and not meta.get("maj"):
                sys.exit(f"REFUSÉ : slug déjà publié ({meta['slug']}). Ajouter « maj: oui » pour mettre à jour.")
            src = RACINE / "outils" / "articles" / f"{meta['slug']}.md"
            if pathlib.Path(chemin).resolve() != src.resolve(): src.write_text(pathlib.Path(chemin).read_text(encoding="utf-8"), encoding="utf-8")
            entree = {k: meta[k] for k in ("titre","description","slug","date","image","alt")}
            entree["mots"] = mots
            reg = [a for a in reg if a["slug"] != meta["slug"]]
            if meta.get("maj"): entree["modifie"] = datetime.date.today().isoformat()
            reg.append(entree); nouveaux.append(f"{SITE}/blog/{meta['slug']}/")
            print(f"généré : /blog/{meta['slug']}/ ({mots} mots{', FAQ' if md_vers_html(corps)[1] else ''})")
        sauver_reg(reg); reg = charger_reg(); generer_tout(reg)
    if pub: publier(nouveaux or [f"{SITE}/blog/"])

if __name__ == "__main__":
    main()
