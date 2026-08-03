"""
Generate a real page per view, so the browser Back button works.

THE PROBLEM
Every view lived at "/" and switched by hiding sections. Back therefore left the
site entirely -- someone who went Overview -> Register -> Map and pressed Back
landed wherever they had been beforehand, which is a plain defect. Views were also
unlinkable: there was no URL for the register, so nobody could send one.

THE APPROACH
The app is one self-contained file, and it now reads location.pathname and opens the
matching view. So each route only needs that same file present at its own URL:

    /                 overview
    /register/        the register
    /map/             the map
    /sites/           sites
    /methods/         methods and limits

Written as real directories with an index.html rather than relying on a 404
fallback, because GitHub Pages serves 404.html with an HTTP 404 status -- fine for
a human, but it would keep every view but the homepage out of the index while
search indexing is deliberately enabled.

Each copy differs only in <title>, <meta name=description> and <link canonical>, so
each view has its own entry in search results instead of five identical ones. The
sitemap is regenerated to list all five.

Asset references in index.html must be root-absolute (/data.json, /favicon.svg),
or they would resolve against the subdirectory and 404. That is asserted here
rather than assumed.

Run after any edit to site/index.html.

Outputs: site/{register,map,sites,methods}/index.html
         site/sitemap.xml
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), "site")
DOMAIN = "https://speciesblacklist.org"

PAGES = [
    ("", "The Species Black List",
     "A register of vertebrate species that the IUCN Red List records as Data "
     "Deficient or has never assessed, ranked by how narrowly restricted the "
     "published record says they are."),
    ("register", "The Register — The Species Black List",
     "All 2,408 species in the register, searchable and filterable by class, "
     "restriction tier and locality, each with the evidence sentence it was judged on."),
    ("map", "Map — The Species Black List",
     "Density of georeferenced specimen records for Data Deficient and unassessed "
     "vertebrates, layered by restriction tier, with cross-checked locality points."),
    ("sites", "Sites — The Species Black List",
     "Localities holding several Data Deficient or unassessed vertebrates, where one "
     "protected area could cover many species at once."),
    ("methods", "Methods & Limits — The Species Black List",
     "How the ranking is built and validated against IUCN's own reassessments, what "
     "was discarded, and the limits of the register stated plainly."),
]

# Anything the sub-pages load must be root-absolute or it resolves into /register/.
MUST_BE_ABSOLUTE = ["/data.json", "/map.json", "/geo.json", "/favicon.svg",
                    "/tbg-frog.png"]


def main():
    src = os.path.join(SITE, "index.html")
    html = open(src, encoding="utf-8").read()

    missing = [a for a in MUST_BE_ABSOLUTE if a not in html]
    if missing:
        sys.exit(f"ERROR: index.html must reference these as root-absolute paths, "
                 f"or the sub-pages will 404 on them: {missing}")
    # a relative fetch would silently break only on the sub-pages, so refuse it
    for bad in ['fetch("data.json")', 'fetch("map.json")', 'fetch("geo.json")',
                'href="favicon.svg"', 'src="tbg-frog.png"']:
        if bad in html:
            sys.exit(f"ERROR: relative asset reference {bad!r} in index.html")

    for slug, title, desc in PAGES:
        page = html
        page = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", page, count=1,
                      flags=re.S)
        page = re.sub(r'<meta name="description" content=".*?">',
                      f'<meta name="description" content="{desc}">', page, count=1,
                      flags=re.S)
        url = f"{DOMAIN}/{slug + '/' if slug else ''}"
        page = re.sub(r'<link rel="canonical" href=".*?">',
                      f'<link rel="canonical" href="{url}">', page, count=1)
        # og:url should follow the canonical, or a shared sub-page link
        # advertises itself as the homepage
        page = re.sub(r'<meta property="og:url" content=".*?">',
                      f'<meta property="og:url" content="{url}">', page, count=1)
        page = re.sub(r'<meta property="og:title" content=".*?">',
                      f'<meta property="og:title" content="{title}">', page, count=1)

        if slug:
            d = os.path.join(SITE, slug)
            os.makedirs(d, exist_ok=True)
            out = os.path.join(d, "index.html")
        else:
            out = src            # rewrite the root page's own title/canonical too
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(page)
        print(f"  {url:<44} -> {os.path.relpath(out, SITE)}")

    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          "<!-- Generated by scripts/14_build_pages.py; do not hand-edit. -->",
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for slug, _, _ in PAGES:
        url = f"{DOMAIN}/{slug + '/' if slug else ''}"
        sm += ["  <url>", f"    <loc>{url}</loc>",
               "    <changefreq>monthly</changefreq>",
               f"    <priority>{'1.0' if not slug else '0.8'}</priority>", "  </url>"]
    sm.append("</urlset>")
    with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sm) + "\n")
    print(f"\nsitemap.xml lists {len(PAGES)} URLs")


if __name__ == "__main__":
    main()
