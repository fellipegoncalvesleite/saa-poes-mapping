// Shared layout for the main paper and the supplement. Numbers come from generated/values.typ.
#import "generated/values.typ": V

/// Manuscript value by claims-register key (fails loudly on a missing key).
#let val(key) = {
  assert(key in V, message: "missing claims-register key: " + key)
  { let v = V.at(key); if type(v) == str { v.replace("\u{202F}", ",") } else { v } }
}

#let paper(title: "", subtitle: none, author: "", short-title: none, body) = {
  set document(title: title, author: author)
  set page(paper: "a4", margin: (x: 2.2cm, y: 2.3cm), numbering: "1",
    header: context { if counter(page).get().first() > 1 [#set text(8pt, fill: luma(110)); #(if short-title != none { short-title } else { title }) ] })
  set text(font: ("Libertinus Serif", "New Computer Modern"), size: 10.5pt, lang: "en")
  set par(justify: true, leading: 0.62em, first-line-indent: 0em, spacing: 0.95em)
  set heading(numbering: "1.1")
  show heading.where(level: 1): it => { v(0.6em); set text(12.5pt, weight: "bold"); it; v(0.2em) }
  show heading.where(level: 2): it => { v(0.3em); set text(10.8pt, weight: "bold"); it }
  set math.equation(numbering: "(1)")
  show figure.caption: set text(9pt)
  show figure.caption: set align(left)
  set figure(gap: 0.7em)
  show figure: set block(breakable: false)
  show table: set text(8.5pt)
  show link: set text(fill: rgb("#1f5fae"))
  align(center)[
    #text(15pt, weight: "bold")[#title]
    #if subtitle != none { v(0.2em); text(11pt)[#subtitle] }
    #v(0.5em)
    #text(11pt)[#author]
    #v(0.8em)
  ]
  body
}

/// Small helper for tables read from CSV files in tables/.
#let csvtable(path, columns: auto, header-map: (:), size: 7.5pt, keep: none) = {
  let rows = csv(path)
  let head = rows.at(0)
  let idx = if keep == none { range(head.len()) } else { keep.map(k => head.position(h => h == k)) }
  let body = rows.slice(1)
  set text(size)
  table(
    columns: if columns == auto { idx.len() } else { columns },
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
    inset: (x: 3pt, y: 2pt),
    align: (x, y) => if x == 0 { left } else { right },
    table.header(..idx.map(i => strong(header-map.at(head.at(i), default: head.at(i))))),
    ..body.map(r => idx.map(i => r.at(i))).flatten(),
  )
}
